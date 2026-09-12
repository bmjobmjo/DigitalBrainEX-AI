"""
Wellness & Health Reminders Engine for DigitalBrainEX AI.
Tracks active keyboard and mouse time to generate:
- Drink Water Reminders (e.g., every 45 min)
- Sedentary / Stand & Move Reminders (e.g., every 60 min)

Behavior:
- Timer only accumulates while user is logged in and actively using keyboard or mouse.
- If mouse/keyboard becomes inactive or workstation is locked/logged out,
  the timer stops counting and resets until the user logs back in and resumes active input.
"""
import ctypes
import os
import sys
from typing import Dict, Any
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from src.core.logger import logger


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def get_idle_seconds() -> float:
    """Returns the seconds elapsed since the last user keyboard or mouse event."""
    if sys.platform != "win32":
        return 0.0
    try:
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
            millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
            return max(0.0, millis / 1000.0)
    except Exception:
        pass
    return 0.0


def is_workstation_locked() -> bool:
    """Returns True if the Windows workstation is locked or showing logon screen."""
    if sys.platform != "win32":
        return False
    try:
        h_desk = ctypes.windll.user32.OpenInputDesktop(0, False, 0x0001)
        if h_desk:
            ctypes.windll.user32.CloseDesktop(h_desk)
            return False
        return True
    except Exception:
        return False


class WellnessReminderManager(QObject):
    """
    Monitors active computer time and triggers hydration and posture/stretch alerts.
    """
    alert_triggered = pyqtSignal(str, str, str)  # (alert_type: "water"|"sedentary", title, message)
    alert_cleared = pyqtSignal(str)              # (alert_type)
    status_updated = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._water_enabled = True
        self._water_interval_min = 45
        self._sedentary_enabled = True
        self._sedentary_interval_min = 60
        self._idle_threshold_sec = 60

        self._water_active_seconds = 0.0
        self._sedentary_active_seconds = 0.0
        self._is_active = False
        self._is_running = False

        self._timer = QTimer(self)
        self._timer.setInterval(1000)  # 1 second sampling tick
        self._timer.timeout.connect(self._on_tick)

        self.reload_settings()

    @property
    def water_enabled(self) -> bool:
        return self._water_enabled

    @property
    def water_interval_min(self) -> int:
        return self._water_interval_min

    @property
    def sedentary_enabled(self) -> bool:
        return self._sedentary_enabled

    @property
    def sedentary_interval_min(self) -> int:
        return self._sedentary_interval_min

    @property
    def idle_threshold_sec(self) -> int:
        return self._idle_threshold_sec

    def reload_settings(self):
        """Loads configuration from persistent settings."""
        try:
            from src.utils.config_manager import load_settings
            cfg = load_settings()
            self._water_enabled = cfg.get("water_reminder_enabled", True)
            self._water_interval_min = max(1, int(cfg.get("water_reminder_interval_min", 45)))
            self._sedentary_enabled = cfg.get("sedentary_reminder_enabled", True)
            self._sedentary_interval_min = max(1, int(cfg.get("sedentary_reminder_interval_min", 60)))
            self._idle_threshold_sec = max(5, int(cfg.get("wellness_idle_timeout_sec", 60)))
            logger.info(
                f"Wellness reminders reloaded: Water={self._water_enabled} ({self._water_interval_min}m), "
                f"Sedentary={self._sedentary_enabled} ({self._sedentary_interval_min}m), "
                f"IdleTimeout={self._idle_threshold_sec}s"
            )
        except Exception as e:
            logger.error(f"Error loading wellness settings: {e}")

    def start(self):
        """Starts monitoring active input."""
        if self._is_running:
            return
        self._is_running = True
        self._timer.start()
        logger.info("Wellness reminder engine started.")

    def stop(self):
        """Stops monitoring."""
        if self._is_running:
            self._timer.stop()
            self._is_running = False
            logger.info("Wellness reminder engine stopped.")

    def reset_timers(self):
        """Resets both active timers to zero."""
        self._water_active_seconds = 0.0
        self._sedentary_active_seconds = 0.0
        self._is_active = False

    def snooze(self, alert_type: str, minutes: int = 5):
        """Snoozes the given alert by backing off the active seconds."""
        backoff_sec = max(60, minutes * 60)
        if alert_type == "water":
            target = self._water_interval_min * 60
            self._water_active_seconds = max(0.0, target - backoff_sec)
        elif alert_type == "sedentary":
            target = self._sedentary_interval_min * 60
            self._sedentary_active_seconds = max(0.0, target - backoff_sec)
        self.alert_cleared.emit(alert_type)

    def dismiss(self, alert_type: str):
        """Acknowledges and clears the active alert."""
        if alert_type == "water":
            self._water_active_seconds = 0.0
        elif alert_type == "sedentary":
            self._sedentary_active_seconds = 0.0
        self.alert_cleared.emit(alert_type)

    def _on_tick(self):
        """1-second timer tick. Evaluates lock state, idle time, and active seconds."""
        # 1. Check if Windows session is locked or logged out
        if is_workstation_locked():
            # Stop counting and reset timer until user logs in again
            if self._is_active or self._water_active_seconds > 0 or self._sedentary_active_seconds > 0:
                self.reset_timers()
            return

        # 2. Check mouse and keyboard idle duration
        idle_sec = get_idle_seconds()
        if idle_sec >= self._idle_threshold_sec:
            # User has stepped away or is inactive: reset timer and stop counting
            if self._is_active or self._water_active_seconds > 0 or self._sedentary_active_seconds > 0:
                self.reset_timers()
            return

        # 3. User is logged in AND mouse/keyboard are active
        self._is_active = True

        # Check Water Reminder
        if self._water_enabled:
            self._water_active_seconds += 1.0
            water_target_sec = self._water_interval_min * 60
            if self._water_active_seconds >= water_target_sec:
                self._water_active_seconds = 0.0
                self.alert_triggered.emit(
                    "water",
                    "Hydration Reminder",
                    f"You have been working actively for {self._water_interval_min} minutes. Time to drink a glass of water!",
                )

        # Check Sedentary / Stand & Move Reminder
        if self._sedentary_enabled:
            self._sedentary_active_seconds += 1.0
            sedentary_target_sec = self._sedentary_interval_min * 60
            if self._sedentary_active_seconds >= sedentary_target_sec:
                self._sedentary_active_seconds = 0.0
                self.alert_triggered.emit(
                    "sedentary",
                    "Stand Up & Stretch",
                    f"You have been sitting for {self._sedentary_interval_min} minutes. Stand up, stretch, and move around!",
                )

        self.status_updated.emit({
            "is_active": self._is_active,
            "water_elapsed_sec": int(self._water_active_seconds),
            "water_target_sec": self._water_interval_min * 60,
            "sedentary_elapsed_sec": int(self._sedentary_active_seconds),
            "sedentary_target_sec": self._sedentary_interval_min * 60,
        })


# Global singleton instance
wellness_engine = WellnessReminderManager()
