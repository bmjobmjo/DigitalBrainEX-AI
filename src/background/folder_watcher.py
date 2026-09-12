"""
Folder Watcher Service for DigitalBrainEX AI.
Monitors configured download and work folders using watchdog and alerts user of new files.
"""
import os
import shutil
import time
from pathlib import Path
from typing import List, Optional
from PyQt6.QtCore import QObject, pyqtSignal
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

from src.config import TEMP_PAD_DIR
from src.core.repository import DataRepository
from src.core.event_bus import event_bus, EVT_WATCH_FOLDER_FILE
from src.core.logger import logger


class WatchFolderHandler(FileSystemEventHandler):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def on_created(self, event):
        if not event.is_directory:
            # Let file settle (avoid reading partial downloads like .crdownload)
            ext = os.path.splitext(event.src_path)[1].lower()
            if ext in (".tmp", ".crdownload", ".part"):
                return
            self.callback(event.src_path)


class FolderWatcher(QObject):
    file_detected = pyqtSignal(str)  # (src_file_path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._observer: Optional[Observer] = None
        self._is_watching = False

    def start_watching(self):
        """Starts monitoring all paths configured in WatchFolder database table."""
        if self._is_watching:
            return

        watch_paths = DataRepository.get_watch_folders()
        if not watch_paths:
            logger.info("No watch folders configured in database.")
            return

        self._observer = Observer()
        handler = WatchFolderHandler(self._on_file_created)

        active_count = 0
        for path_str in watch_paths:
            if os.path.exists(path_str):
                self._observer.schedule(handler, path_str, recursive=False)
                active_count += 1
                logger.info(f"Watching folder: {path_str}")

        if active_count > 0:
            self._observer.start()
            self._is_watching = True
            logger.info(f"FolderWatcher active across {active_count} folders.")

    def stop_watching(self):
        if self._is_watching and self._observer:
            self._observer.stop()
            self._observer.join(timeout=2.0)
            self._observer = None
            self._is_watching = False
            logger.info("FolderWatcher stopped.")

    def _on_file_created(self, src_path: str):
        logger.info(f"New file detected in watched folder: {src_path}")
        event_bus.publish(EVT_WATCH_FOLDER_FILE, file_path=src_path)
        self.file_detected.emit(src_path)
