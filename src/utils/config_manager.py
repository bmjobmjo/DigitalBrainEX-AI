"""
Configuration Manager for DigitalBrainEX AI.
Handles persistent settings (DocFolder, database path, etc.) across
settings.json, Windows Registry, and environment variables.
"""
import os
import sys
import json
import subprocess
import webbrowser
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path(os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))) / "DigitalBrainEX"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
REG_SETTINGS_PATH = r"Software\DigitalBrain\Settings"


def _read_registry_doc_folder() -> Optional[str]:
    """Reads DocFolder from Windows Registry if available."""
    if sys.platform != "win32":
        return None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_SETTINGS_PATH, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, "DocFolder")
            if val and os.path.exists(val):
                return val
    except Exception:
        pass
    return None


def _write_registry_doc_folder(folder_path: str):
    """Writes DocFolder to Windows Registry."""
    if sys.platform != "win32":
        return
    try:
        import winreg
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_SETTINGS_PATH) as key:
            winreg.SetValueEx(key, "DocFolder", 0, winreg.REG_SZ, folder_path)
    except Exception as e:
        print(f"Warning: Could not write DocFolder to registry: {e}")


DEFAULT_SETTINGS = {
    "water_reminder_enabled": True,
    "water_reminder_interval_min": 45,
    "sedentary_reminder_enabled": True,
    "sedentary_reminder_interval_min": 60,
    "wellness_idle_timeout_sec": 60,
    "openrouter_enabled": False,
    "openrouter_api_key": "",
    "openrouter_model": "anthropic/claude-3.5-sonnet",
    "embedding_model_name": "sentence-transformers/all-MiniLM-L6-v2",
    "embedding_model_version": "1.0",
}


def load_settings() -> dict:
    """Loads settings dictionary from settings.json."""
    data = dict(DEFAULT_SETTINGS)
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                data.update(saved)
                return data
        except Exception:
            pass
    return data


def save_settings(data: dict):
    """Saves settings dictionary to settings.json."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        current = load_settings()
        current.update(data)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save settings: {e}")


def get_wellness_settings() -> dict:
    """Returns wellness settings dictionary."""
    settings = load_settings()
    return {
        "water_reminder_enabled": bool(settings.get("water_reminder_enabled", True)),
        "water_reminder_interval_min": int(settings.get("water_reminder_interval_min", 45)),
        "sedentary_reminder_enabled": bool(settings.get("sedentary_reminder_enabled", True)),
        "sedentary_reminder_interval_min": int(settings.get("sedentary_reminder_interval_min", 60)),
        "wellness_idle_timeout_sec": int(settings.get("wellness_idle_timeout_sec", 60)),
    }


def save_wellness_settings(wellness_cfg: dict):
    """Saves wellness settings and updates config."""
    save_settings(wellness_cfg)


def get_openrouter_settings() -> dict:
    """Returns OpenRouter configuration dictionary."""
    settings = load_settings()
    env_key = os.environ.get("OPENROUTER_API_KEY", "")
    key = settings.get("openrouter_api_key", "") or env_key
    return {
        "openrouter_enabled": bool(settings.get("openrouter_enabled", False)),
        "openrouter_api_key": key,
        "openrouter_model": str(settings.get("openrouter_model", "anthropic/claude-3.5-sonnet")),
    }


def save_openrouter_settings(cfg: dict):
    """Persists OpenRouter settings and updates os.environ."""
    save_settings(cfg)
    if cfg.get("openrouter_api_key"):
        os.environ["OPENROUTER_API_KEY"] = cfg["openrouter_api_key"]


def get_embedding_settings() -> dict:
    """Returns local embedding model configuration dictionary."""
    settings = load_settings()
    return {
        "embedding_model_name": str(settings.get("embedding_model_name", "Qwen/Qwen3-Embedding-0.6B")),
        "embedding_model_version": str(settings.get("embedding_model_version", "1.0")),
    }


def save_embedding_settings(cfg: dict):
    """Persists local embedding model configuration."""
    save_settings(cfg)


def get_doc_folder() -> str:
    r"""
    Returns the configured document storage root directory (DocFolder).
    Checks:
    1. DIGITALBRAIN_DOC_FOLDER environment variable
    2. settings.json in %LOCALAPPDATA%/DigitalBrainEX
    3. Windows Registry HKCU\Software\DigitalBrain\Settings\DocFolder
    4. Known original archive path (e.g. D:\DBX\LocalDocFolder if it exists)
    5. Fallback to ~/Documents/DigitalBrainEX
    """
    # 1. Environment variable
    env_path = os.environ.get("DIGITALBRAIN_DOC_FOLDER")
    if env_path and os.path.exists(env_path):
        return env_path

    # 2. settings.json
    settings = load_settings()
    if "doc_folder" in settings and os.path.exists(settings["doc_folder"]):
        return settings["doc_folder"]

    # 3. Registry
    reg_path = _read_registry_doc_folder()
    if reg_path:
        return reg_path

    # 4. Known user archive directory if present on machine
    known_dbx = r"D:\DBX\LocalDocFolder"
    if os.path.exists(known_dbx):
        return known_dbx

    # 5. Default fallback
    default_dir = os.path.join(os.path.expanduser("~"), "Documents", "DigitalBrainEX")
    return default_dir


def set_doc_folder(folder_path: str):
    """Updates and persists the configured DocFolder."""
    if not folder_path:
        return
    folder_path = os.path.normpath(folder_path.strip())
    os.makedirs(folder_path, exist_ok=True)

    os.environ["DIGITALBRAIN_DOC_FOLDER"] = folder_path
    save_settings({"doc_folder": folder_path})
    _write_registry_doc_folder(folder_path)


def resolve_document_path(uri: Optional[str]) -> str:
    """
    Resolves a document URI into a full filesystem path or URL.
    - If empty: returns ''
    - If URL (http:// or https://): returns the URL unchanged
    - If already absolute path and exists: returns the path unchanged
    - If relative path (e.g. '\\3\\DesignDoc.pdf' or '3/DesignDoc.pdf'):
      prepends DocFolder and normalizes slashes.
    """
    if not uri or not uri.strip():
        return ""
    clean_uri = uri.strip()
    lower = clean_uri.lower()

    if lower.startswith("http://") or lower.startswith("https://") or lower.startswith("www."):
        return clean_uri

    if os.path.isabs(clean_uri) and os.path.exists(clean_uri):
        return os.path.normpath(clean_uri)

    # Relative to DocFolder
    doc_folder = get_doc_folder()
    # Strip any leading slashes or backslashes
    relative_part = clean_uri.lstrip("\\/")
    resolved = os.path.normpath(os.path.join(doc_folder, relative_part))
    return resolved


def open_path_or_url(path_or_url: str, parent_widget=None) -> bool:
    """
    Opens the target path or URL in the default browser or Windows handler.
    Shows friendly message dialog if the file does not exist.
    """
    if not path_or_url:
        if parent_widget:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(parent_widget, "No File", "No file path or URL specified.")
        return False

    lower = path_or_url.lower()
    if lower.startswith("http://") or lower.startswith("https://") or lower.startswith("www."):
        url = path_or_url if "://" in path_or_url else f"https://{path_or_url}"
        webbrowser.open(url)
        return True

    if os.path.exists(path_or_url):
        try:
            os.startfile(os.path.normpath(path_or_url))
            return True
        except Exception as e:
            if parent_widget:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(parent_widget, "Open Error", f"Could not open file:\n{e}")
            return False
    else:
        if parent_widget:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                parent_widget,
                "File Not Found",
                f"Cannot find the specified file:\n\n{path_or_url}\n\n"
                f"Please verify that your Document Storage Folder (DocFolder) "
                f"is correctly configured under Settings -> Paths & Storage.",
            )
        return False


def show_in_file_manager(file_path: str):
    """Selects and shows the file in Windows File Explorer."""
    if not file_path:
        return
    norm = os.path.normpath(file_path)
    if os.path.exists(norm):
        subprocess.run(["explorer.exe", f"/select,{norm}"])
    else:
        parent_dir = os.path.dirname(norm)
        if os.path.exists(parent_dir):
            os.startfile(parent_dir)
