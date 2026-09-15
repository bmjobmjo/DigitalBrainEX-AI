"""
DigitalBrainEX AI - Main Application Entry Point.
Initializes the Qt application, database, system tray, and main window.
"""
import sys
import os
from pathlib import Path

# Ensure package root is in python search path
pkg_root = Path(__file__).resolve().parent.parent
if str(pkg_root) not in sys.path:
    sys.path.insert(0, str(pkg_root))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from src.config import APP_NAME, APP_VERSION
from src.core.database import init_db
from src.core.logger import setup_logger, logger
from src.ui.theme import apply_theme
from src.ui.main_window import MainWindow
from src.background.tray_manager import TrayManager


def main():
    # Ensure working directory is package root
    try:
        os.chdir(str(pkg_root))
    except Exception:
        pass

    # Setup logger
    setup_logger()
    logger.info(f"Starting {APP_NAME} v{APP_VERSION}...")

    # Initialize QApplication early for singleton IPC and GUI
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setQuitOnLastWindowClosed(False)  # Allows running in system tray

    # Singleton check: ensure only one instance is active
    from src.utils.single_instance import SingleInstanceManager
    single_instance = SingleInstanceManager()
    if single_instance.is_already_running():
        logger.info("Another instance of DigitalBrainEX is already running. Activating existing instance...")
        single_instance.notify_running_instance()
        sys.exit(0)

    # Initialize SQLite database connection
    try:
        init_db()
        from src.core.database import take_startup_db_backup, remove_old_db_backups
        take_startup_db_backup()
        remove_old_db_backups(max_days=5)
    except Exception as e:
        logger.error(f"Fatal error initializing database: {e}", exc_info=True)
        single_instance.cleanup()
        sys.exit(1)

    # Ensure running on interactive user desktop in Windows
    if sys.platform == "win32":
        import ctypes
        try:
            h_desk = ctypes.windll.user32.OpenDesktopW("default", 0, False, 0x01FF)
            if h_desk:
                ctypes.windll.user32.SetThreadDesktop(h_desk)
        except Exception as e:
            logger.warning(f"Could not switch thread desktop: {e}")

    # Setup Windows AppUserModelID so Windows taskbar uses app icon instead of python.exe
    from src.utils.win32_helper import setup_windows_app_id, apply_native_window_icon
    setup_windows_app_id()

    # Set authentic application window icon
    from PyQt6.QtGui import QIcon
    from src.config import ASSETS_DIR
    app_icon_path = str(ASSETS_DIR / "app_icon.ico")
    if not os.path.exists(app_icon_path):
        app_icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "app_icon.ico"))
    if os.path.exists(app_icon_path):
        app.setWindowIcon(QIcon(app_icon_path))

    # Apply sleek modern light/dark theme
    apply_theme(app)

    # Create Main Window
    main_window = MainWindow()

    # Start Singleton IPC server to handle future instance activations
    single_instance.start_server(on_activate_callback=lambda args: main_window.show_and_activate())
    app.aboutToQuit.connect(single_instance.cleanup)

    # Create System Tray Manager
    tray_manager = TrayManager()
    tray_manager.show_main_window_requested.connect(main_window.show_and_activate)
    tray_manager.screenshot_requested.connect(main_window._on_screenshot_requested)
    tray_manager.clipboard_history_requested.connect(main_window._open_clipboard_history)
    tray_manager.settings_requested.connect(lambda: (main_window.show_and_activate(), main_window.sidebar.select_module_by_name("Settings")))
    tray_manager.exit_requested.connect(lambda: (single_instance.cleanup(), tray_manager.hide(), app.quit()))

    # Background Services
    from src.background.clipboard_monitor import ClipboardMonitor
    from src.background.window_tracker import WindowTracker
    from src.background.folder_watcher import FolderWatcher
    from src.background.task_scheduler import TaskScheduler

    clipboard_monitor = ClipboardMonitor()
    clipboard_monitor.start_monitoring()

    window_tracker = WindowTracker()
    window_tracker.start_tracking()

    folder_watcher = FolderWatcher()
    folder_watcher.start_watching()

    task_scheduler = TaskScheduler()
    task_scheduler.task_due.connect(
        lambda tid, name, due: (
            main_window.trigger_task_alert(name, due),
            tray_manager.show_notification("⏰ Task Due Reminder", f"{name} is due now!"),
        )
    )
    task_scheduler.start()

    # Wellness Reminders Engine (Hydration & Sedentary Alerts)
    from src.background.wellness_reminders import wellness_engine
    from src.ui.components.wellness_alert_banner import flash_wellness_alert

    def on_wellness_alert(alert_type: str, title: str, message: str):
        tray_manager.start_blinking(alert_type)
        flash_wellness_alert(
            alert_type=alert_type,
            title=title,
            message=message,
            on_dismiss=lambda: wellness_engine.dismiss(alert_type),
            on_snooze=lambda: wellness_engine.snooze(alert_type, 5),
        )

    wellness_engine.alert_triggered.connect(on_wellness_alert)
    wellness_engine.alert_cleared.connect(lambda at: tray_manager.stop_blinking())
    wellness_engine.start()

    # Global Hotkeys
    from src.background.hotkey_manager import GlobalHotkeyManager
    hotkey_manager = GlobalHotkeyManager()
    hotkey_manager.screenshot_triggered.connect(main_window._on_screenshot_requested)
    hotkey_manager.clipboard_triggered.connect(main_window._open_clipboard_history)
    hotkey_manager.escape_triggered.connect(main_window._on_escape_pressed)
    hotkey_manager.register_hotkeys()

    tray_manager.show()

    start_minimized = "--minimized" in sys.argv
    if not start_minimized:
        main_window.show()
        if os.path.exists(app_icon_path):
            apply_native_window_icon(int(main_window.winId()), app_icon_path)
        main_window.raise_()
        main_window.activateWindow()
    else:
        logger.info("Application started in system tray (minimized).")
        tray_manager.show_notification(
            "DigitalBrainEX AI",
            "Running quietly in system tray. Press PrintScreen to capture.",
            msecs=3000,
        )

    logger.info("Application UI and background system tray initialized successfully.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
