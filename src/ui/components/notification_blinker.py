"""
Floating Notification Border Blinker for DigitalBrainEX AI.
A topmost, frameless, non-focus-stealing screen border that flashes to alert
the user of imminent task deadlines or incoming background alerts.
"""
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen


class NotificationBlinker(QWidget):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(
            parent,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        self._flash_count = 0
        self._max_flashes = 12
        self._is_on = False
        self._border_color = QColor("#ed8796")  # Danger soft coral red
        self._border_width = 8

        self._timer = QTimer(self)
        self._timer.setInterval(400)  # 400ms per blink
        self._timer.timeout.connect(self._on_blink_tick)

    def start_blink(self, color: str = "#ed8796", flashes: int = 12):
        """Starts the flashing screen border."""
        self._border_color = QColor(color)
        self._max_flashes = flashes
        self._flash_count = 0
        self._is_on = True

        # Position over the primary screen geometry
        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())

        self.show()
        self._timer.start()

    def stop_blink(self):
        """Stops flashing and hides the window."""
        self._timer.stop()
        self.hide()

    def _on_blink_tick(self):
        self._is_on = not self._is_on
        self._flash_count += 1
        self.update()

        if self._flash_count >= self._max_flashes:
            self.stop_blink()

    def paintEvent(self, event):
        if not self._is_on:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = QPen(self._border_color, self._border_width)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        half_w = self._border_width // 2
        painter.drawRect(
            half_w,
            half_w,
            self.width() - self._border_width,
            self.height() - self._border_width,
        )
        painter.end()

    def mousePressEvent(self, event):
        self.stop_blink()
        self.clicked.emit()
