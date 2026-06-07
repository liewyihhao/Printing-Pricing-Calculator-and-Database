"""Central configuration, loaded from crawler/.env."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

CRAWLER_DIR = Path(__file__).resolve().parent.parent
load_dotenv(CRAWLER_DIR / ".env")

# Windows consoles default to cp1252 and choke on non-ASCII; force UTF-8.
# Use reconfigure (non-destructive) and skip under pytest, whose capture object
# must not be replaced.
if "pytest" not in sys.modules:  # pragma: no cover - environment dependent
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

# --- Excard ---
USERNAME = os.getenv("EXCARD_USERNAME", "").strip()
PASSWORD = os.getenv("EXCARD_PASSWORD", "").strip()
# Optional extra accounts for parallel crawling (independent server sessions;
# only useful across separate machines — one laptop can't drive multiple browsers).
USERNAME_2 = os.getenv("EXCARD_USERNAME_2", "").strip()
PASSWORD_2 = os.getenv("EXCARD_PASSWORD_2", "").strip()
USERNAME_3 = os.getenv("EXCARD_USERNAME_3", "").strip()
PASSWORD_3 = os.getenv("EXCARD_PASSWORD_3", "").strip()
LOGIN_URL = os.getenv("EXCARD_LOGIN_URL", "https://www.excard.com.my/login").strip()
PRICE_URL = os.getenv("EXCARD_PRICE_URL", "https://www.excard.com.my/price-list/Litho/21").strip()
BASE_URL = "https://www.excard.com.my"

# --- Politeness / timing ---
MIN_DELAY_MS = int(os.getenv("CRAWL_MIN_DELAY_MS", "1500"))
MAX_DELAY_MS = int(os.getenv("CRAWL_MAX_DELAY_MS", "3500"))
GENERATE_TIMEOUT_MS = int(os.getenv("GENERATE_TIMEOUT_MS", "50000"))
HEADLESS = os.getenv("HEADLESS", "false").strip().lower() == "true"

# --- Runner ---
MAX_ATTEMPTS = int(os.getenv("CRAWL_MAX_ATTEMPTS", "3"))
WORKERS = int(os.getenv("CRAWL_WORKERS", "1"))

# --- PostgreSQL ---
PGHOST = os.getenv("PGHOST", "localhost")
PGPORT = os.getenv("PGPORT", "5432")
PGUSER = os.getenv("PGUSER", "postgres")
PGPASSWORD = os.getenv("PGPASSWORD", "")
PGDATABASE = os.getenv("PGDATABASE", "printoka")

# The matrix field-name prefix for the standard order-spec controls.
MATRIX_PREFIX = (
    "ctl00$mainContent$order_spec_controller1$order_spec_standard_matrix1$"
)
PRODUCT_SELECT = "ctl00$mainContent$order_spec_controller1$ddlProduct"
GENERATE_POSTBACK_TARGET = "ctl00$mainContent$btnPriceList"

# Delivery destinations (rblOrderCountryCode values), as required by the user.
DELIVERIES = {
    99: "West Malaysia",
    98: "East Malaysia",
    96: "Singapore",
    100: "Thailand (Bangkok only)",
}

OUTPUT_DIR = CRAWLER_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def dsn(database: str | None = None) -> str:
    """SQLAlchemy DSN. Pass database=None to connect to the default 'postgres'
    maintenance DB (used to CREATE DATABASE)."""
    db = database if database is not None else PGDATABASE
    return (
        f"postgresql+psycopg://{PGUSER}:{quote_plus(PGPASSWORD)}"
        f"@{PGHOST}:{PGPORT}/{db}"
    )
