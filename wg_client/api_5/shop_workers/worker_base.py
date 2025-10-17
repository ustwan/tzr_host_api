"""Базовый класс воркера магазина"""
import asyncio
import time
from datetime import datetime
from typing import Optional

from app.config import config
from app.infrastructure.game_socket_client import GameSocketClient
from app.infrastructure.db.database import Database
from app.infrastructure.db.repositories import (
    ShopRepository, ItemTemplateRepository, ShopItemRepository,
    SnapshotRepository, BotSessionRepository
)
from app.usecases.parse_category import ParseCategoryUseCase
from app.usecases.create_snapshot import CreateSnapshotUseCase
from app.domain.entities import BotSession


class ShopWorkerBase:
    """
    Базовый воркер для парсинга магазина
    
    Каждый воркер:
    1. Логинится в игру
    2. Заходит в свой магазин
    3. Парсит категории
    4. Создаёт снимки каждый час
    5. Отправляет keep-alive пинги
    """
    
    def __init__(self, shop_code: str, bot_login: str, bot_login_key: str):
        self.shop_code = shop_code
        self.bot_login = bot_login
        self.bot_login_key = bot_login_key
        
        # Database
        self.db = Database()
        
        # Game client
        self.client = GameSocketClient(
            host=config.GAME_SERVER_HOST,
            port=config.GAME_SERVER_PORT,
            timeout=config.GAME_SERVER_TIMEOUT
        )
        
        # State
        self.running = False
        self.last_snapshot_time: Optional[datetime] = None
        self.last_keepalive_time: Optional[datetime] = None
    
    async def start(self):
        """Запустить воркер"""
        self.running = True
        print(f"🤖 {self.shop_code.upper()} Worker: запущен")
        
        # Аутентификация
        if not await self._authenticate():
            print(f"❌ {self.shop_code.upper()}: не удалось залогиниться")
            return
        
        # Главный цикл
        while self.running:
            try:
                # Keep-alive пинги
                await self._send_keepalive()
                
                # Создание снимка (каждый час)
                await self._create_snapshot_if_needed()
                
                # Пауза
                await asyncio.sleep(10)  # Проверка каждые 10 секунд
                
            except Exception as e:
                print(f"❌ {self.shop_code.upper()}: ошибка в цикле - {e}")
                await asyncio.sleep(config.RECONNECT_DELAY)
                
                # Попытка переподключения
                if not self.client.authenticated:
                    await self._authenticate()
    
    async def stop(self):
        """Остановить воркер"""
        self.running = False
        self.client.disconnect()
        self.db.close()
        print(f"✓ {self.shop_code.upper()} Worker: остановлен")
    
    async def _authenticate(self) -> bool:
        """Аутентификация бота (как в XML Workers)"""
        print(f"🔐 {self.shop_code.upper()}: аутентификация...")
        
        success, result = self.client.authenticate(self.bot_login, self.bot_login_key)
        
        if success:
            # Сохранить сессию в БД
            with self.db.get_session() as session:
                bot_repo = BotSessionRepository(session)
                bot_session = BotSession(
                    bot_login=self.bot_login,
                    shop_code=self.shop_code,
                    session_id=result,
                    authenticated=True,
                    last_activity=datetime.utcnow(),
                    location=f"{self.shop_code}_shop"
                )
                bot_repo.upsert(bot_session)
            
            print(f"✓ {self.shop_code.upper()}: аутентификация успешна")
            return True
        else:
            print(f"❌ {self.shop_code.upper()}: ошибка аутентификации - {result}")
            return False
    
    async def _send_keepalive(self):
        """Отправить keep-alive пинг"""
        now = datetime.utcnow()
        
        if self.last_keepalive_time is None or \
           (now - self.last_keepalive_time).total_seconds() >= config.KEEPALIVE_INTERVAL:
            
            if self.client.ping():
                self.last_keepalive_time = now
                
                # Обновить в БД
                with self.db.get_session() as session:
                    bot_repo = BotSessionRepository(session)
                    bot_session = bot_repo.get_by_shop(self.shop_code)
                    if bot_session:
                        bot_session.last_activity = now
                        bot_repo.upsert(bot_session)
            else:
                print(f"⚠ {self.shop_code.upper()}: ping failed, переподключение...")
                await self._authenticate()
    
    async def _create_snapshot_if_needed(self):
        """Создать снимок если прошёл час"""
        now = datetime.utcnow()
        
        if self.last_snapshot_time is None or \
           (now - self.last_snapshot_time).total_seconds() >= config.SNAPSHOT_INTERVAL:
            
            print(f"📸 {self.shop_code.upper()}: создание снимка...")
            
            try:
                with self.db.get_session() as session:
                    shop_repo = ShopRepository(session)
                    template_repo = ItemTemplateRepository(session)
                    item_repo = ShopItemRepository(session)
                    snapshot_repo = SnapshotRepository(session)
                    
                    # Use cases
                    parse_uc = ParseCategoryUseCase(
                        shop_repo, template_repo, item_repo, self.client
                    )
                    snapshot_uc = CreateSnapshotUseCase(
                        shop_repo, snapshot_repo, item_repo, parse_uc
                    )
                    
                    # Создать снимок
                    snapshot = snapshot_uc.execute(
                        shop_code=self.shop_code,
                        worker_name=f"{self.shop_code}_worker"
                    )
                    
                    self.last_snapshot_time = now
                    print(f"✓ {self.shop_code.upper()}: снимок создан (ID={snapshot.id}, items={snapshot.items_count})")
                    
            except Exception as e:
                print(f"❌ {self.shop_code.upper()}: ошибка создания снимка - {e}")


# Функция для запуска воркера в отдельном процессе/потоке
async def run_worker(shop_code: str, bot_login: str, bot_login_key: str):
    """Запустить воркер"""
    worker = ShopWorkerBase(shop_code, bot_login, bot_login_key)
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        print(f"\n⚠ {shop_code.upper()}: получен сигнал остановки")
    finally:
        await worker.stop()


