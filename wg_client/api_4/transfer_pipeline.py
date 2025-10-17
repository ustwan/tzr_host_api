#!/usr/bin/env python3
"""
Пайплайн переноса TZB файлов:
1. Дедупликация <BATTLE> тегов
2. Проверка на существование в БД (по SHA256)
3. Сжатие pigz
4. Передача в HOST_API
"""
import asyncio
import os
import sys
import hashlib
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional
import httpx

# Добавляем путь к модулям
sys.path.append('/app')

from app.database import BattleDatabase
# Импортируем дедупликацию из example/parser
import sys
sys.path.append('/app/example/parser')
from dedupe_tzb import dedupe_tzb_content


class TransferPipeline:
    def __init__(self, source_dir: str, host_api_url: str = "http://api_mother:8083"):
        self.source_dir = Path(source_dir)
        self.host_api_url = host_api_url
        self.db = BattleDatabase()
        self.processed_count = 0
        self.skipped_count = 0
        self.error_count = 0
        
    async def calculate_sha256(self, content: str) -> str:
        """Вычисление SHA256 хеша"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    async def check_file_exists_in_db(self, sha256: str) -> bool:
        """Проверка существования файла в БД по SHA256"""
        try:
            query = "SELECT id FROM battles WHERE sha256 = $1 LIMIT 1"
            result = await self.db._execute_one(query, sha256)
            return result is not None
        except Exception as e:
            print(f"❌ Ошибка проверки БД: {e}")
            return False
    
    async def check_archive_exists_in_db(self, original_sha256: str) -> bool:
        """Проверка существования архива .tzb.gz в БД по оригинальному SHA256"""
        try:
            # Ищем файл с таким же оригинальным SHA256 (до сжатия)
            query = "SELECT id FROM battles WHERE sha256 = $1 AND storage_key LIKE '%.tzb.gz' LIMIT 1"
            result = await self.db._execute_one(query, original_sha256)
            return result is not None
        except Exception as e:
            print(f"❌ Ошибка проверки архива в БД: {e}")
            return False
    
    async def dedupe_file(self, file_path: Path) -> str:
        """Дедупликация файла - удаление дублированных <BATTLE> тегов"""
        print(f"🔄 Дедупликация: {file_path.name}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Применяем дедупликацию
        deduped_content = dedupe_tzb_content(content)
        
        # Проверяем, была ли дедупликация
        if deduped_content != content:
            print(f"   ✅ Удалены дублированные <BATTLE> теги")
        else:
            print(f"   ℹ️  Дубликаты не найдены")
        
        return deduped_content
    
    async def compress_with_pigz(self, content: str, output_path: Path) -> bool:
        """Сжатие файла с помощью pigz"""
        try:
            print(f"🗜️  Сжатие pigz: {output_path.name}")
            
            # Создаем временный файл
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False) as tmp_file:
                tmp_file.write(content)
                tmp_file_path = tmp_file.name
            
            # Сжимаем с помощью pigz (бинарный режим)
            result = subprocess.run([
                'pigz', '-c', tmp_file_path
            ], capture_output=True)  # Убираем text=True для бинарного режима
            
            if result.returncode == 0:
                # Сохраняем сжатый файл (бинарные данные)
                with open(output_path, 'wb') as f:
                    f.write(result.stdout)
                
                # Удаляем временный файл
                os.unlink(tmp_file_path)
                return True
            else:
                print(f"   ❌ Ошибка pigz: {result.stderr.decode('utf-8', errors='ignore')}")
                os.unlink(tmp_file_path)
                return False
                
        except Exception as e:
            print(f"   ❌ Ошибка сжатия: {e}")
            return False
    
    async def transfer_to_api4(self, file_path: Path) -> bool:
        """Передача файла напрямую в API 4"""
        try:
            print(f"📤 Передача в API 4: {file_path.name}")
            
            # Используем прямой вызов API без HTTP
            from app.loader import BattleLoader
            from app.database import BattleDatabase
            from app.parser import BattleParser
            import gzip
            import tempfile
            
            # Если файл сжат, разархивируем его
            if file_path.suffix == '.gz':
                with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                    content = f.read()
                
                # Создаем временный несжатый файл
                with tempfile.NamedTemporaryFile(mode='w', suffix='.tzb', delete=False, encoding='utf-8') as tmp_file:
                    tmp_file.write(content)
                    tmp_tzb_path = tmp_file.name
            else:
                tmp_tzb_path = str(file_path)
            
            db = BattleDatabase()
            parser = BattleParser()
            loader = BattleLoader(db, parser)
            
            # Обрабатываем файл напрямую
            result = await loader.process_file(tmp_tzb_path)
            
            # Удаляем временный файл если создавали
            if file_path.suffix == '.gz':
                import os
                os.unlink(tmp_tzb_path)
            
            if result and result.get("battle_id"):
                print(f"   ✅ Успешно: Файл {file_path.name} обработан")
                await db.disconnect()
                return True
            else:
                print(f"   ❌ Ошибка обработки: {result}")
                await db.disconnect()
                return False
                    
        except Exception as e:
            print(f"   ❌ Ошибка передачи: {type(e).__name__}: {e}")
            return False
    
    async def process_single_file(self, file_path: Path, temp_dir: Path) -> Dict[str, Any]:
        """Обработка одного файла через весь пайплайн"""
        result = {
            'file': file_path.name,
            'status': 'pending',
            'steps': {},
            'error': None
        }
        
        try:
            # Шаг 1: Дедупликация
            print(f"\n📁 Обработка: {file_path.name}")
            deduped_content = await self.dedupe_file(file_path)
            result['steps']['dedupe'] = 'success'
            
            # Шаг 2: Вычисление SHA256 оригинального файла (до сжатия)
            original_sha256 = await self.calculate_sha256(deduped_content)
            result['original_sha256'] = original_sha256
            result['steps']['sha256'] = 'success'
            
            # Шаг 3: Проверка существования архива .tzb.gz в БД
            archive_exists = await self.check_archive_exists_in_db(original_sha256)
            if archive_exists:
                print(f"   ⏭️  Архив .tzb.gz уже существует в БД, пропускаем")
                result['status'] = 'skipped'
                result['steps']['archive_check'] = 'exists'
                self.skipped_count += 1
                return result
            
            # Шаг 4: Проверка существования несжатого файла в БД
            file_exists = await self.check_file_exists_in_db(original_sha256)
            if file_exists:
                print(f"   🔄 Несжатый файл существует, перезаписываем архивом")
                result['steps']['archive_check'] = 'overwrite'
            else:
                print(f"   ✨ Новый файл, создаем архив")
                result['steps']['archive_check'] = 'new'
            
            # Шаг 5: Сжатие pigz
            compressed_path = temp_dir / f"{file_path.stem}.tzb.gz"
            if not await self.compress_with_pigz(deduped_content, compressed_path):
                result['status'] = 'error'
                result['error'] = 'Compression failed'
                result['steps']['compress'] = 'failed'
                self.error_count += 1
                return result
            
            result['steps']['compress'] = 'success'
            
            # Шаг 6: Вычисление SHA256 сжатого файла
            with open(compressed_path, 'rb') as f:
                compressed_content = f.read()
            compressed_sha256 = hashlib.sha256(compressed_content).hexdigest()
            result['compressed_sha256'] = compressed_sha256
            
            # Шаг 7: Передача в API 4
            if not await self.transfer_to_api4(compressed_path):
                result['status'] = 'error'
                result['error'] = 'Transfer failed'
                result['steps']['transfer'] = 'failed'
                self.error_count += 1
                return result
            
            result['steps']['transfer'] = 'success'
            result['status'] = 'success'
            self.processed_count += 1
            
            # Очищаем временный файл
            compressed_path.unlink()
            
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            self.error_count += 1
        
        return result
    
    async def process_batch(self, files: List[Path], batch_size: int = 10) -> Dict[str, Any]:
        """Обработка батча файлов"""
        results = {
            'total_files': len(files),
            'processed': 0,
            'skipped': 0,
            'errors': 0,
            'details': []
        }
        
        # Создаем временную директорию
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            for i in range(0, len(files), batch_size):
                batch = files[i:i + batch_size]
                print(f"\n🔄 Батч {i//batch_size + 1}: файлы {i+1}-{min(i+batch_size, len(files))}")
                
                for file_path in batch:
                    result = await self.process_single_file(file_path, temp_path)
                    results['details'].append(result)
                    
                    if result['status'] == 'success':
                        results['processed'] += 1
                    elif result['status'] == 'skipped':
                        results['skipped'] += 1
                    else:
                        results['errors'] += 1
        
        return results
    
    async def transfer_mass_data(self, limit: int = 1000) -> Dict[str, Any]:
        """Массовый перенос файлов"""
        print(f"🚀 Начинаю массовый перенос до {limit} файлов...")
        print(f"📁 Источник: {self.source_dir}")
        print(f"🌐 HOST_API: {self.host_api_url}")
        
        # Находим все TZB файлы
        tzb_files = list(self.source_dir.rglob('*.tzb'))[:limit]
        print(f"📊 Найдено {len(tzb_files)} TZB файлов")
        
        if not tzb_files:
            print("❌ TZB файлы не найдены")
            return {'error': 'No TZB files found'}
        
        # Обрабатываем батчами
        results = await self.process_batch(tzb_files, batch_size=5)
        
        print(f"\n📊 Итоговые результаты:")
        print(f"   Всего файлов: {results['total_files']}")
        print(f"   Обработано: {results['processed']}")
        print(f"   Пропущено (уже в БД): {results['skipped']}")
        print(f"   Ошибок: {results['errors']}")
        
        # Показываем ошибки
        errors = [r for r in results['details'] if r['status'] == 'error']
        if errors:
            print(f"\n❌ Ошибки ({len(errors)}):")
            for error in errors[:5]:
                print(f"   {error['file']}: {error['error']}")
            if len(errors) > 5:
                print(f"   ... и еще {len(errors) - 5} ошибок")
        
        return results
    
    async def cleanup(self):
        """Очистка ресурсов"""
        await self.db.disconnect()


async def main():
    if len(sys.argv) < 2:
        print("Usage: transfer_pipeline.py <source_directory> [limit] [host_api_url]")
        print("Example: transfer_pipeline.py /path/to/tzb/files 1000 http://api_mother:8083")
        sys.exit(1)
    
    source_dir = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    host_api_url = sys.argv[3] if len(sys.argv) > 3 else "http://api_mother:8083"
    
    # Устанавливаем переменные окружения
    os.environ.setdefault("DB_MODE", "test")
    
    pipeline = TransferPipeline(source_dir, host_api_url)
    
    try:
        results = await pipeline.transfer_mass_data(limit)
        print(f"\n✅ Перенос завершен: {results}")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)
    finally:
        await pipeline.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
