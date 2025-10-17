#!/usr/bin/env python3
"""
Скрипт для массовой загрузки TZB файлов с дедупликацией и сжатием
"""
import asyncio
import os
import sys
import gzip
import shutil
from pathlib import Path
from typing import List, Dict, Any

# Добавляем путь к модулям
sys.path.append('/app')

from app.database import BattleDatabase
from app.loader import BattleLoader
from app.parser import BattleParser


class MassLoader:
    def __init__(self, source_dir: str, target_dir: str = "/srv/btl_mirror"):
        self.source_dir = Path(source_dir)
        self.target_dir = Path(target_dir)
        self.db = BattleDatabase()
        self.parser = BattleParser()
        self.loader = BattleLoader(self.db, self.parser)
        
    async def dedupe_and_compress(self, file_path: Path) -> Path:
        """Дедупликация и сжатие файла"""
        # Читаем файл
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Дедупликация (удаляем дублирующиеся <BATTLE> блоки)
        from app.external_parser import dedupe_tzb_content
        deduped_content = dedupe_tzb_content(content)
        
        # Создаем сжатый файл
        compressed_path = self.target_dir / f"{file_path.stem}.tzb.gz"
        with gzip.open(compressed_path, 'wt', encoding='utf-8') as f:
            f.write(deduped_content)
        
        return compressed_path
    
    async def process_batch(self, files: List[Path], batch_size: int = 10) -> Dict[str, Any]:
        """Обработка батча файлов"""
        results = {
            'total_files': len(files),
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        # Создаем целевую директорию
        self.target_dir.mkdir(parents=True, exist_ok=True)
        
        for i in range(0, len(files), batch_size):
            batch = files[i:i + batch_size]
            print(f"🔄 Обрабатываю батч {i//batch_size + 1}: файлы {i+1}-{min(i+batch_size, len(files))}")
            
            for file_path in batch:
                try:
                    # Дедупликация и сжатие
                    compressed_path = await self.dedupe_and_compress(file_path)
                    
                    # Загружаем в базу
                    result = await self.loader.process_file(str(compressed_path))
                    
                    results['processed'] += 1
                    if result.get('status') == 'success':
                        results['successful'] += 1
                        print(f"✅ {file_path.name} -> {compressed_path.name}")
                    else:
                        results['failed'] += 1
                        error_msg = f"Ошибка обработки {file_path.name}: {result.get('error', 'Unknown error')}"
                        results['errors'].append(error_msg)
                        print(f"❌ {file_path.name}: {error_msg}")
                    
                except Exception as e:
                    results['failed'] += 1
                    error_msg = f"Ошибка обработки {file_path.name}: {str(e)}"
                    results['errors'].append(error_msg)
                    print(f"❌ {file_path.name}: {error_msg}")
        
        return results
    
    async def load_mass_data(self, limit: int = 1000) -> Dict[str, Any]:
        """Загрузка большого количества файлов"""
        print(f"🚀 Начинаю массовую загрузку до {limit} файлов...")
        
        # Находим все TZB файлы
        tzb_files = list(self.source_dir.rglob('*.tzb'))[:limit]
        print(f"📁 Найдено {len(tzb_files)} TZB файлов")
        
        if not tzb_files:
            print("❌ TZB файлы не найдены")
            return {'error': 'No TZB files found'}
        
        # Обрабатываем батчами
        results = await self.process_batch(tzb_files, batch_size=10)
        
        print(f"\n📊 Результаты загрузки:")
        print(f"   Всего файлов: {results['total_files']}")
        print(f"   Обработано: {results['processed']}")
        print(f"   Успешно: {results['successful']}")
        print(f"   Ошибок: {results['failed']}")
        
        if results['errors']:
            print(f"\n❌ Ошибки:")
            for error in results['errors'][:5]:  # Показываем первые 5 ошибок
                print(f"   {error}")
            if len(results['errors']) > 5:
                print(f"   ... и еще {len(results['errors']) - 5} ошибок")
        
        return results
    
    async def cleanup(self):
        """Очистка ресурсов"""
        await self.db.disconnect()


async def main():
    if len(sys.argv) < 2:
        print("Usage: mass_load.py <source_directory> [limit]")
        sys.exit(1)
    
    source_dir = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    
    # Устанавливаем переменные окружения
    os.environ.setdefault("DB_MODE", "test")
    
    loader = MassLoader(source_dir)
    
    try:
        results = await loader.load_mass_data(limit)
        print(f"\n✅ Загрузка завершена: {results}")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)
    finally:
        await loader.cleanup()


if __name__ == "__main__":
    asyncio.run(main())









