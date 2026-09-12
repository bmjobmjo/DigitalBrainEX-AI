"""
Unit tests for background services (ClipboardMonitor, WindowTracker, TaskScheduler, FolderWatcher).
"""
import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication
from src.background.clipboard_monitor import ClipboardMonitor
from src.background.window_tracker import WindowTracker
from src.background.task_scheduler import TaskScheduler
from src.background.folder_watcher import FolderWatcher

app = QApplication.instance() or QApplication(["test_bg"])


class TestBackgroundServices(unittest.TestCase):

    def test_clipboard_monitor_init(self):
        monitor = ClipboardMonitor()
        monitor.start_monitoring()
        self.assertTrue(monitor._is_monitoring)
        monitor.stop_monitoring()
        self.assertFalse(monitor._is_monitoring)
        print("ClipboardMonitor lifecycle OK!")

    def test_window_tracker_init(self):
        tracker = WindowTracker()
        tracker.start_tracking()
        self.assertTrue(tracker._is_running)
        tracker.stop_tracking()
        self.assertFalse(tracker._is_running)
        print("WindowTracker lifecycle OK!")

    def test_task_scheduler_init(self):
        scheduler = TaskScheduler()
        scheduler.start()
        self.assertTrue(scheduler._is_running)
        scheduler.stop()
        self.assertFalse(scheduler._is_running)
        print("TaskScheduler lifecycle OK!")

    def test_folder_watcher_init(self):
        watcher = FolderWatcher()
        watcher.start_watching()
        watcher.stop_watching()
        print("FolderWatcher lifecycle OK!")


if __name__ == "__main__":
    unittest.main()
