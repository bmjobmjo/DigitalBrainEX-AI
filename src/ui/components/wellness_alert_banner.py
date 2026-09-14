"""
On-screen animated flash banner for Wellness & Health Reminders.
Flashes briefly only once on timeout to alert user to drink water or stand & stretch.
Non-intrusive, auto-fades after 5 seconds, does not steal keyboard focus.
"""
import math
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QGraphicsOpacityEffect,
    QApplication,
    QFrame,
)
from PyQt6.QtCore import (
    Qt,
    QTimer,
    QPropertyAnimation,
    QEasingCurve,
    QPoint,
    QRect,
    pyqtSignal,
)
from PyQt6.QtGui import QPainter, QColor, QFont, QPixmap
from src.ui.icons import IconHelper


class PulsingIconWidget(QWidget):
    """An animated vector icon widget that smoothly pulses in size and glow."""

    def __init__(self, icon_name: str, base_color: str, parent=None):
        super().__init__(parent)
        self._icon_name = icon_name
        self._base_color = QColor(base_color)
        self._scale = 1.0
        self._phase = 0.0
        self.setFixedSize(60, 60)

        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(30)  # ~33 FPS
        self._anim_timer.timeout.connect(self._on_anim_step)
        self._anim_timer.start()

    def _on_anim_step(self):
        self._phase += 0.08
        # Gentle sine pulse between 0.92 and 1.08
        self._scale = 1.0 + 0.08 * math.sin(self._phase)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center_x = self.width() / 2.0
        center_y = self.height() / 2.0

        # Draw soft outer glow ring
        glow_radius = 24.0 * self._scale
        glow_alpha = int(35 + 25 * math.sin(self._phase))
        glow_color = QColor(self._base_color)
        glow_color.setAlpha(glow_alpha)
        painter.setBrush(glow_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPoint(int(center_x), int(center_y)), int(glow_radius), int(glow_radius))

        # Render icon at scaled dimension
        pix_size = int(36 * self._scale)
        pm = IconHelper.get_pixmap(self._icon_name, pix_size)
        if not pm.isNull():
            draw_x = int(center_x - pix_size / 2.0)
            draw_y = int(center_y - pix_size / 2.0)
            painter.drawPixmap(draw_x, draw_y, pm)
        painter.end()


class WellnessAlertBanner(QWidget):
    """
    Floating animated toast banner that flashes on screen briefly only once on timeout.
    """
    snooze_requested = pyqtSignal(str)   # (alert_type)
    dismiss_requested = pyqtSignal(str)  # (alert_type)

    def __init__(self, alert_type: str, title: str, message: str, parent=None):
        super().__init__(
            parent,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self._alert_type = alert_type
        self._is_closing = False

        self._init_ui(alert_type, title, message)

        # Fade in animation
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._opacity_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._opacity_anim.setDuration(350)
        self._opacity_anim.setStartValue(0.0)
        self._opacity_anim.setEndValue(1.0)
        self._opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Auto-dismiss timer: stays visible for 5.5 seconds then auto-fades
        self._auto_close_timer = QTimer(self)
        self._auto_close_timer.setSingleShot(True)
        self._auto_close_timer.setInterval(5500)
        self._auto_close_timer.timeout.connect(self._on_auto_close_timeout)

    def _init_ui(self, alert_type: str, title: str, message: str):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(10, 10, 10, 10)

        # Card container with shadow border
        card = QFrame()
        card_border = "#0284c7" if alert_type == "water" else "#ea580c"
        card.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(255, 255, 255, 0.97);
                border: 2px solid {card_border};
                border-radius: 12px;
            }}
        """)

        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 16, 12)
        card_layout.setSpacing(14)

        # Animated pulsing icon
        icon_name = "water_drop" if alert_type == "water" else "sedentary_walk"
        base_color = "#0284c7" if alert_type == "water" else "#ea580c"
        self._pulse_widget = PulsingIconWidget(icon_name, base_color, card)
        card_layout.addWidget(self._pulse_widget)

        # Text information
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {base_color}; background: transparent; border: none;")
        text_layout.addWidget(lbl_title)

        lbl_msg = QLabel(message)
        lbl_msg.setWordWrap(True)
        lbl_msg.setStyleSheet("font-size: 12px; color: #334155; background: transparent; border: none;")
        text_layout.addWidget(lbl_msg)

        card_layout.addLayout(text_layout, 1)

        # Action buttons
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(6)

        btn_done = QPushButton("✓ Done")
        btn_done.setStyleSheet(f"""
            QPushButton {{
                background-color: {base_color};
                color: #ffffff;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 5px 12px;
                min-width: 68px;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
        """)
        btn_done.clicked.connect(self._on_done_clicked)
        btn_layout.addWidget(btn_done)

        btn_snooze = QPushButton("⏰ Snooze 5m")
        btn_snooze.setStyleSheet("""
            QPushButton {{
                background-color: #f1f5f9;
                color: #475569;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: #e2e8f0;
            }}
        """)
        btn_snooze.clicked.connect(self._on_snooze_clicked)
        btn_layout.addWidget(btn_snooze)

        card_layout.addLayout(btn_layout)
        outer_layout.addWidget(card)

        self.setFixedWidth(460)

    def show_alert(self):
        """Positions banner at top-center of primary screen and plays fade-in."""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geom = screen.availableGeometry()
            x = screen_geom.center().x() - self.width() // 2
            y = screen_geom.top() + 30
            self.move(x, y)

        self.show()
        self._opacity_anim.start()
        self._auto_close_timer.start()

    def _on_done_clicked(self):
        self.dismiss_requested.emit(self._alert_type)
        self.fade_out_and_close()

    def _on_snooze_clicked(self):
        self.snooze_requested.emit(self._alert_type)
        self.fade_out_and_close()

    def _on_auto_close_timeout(self):
        self.dismiss_requested.emit(self._alert_type)
        self.fade_out_and_close()

    def fade_out_and_close(self):
        if self._is_closing:
            return
        self._is_closing = True
        self._auto_close_timer.stop()

        self._fade_out_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_out_anim.setDuration(400)
        self._fade_out_anim.setStartValue(self._opacity_effect.opacity())
        self._fade_out_anim.setEndValue(0.0)
        self._fade_out_anim.setEasingCurve(QEasingCurve.Type.InCubic)

        def _cleanup():
            global _active_banner
            if _active_banner is self:
                _active_banner = None
            self.close()

        self._fade_out_anim.finished.connect(_cleanup)
        self._fade_out_anim.start()


# Active banner reference
_active_banner = None


def flash_wellness_alert(alert_type: str, title: str, message: str, on_dismiss=None, on_snooze=None):
    """Flashes a wellness alert banner on the screen briefly only once on timeout."""
    global _active_banner
    if _active_banner is not None:
        try:
            _active_banner.close()
        except Exception:
            pass

    banner = WellnessAlertBanner(alert_type, title, message)
    if on_dismiss:
        banner.dismiss_requested.connect(on_dismiss)
    if on_snooze:
        banner.snooze_requested.connect(on_snooze)

    _active_banner = banner
    banner.show_alert()
    return banner
