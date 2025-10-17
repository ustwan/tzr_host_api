import os
import gzip
import httpx
from pathlib import Path
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.openapi.utils import get_openapi

app = FastAPI(title="API_MOTHER file aggregator")

# CORS middleware для Swagger UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LOGS_RAW = os.getenv('LOGS_RAW', '/srv/btl/raw')
LOGS_STORE = os.getenv('LOGS_STORE', '/srv/btl/gz')
API4_URL = os.getenv('API4_URL', 'http://api_4:8084')

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version="1.0.0",
        routes=app.routes,
    )
    # Убираем префикс для прямого доступа через localhost:8083
    openapi_schema["servers"] = [{"url": "/"}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi  # type: ignore

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.post("/sync")
def sync_logs():
    """Запускает синхронизацию логов (заглушка для интеграции с btl_syncer)"""
    # В реальности здесь будет команда к btl_syncer через очередь или HTTP
    return {"ok": True, "message": "sync scheduled"}

@app.get("/gz/{path:path}")
def serve_gz(path: str):
    """Отдаёт .gz файл из локального хранилища с учётом шардирования"""
    # Извлекаем battle_id из пути (например: "3777832.tzb" или "75/3777832.tzb")
    filename = Path(path).name
    try:
        battle_id = int(filename.replace('.tzb', ''))
        shard = battle_id // 50000
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid battle_id in path")
    
    # Проверяем с шардированием: /srv/btl/gz/{shard}/{battle_id}.tzb.gz
    gz_path = Path(LOGS_STORE) / str(shard) / f"{battle_id}.tzb.gz"
    
    if not gz_path.exists():
        # Пробуем найти в RAW и сжать на лету
        tzb_path = Path(LOGS_RAW) / str(shard) / f"{battle_id}.tzb"
        if tzb_path.exists():
            try:
                # Создаём директорию для .gz
                gz_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Сжимаем на лету
                import gzip as gzip_module
                with open(tzb_path, 'rb') as f_in:
                    with gzip_module.open(gz_path, 'wb') as f_out:
                        f_out.write(f_in.read())
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Compression failed: {e}")
        else:
            raise HTTPException(status_code=404, detail=f"File not found: {battle_id}.tzb (shard {shard})")
    
    return FileResponse(
        path=str(gz_path),
        media_type='application/gzip',
        filename=f"{battle_id}.tzb.gz"
    )

@app.get("/list")
def list_files():
    """Список доступных файлов"""
    raw_path = Path(LOGS_RAW)
    store_path = Path(LOGS_STORE)
    
    files = []
    if raw_path.exists():
        for tzb_file in raw_path.rglob('*.tzb'):
            rel_path = tzb_file.relative_to(raw_path)
            gz_path = store_path / f"{rel_path}.gz"
            files.append({
                "path": str(rel_path),
                "size": tzb_file.stat().st_size,
                "mtime": tzb_file.stat().st_mtime,
                "compressed": gz_path.exists()
            })
    
    return {"files": files, "count": len(files)}

@app.post("/process/{path:path}")
async def process_file(path: str):
    """Отправляет файл в API 4 для обработки"""
    tzb_path = Path(LOGS_MIRROR) / path
    
    if not tzb_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        async with httpx.AsyncClient() as client:
            # Определяем тип файла и media_type
            if path.endswith('.tzb.gz'):
                media_type = 'application/gzip'
                print(f"🔄 Обрабатываю архив: {path}")
            else:
                media_type = 'application/xml'
                print(f"🔄 Обрабатываю файл: {path}")
            
            # Читаем файл и отправляем в API 4
            with open(tzb_path, 'rb') as f:
                files = {'file': (path, f, media_type)}
                response = await client.post(f"{API4_URL}/battles/upload", files=files)
                
            if response.status_code == 200:
                return {"ok": True, "message": f"File {path} processed successfully", "result": response.json()}
            else:
                return {"ok": False, "message": f"API 4 error: {response.status_code}", "detail": response.text}
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}")

@app.post("/process-batch")
async def process_batch(limit: int = 10, max_parallel: int = 1, delete_after_parse: bool = True):
    """Обрабатывает несколько файлов через API 4 с контролем параллельности
    
    После успешного парсинга:
    - Сжимает файл в .gz
    - Перемещает в /srv/btl/gz
    - Удаляет из /srv/btl/raw
    """
    import asyncio
    import gzip
    import shutil
    import logging
    
    logger = logging.getLogger(__name__)
    raw_path = Path(LOGS_RAW)
    store_path = Path(LOGS_STORE)
    
    if not raw_path.exists():
        raise HTTPException(status_code=404, detail="Raw directory not found")
    
    store_path.mkdir(parents=True, exist_ok=True)
    
    files = list(raw_path.rglob('*.tzb'))[:limit]
    results = []
    
    # Семафор для ограничения параллельности
    semaphore = asyncio.Semaphore(max_parallel)
    
    async def process_file(tzb_file: Path):
        """Обрабатывает один файл с ограничением параллельности"""
        async with semaphore:
            rel_path = tzb_file.relative_to(raw_path)
            try:
                # Парсим через API 4
                async with httpx.AsyncClient(timeout=60.0) as client:
                    with open(tzb_file, 'rb') as f:
                        files_data = {'file': (str(rel_path), f, 'application/xml')}
                        response = await client.post(f"{API4_URL}/battles/upload", files=files_data)
                        
                    result = {
                        "file": str(rel_path),
                        "status": response.status_code,
                        "success": response.status_code == 200,
                    }
                    
                    # Если парсинг успешен
                    if response.status_code == 200:
                        result["result"] = response.json()
                        
                        # Сжимаем и удаляем
                        if delete_after_parse:
                            try:
                                # Путь в gz (сохраняем структуру шардов)
                                gz_path = store_path / f"{rel_path}.gz"
                                gz_path.parent.mkdir(parents=True, exist_ok=True)
                                
                                # Сжимаем
                                with open(tzb_file, 'rb') as f_in:
                                    with gzip.open(gz_path, 'wb', compresslevel=6) as f_out:
                                        shutil.copyfileobj(f_in, f_out)
                                
                                # Удаляем из raw
                                tzb_file.unlink()
                                
                                result["compressed"] = str(gz_path)
                                result["raw_deleted"] = True
                                logger.info(f"✅ {rel_path}: parsed → gz → deleted")
                            except Exception as e:
                                logger.error(f"Ошибка сжатия {rel_path}: {e}")
                                result["compress_error"] = str(e)[:200]
                    else:
                        result["error"] = response.text[:200]
                    
                    return result
            except Exception as e:
                return {
                    "file": str(rel_path),
                    "status": 500,
                    "success": False,
                    "error": str(e)[:200]
                }
    
    # Обрабатываем файлы параллельно
    tasks = [process_file(tzb_file) for tzb_file in files]
    results = await asyncio.gather(*tasks)
    
    successful = sum(1 for r in results if r.get("success"))
    compressed = sum(1 for r in results if r.get("raw_deleted"))
    
    return {
        "processed": len(results), 
        "successful": successful,
        "compressed_to_gz": compressed,
        "results": list(results)
    }

@app.post("/upload/{battle_id}")
async def upload_battle_log(battle_id: int, content: bytes = Body(...)):
    """Принимает лог боя от XML Sync и сохраняет в зеркало"""
    try:
        # Определяем путь по шардированию (battle_id / 50000)
        shard = battle_id // 50000
        shard_dir = Path(LOGS_RAW) / str(shard)
        shard_dir.mkdir(parents=True, exist_ok=True)
        
        # Сохраняем файл
        file_path = shard_dir / f"{battle_id}.tzb"
        with open(file_path, 'wb') as f:
            f.write(content)
        
        return {
            "ok": True,
            "battle_id": battle_id,
            "file_path": str(file_path),
            "size_bytes": len(content),
            "shard": shard
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")
