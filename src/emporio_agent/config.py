"""Centralized configuration: file paths and the store's time zone."""

from pathlib import Path
from zoneinfo import ZoneInfo

ROOT_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"

# The store is in Campo Grande/MS (UTC-4, no daylight saving time).
STORE_TZ = ZoneInfo("America/Campo_Grande")
