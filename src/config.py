import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "exam_scheduler.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

APP_NAME = "Dinamik Sınav Takvimi Oluşturma Sistemi"
APP_VERSION = "0.1.0"

DEFAULT_EXAM_DURATION = 75
DEFAULT_BREAK_TIME = 15
DEFAULT_WORK_DAYS = [0, 1, 2, 3, 4]

LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "app.log"

TEMPLATES_DIR = BASE_DIR / "templates"

OUTPUT_DIR = BASE_DIR / "output"
