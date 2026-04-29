"""Configuración centralizada del logger con rotación de archivos."""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger(name: str = "innotech_videotutor") -> logging.Logger:
    """Configura y retorna el logger de la aplicación."""
    from app.config import LOGS_DIR

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(module)s.%(funcName)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    log_file = LOGS_DIR / "innotech_videotutor.log"
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    if not getattr(sys, "frozen", False):
        try:
            from rich.logging import RichHandler
            rich_handler = RichHandler(rich_tracebacks=True, show_path=False)
            rich_handler.setLevel(logging.DEBUG)
            logger.addHandler(rich_handler)
        except ImportError:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(fmt)
            console_handler.setLevel(logging.DEBUG)
            logger.addHandler(console_handler)

    return logger


def get_logger(module_name: str = "innotech_videotutor") -> logging.Logger:
    """Obtiene el logger ya configurado."""
    return logging.getLogger(module_name)
