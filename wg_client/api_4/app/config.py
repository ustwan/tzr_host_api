"""
Конфигурация API 4 - настройки по умолчанию
"""
import os
from typing import Literal


class AppConfig:
    """Основная конфигурация приложения"""
    
    # Режим синхронизации логов
    # "xml" - загрузка через XML Workers (по умолчанию, рекомендуется)
    # "file" - загрузка через POST /battles/upload
    # "both" - оба режима доступны
    SYNC_MODE: Literal["xml", "file", "both"] = os.getenv("SYNC_MODE", "xml")
    
    # Автоматический XML sync при старте
    ENABLE_XML_SYNC_ON_START: bool = os.getenv("ENABLE_XML_SYNC_ON_START", "true").lower() == "true"
    
    # Размер батча для auto-continue XML sync
    XML_SYNC_BATCH_SIZE: int = int(os.getenv("XML_SYNC_BATCH_SIZE", "1000"))
    
    # Автоматическое применение миграций при старте
    AUTO_APPLY_MIGRATIONS: bool = os.getenv("AUTO_APPLY_MIGRATIONS", "true").lower() == "true"
    
    # Режим работы (test/prod)
    DB_MODE: str = os.getenv("DB_MODE", "test")
    
    # Интервал auto-continue XML sync (в секундах, 0 = отключен)
    XML_SYNC_INTERVAL: int = int(os.getenv("XML_SYNC_INTERVAL", "0"))
    
    @classmethod
    def is_xml_mode(cls) -> bool:
        """Проверка что XML sync включён"""
        return cls.SYNC_MODE in ("xml", "both")
    
    @classmethod
    def is_file_mode(cls) -> bool:
        """Проверка что file upload включён"""
        return cls.SYNC_MODE in ("file", "both")
    
    @classmethod
    def get_config_summary(cls) -> dict:
        """Получить сводку конфигурации"""
        return {
            "sync_mode": cls.SYNC_MODE,
            "xml_sync_on_start": cls.ENABLE_XML_SYNC_ON_START,
            "xml_batch_size": cls.XML_SYNC_BATCH_SIZE,
            "auto_migrations": cls.AUTO_APPLY_MIGRATIONS,
            "db_mode": cls.DB_MODE,
            "xml_sync_interval": cls.XML_SYNC_INTERVAL
        }




