"""
Task & Reminder Scheduler for DigitalBrainEX AI.
Periodically checks for due deadlines and dispatches alerts and blinker triggers.
"""
from datetime import datetime, date
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from src.core.repository import DataRepository
from src.core.event_bus import event_bus, EVT_TASK_DUE
from src.core.logger import logger


class TaskScheduler(QObject):
    task_due = pyqtSignal(int, str, str)  # (task_id, task_name, due_on)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running = False
        self._timer = QTimer(self)
        self._timer.setInterval(30000)  # Check every 30 seconds
        self._timer.timeout.connect(self._check_tasks)

    def start(self):
        if self._is_running:
            return
        self._is_running = True
        self._timer.start()
        logger.info("Task reminder scheduler started.")

    def stop(self):
        if self._is_running:
            self._timer.stop()
            self._is_running = False
            logger.info("Task reminder scheduler stopped.")

    def _check_tasks(self):
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        current_hhmm = now.strftime("%H:%M")

        try:
            active_tasks = DataRepository.get_tasks(status="Active")
            for t in active_tasks:
                if not t.DueOn:
                    continue

                # Check if due today
                if t.DueOn.startswith(today_str):
                    rem_time = t.ReminderTimeHHMM or "00:00"

                    # Has it already alerted today?
                    if t.AlertedOn == today_str:
                        continue

                    # If reminder time reached or passed
                    if current_hhmm >= rem_time:
                        DataRepository.update_task(t.TaskID, AlertedOn=today_str)
                        logger.info(f"Task reminder triggered: [{t.TaskID}] {t.TaskName}")
                        event_bus.publish(EVT_TASK_DUE, task_id=t.TaskID, task_name=t.TaskName, due_on=t.DueOn)
                        self.task_due.emit(t.TaskID, t.TaskName or "Untitled Task", t.DueOn)
        except Exception as e:
            logger.error(f"Error checking due tasks in scheduler: {e}")
