"""
Screenshot Annotation Overlay Canvas for DigitalBrainEX AI.
Provides a transparent full-screen drawing canvas, 8-point sizing handles,
vector shapes (Arrow, Rect, Ellipse, Pen, Text), and floating action toolbar.
"""
import math
from typing import List, Optional, Tuple
from PyQt6.QtWidgets import QWidget, QApplication, QInputDialog, QLineEdit
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QBrush,
    QPixmap,
    QPainterPath,
    QFont,
    QKeyEvent,
    QMouseEvent,
)
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal

from src.media.toolbar_widget import AnnotationToolbar, ToolMode
from src.media.screen_capture import ScreenCaptureEngine


class AnnotationItem:
    """Base class for vector annotations drawn over the screenshot."""
    def __init__(self, color: QColor, thickness: int):
        self.color = color
        self.thickness = thickness

    def draw(self, painter: QPainter):
        raise NotImplementedError


class PenItem(AnnotationItem):
    def __init__(self, points: List[QPoint], color: QColor, thickness: int):
        super().__init__(color, thickness)
        self.points = list(points)

    def draw(self, painter: QPainter):
        if len(self.points) < 2:
            return
        pen = QPen(self.color, self.thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(len(self.points) - 1):
            painter.drawLine(self.points[i], self.points[i + 1])


class RectItem(AnnotationItem):
    def __init__(self, rect: QRect, color: QColor, thickness: int):
        super().__init__(color, thickness)
        self.rect = rect

    def draw(self, painter: QPainter):
        pen = QPen(self.color, self.thickness, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(self.rect)


class EllipseItem(AnnotationItem):
    def __init__(self, rect: QRect, color: QColor, thickness: int):
        super().__init__(color, thickness)
        self.rect = rect

    def draw(self, painter: QPainter):
        pen = QPen(self.color, self.thickness, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(self.rect)


class ArrowItem(AnnotationItem):
    def __init__(self, start: QPoint, end: QPoint, color: QColor, thickness: int):
        super().__init__(color, thickness)
        self.start = start
        self.end = end

    def draw(self, painter: QPainter):
        pen = QPen(self.color, self.thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(self.start, self.end)

        # Draw arrowhead
        dx = self.end.x() - self.start.x()
        dy = self.end.y() - self.start.y()
        angle = math.atan2(dy, dx)
        arrow_len = max(14, self.thickness * 3)
        arrow_angle = math.pi / 6  # 30 degrees

        p1 = QPoint(
            int(self.end.x() - arrow_len * math.cos(angle - arrow_angle)),
            int(self.end.y() - arrow_len * math.sin(angle - arrow_angle)),
        )
        p2 = QPoint(
            int(self.end.x() - arrow_len * math.cos(angle + arrow_angle)),
            int(self.end.y() - arrow_len * math.sin(angle + arrow_angle)),
        )

        painter.setBrush(QBrush(self.color))
        arrow_path = QPainterPath()
        arrow_path.moveTo(self.end.x(), self.end.y())
        arrow_path.lineTo(p1.x(), p1.y())
        arrow_path.lineTo(p2.x(), p2.y())
        arrow_path.closeSubpath()
        painter.drawPath(arrow_path)


class TextItem(AnnotationItem):
    def __init__(self, text: str, pos: QPoint, color: QColor, thickness: int):
        super().__init__(color, thickness)
        self.text = text
        self.pos = pos

    def draw(self, painter: QPainter):
        painter.setPen(self.color)
        font = QFont("Segoe UI", max(12, self.thickness * 4), QFont.Weight.Bold)
        painter.setFont(font)
        fm = painter.fontMetrics()
        painter.drawText(self.pos.x() + 4, self.pos.y() + fm.ascent() + 4, self.text)


class AnnotationLineEdit(QLineEdit):
    """Inline text editor placed directly on the screenshot canvas for text annotations."""
    committed = pyqtSignal(str, QPoint)
    canceled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pos = QPoint()
        self._is_finishing = False
        self.setPlaceholderText("Type text and press Enter...")
        self.hide()

    def start_edit(self, pos: QPoint, font: QFont, color: QColor, max_w: int):
        self._is_finishing = False
        self._pos = pos
        self.setFont(font)
        self.setStyleSheet(f"""
            QLineEdit {{
                color: {color.name()};
                background-color: rgba(255, 255, 255, 0.95);
                border: 2px solid #2563eb;
                border-radius: 4px;
                padding: 3px 6px;
                selection-background-color: #2563eb;
                selection-color: #ffffff;
            }}
        """)
        self.clear()
        fm = self.fontMetrics()
        h = fm.height() + 12
        w = max(200, min(max_w, 450))
        self.setGeometry(pos.x(), pos.y(), w, h)
        self.show()
        self.setFocus(Qt.FocusReason.OtherFocusReason)

    def commit_and_close(self):
        if self._is_finishing:
            return
        self._is_finishing = True
        text = self.text().strip()
        self.hide()
        if text:
            self.committed.emit(text, self._pos)
        else:
            self.canceled.emit()

    def cancel_and_close(self):
        if self._is_finishing:
            return
        self._is_finishing = True
        self.hide()
        self.canceled.emit()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.commit_and_close()
            event.accept()
        elif event.key() == Qt.Key.Key_Escape:
            self.cancel_and_close()
            event.accept()
        else:
            super().keyPressEvent(event)

    def focusOutEvent(self, event):
        if not self._is_finishing:
            self.commit_and_close()
        super().focusOutEvent(event)


class OverlayCanvas(QWidget):
    capture_completed = pyqtSignal(str)  # (saved_filepath)

    HANDLE_SIZE = 8

    def __init__(self, parent=None):
        super().__init__(
            parent,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Global escape shortcut as redundant safety layer
        from PyQt6.QtGui import QShortcut, QKeySequence
        self._esc_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self._esc_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self._esc_shortcut.activated.connect(self.close)

        self._desktop_pixmap = QPixmap()
        self._selection_rect = QRect()
        self._is_selecting = False
        self._is_moving = False
        self._active_handle = None
        self._drag_start = QPoint()

        # Annotations
        self._annotations: List[AnnotationItem] = []
        self._current_tool = ToolMode.SELECT
        self._current_color = QColor("#ef4444")
        self._current_thickness = 4
        self._active_points: List[QPoint] = []

        # Floating Toolbar
        self.toolbar = AnnotationToolbar(self)
        self.toolbar.tool_changed.connect(self._on_tool_changed)
        self.toolbar.color_changed.connect(self._on_color_changed)
        self.toolbar.thickness_changed.connect(self._on_thickness_changed)
        self.toolbar.undo_requested.connect(self._undo)
        self.toolbar.done_requested.connect(self._finalize_and_save)
        self.toolbar.cancel_requested.connect(self.close)

        # Inline Text Annotation Editor
        self._text_editor = AnnotationLineEdit(self)
        self._text_editor.committed.connect(self._on_text_committed)
        self._text_editor.canceled.connect(self._on_text_canceled)

    def _on_text_committed(self, text: str, pos: QPoint):
        """Stamps committed text onto canvas as a vector TextItem."""
        self._annotations.append(TextItem(text, pos, self._current_color, self._current_thickness))
        self.update()

    def _on_text_canceled(self):
        self.update()

    def _commit_text_editor(self):
        """Commits any pending active text editor."""
        if hasattr(self, "_text_editor") and self._text_editor.isVisible():
            self._text_editor.commit_and_close()

    def start_capture(self):
        """Grabs the full virtual desktop and displays the transparent overlay."""
        self._desktop_pixmap = ScreenCaptureEngine.capture_full_virtual_desktop()
        virtual_rect = ScreenCaptureEngine.get_virtual_geometry()
        self.setGeometry(virtual_rect)

        self._selection_rect = QRect()
        self._annotations.clear()
        self._current_tool = ToolMode.SELECT
        self.toolbar.hide()
        if hasattr(self, "_text_editor"):
            self._text_editor.hide()

        self.show()
        self.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
        self.activateWindow()
        self.raise_()

    def close(self):
        """Ensures keyboard grab is released, text editor hidden, and toolbar hidden when closing."""
        if hasattr(self, "_text_editor"):
            self._text_editor.hide()
        try:
            self.releaseKeyboard()
        except Exception:
            pass
        if hasattr(self, "toolbar"):
            self.toolbar.hide()
        super().close()

    def closeEvent(self, event):
        """Safely releases keyboard hook and hides children when window closes."""
        if hasattr(self, "_text_editor"):
            self._text_editor.hide()
        try:
            self.releaseKeyboard()
        except Exception:
            pass
        if hasattr(self, "toolbar"):
            self.toolbar.hide()
        super().closeEvent(event)

    def _on_tool_changed(self, tool: ToolMode):
        self._commit_text_editor()
        self._current_tool = tool
        if tool == ToolMode.SELECT:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            self.setCursor(Qt.CursorShape.CrossCursor)

    def _on_color_changed(self, color: QColor):
        self._current_color = color

    def _on_thickness_changed(self, thickness: int):
        self._current_thickness = thickness

    def _undo(self):
        if self._annotations:
            self._annotations.pop()
            self.update()

    def _get_handles(self) -> dict:
        """Returns bounding points for the 8 resize handles."""
        r = self._selection_rect.normalized()
        hs = self.HANDLE_SIZE
        half = hs // 2
        return {
            "TL": QRect(r.left() - half, r.top() - half, hs, hs),
            "TC": QRect(r.center().x() - half, r.top() - half, hs, hs),
            "TR": QRect(r.right() - half, r.top() - half, hs, hs),
            "ML": QRect(r.left() - half, r.center().y() - half, hs, hs),
            "MR": QRect(r.right() - half, r.center().y() - half, hs, hs),
            "BL": QRect(r.left() - half, r.bottom() - half, hs, hs),
            "BC": QRect(r.center().x() - half, r.bottom() - half, hs, hs),
            "BR": QRect(r.right() - half, r.bottom() - half, hs, hs),
        }

    def _get_handle_at(self, pos: QPoint) -> Optional[str]:
        if self._selection_rect.isEmpty():
            return None
        for name, handle_rect in self._get_handles().items():
            if handle_rect.contains(pos):
                return name
        return None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Draw desktop snapshot
        if not self._desktop_pixmap.isNull():
            painter.drawPixmap(0, 0, self._desktop_pixmap)

        # 2. Dim background outside selection
        dim_color = QColor(0, 0, 0, 110)
        if self._selection_rect.isEmpty():
            painter.fillRect(self.rect(), dim_color)
        else:
            norm_rect = self._selection_rect.normalized()
            # Top
            painter.fillRect(0, 0, self.width(), norm_rect.top(), dim_color)
            # Bottom
            painter.fillRect(0, norm_rect.bottom() + 1, self.width(), self.height() - norm_rect.bottom() - 1, dim_color)
            # Left
            painter.fillRect(0, norm_rect.top(), norm_rect.left(), norm_rect.height(), dim_color)
            # Right
            painter.fillRect(norm_rect.right() + 1, norm_rect.top(), self.width() - norm_rect.right() - 1, norm_rect.height(), dim_color)

            # Draw selection bounding border
            pen = QPen(QColor("#2563eb"), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(norm_rect)

            # Draw 8 resize handles
            handle_pen = QPen(QColor("#ffffff"), 1)
            handle_brush = QBrush(QColor("#2563eb"))
            painter.setPen(handle_pen)
            painter.setBrush(handle_brush)
            for handle_rect in self._get_handles().values():
                painter.drawRect(handle_rect)

        # 3. Draw existing annotations
        for ann in self._annotations:
            ann.draw(painter)

        # 4. Draw active in-progress shape
        if self._active_points and len(self._active_points) >= 2:
            if self._current_tool == ToolMode.PEN:
                pen_item = PenItem(self._active_points, self._current_color, self._current_thickness)
                pen_item.draw(painter)
            elif self._current_tool == ToolMode.ARROW:
                arrow_item = ArrowItem(self._active_points[0], self._active_points[-1], self._current_color, self._current_thickness)
                arrow_item.draw(painter)
            elif self._current_tool == ToolMode.RECT:
                rect = QRect(self._active_points[0], self._active_points[-1]).normalized()
                rect_item = RectItem(rect, self._current_color, self._current_thickness)
                rect_item.draw(painter)
            elif self._current_tool == ToolMode.ELLIPSE:
                rect = QRect(self._active_points[0], self._active_points[-1]).normalized()
                ellipse_item = EllipseItem(rect, self._current_color, self._current_thickness)
                ellipse_item.draw(painter)

        painter.end()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.RightButton:
            # Right click cancels active selection or exits overlay immediately
            if not self._selection_rect.isEmpty() or self._annotations:
                self._selection_rect = QRect()
                self._annotations.clear()
                self._active_points = []
                self.toolbar.hide()
                self.update()
            else:
                self.close()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()

            # If text editor was active, commit any pending text
            self._commit_text_editor()

            # If inside annotation mode and inside selection rect
            if self._current_tool != ToolMode.SELECT and not self._selection_rect.isEmpty():
                if self._current_tool == ToolMode.TEXT:
                    font = QFont("Segoe UI", max(12, self._current_thickness * 4), QFont.Weight.Bold)
                    norm_rect = self._selection_rect.normalized()
                    avail_w = max(180, norm_rect.right() - pos.x() - 10)
                    self._text_editor.start_edit(pos, font, self._current_color, avail_w)
                    return
                self._active_points = [pos]
                self.update()
                return

            # Selection / Resizing mode
            handle = self._get_handle_at(pos)
            if handle:
                self._active_handle = handle
                self._drag_start = pos
            elif not self._selection_rect.isEmpty() and self._selection_rect.normalized().contains(pos):
                self._is_moving = True
                self._drag_start = pos
            else:
                self._is_selecting = True
                self._selection_rect = QRect(pos, pos)
                self.toolbar.hide()
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.pos()

        # In-progress drawing
        if self._active_points and self._current_tool != ToolMode.SELECT:
            if self._current_tool == ToolMode.PEN:
                self._active_points.append(pos)
            else:
                if len(self._active_points) == 1:
                    self._active_points.append(pos)
                else:
                    self._active_points[-1] = pos
            self.update()
            return

        # Resizing via handle
        if self._active_handle:
            r = self._selection_rect
            if "L" in self._active_handle:
                r.setLeft(pos.x())
            if "R" in self._active_handle:
                r.setRight(pos.x())
            if "T" in self._active_handle:
                r.setTop(pos.y())
            if "B" in self._active_handle:
                r.setBottom(pos.y())
            self._position_toolbar()
            self.update()
            return

        # Moving selection box
        if self._is_moving:
            diff = pos - self._drag_start
            self._selection_rect.translate(diff)
            self._drag_start = pos
            self._position_toolbar()
            self.update()
            return

        # Creating new selection box
        if self._is_selecting:
            self._selection_rect.setBottomRight(pos)
            self.update()
            return

        # Update cursor on hover
        if self._current_tool == ToolMode.SELECT:
            handle = self._get_handle_at(pos)
            if handle in ("TL", "BR"):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif handle in ("TR", "BL"):
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif handle in ("TC", "BC"):
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            elif handle in ("ML", "MR"):
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif not self._selection_rect.isEmpty() and self._selection_rect.normalized().contains(pos):
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.setCursor(Qt.CursorShape.CrossCursor)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            # Finalize active shape annotation
            if self._active_points and self._current_tool != ToolMode.SELECT:
                if self._current_tool == ToolMode.PEN and len(self._active_points) >= 2:
                    self._annotations.append(PenItem(self._active_points, self._current_color, self._current_thickness))
                elif self._current_tool == ToolMode.ARROW and len(self._active_points) >= 2:
                    self._annotations.append(ArrowItem(self._active_points[0], self._active_points[-1], self._current_color, self._current_thickness))
                elif self._current_tool == ToolMode.RECT and len(self._active_points) >= 2:
                    rect = QRect(self._active_points[0], self._active_points[-1]).normalized()
                    self._annotations.append(RectItem(rect, self._current_color, self._current_thickness))
                elif self._current_tool == ToolMode.ELLIPSE and len(self._active_points) >= 2:
                    rect = QRect(self._active_points[0], self._active_points[-1]).normalized()
                    self._annotations.append(EllipseItem(rect, self._current_color, self._current_thickness))
                self._active_points = []
                self.update()
                return

            self._is_selecting = False
            self._is_moving = False
            self._active_handle = None

            # Normalize selection
            self._selection_rect = self._selection_rect.normalized()
            if self._selection_rect.width() > 10 and self._selection_rect.height() > 10:
                self._position_toolbar()
                self.toolbar.show()
                self.toolbar.raise_()
            else:
                self.toolbar.hide()
            self.update()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        # Double clicking selection box captures and saves immediately
        if not self._selection_rect.isEmpty() and self._selection_rect.contains(event.pos()):
            self._finalize_and_save()

    def keyPressEvent(self, event: QKeyEvent):
        if hasattr(self, "_text_editor") and self._text_editor.isVisible():
            super().keyPressEvent(event)
            return

        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._finalize_and_save()
        elif event.key() == Qt.Key.Z and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self._undo()
        else:
            super().keyPressEvent(event)

    def _position_toolbar(self):
        """Positions the floating toolbar right beneath or above the selection box in global coordinates."""
        r = self._selection_rect.normalized()
        if r.isEmpty():
            return

        self.toolbar.adjustSize()
        tb_size = self.toolbar.sizeHint()
        tb_w = max(tb_size.width(), self.toolbar.width())
        tb_h = max(tb_size.height(), self.toolbar.height())

        # Map local selection rectangle to global virtual desktop coordinates
        global_tl = self.mapToGlobal(r.topLeft())
        global_br = self.mapToGlobal(r.bottomRight())
        global_rect = QRect(global_tl, global_br)

        # Detect the screen where the selection was drawn
        screen = QApplication.screenAt(global_rect.center())
        if not screen:
            screen = QApplication.screenAt(global_rect.topLeft())
        if not screen:
            screen = QApplication.primaryScreen()

        screen_geom = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)

        # Calculate position centered horizontally with the selection
        gx = global_rect.center().x() - tb_w // 2
        gy = global_rect.bottom() + 10

        # Boundary checks: if overflowing bottom of this screen, flip above selection
        if gy + tb_h > screen_geom.bottom() - 8:
            gy = global_rect.top() - tb_h - 10
            # If also above top of screen, place inside selection at bottom
            if gy < screen_geom.top() + 8:
                gy = max(screen_geom.top() + 8, min(global_rect.bottom() - tb_h - 10, screen_geom.bottom() - tb_h - 8))

        # Clamp horizontally within this monitor's visible boundary
        gx = max(screen_geom.left() + 8, min(gx, screen_geom.right() - tb_w - 8))
        gy = max(screen_geom.top() + 8, min(gy, screen_geom.bottom() - tb_h - 8))

        self.toolbar.move(gx, gy)

    def _finalize_and_save(self):
        """Renders the selection rectangle and all vector annotations, then saves to disk."""
        self._commit_text_editor()
        target_rect = self._selection_rect.normalized()
        if target_rect.isEmpty():
            target_rect = self.rect()

        # Determine DPI scaling factor
        dpr = self._desktop_pixmap.devicePixelRatio() if not self._desktop_pixmap.isNull() else self.devicePixelRatio()
        if dpr <= 0:
            dpr = 1.0

        # Physical pixel dimensions for high-DPI crisp capture
        phys_w = max(1, int(round(target_rect.width() * dpr)))
        phys_h = max(1, int(round(target_rect.height() * dpr)))

        rendered_pixmap = QPixmap(phys_w, phys_h)
        rendered_pixmap.setDevicePixelRatio(dpr)
        rendered_pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(rendered_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw source desktop pixmap offset so target_rect starts at (0, 0) in logical coordinates
        painter.drawPixmap(-target_rect.x(), -target_rect.y(), self._desktop_pixmap)

        # Offset painter to match annotations relative to selection top-left
        painter.translate(-target_rect.x(), -target_rect.y())
        for ann in self._annotations:
            ann.draw(painter)
        painter.end()

        # Save and copy
        saved_path = ScreenCaptureEngine.save_and_copy_screenshot(rendered_pixmap)

        self.toolbar.hide()
        self.close()
        self.capture_completed.emit(saved_path)
