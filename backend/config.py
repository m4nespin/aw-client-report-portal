from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = f"sqlite:///{BASE_DIR / 'dev.db'}"
REPORT_STORAGE_DIR = BASE_DIR / "generated_reports"
REPORT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
