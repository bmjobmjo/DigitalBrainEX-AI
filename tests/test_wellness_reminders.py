"""
Unit tests for Wellness Reminders system and Tray Blinking.
"""
import unittest
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication

app = QApplication.instance() or QApplication(["test_wellness"])

from src.background.wellness_reminders import WellnessReminderManager
from src.utils.config_manager import get_wellness_settings, save_wellness_settings
from src.ui.components.wellness_alert_banner import WellnessAlertBanner
from src.background.tray_manager import TrayManager


class TestWellnessReminders(unittest.TestCase):

    def test_settings_persistence(self):
        """Tests that wellness settings can be read and written."""
        cfg = get_wellness_settings()
        self.assertIn("water_reminder_enabled", cfg)
        self.assertIn("water_reminder_interval_min", cfg)
        self.assertIn("sedentary_reminder_enabled", cfg)
        self.assertIn("sedentary_reminder_interval_min", cfg)
        self.assertIn("wellness_idle_timeout_sec", cfg)

        # Test saving and reading back
        save_wellness_settings({"water_reminder_interval_min": 35})
        updated = get_wellness_settings()
        self.assertEqual(updated["water_reminder_interval_min"], 35)

        # Restore default
        save_wellness_settings({"water_reminder_interval_min": 45})

    @patch("src.background.wellness_reminders.is_workstation_locked", return_value=False)
    @patch("src.background.wellness_reminders.get_idle_seconds", return_value=5.0)
    def test_active_accumulation(self, mock_idle, mock_locked):
        """Tests that active seconds increment when user is active and unlocked."""
        manager = WellnessReminderManager()
        manager._water_enabled = True
        manager._sedentary_enabled = True
        manager._idle_threshold_sec = 60
        manager._water_interval_min = 45
        manager._sedentary_interval_min = 60
        manager.reset_timers()

        self.assertEqual(manager._water_active_seconds, 0.0)
        self.assertEqual(manager._sedentary_active_seconds, 0.0)

        # 5 ticks active
        for _ in range(5):
            manager._on_tick()

        self.assertEqual(manager._water_active_seconds, 5.0)
        self.assertEqual(manager._sedentary_active_seconds, 5.0)
        self.assertTrue(manager._is_active)

    @patch("src.background.wellness_reminders.is_workstation_locked", return_value=False)
    def test_idle_reset(self, mock_locked):
        """Tests that timer stops counting and resets when mouse/keyboard is inactive."""
        manager = WellnessReminderManager()
        manager._water_enabled = True
        manager._idle_threshold_sec = 60
        manager.reset_timers()

        # Simulate user active for 30 seconds
        with patch("src.background.wellness_reminders.get_idle_seconds", return_value=2.0):
            for _ in range(30):
                manager._on_tick()
        self.assertEqual(manager._water_active_seconds, 30.0)

        # Now simulate user inactive (e.g. idle for 65 seconds >= 60s threshold)
        with patch("src.background.wellness_reminders.get_idle_seconds", return_value=65.0):
            manager._on_tick()

        # Timer must be reset to 0
        self.assertEqual(manager._water_active_seconds, 0.0)
        self.assertEqual(manager._sedentary_active_seconds, 0.0)
        self.assertFalse(manager._is_active)

    def test_locked_reset(self):
        """Tests that timer stops counting and resets when workstation is locked/logged out."""
        manager = WellnessReminderManager()
        manager._water_enabled = True
        manager.reset_timers()

        # Simulate user active for 20 seconds
        with patch("src.background.wellness_reminders.is_workstation_locked", return_value=False):
            with patch("src.background.wellness_reminders.get_idle_seconds", return_value=1.0):
                for _ in range(20):
                    manager._on_tick()
        self.assertEqual(manager._water_active_seconds, 20.0)

        # Now simulate workstation locked (Win+L / logged out)
        with patch("src.background.wellness_reminders.is_workstation_locked", return_value=True):
            manager._on_tick()

        # Timer must be reset to 0
        self.assertEqual(manager._water_active_seconds, 0.0)
        self.assertEqual(manager._sedentary_active_seconds, 0.0)

    @patch("src.background.wellness_reminders.is_workstation_locked", return_value=False)
    @patch("src.background.wellness_reminders.get_idle_seconds", return_value=0.5)
    def test_alert_triggered(self, mock_idle, mock_locked):
        """Tests that alert_triggered signal is emitted when interval completes."""
        manager = WellnessReminderManager()
        manager._water_enabled = True
        manager._water_interval_min = 1  # 1 minute = 60 seconds
        manager._sedentary_enabled = False
        manager.reset_timers()

        alerts_received = []
        manager.alert_triggered.connect(lambda at, t, m: alerts_received.append((at, t, m)))

        # Fast forward to 59 seconds
        manager._water_active_seconds = 59.0
        manager._on_tick()  # Reaches 60 seconds

        self.assertEqual(len(alerts_received), 1)
        self.assertEqual(alerts_received[0][0], "water")
        self.assertIn("Hydration", alerts_received[0][1])
        # Timer resets after firing
        self.assertEqual(manager._water_active_seconds, 0.0)

    def test_snooze_and_dismiss(self):
        """Tests snooze and dismiss behavior."""
        manager = WellnessReminderManager()
        manager._water_interval_min = 45
        manager.snooze("water", minutes=5)
        # 45m * 60 = 2700s, - 5m * 60 (300s) = 2400s
        self.assertEqual(manager._water_active_seconds, 2400.0)

        manager.dismiss("water")
        self.assertEqual(manager._water_active_seconds, 0.0)

    def test_banner_and_tray_blinking(self):
        """Tests creation of banner and tray blinking methods."""
        banner = WellnessAlertBanner(
            alert_type="water",
            title="Drink Water",
            message="Take a sip of water!",
        )
        self.assertIsNotNone(banner)

        tray = TrayManager()
        tray.start_blinking("water")
        self.assertTrue(tray._is_blinking)
        tray.stop_blinking()
        self.assertFalse(tray._is_blinking)


if __name__ == "__main__":
    unittest.main()
