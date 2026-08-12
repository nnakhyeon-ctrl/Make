from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DOWNLOADS_DIR = DATA_DIR / "downloads"
EXPORTS_DIR = DATA_DIR / "exports"
DB_PATH = DATA_DIR / "gm_orders.db"
COLUMN_MAPPING_PATH = Path(__file__).resolve().parent / "column_mapping.json"

for d in (DOWNLOADS_DIR, EXPORTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

APP_TITLE = "GM 발주 자동화"
SUPPORTED_EXTENSIONS = (".xlsx", ".xls", ".csv", ".htm", ".html")
