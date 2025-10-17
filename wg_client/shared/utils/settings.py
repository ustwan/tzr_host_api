import os
from dataclasses import dataclass


@dataclass
class BaseSettings:
    timezone: str = os.getenv("TZ", "Europe/Moscow")
    log_level: str = os.getenv("LOG_LEVEL", os.getenv("LOGLEVEL", "INFO"))
    # API_4 loader settings
    batch_size: int = int(os.getenv("BATCH_SIZE", "100"))
    max_workers: int = int(os.getenv("MAX_WORKERS", "4"))
    retry_attempts: int = int(os.getenv("RETRY_ATTEMPTS", "3"))
    retry_delay: float = float(os.getenv("RETRY_DELAY", "1.0"))



