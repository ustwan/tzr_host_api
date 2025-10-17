#!/usr/bin/env python3
import os
import time
import subprocess
from pathlib import Path

LOGS_MIRROR = os.getenv('LOGS_MIRROR', '/srv/btl_mirror')
LOGS_STORE = os.getenv('LOGS_STORE', '/srv/btl_store/gz')
COMPRESS_INTERVAL = int(os.getenv('COMPRESS_INTERVAL', '30'))

def compress_file(src_path, dst_path):
    """Атомарное сжатие файла в .gz"""
    try:
        # Создаём директорию назначения (для шардирования)
        dst_path = Path(dst_path)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Создаём временный файл
        temp_path = f"{dst_path}.tmp"
        
        # Сжимаем во временный файл
        result = subprocess.run(['pigz', '-c', str(src_path)], 
                              stdout=open(temp_path, 'wb'), 
                              stderr=subprocess.PIPE, 
                              check=True)
        
        # Атомарно переименовываем
        os.rename(temp_path, dst_path)
        print(f"Compressed: {src_path} -> {dst_path}")
        return True
    except Exception as e:
        print(f"Compression failed {src_path}: {e}")
        # Удаляем временный файл при ошибке
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        return False

SHARD_DIVISOR = int(os.getenv('SHARD_DIVISOR', '0'))

def find_new_files():
    """Находит новые .tzb файлы для сжатия"""
    mirror_path = Path(LOGS_MIRROR)
    store_path = Path(LOGS_STORE)
    
    if not mirror_path.exists():
        return []
    
    store_path.mkdir(parents=True, exist_ok=True)
    
    new_files = []
    for tzb_file in mirror_path.rglob('*.tzb'):
        # Вычисляем путь в хранилище
        rel_path = tzb_file.relative_to(mirror_path)
        # Опциональное шардирование: ожидаем имя файла как <index>.tzb
        if SHARD_DIVISOR and rel_path.name.endswith('.tzb') and rel_path.name.split('.')[0].isdigit():
            idx = int(rel_path.name.split('.')[0])
            shard = idx // SHARD_DIVISOR
            rel_path = Path(str(rel_path.parent)) / str(shard) / rel_path.name
        gz_path = store_path / f"{rel_path}.gz"
        
        # Проверяем, нужно ли сжимать
        if not gz_path.exists() or tzb_file.stat().st_mtime > gz_path.stat().st_mtime:
            new_files.append((tzb_file, gz_path))
    
    return new_files

def main():
    print(f"Starting btl_compressor: {LOGS_MIRROR} -> {LOGS_STORE}")
    
    while True:
        try:
            new_files = find_new_files()
            if new_files:
                print(f"Found {len(new_files)} files to compress")
                for src, dst in new_files:
                    compress_file(src, dst)
            else:
                print("No new files to compress")
            
            time.sleep(COMPRESS_INTERVAL)
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
