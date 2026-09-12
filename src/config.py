"""
Application Configuration and Path Management for DigitalBrainEX AI.
"""
from pathlib import Path
import os
import sys

# Base and data directories
IS_FROZEN = getattr(sys, "frozen", False)

if IS_FROZEN:
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)))
    DATA_DIR = Path(os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))) / "DigitalBrainEX"
    BASE_DIR = DATA_DIR
else:
    BUNDLE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = BUNDLE_DIR
    BASE_DIR = BUNDLE_DIR

DATABASE_DIR = DATA_DIR / "database"
LOGS_DIR = DATA_DIR / "logs"
SCREENSHOTS_DIR = DATA_DIR / "screenshots"
RECORDINGS_DIR = DATA_DIR / "recordings"
TEMP_PAD_DIR = DATA_DIR / "temp_pad"

ASSETS_DIR = BUNDLE_DIR / "src" / "assets"
if not ASSETS_DIR.exists():
    ASSETS_DIR = BUNDLE_DIR / "assets"

# Ensure runtime directories exist
for directory in [DATABASE_DIR, LOGS_DIR, SCREENSHOTS_DIR, RECORDINGS_DIR, TEMP_PAD_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Default database file path
DEFAULT_DB_PATH = DATABASE_DIR / "DevDiary-10-09-2026.db3"

# Seed database on first run if persistent database does not exist
if not DEFAULT_DB_PATH.exists():
    import shutil
    candidates = [
        BUNDLE_DIR / "database" / "DevDiary_template.db3",
        BUNDLE_DIR / "database" / "DevDiary-10-09-2026.db3",
        DATABASE_DIR / "DevDiary_template.db3",
    ]
    for cand in candidates:
        if cand.exists() and cand.resolve() != DEFAULT_DB_PATH.resolve():
            try:
                shutil.copy2(cand, DEFAULT_DB_PATH)
                print(f"Seeded database from {cand.name}")
                break
            except Exception as e:
                print(f"Warning: could not seed database from {cand}: {e}")

# Application metadata
APP_NAME = "DigitalBrainEX AI"
APP_VERSION = "2.0.0"
APP_AUTHOR = "DigitalBrainEX Team"

# Database Configuration
DB_PATH = os.environ.get("DIGITALBRAIN_DB_PATH", str(DEFAULT_DB_PATH))
DATABASE_URI = f"sqlite:///{DB_PATH}"

# Audio recording defaults
AUDIO_SAMPLE_RATE = 16000  # 16kHz optimal for speech recognition
AUDIO_CHANNELS = 1

# Clipboard Monitoring
CLIPBOARD_POLL_INTERVAL_MS = 1000
MAX_CLIPBOARD_HISTORY_DISPLAY = 100

# Window Tracking (TrackMe)
TRACKME_INTERVAL_SECONDS = 5
TRACKME_IDLE_THRESHOLD_SECONDS = 60

# Appearance
DEFAULT_THEME = "light"

# Document & Media Storage Folder (DocFolder)
from src.utils.config_manager import (
    get_doc_folder,
    set_doc_folder,
    resolve_document_path,
    open_path_or_url,
    show_in_file_manager,
)
DOC_FOLDER = get_doc_folder()
