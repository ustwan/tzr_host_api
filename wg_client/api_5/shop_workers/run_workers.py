"""Запуск всех 3 shop workers"""
import asyncio
import sys
from pathlib import Path

# Добавить app в путь
app_path = Path(__file__).parent.parent
sys.path.insert(0, str(app_path))

from app.config import config
from shop_workers.worker_base import run_worker


async def main():
    """Запустить всех воркеров параллельно"""
    print("=" * 60)
    print("🤖 Shop Workers - Запуск")
    print("=" * 60)
    
    # Получить конфигурацию ботов
    bots = config.get_bots_config()
    
    # Создать задачи для каждого воркера
    tasks = []
    for shop_code, bot_config in bots.items():
        if not bot_config.enabled:
            print(f"⚠ {shop_code.upper()}: отключен в конфигурации")
            continue
        
        if not bot_config.login_key:
            print(f"❌ {shop_code.upper()}: LOGIN_KEY не установлен")
            continue
        
        task = asyncio.create_task(
            run_worker(shop_code, bot_config.login, bot_config.login_key)
        )
        tasks.append(task)
        print(f"✓ {shop_code.upper()}: воркер запланирован")
    
    if not tasks:
        print("❌ Нет активных воркеров")
        return
    
    print("=" * 60)
    print(f"🚀 Запущено {len(tasks)} воркеров")
    print("=" * 60)
    
    # Запустить все воркеры
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        print("\n⚠ Получен сигнал остановки...")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        print("✓ Все воркеры остановлены")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


