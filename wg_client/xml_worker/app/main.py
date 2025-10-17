"""
XML Worker - ЭПИЗОДИЧЕСКОЕ соединение (context manager)
Открыть → авторизоваться → забрать батч → закрыть
"""
import os
import socket
import time
import logging
import re
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger("app.main")

# Конфигурация из ENV
WORKER_ID = os.getenv("WORKER_ID", "unknown")
LOGIN_NAME = os.getenv("LOGIN_NAME", "")
LOGIN_KEY = os.getenv("LOGIN_KEY", "")
API_MOTHER_URL = os.getenv("API_MOTHER_URL", "http://host-api-service-api_mother-1:8083")

if not LOGIN_NAME or not LOGIN_KEY:
    raise ValueError("LOGIN_NAME и LOGIN_KEY должны быть установлены!")

logger.info(f"XML Worker {WORKER_ID} запущен с аккаунтом: {LOGIN_NAME}")

app = FastAPI(title=f"XML Worker {WORKER_ID}")


class GameConn:
    """Эпизодическое соединение с игровым сервером: открыть → авторизоваться → забрать батч → закрыть."""
    
    def __init__(self, host: str, port: int, login: str, key: str):
        self.host = host
        self.port = int(port)
        self.login = login
        self.key = key
        self.sock: Optional[socket.socket] = None

    def __enter__(self):
        """Context manager: открываем соединение и авторизуемся."""
        self._connect_and_auth()
        return self

    def __exit__(self, exc_type, exc, tb):
        """Context manager: гарантированно закрываем соединение."""
        self._safe_close()

    def _safe_close(self):
        """Безопасное закрытие сокета."""
        try:
            if self.sock:
                self.sock.close()
                logger.debug("🔌 Соединение закрыто")
        except Exception as e:
            logger.warning(f"Ошибка при закрытии сокета: {e}")
        finally:
            self.sock = None

    def _connect_and_auth(self):
        """Подключение и авторизация."""
        try:
            self.sock = socket.create_connection((self.host, self.port), timeout=10)
            # Ускоряем детект мёртвого соединения
            try:
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            except Exception:
                pass
            
            # Читаем приветствие
            welcome = self.sock.recv(8192)
            logger.debug(f"Приветствие: {welcome[:50]}...")
            
            # Логин
            login_xml = f'<LOGIN v3="10.20.30.40" lang="ru" v2="4875537" v="108" p="{self.key}" l="{self.login}" />\x00'
            self.sock.sendall(login_xml.encode('utf-8'))
            login_response = self.sock.recv(8192)
            
            if b'<ERROR' in login_response:
                raise ConnectionError(f"Ошибка авторизации: {login_response[:100]}")
            
            logger.debug(f"LOGIN OK: {login_response[:50]}...")
            
            # GETME для активации сессии
            self.sock.sendall(b"<GETME />\x00")
            time.sleep(0.2)
            
            # Очищаем буфер от хвостов (MYPARAM и прочего)
            self._drain(0.3)
            
            logger.info(f"✅ Подключено к {self.host}:{self.port} как {self.login}")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения: {e}")
            self._safe_close()
            raise

    def _drain(self, timeout: float = 0.3):
        """Очистка буфера от остатков данных."""
        if not self.sock:
            return
        self.sock.settimeout(timeout)
        drained = 0
        try:
            while True:
                chunk = self.sock.recv(65536)
                if not chunk:
                    break
                drained += len(chunk)
        except socket.timeout:
            pass
        finally:
            self.sock.settimeout(5)
        if drained > 0:
            logger.debug(f"🧹 Очищено {drained} байт из буфера")

    def fetch_one_blook(self, battle_id: int, hard_timeout: float = 20.0) -> Optional[str]:
        """
        Запрашивает один бой и читает до </BLOOK>.
        
        Args:
            battle_id: ID боя
            hard_timeout: Максимальное время ожидания ответа
            
        Returns:
            XML строка или None при ошибке
        """
        if not self.sock:
            logger.error(f"❌ {battle_id}: сокет не инициализирован")
            return None
            
        try:
            # Запрос боя
            self.sock.sendall(f'<POST t="//blook {battle_id}" />\x00'.encode('utf-8'))
            time.sleep(0.05)
            self.sock.sendall(b"<GETMYBATTLE />\x00")
        except OSError as e:
            logger.error(f"❌ {battle_id}: ошибка отправки команды: {e}")
            return None

        # Чтение ответа до </BLOOK>
        buf = b""
        self.sock.settimeout(1.0)
        start_time = time.time()
        
        while time.time() - start_time < hard_timeout:
            try:
                chunk = self.sock.recv(65536)
                if not chunk:
                    # Сервер закрыл соединение
                    logger.warning(f"⚠️ {battle_id}: сервер закрыл соединение")
                    return None
                buf += chunk
                if b"</BLOOK>" in buf:
                    break
                if b"<ERROR" in buf:
                    error_text = buf.decode('utf-8', errors='replace')[:200]
                    logger.warning(f"⚠️ {battle_id}: сервер вернул ERROR: {error_text}")
                    return None
            except socket.timeout:
                # Продолжаем ждать в пределах hard_timeout
                pass

        if b"</BLOOK>" not in buf:
            logger.warning(f"⚠️ {battle_id}: таймаут {hard_timeout}с (получено {len(buf)} байт)")
            return None

        # Декодирование и очистка
        decoded = buf.decode('utf-8', errors='replace')
        decoded = decoded.replace('\x00', '').replace('\x1f', '')
        
        # Извлечение первого полного BLOOK
        start = decoded.find("<BLOOK>")
        end = decoded.find("</BLOOK>", start)
        if start == -1 or end == -1:
            logger.warning(f"⚠️ {battle_id}: некорректный XML (нет BLOOK тегов)")
            return None
        end += len("</BLOOK>")
        blook_xml = decoded[start:end]
        
        # Проверяем что это правильный бой
        match = re.search(r'battleid="(\d+)"', blook_xml)
        if match:
            received_id = int(match.group(1))
            if received_id != battle_id:
                logger.warning(f"⚠️ Запросили {battle_id}, получили {received_id}")
        
        return blook_xml


class FetchResponse(BaseModel):
    battle_id: int
    status: str
    error: Optional[str] = None
    size_bytes: Optional[int] = None
    uploaded_to_mother: bool = False


class BatchFetchRequest(BaseModel):
    battle_ids: List[int]
    semaphore_limit: int = 1
    delay_seconds: float = 0.5
    upload_to_mother: bool = True


class BatchFetchResponse(BaseModel):
    results: List[FetchResponse]
    total: int
    success: int
    failed: int
    timeout: int


@app.get("/health")
async def health():
    """Проверка здоровья"""
    return {
        "status": "healthy",
        "worker_id": WORKER_ID,
        "login": LOGIN_NAME
    }


@app.post("/fetch_batch", response_model=BatchFetchResponse)
async def fetch_battle_batch(request: BatchFetchRequest):
    """
    Получить пачку боёв с ЭПИЗОДИЧЕСКИМ соединением.
    Одно соединение на весь батч: открыть → забрать все → закрыть.
    """
    host = "185.92.72.18"
    port = 5190
    output_dir = "/srv/btl/raw"
    os.makedirs(output_dir, exist_ok=True)
    
    results = []
    saved_files = []
    success_count = 0
    failed_count = 0
    timeout_count = 0
    
    logger.info(f"📦 Batch: {len(request.battle_ids)} боев (эпизодический режим)")
    
    try:
        # ОДНО соединение на весь батч (живёт только пока идёт батч)
        with GameConn(host, port, LOGIN_NAME, LOGIN_KEY) as gc:
            for battle_id in request.battle_ids:
                # Первая попытка
                xml = gc.fetch_one_blook(battle_id, hard_timeout=20.0)
                
                # Ретрай с переподключением при обрыве
                if xml is None:
                    logger.warning(f"🔄 {battle_id}: ретрай с переподключением")
                    gc._safe_close()
                    try:
                        gc._connect_and_auth()
                        xml = gc.fetch_one_blook(battle_id, hard_timeout=20.0)
                    except Exception as e:
                        logger.error(f"❌ {battle_id}: ошибка переподключения: {e}")
                
                # Результат
                if xml is None:
                    results.append(FetchResponse(
                        battle_id=battle_id,
                        status="failed",
                        error="connection closed or timeout after retry"
                    ))
                    failed_count += 1
                else:
                    # Сохраняем файл
                    shard = battle_id // 50000
                    shard_dir = os.path.join(output_dir, str(shard))
                    os.makedirs(shard_dir, exist_ok=True)
                    file_path = os.path.join(shard_dir, f"{battle_id}.tzb")
                    
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(xml)
                    
                    size_kb = len(xml) / 1024
                    logger.info(f"✓ {battle_id}.tzb ({size_kb:.1f} KB)")
                    
                    results.append(FetchResponse(
                        battle_id=battle_id,
                        status="success",
                        size_bytes=len(xml)
                    ))
                    saved_files.append(file_path)
                    success_count += 1
                
                # Пауза между боями
                if request.delay_seconds > 0:
                    time.sleep(request.delay_seconds)
        
        # ← Здесь сокет уже закрыт (вышли из with)
        
    except Exception as e:
        # Глобальная ошибка - остальные бои помечаем как failed
        logger.error(f"❌ Глобальная ошибка батча: {e}")
        for bid in request.battle_ids[len(results):]:
            results.append(FetchResponse(
                battle_id=bid,
                status="failed",
                error=f"batch error: {str(e)[:100]}"
            ))
            failed_count += 1
    
    logger.info(f"📊 Результат: {success_count} успешно, {failed_count} ошибок, {timeout_count} таймаутов")
    
    # Upload в mother (опционально)
    uploaded_count = 0
    if request.upload_to_mother and saved_files:
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            for file_path in saved_files:
                try:
                    battle_id = int(os.path.basename(file_path).split(".")[0])
                    
                    with open(file_path, "r", encoding="utf-8") as f:
                        xml_content = f.read()
                    
                    response = await http_client.post(
                        f"{API_MOTHER_URL}/upload/{battle_id}",
                        content=xml_content,
                        headers={"Content-Type": "application/xml"}
                    )
                    
                    if response.status_code == 200:
                        uploaded_count += 1
                        for res in results:
                            if res.battle_id == battle_id:
                                res.uploaded_to_mother = True
                                break
                except Exception as e:
                    logger.warning(f"upload failed for {file_path}: {e}")
        
        logger.info(f"📤 Загружено в mother: {uploaded_count}/{success_count}")
    
    return BatchFetchResponse(
        results=results,
        total=len(request.battle_ids),
        success=success_count,
        failed=failed_count,
        timeout=timeout_count
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "9000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
