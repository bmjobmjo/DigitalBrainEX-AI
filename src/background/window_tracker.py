"""
Active Window Time Tracker (TrackMe) for DigitalBrainEX AI.
Logs application usage and window titles into SQLite with idle detection.
"""
import ctypes
import os
import threading
import time
from typing import Optional
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from src.config import TRACKME_INTERVAL_SECONDS, TRACKME_IDLE_THRESHOLD_SECONDS
from src.core.repository import DataRepository
from src.core.event_bus import event_bus, EVT_WINDOW_TRACKED
from src.core.logger import logger

try:
    import win32gui
    import win32process
    import psutil
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def get_idle_seconds() -> float:
    """Returns the seconds elapsed since last user keyboard or mouse input."""
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
        millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
        return max(0.0, millis / 1000.0)
    return 0.0


class WindowTracker(QObject):
    activity_logged = pyqtSignal(str, str, int)  # (app, title, seconds)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running = False
        self._interval_seconds = TRACKME_INTERVAL_SECONDS
        self._idle_threshold = TRACKME_IDLE_THRESHOLD_SECONDS
        self._current_project_id = 0
        self._current_project_name = "General"

        self._timer = QTimer(self)
        self._timer.setInterval(self._interval_seconds * 1000)
        self._timer.timeout.connect(self._track_tick)

    def set_active_project(self, project_id: int, project_name: str):
        self._current_project_id = project_id
        self._current_project_name = project_name

    def start_tracking(self):
        if self._is_running or not WIN32_AVAILABLE:
            return
        self._is_running = True
        self._timer.start()
        logger.info(f"Window tracker started (sampling every {self._interval_seconds}s).")

    def stop_tracking(self):
        if self._is_running:
            self._timer.stop()
            self._is_running = False
            logger.info("Window tracker stopped.")

    def _track_tick(self):
        if not self._is_running or not WIN32_AVAILABLE:
            return

        # Check for user idle state
        try:
            idle_secs = get_idle_seconds()
            if idle_secs >= self._idle_threshold:
                return  # Skip tracking while user is away from keyboard

            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return

            window_title = win32gui.GetWindowText(hwnd) or "Untitled"
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            pid = pid & 0xFFFFFFFF

            app_name = "System"
            if pid > 0:
                try:
                    proc = psutil.Process(pid)
                    app_name = proc.name()
                except Exception:
                    pass

            # Ignore tracking our own background dialogs or task switches
            if app_name.lower().startswith("python") and "DigitalBrain" in window_title:
                pass  # Still log or skip as desired

            # Record to database
            DataRepository.log_activity(
                app_name=app_name,
                window_title=window_title,
                seconds=self._interval_seconds,
                project_id=self._current_project_id,
                project_name=self._current_project_name,
            )

            event_bus.publish(
                EVT_WINDOW_TRACKED,
                app_name=app_name,
                window_title=window_title,
                seconds=self._interval_seconds,
            )
            self.activity_logged.emit(app_name, window_title, self._interval_seconds)

        except Exception as e:
            logger.debug(f"Window tracker tick warning: {e}")
