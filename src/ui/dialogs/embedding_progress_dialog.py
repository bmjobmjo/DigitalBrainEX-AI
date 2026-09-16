"""
Dedicated Modal Progress Dialog for Processing Document Embeddings in DigitalBrainEX AI.
Features dual progress bars:
1. Overall progress tracking number of files/notes processed with live counters.
2. Current file/note progress tracking intra-item parsing, chunking, and vectorizing.
"""
from typing import Optional
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QFrame,
    QListWidget,
    QMessageBox,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QCloseEvent

from src.ui.icons import IconHelper


class EmbeddingProgressDialog(QDialog):
    """
    Modal dialog displaying dual progress bars and real-time activity
    for background document embedding operations.
    """

    cancel_requested = pyqtSignal()

    def __init__(self, total_docs: int = 0, title: str = "Processing Document Embeddings", parent=None):
        super().__init__(parent)
        self.total_docs = total_docs
        self.succeeded_count = 0
        self.failed_count = 0
        self.is_finished = False
        self.is_cancelling = False

        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumSize(580, 480)
        self.resize(620, 520)

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(22, 20, 22, 20)
        main_layout.setSpacing(14)

        # ---------------------------------------------------------------------
        # 1. Header Section
        # ---------------------------------------------------------------------
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(IconHelper.get_icon("ai", 32).pixmap(32, 32))
        header_layout.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        lbl_title = QLabel("Document Vector Indexing")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0f172a;")
        title_col.addWidget(lbl_title)

        lbl_sub = QLabel("Generating AI embeddings for semantic search & AskMe Assistant")
        lbl_sub.setStyleSheet("font-size: 12px; color: #64748b;")
        title_col.addWidget(lbl_sub)
        header_layout.addLayout(title_col, stretch=1)

        main_layout.addLayout(header_layout)

        # Subtle separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setFrameShadow(QFrame.Shadow.Sunken)
        sep1.setStyleSheet("color: #e2e8f0;")
        main_layout.addWidget(sep1)

        # ---------------------------------------------------------------------
        # 2. Overall Progress (Number of files/notes processed)
        # ---------------------------------------------------------------------
        overall_box = QVBoxLayout()
        overall_box.setSpacing(6)

        lbl_row = QHBoxLayout()
        lbl_overall_title = QLabel("Overall Progress (Documents & Notes):")
        lbl_overall_title.setStyleSheet("font-weight: 600; font-size: 13px; color: #1e293b;")
        lbl_row.addWidget(lbl_overall_title)

        self.lbl_overall_pct = QLabel(f"0 / {self.total_docs} (0%)")
        self.lbl_overall_pct.setStyleSheet("font-weight: 600; font-size: 13px; color: #2563eb;")
        lbl_row.addWidget(self.lbl_overall_pct, alignment=Qt.AlignmentFlag.AlignRight)
        overall_box.addLayout(lbl_row)

        self.bar_overall = QProgressBar()
        self.bar_overall.setRange(0, max(1, self.total_docs))
        self.bar_overall.setValue(0)
        self.bar_overall.setFixedHeight(22)
        self.bar_overall.setTextVisible(True)
        self.bar_overall.setStyleSheet("""
            QProgressBar {
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                text-align: center;
                background-color: #f1f5f9;
                font-weight: bold;
                color: #0f172a;
            }
            QProgressBar::chunk {
                background-color: #2563eb;
                border-radius: 5px;
            }
        """)
        overall_box.addWidget(self.bar_overall)

        # Stats chips row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)

        self.lbl_succeeded = QLabel("✅ Succeeded: 0")
        self.lbl_succeeded.setStyleSheet("color: #16a34a; font-weight: 600; font-size: 12px;")
        stats_row.addWidget(self.lbl_succeeded)

        self.lbl_failed = QLabel("❌ Failed: 0")
        self.lbl_failed.setStyleSheet("color: #dc2626; font-weight: 600; font-size: 12px;")
        stats_row.addWidget(self.lbl_failed)

        self.lbl_remaining = QLabel(f"⏳ Remaining: {self.total_docs}")
        self.lbl_remaining.setStyleSheet("color: #64748b; font-weight: 500; font-size: 12px;")
        stats_row.addWidget(self.lbl_remaining)

        stats_row.addStretch()
        overall_box.addLayout(stats_row)
        main_layout.addLayout(overall_box)

        # ---------------------------------------------------------------------
        # 3. Current File / Note Progress Section
        # ---------------------------------------------------------------------
        current_frame = QFrame()
        current_frame.setStyleSheet("""
            QFrame {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
            }
        """)
        curr_layout = QVBoxLayout(current_frame)
        curr_layout.setContentsMargins(14, 12, 14, 12)
        curr_layout.setSpacing(8)

        item_row = QHBoxLayout()
        item_prefix = QLabel("Active Item:")
        item_prefix.setStyleSheet("font-weight: 600; color: #475569; font-size: 12px; border: none;")
        item_row.addWidget(item_prefix)

        self.lbl_current_item = QLabel("Initializing background worker...")
        self.lbl_current_item.setStyleSheet("font-weight: bold; color: #0f172a; font-size: 12px; border: none;")
        self.lbl_current_item.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        item_row.addWidget(self.lbl_current_item, stretch=1)
        curr_layout.addLayout(item_row)

        self.lbl_current_stage = QLabel("Preparing to parse...")
        self.lbl_current_stage.setStyleSheet("color: #64748b; font-size: 11px; border: none;")
        curr_layout.addWidget(self.lbl_current_stage)

        # Progress bar for the current file / note
        self.bar_current = QProgressBar()
        self.bar_current.setRange(0, 100)
        self.bar_current.setValue(0)
        self.bar_current.setFixedHeight(16)
        self.bar_current.setTextVisible(True)
        self.bar_current.setStyleSheet("""
            QProgressBar {
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                text-align: center;
                background-color: #ffffff;
                font-size: 10px;
                color: #0f172a;
            }
            QProgressBar::chunk {
                background-color: #0ea5e9;
                border-radius: 3px;
            }
        """)
        curr_layout.addWidget(self.bar_current)
        main_layout.addWidget(current_frame)

        # ---------------------------------------------------------------------
        # 4. Activity Log Feed
        # ---------------------------------------------------------------------
        lbl_log_title = QLabel("Activity Log:")
        lbl_log_title.setStyleSheet("font-weight: 600; font-size: 12px; color: #334155;")
        main_layout.addWidget(lbl_log_title)

        self.list_activity = QListWidget()
        self.list_activity.setFixedHeight(100)
        self.list_activity.setStyleSheet("""
            QListWidget {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                color: #334155;
                padding: 4px;
            }
            QListWidget::item {
                padding: 2px 4px;
            }
        """)
        main_layout.addWidget(self.list_activity)

        # ---------------------------------------------------------------------
        # 5. Bottom Controls (Status message, Cancel, Close)
        # ---------------------------------------------------------------------
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)

        self.lbl_bottom_status = QLabel("Processing documents...")
        self.lbl_bottom_status.setStyleSheet("color: #475569; font-size: 12px; font-style: italic;")
        bottom_row.addWidget(self.lbl_bottom_status, stretch=1)

        self.btn_cancel = QPushButton("Cancel Indexing")
        self.btn_cancel.setIcon(IconHelper.get_icon("delete", 14))
        self.btn_cancel.setMinimumHeight(30)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #fef2f2;
                border: 1px solid #fca5a5;
                color: #b91c1c;
                font-weight: 600;
                border-radius: 6px;
                padding: 4px 14px;
            }
            QPushButton:hover {
                background-color: #fee2e2;
            }
            QPushButton:disabled {
                background-color: #f1f5f9;
                border-color: #e2e8f0;
                color: #94a3b8;
            }
        """)
        self.btn_cancel.clicked.connect(self._on_cancel_clicked)
        bottom_row.addWidget(self.btn_cancel)

        self.btn_close = QPushButton("Close")
        self.btn_close.setIcon(IconHelper.get_icon("check", 14))
        self.btn_close.setMinimumHeight(30)
        self.btn_close.setEnabled(False)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                border: 1px solid #1d4ed8;
                color: #ffffff;
                font-weight: 600;
                border-radius: 6px;
                padding: 4px 18px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton:disabled {
                background-color: #e2e8f0;
                border-color: #cbd5e1;
                color: #94a3b8;
            }
        """)
        self.btn_close.clicked.connect(self.accept)
        bottom_row.addWidget(self.btn_close)

        main_layout.addLayout(bottom_row)

    # -------------------------------------------------------------------------
    # Public Slots for Worker Communication
    # -------------------------------------------------------------------------
    def update_overall_progress(self, current: int, total: int, succeeded: int, failed: int):
        """Updates the overall files progress bar and count labels."""
        self.total_docs = max(total, self.total_docs)
        self.succeeded_count = succeeded
        self.failed_count = failed

        self.bar_overall.setRange(0, max(1, self.total_docs))
        self.bar_overall.setValue(current)

        pct = (current / self.total_docs * 100.0) if self.total_docs > 0 else 0.0
        self.lbl_overall_pct.setText(f"{current} / {self.total_docs} ({pct:.1f}%)")

        self.lbl_succeeded.setText(f"✅ Succeeded: {succeeded}")
        self.lbl_failed.setText(f"❌ Failed: {failed}")
        remaining = max(0, self.total_docs - current)
        self.lbl_remaining.setText(f"⏳ Remaining: {remaining}")

    def update_item_progress(self, doc_name: str, stage_desc: str, current_step: int, total_steps: int):
        """Updates progress and status for the current active file or note."""
        display_name = doc_name if len(doc_name) <= 60 else doc_name[:57] + "..."
        self.lbl_current_item.setText(display_name)
        self.lbl_current_item.setToolTip(doc_name)

        self.lbl_current_stage.setText(stage_desc)

        self.bar_current.setRange(0, max(1, total_steps))
        self.bar_current.setValue(current_step)

    def append_log(self, message: str):
        """Adds an entry to the live activity feed."""
        self.list_activity.addItem(message)
        self.list_activity.scrollToBottom()

    def on_finished(self, total: int, succeeded: int):
        """Called when the background worker finishes all tasks or is stopped."""
        self.is_finished = True
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setVisible(False)
        self.btn_close.setEnabled(True)
        self.btn_close.setFocus()

        if self.is_cancelling:
            self.lbl_bottom_status.setText(f"Stopped by user. {succeeded}/{total} documents indexed.")
            self.lbl_bottom_status.setStyleSheet("color: #d97706; font-weight: bold;")
        else:
            self.lbl_bottom_status.setText(f"Indexing completed! {succeeded}/{total} documents successfully indexed.")
            self.lbl_bottom_status.setStyleSheet("color: #16a34a; font-weight: bold;")
            self.bar_overall.setValue(total)
            self.bar_current.setValue(100)
            self.lbl_current_stage.setText("All tasks completed.")

    # -------------------------------------------------------------------------
    # Internal Handlers
    # -------------------------------------------------------------------------
    def _on_cancel_clicked(self):
        if self.is_finished or self.is_cancelling:
            return

        confirm = QMessageBox.question(
            self,
            "Cancel Embedding",
            "Are you sure you want to stop indexing?\n\nDocuments already indexed will be preserved.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.is_cancelling = True
            self.btn_cancel.setEnabled(False)
            self.btn_cancel.setText("Stopping...")
            self.lbl_bottom_status.setText("Stopping indexing after current document completes...")
            self.lbl_bottom_status.setStyleSheet("color: #d97706; font-style: italic;")
            self.cancel_requested.emit()

    def closeEvent(self, event: QCloseEvent):
        """Prevents closing the modal dialog mid-process without confirmation."""
        if self.isVisible() and not self.is_finished and not self.is_cancelling:
            confirm = QMessageBox.question(
                self,
                "Cancel Indexing?",
                "Document indexing is actively in progress in the background.\n\n"
                "Do you want to cancel indexing and close?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if confirm == QMessageBox.StandardButton.Yes:
                self._on_cancel_clicked()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
