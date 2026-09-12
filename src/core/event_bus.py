"""
Event Bus for DigitalBrainEX AI.
Provides decoupled publish/subscribe mechanism across background worker threads and UI views.
"""
from typing import Callable, Dict, List
import threading
from src.core.logger import logger


class EventBus:
    """Thread-safe event bus for publishing and subscribing to application events."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()

    def subscribe(self, event_name: str, callback: Callable):
        """Subscribes a callable to an event."""
        with self._lock:
            if event_name not in self._subscribers:
                self._subscribers[event_name] = []
            if callback not in self._subscribers[event_name]:
                self._subscribers[event_name].append(callback)

    def unsubscribe(self, event_name: str, callback: Callable):
        """Unsubscribes a callable from an event."""
        with self._lock:
            if event_name in self._subscribers and callback in self._subscribers[event_name]:
                self._subscribers[event_name].remove(callback)

    def publish(self, event_name: str, *args, **kwargs):
        """Publishes an event to all subscribers."""
        with self._lock:
            subscribers = list(self._subscribers.get(event_name, []))

        for cb in subscribers:
            try:
                cb(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error invoking subscriber {cb} for event '{event_name}': {e}", exc_info=True)


# Global singleton event bus
event_bus = EventBus()

# Standard Event Names
EVT_PROJECT_CHANGED = "project.changed"
EVT_CLIPBOARD_NEW = "clipboard.new"
EVT_TASK_DUE = "task.due"
EVT_TASK_UPDATED = "task.updated"
EVT_WINDOW_TRACKED = "window.tracked"
EVT_WATCH_FOLDER_FILE = "watchfolder.file"
EVT_SCREENSHOT_TAKEN = "screenshot.taken"
