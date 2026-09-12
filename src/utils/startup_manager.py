"""
Windows Auto-Startup Manager for DigitalBrainEX AI.
Manages registry entries under HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run.
"""
import sys
import os
from pathlib import Path
from typing import Optional

REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_REG_NAME = "DigitalBrainEX"


def get_default_launch_command() -> str:
    """Constructs the optimal Windows startup command line."""
    if getattr(sys, "frozen", False):
        # Running as compiled standalone executable
        return f'"{sys.executable}" --minimized'

    # Running as Python source: use pythonw to prevent command console window
    python_dir = os.path.dirname(sys.executable)
    pythonw = os.path.join(python_dir, "pythonw.exe")
    if not os.path.exists(pythonw):
        pythonw = sys.executable

    pkg_root = Path(__file__).resolve().parent.parent.parent
    app_py = pkg_root / "src" / "app.py"
    return f'"{pythonw}" "{app_py}" --minimized'


def is_auto_startup_enabled() -> bool:
    """Checks if DigitalBrainEX is registered in Windows Startup Run key."""
    if sys.platform != "win32":
        return False

    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, APP_REG_NAME)
            return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


def set_auto_startup(enabled: bool, command: Optional[str] = None) -> bool:
    """Enables or disables auto startup in HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run."""
    if sys.platform != "win32":
        return False

    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                cmd = command or get_default_launch_command()
                winreg.SetValueEx(key, APP_REG_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, APP_REG_NAME)
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        print(f"Error setting Windows auto startup: {e}")
        return False
