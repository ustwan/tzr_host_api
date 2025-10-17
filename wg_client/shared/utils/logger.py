import logging
import os


def setup_logger(name: str) -> logging.Logger:
    level_name = os.getenv("LOG_LEVEL", os.getenv("LOGLEVEL", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    return logging.getLogger(name)



