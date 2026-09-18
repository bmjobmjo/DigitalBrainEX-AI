"""
Floating Annotation Toolbar for DigitalBrainEX AI Screen Capture.
Provides tool selection (Arrow, Rect, Pen, Text, Ellipse), color picker, and actions.
"""
from enum import Enum, auto
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
    QColorDialog,
    QComboBox,
    QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor


class ToolMode(Enum):
    SELECT = auto()
    PEN = auto()
    ARROW = auto()
    RECT = auto()
    ELLIPSE = auto()
    TEXT = auto()


class AnnotationToolbar(QWidget):
    tool_changed = pyqtSignal(ToolMode)
    color_changed = pyqtSignal(QColor)
    thickness_changed = pyqtSignal(int)
    undo_requested = pyqtSignal()
    done_requested = pyqtSignal()
    save_file_requested = pyqtSignal()
    save_dbx_requested = pyqtSignal()
    cancel_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setObjectName("AnnotationToolbar")
        self._current_color = QColor("#ef4444")  # Coral red default
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(
            "#AnnotationToolbar { background-color: #ffffff; border: 1px solid #c8ccd1; border-radius: 8px; } "
            "QPushButton { background-color: #f8fafc; color: #1e293b; border: 1px solid #c8ccd1; border-radius: 4px; padding: 5px 8px; min-height: 18px; } "
            "QPushButton:hover { background-color: #e2e8f0; border-color: #2563eb; } "
            "QPushButton:checked { background-color: #2563eb; color: #ffffff; font-weight: bold; border-color: #2563eb; } "
            "QComboBox { background-color: #ffffff; color: #1e293b; border: 1px solid #c8ccd1; border-radius: 4px; padding: 2px 6px; }"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        # Tool buttons
        self.btn_select = QPushButton("↖")
        self.btn_select.setToolTip("Select & Resize (Move selection)")
        self.btn_select.setCheckable(True)
        self.btn_select.setChecked(True)
        self.btn_select.clicked.connect(lambda: self._set_tool(ToolMode.SELECT))
        layout.addWidget(self.btn_select)

        self.btn_pen = QPushButton("✏️")
        self.btn_pen.setToolTip("Freehand Drawing")
        self.btn_pen.setCheckable(True)
        self.btn_pen.clicked.connect(lambda: self._set_tool(ToolMode.PEN))
        layout.addWidget(self.btn_pen)

        self.btn_arrow = QPushButton("↗")
        self.btn_arrow.setToolTip("Arrow Callout")
        self.btn_arrow.setCheckable(True)
        self.btn_arrow.clicked.connect(lambda: self._set_tool(ToolMode.ARROW))
        layout.addWidget(self.btn_arrow)

        self.btn_rect = QPushButton("▭")
        self.btn_rect.setToolTip("Rectangle Box")
        self.btn_rect.setCheckable(True)
        self.btn_rect.clicked.connect(lambda: self._set_tool(ToolMode.RECT))
        layout.addWidget(self.btn_rect)

        self.btn_ellipse = QPushButton("◯")
        self.btn_ellipse.setToolTip("Circle / Ellipse")
        self.btn_ellipse.setCheckable(True)
        self.btn_ellipse.clicked.connect(lambda: self._set_tool(ToolMode.ELLIPSE))
        layout.addWidget(self.btn_ellipse)

        self.btn_text = QPushButton("🔤")
        self.btn_text.setToolTip("Add Text Annotation")
        self.btn_text.setCheckable(True)
        self.btn_text.clicked.connect(lambda: self._set_tool(ToolMode.TEXT))
        layout.addWidget(self.btn_text)

        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setStyleSheet("color: #cbd5e1;")
        layout.addWidget(sep1)

        # Color picker button
        self.btn_color = QPushButton("🎨")
        self.btn_color.setToolTip("Pick Annotation Color")
        self.btn_color.setStyleSheet(f"border-bottom: 3px solid {self._current_color.name()};")
        self.btn_color.clicked.connect(self._pick_color)
        layout.addWidget(self.btn_color)

        # Thickness Combo
        self.combo_thickness = QComboBox()
        self.combo_thickness.addItem("2px", 2)
        self.combo_thickness.addItem("4px", 4)
        self.combo_thickness.addItem("6px", 6)
        self.combo_thickness.addItem("8px", 8)
        self.combo_thickness.setCurrentIndex(1)  # 4px default
        self.combo_thickness.currentIndexChanged.connect(self._on_thickness_changed)
        layout.addWidget(self.combo_thickness)

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet("color: #cbd5e1;")
        layout.addWidget(sep2)

        # Undo button
        self.btn_undo = QPushButton("↩ Undo")
        self.btn_undo.setToolTip("Undo Last Annotation (Ctrl+Z)")
        self.btn_undo.clicked.connect(self.undo_requested.emit)
        layout.addWidget(self.btn_undo)

        # Separator
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.VLine)
        sep3.setStyleSheet("color: #cbd5e1;")
        layout.addWidget(sep3)

        # Save As File button
        self.btn_save_file = QPushButton("💾 Save As...")
        self.btn_save_file.setToolTip("Save Screenshot as File (Ctrl+S)")
        self.btn_save_file.clicked.connect(self.save_file_requested.emit)
        layout.addWidget(self.btn_save_file)

        # Save to DigitalBrainEX button
        self.btn_save_dbx = QPushButton("📥 Add to DBX")
        self.btn_save_dbx.setToolTip("Save Screenshot to DigitalBrainEX Documents (Ctrl+D)")
        self.btn_save_dbx.clicked.connect(self.save_dbx_requested.emit)
        layout.addWidget(self.btn_save_dbx)

        # Copy & Quick Save button
        self.btn_done = QPushButton("📋 Copy")
        self.btn_done.setStyleSheet("background-color: #16a34a; color: #ffffff; font-weight: bold; border: 1px solid #16a34a;")
        self.btn_done.setToolTip("Copy to Clipboard & Auto-Save (Enter / Ctrl+C)")
        self.btn_done.clicked.connect(self.done_requested.emit)
        layout.addWidget(self.btn_done)

        # Cancel button
        self.btn_cancel = QPushButton("✕")
        self.btn_cancel.setStyleSheet("background-color: #ffffff; color: #dc2626; border: 1px solid #fca5a5; font-weight: bold;")
        self.btn_cancel.setToolTip("Cancel (Esc)")
        self.btn_cancel.clicked.connect(self.cancel_requested.emit)
        layout.addWidget(self.btn_cancel)

    def _set_tool(self, mode: ToolMode):
        self.btn_select.setChecked(mode == ToolMode.SELECT)
        self.btn_pen.setChecked(mode == ToolMode.PEN)
        self.btn_arrow.setChecked(mode == ToolMode.ARROW)
        self.btn_rect.setChecked(mode == ToolMode.RECT)
        self.btn_ellipse.setChecked(mode == ToolMode.ELLIPSE)
        self.btn_text.setChecked(mode == ToolMode.TEXT)
        self.tool_changed.emit(mode)

    def _pick_color(self):
        col = QColorDialog.getColor(self._current_color, self, "Pick Annotation Color")
        if col.isValid():
            self._current_color = col
            self.btn_color.setStyleSheet(f"border-bottom: 3px solid {col.name()};")
            self.color_changed.emit(col)

    def _on_thickness_changed(self, index: int):
        val = self.combo_thickness.currentData() or 4
        self.thickness_changed.emit(val)
