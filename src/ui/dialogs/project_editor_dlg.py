"""
Dedicated Project Editor Popup Dialog for DigitalBrainEX AI.
Matches original AddProject.cs popup dialog.
"""
from typing import Optional
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QComboBox,
    QDateEdit,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QDate

from src.core.repository import DataRepository
from src.core.logger import logger


class ProjectEditorDialog(QDialog):
    def __init__(self, parent=None, project_id: Optional[int] = None):
        super().__init__(parent)
        self.project_id = project_id
        self.saved_project_id: Optional[int] = None

        self.setWindowTitle("Edit Project" if self.project_id else "New Project")
        self.setMinimumSize(560, 440)
        self.resize(600, 480)
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # Header Title
        title_text = "✏️ Edit Project" if self.project_id else "📁 Create New Project"
        header = QLabel(title_text)
        header.setObjectName("ViewTitleLabel")
        layout.addWidget(header)

        # Project Name
        layout.addWidget(QLabel("Project Name:"))
        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("Enter project name...")
        layout.addWidget(self.edit_name)

        # Metadata Row: Start Date + Status
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(14)

        date_col = QVBoxLayout()
        date_col.addWidget(QLabel("Start Date:"))
        self.edit_date = QDateEdit()
        self.edit_date.setCalendarPopup(True)
        self.edit_date.setDate(QDate.currentDate())
        date_col.addWidget(self.edit_date)
        meta_layout.addLayout(date_col, stretch=1)

        status_col = QVBoxLayout()
        status_col.addWidget(QLabel("Status:"))
        self.combo_status = QComboBox()
        self.combo_status.addItems(["Active", "Closed"])
        status_col.addWidget(self.combo_status)
        meta_layout.addLayout(status_col, stretch=1)

        layout.addLayout(meta_layout)

        # Description / Scope
        layout.addWidget(QLabel("Description / Project Scope:"))
        self.edit_desc = QTextEdit()
        self.edit_desc.setPlaceholderText("Enter project goals, deliverables, or notes...")
        layout.addWidget(self.edit_desc, stretch=1)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("💾 Save Project")
        self.btn_save.setObjectName("PrimaryButton")
        self.btn_save.clicked.connect(self._save_project)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _load_data(self):
        if self.project_id:
            p = DataRepository.get_project_by_id(self.project_id)
            if p:
                self.edit_name.setText(p.ProjectName or "")
                self.edit_desc.setPlainText(p.Desc or "")
                idx = self.combo_status.findText(p.Status or "Active")
                if idx >= 0:
                    self.combo_status.setCurrentIndex(idx)
                if p.StartDate:
                    try:
                        qdate = QDate.fromString(p.StartDate[:10], "yyyy-MM-dd")
                        if qdate.isValid():
                            self.edit_date.setDate(qdate)
                    except Exception:
                        pass

    def _save_project(self):
        name = self.edit_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Please enter a Project Name.")
            self.edit_name.setFocus()
            return

        date_str = self.edit_date.date().toString("yyyy-MM-dd")
        status = self.combo_status.currentText()
        desc = self.edit_desc.toPlainText()

        try:
            if self.project_id:
                DataRepository.update_project(
                    self.project_id,
                    ProjectName=name,
                    StartDate=date_str,
                    Status=status,
                    Desc=desc,
                )
                self.saved_project_id = self.project_id
            else:
                new_proj = DataRepository.create_project(
                    name=name,
                    desc=desc,
                    start_date=date_str,
                    status=status,
                )
                self.saved_project_id = new_proj.PojectID

            self.accept()
        except Exception as e:
            logger.error(f"Error saving project: {e}")
            QMessageBox.critical(self, "Save Error", f"Failed to save project:\n{e}")
