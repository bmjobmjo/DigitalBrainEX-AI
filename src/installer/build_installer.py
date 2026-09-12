"""
Builder script for DigitalBrainEX AI Setup.
Compiles setup_gui.py into a standalone DigitalBrainEX_Setup.exe using PyInstaller.
"""
import sys
import os
import subprocess
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parent.parent.parent
INSTALLER_SCRIPT = PKG_ROOT / "src" / "installer" / "setup_gui.py"
APP_ICON = PKG_ROOT / "src" / "assets" / "app_icon.ico"
OUTPUT_DIR = PKG_ROOT / "dist"


def build_installer():
    print(f"Building DigitalBrainEX AI Setup from {INSTALLER_SCRIPT}...")
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconsole",
        "--onefile",
        "--clean",
        "--name",
        "DigitalBrainEX_Setup",
        f"--icon={APP_ICON}",
        f"--paths={PKG_ROOT}",
        f"--add-data={PKG_ROOT / 'src'}{os.pathsep}src",
        f"--add-data={PKG_ROOT / 'src' / 'assets'}{os.pathsep}assets",
        f"--add-data={PKG_ROOT / 'database'}{os.pathsep}database",
        f"--add-data={PKG_ROOT / 'requirements.txt'}{os.pathsep}.",
        "--hidden-import=PyQt6",
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtGui",
        "--hidden-import=PyQt6.QtWidgets",
        "--hidden-import=src",
        "--hidden-import=src.installer.shortcut_helper",
        "--hidden-import=src.utils.config_manager",
        "--hidden-import=src.utils.startup_manager",
        "--hidden-import=src.utils.win32_helper",
        str(INSTALLER_SCRIPT),
    ]

    print("Running:", " ".join(cmd))
    res = subprocess.run(cmd, cwd=str(PKG_ROOT))
    if res.returncode == 0:
        print("\nSetup installer built successfully! Located at:")
        print(OUTPUT_DIR / "DigitalBrainEX_Setup.exe")
        return True
    else:
        print("\nPyInstaller build failed with return code:", res.returncode)
        return False


if __name__ == "__main__":
    success = build_installer()
    sys.exit(0 if success else 1)
