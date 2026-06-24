import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = Path(os.getenv("APP_DATA_DIR", BASE_DIR)).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'dev.db'}")
REPORT_STORAGE_DIR = Path(os.getenv("REPORT_STORAGE_DIR", DATA_DIR / "generated_reports")).resolve()
REPORT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
FRONTEND_DIST_DIR = BASE_DIR / "frontend" / "dist"
