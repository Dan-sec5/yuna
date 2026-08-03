"""
core/logger.py — Sistema de logging centralizado de Yuna
"""
import logging
import logging.handlers
import os
from pathlib import Path
from config import get

# Ruta de logs
LOG_DIR = Path(get("paths.logs", "~/yuna/logs/")).expanduser()
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "yuna.log"

# Formato
FORMATO = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
FORMATO_CONSOLA = "%(levelname)-8s | %(name)s | %(message)s"

def get_logger(nombre: str) -> logging.Logger:
    """Retorna un logger configurado para el módulo dado."""
    logger = logging.getLogger(nombre)

    if logger.handlers:
        return logger  # Ya configurado

    logger.setLevel(logging.DEBUG)

    # Handler archivo — rota cada 1MB, guarda 5 backups
    fh = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(FORMATO))

    # Handler consola — solo WARNING y superior
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    ch.setFormatter(logging.Formatter(FORMATO_CONSOLA))

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger

# Logger raíz de Yuna
log = get_logger("yuna")
