"""Конфигурация API 5 (Shop Parser)"""
import os
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class BotConfig:
    """Конфигурация бота-парсера"""
    login: str
    login_key: str  # LOGIN_KEY из XML Workers
    shop_code: str
    shop_name: str
    enabled: bool = True


@dataclass
class DatabaseConfig:
    """Конфигурация БД"""
    host: str
    port: int
    name: str
    user: str
    password: str

    @property
    def dsn(self) -> str:
        """PostgreSQL DSN"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class Config:
    """Главная конфигурация API 5"""

    # Режим работы
    DB_MODE: str = os.getenv("DB_MODE", "test")

    # Игровой сервер (как в XML Workers)
    GAME_SERVER_HOST: str = os.getenv("GAME_SERVER_HOST", "185.92.72.18")
    GAME_SERVER_PORT: int = int(os.getenv("GAME_SERVER_PORT", "5190"))
    GAME_SERVER_TIMEOUT: int = int(os.getenv("GAME_SERVER_TIMEOUT", "20"))

    # Планировщик
    SNAPSHOT_INTERVAL: int = int(os.getenv("SNAPSHOT_INTERVAL", "3600"))  # 1 час
    KEEPALIVE_INTERVAL: int = int(os.getenv("KEEPALIVE_INTERVAL", "30"))   # 30 секунд
    RECONNECT_DELAY: int = int(os.getenv("RECONNECT_DELAY", "5"))          # 5 секунд

    # Парсинг
    PAGE_RETRY_ATTEMPTS: int = int(os.getenv("PAGE_RETRY_ATTEMPTS", "5"))
    PAGE_RETRY_DELAY: float = float(os.getenv("PAGE_RETRY_DELAY", "2.0"))
    GROUP_ITEMS_PER_PAGE: int = 8  # По умолчанию 8 товаров на странице группы

    # Категории магазина (все возможные)
    SHOP_CATEGORIES: List[str] = [
        "k",  # Холодное
        "p",  # Пистолеты
        "v",  # Винтовки/автоматы
        "w",  # Тяжёлое
        "e",  # Энергетическое
        "x",  # Биологическое
        "g",  # Метательное
        "m",  # Боевые устройства
        "a",  # Патроны
        "i",  # Энергомодули
        "h",  # Каски/береты
        "c",  # Куртки/бронежилеты
        "l",  # Нарукавники
        "t",  # Брюки
        "b",  # Обувь
        "f",  # Гражданская
        "q",  # Комплекты брони
        "u",  # Встройки
        "n",  # Улучшение
        "j",  # Оборудование
        "d",  # Медицина
        "s",  # Ресурсы
        "y",  # Крафт-реагенты
        "r",  # Документы
        "z",  # Прочее
        "0",  # Импланты
        "1",  # Мои вещи
    ]

    # Админ токен
    ADMIN_API_TOKEN: str = os.getenv("ADMIN_API_TOKEN", "local_admin_token")

    @classmethod
    def get_db_config(cls) -> DatabaseConfig:
        """Получить конфигурацию БД в зависимости от режима"""
        if cls.DB_MODE == "prod":
            return DatabaseConfig(
                host=os.getenv("DB_API5_PROD_HOST", "localhost"),
                port=int(os.getenv("DB_API5_PROD_PORT", "5432")),
                name=os.getenv("DB_API5_PROD_NAME", "api5_shop"),
                user=os.getenv("DB_API5_PROD_USER", "api5_user"),
                password=os.getenv("DB_API5_PROD_PASSWORD", "api5_pass"),
            )
        else:
            return DatabaseConfig(
                host=os.getenv("DB_API5_TEST_HOST", "api_5_db"),
                port=int(os.getenv("DB_API5_TEST_PORT", "5432")),
                name=os.getenv("DB_API5_TEST_NAME", "api5_shop"),
                user=os.getenv("DB_API5_TEST_USER", "api5_user"),
                password=os.getenv("DB_API5_TEST_PASSWORD", "api5_pass"),
            )

    @classmethod
    def get_bots_config(cls) -> Dict[str, BotConfig]:
        """Получить конфигурацию всех ботов (используем переменные из XML Workers)"""
        return {
            "moscow": BotConfig(
                login=os.getenv("SOVA_MOSCOW_LOGIN", "Sova"),
                login_key=os.getenv("SOVA_MOSCOW_KEY", ""),
                shop_code="moscow",
                shop_name="Moscow",
                enabled=os.getenv("SOVA_MOSCOW_ENABLED", "true").lower() == "true",
            ),
            "oasis": BotConfig(
                login=os.getenv("SOVA_OASIS_LOGIN", "Sova"),
                login_key=os.getenv("SOVA_OASIS_KEY", ""),
                shop_code="oasis",
                shop_name="Oasis",
                enabled=os.getenv("SOVA_OASIS_ENABLED", "true").lower() == "true",
            ),
            "neva": BotConfig(
                login=os.getenv("SOVA_NEVA_LOGIN", "Sova"),
                login_key=os.getenv("SOVA_NEVA_KEY", ""),
                shop_code="neva",
                shop_name="Neva",
                enabled=os.getenv("SOVA_NEVA_ENABLED", "true").lower() == "true",
            ),
        }

    @classmethod
    def validate(cls):
        """Валидация конфигурации"""
        bots = cls.get_bots_config()
        
        # Проверка ключей ботов (предупреждение, не ошибка)
        enabled_bots = 0
        for shop_code, bot_config in bots.items():
            if bot_config.enabled:
                if not bot_config.login_key:
                    print(f"⚠️  WARNING: Bot {shop_code} enabled but LOGIN_KEY not set (SOVA_{shop_code.upper()}_KEY). Bot будет работать в режиме только-чтение API.")
                else:
                    enabled_bots += 1
                    print(f"✓ Bot {shop_code} enabled with key")
        
        # Проверка БД
        db_config = cls.get_db_config()
        if not db_config.password:
            print(f"⚠️  WARNING: Database password not set for {cls.DB_MODE} mode. Using default.")
        
        print(f"✓ Config validated: {cls.DB_MODE} mode, {enabled_bots}/{len(bots)} bots enabled with keys")


# Singleton instance
config = Config()


