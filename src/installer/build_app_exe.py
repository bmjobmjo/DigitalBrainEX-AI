"""
Builder script for DigitalBrainEX AI Standalone Application Executable.
Compiles src/app.py into a single, fully self-contained DigitalBrainEX.exe with all binary dependencies.
"""
import sys
import os
import subprocess
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parent.parent.parent
APP_SCRIPT = PKG_ROOT / "src" / "app.py"
APP_ICON = PKG_ROOT / "src" / "assets" / "app_icon.ico"
OUTPUT_DIR = PKG_ROOT / "dist"


def build_app_exe() -> bool:
    print(f"Building standalone DigitalBrainEX.exe from {APP_SCRIPT}...")
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconsole",
        "--onefile",
        "--clean",
        "--name",
        "DigitalBrainEX",
        f"--icon={APP_ICON}",
        f"--paths={PKG_ROOT}",
        f"--add-data={PKG_ROOT / 'src' / 'assets'}{os.pathsep}assets",
        f"--add-data={PKG_ROOT / 'src' / 'assets'}{os.pathsep}src/assets",
        f"--add-data={PKG_ROOT / 'database' / 'DevDiary_template.db3'}{os.pathsep}database",
        # Exclude large unused packages to keep executable lightweight and fast
        "--exclude-module=torch",
        "--exclude-module=tensorflow",
        "--exclude-module=pyarrow",
        "--exclude-module=scipy",
        "--exclude-module=matplotlib",
        "--exclude-module=IPython",
        "--exclude-module=tornado",
        "--exclude-module=jupyter",
        "--exclude-module=tensorboard",
        "--exclude-module=streamlit",
        # Core & GUI hidden imports
        "--hidden-import=PyQt6",
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtGui",
        "--hidden-import=PyQt6.QtWidgets",
        "--hidden-import=PyQt6.QtSvg",
        "--hidden-import=PyQt6.QtSvgWidgets",
        # Database & ORM
        "--hidden-import=sqlalchemy",
        "--hidden-import=sqlalchemy.dialects.sqlite",
        "--hidden-import=sqlite3",
        # Imaging & Windows APIs
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        "--hidden-import=PIL.ImageDraw",
        "--hidden-import=ctypes",
        "--hidden-import=winreg",
        # Application modules
        "--hidden-import=src",
        "--hidden-import=src.config",
        "--hidden-import=src.core.database",
        "--hidden-import=src.core.models",
        "--hidden-import=src.core.repository",
        "--hidden-import=src.core.logger",
        "--hidden-import=src.ui.main_window",
        "--hidden-import=src.ui.icons",
        "--hidden-import=src.ui.theme",
        "--hidden-import=src.ui.components.wellness_alert_banner",
        "--hidden-import=src.background.tray_manager",
        "--hidden-import=src.background.wellness_reminders",
        "--hidden-import=src.background.clipboard_monitor",
        "--hidden-import=src.background.window_tracker",
        "--hidden-import=src.background.folder_watcher",
        "--hidden-import=src.background.task_scheduler",
        "--hidden-import=src.background.hotkey_manager",
        "--hidden-import=src.utils.config_manager",
        "--hidden-import=src.utils.startup_manager",
        "--hidden-import=src.utils.win32_helper",
        "--hidden-import=src.media.screen_capture",
        "--hidden-import=src.media.overlay_canvas",
        "--hidden-import=src.media.audio_recorder",
        str(APP_SCRIPT),
    ]

    print("Running:", " ".join(cmd))
    res = subprocess.run(cmd, cwd=str(PKG_ROOT))
    if res.returncode == 0:
        exe_path = OUTPUT_DIR / "DigitalBrainEX.exe"
        print(f"\nStandalone DigitalBrainEX.exe built successfully! ({exe_path})")
        return True
    else:
        print(f"\nPyInstaller build failed with return code: {res.returncode}")
        return False


if __name__ == "__main__":
    ok = build_app_exe()
    sys.exit(0 if ok else 1)
