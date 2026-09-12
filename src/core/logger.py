"""
Application Logger for DigitalBrainEX AI.
Provides unified console and file logging with rotation.
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from src.config import LOGS_DIR

_logger = None

def setup_logger(name: str = "DigitalBrainEX", log_file: str = "app.log", level: int = logging.INFO) -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger

    logger_inst = logging.getLogger(name)
    logger_inst.setLevel(level)

    # Avoid duplicate handlers
    if logger_inst.handlers:
        _logger = logger_inst
        return _logger

    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s:%(filename)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger_inst.addHandler(console_handler)

    # Rotating File Handler (Max 10 MB per file, keep 5 backups)
    log_path = LOGS_DIR / log_file
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger_inst.addHandler(file_handler)

    _logger = logger_inst
    return _logger

logger = setup_logger()
