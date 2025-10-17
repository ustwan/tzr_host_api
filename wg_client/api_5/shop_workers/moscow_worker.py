"""Moscow shop worker - для запуска отдельно"""
import asyncio
import sys
from pathlib import Path

app_path = Path(__file__).parent.parent
sys.path.insert(0, str(app_path))

from app.config import config
from shop_workers.worker_base import run_worker


if __name__ == "__main__":
    bots = config.get_bots_config()
    bot = bots["moscow"]
    
    if not bot.enabled or not bot.login_key:
        print("❌ Moscow worker: не настроен (нужен SOVA_MOSCOW_KEY)")
        sys.exit(1)
    
    try:
        asyncio.run(run_worker("moscow", bot.login, bot.login_key))
    except KeyboardInterrupt:
        pass


