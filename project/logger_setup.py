import logging
from logging.handlers import RotatingFileHandler

from config import settings


def get_logger(name: str = "portal") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        settings.log_dir / "portal.log",
        maxBytes=1_000_000, backupCount=3, encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    )
    logger.addHandler(handler)
    return logger