"""
Logger centralizado para o scanner_eventos.
Usa loguru com rotação, níveis e formato estruturado.
"""
import os
import sys
from pathlib import Path
from loguru import logger

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

logger.remove()

logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level=LOG_LEVEL,
    colorize=True,
)

logger.add(
    LOG_DIR / "scanner_{time:YYYY-MM}.log",
    rotation="500 MB",
    retention="30 days",
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
    level=LOG_LEVEL,
    backtrace=True,
    diagnose=True,
)

logger.add(
    LOG_DIR / "error_{time:YYYY-MM-DD}.log",
    rotation="100 MB",
    retention="90 days",
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
    level="ERROR",
    backtrace=True,
    diagnose=True,
)

def get_logger():
    """Retorna a instância do logger."""
    return logger