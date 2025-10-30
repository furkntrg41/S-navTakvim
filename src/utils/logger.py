import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from src.config import LOG_DIR, LOG_FILE


def get_logger(name: str = "exam_scheduler", level=logging.INFO):
    return setup_logger(name, level)


def setup_logger(name: str = "exam_scheduler", level=logging.INFO):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass
    
    file_handler = RotatingFileHandler(
        LOG_FILE, 
        encoding='utf-8',
        maxBytes=5*1024*1024,
        backupCount=5
    )
    file_handler.setLevel(level)
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    
    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    return logger


logger = setup_logger()
