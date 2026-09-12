"""
Dedicated URL / Bookmark Editor Popup Dialog for DigitalBrainEX AI.
Matches original AddUrl.cs popup dialog.
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
    QMessageBox,
)
from PyQt6.QtCore import Qt

from src.core.repository import DataRepository
from src.core.logger import logger


class UrlEditorDialog(QDialog):
    def __init__(self, parent=None, url_id: Optional[int] = None, default_project_id: int = 0):
        super().__init__(parent)
        self.url_id = url_id
        self.default_project_id = default_project_id
        self.saved_url_id: Optional[int] = None

        self.setWindowTitle("Edit Bookmark" if self.url_id else "Add Bookmark / URL")
        self.setMinimumSize(600, 460)
        self.resize(650, 500)
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # Header Title
        title_text = "✏️ Edit Bookmark" if self.url_id else "🔗 Add New Bookmark / URL"
        header = QLabel(title_text)
        header.setObjectName("ViewTitleLabel")
        layout.addWidget(header)

        # Bookmark Name
        layout.addWidget(QLabel("Bookmark Name:"))
        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("Enter bookmark title or description...")
        layout.addWidget(self.edit_name)

        # Web URL
        layout.addWidget(QLabel("Web URL:"))
        self.edit_url = QLineEdit()
        self.edit_url.setPlaceholderText("https://example.com/page...")
        layout.addWidget(self.edit_url)

        # Metadata: Project + Category
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(14)

        proj_col = QVBoxLayout()
        proj_col.addWidget(QLabel("Project:"))
        self.combo_project = QComboBox()
        self._populate_projects()
        proj_col.addWidget(self.combo_project)
        meta_layout.addLayout(proj_col, stretch=1)

        cat_col = QVBoxLayout()
        cat_col.addWidget(QLabel("Category / Tag:"))
        self.edit_category = QLineEdit()
        self.edit_category.setText("General")
        cat_col.addWidget(self.edit_category)
        meta_layout.addLayout(cat_col, stretch=1)

        layout.addLayout(meta_layout)

        # Notes
        layout.addWidget(QLabel("Notes & Description:"))
        self.edit_notes = QTextEdit()
        self.edit_notes.setPlaceholderText("Add notes, credentials hints, or key information about this URL...")
        layout.addWidget(self.edit_notes, stretch=1)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("💾 Save Bookmark")
        self.btn_save.setObjectName("PrimaryButton")
        self.btn_save.clicked.connect(self._save_url)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _populate_projects(self):
        self.combo_project.clear()
        self.combo_project.addItem("General", userData=0)
        try:
            projects = DataRepository.get_all_projects()
            for p in projects:
                name = p.ProjectName.strip() if p.ProjectName else f"Project #{p.PojectID}"
                self.combo_project.addItem(name, userData=p.PojectID)
        except Exception as e:
            logger.error(f"Error populating URL projects: {e}")

    def _load_data(self):
        if self.url_id:
            u = DataRepository.get_url_by_id(self.url_id)
            if u:
                self.edit_name.setText(u.UrlName or "")
                self.edit_url.setText(u.Url or "")
                self.edit_notes.setPlainText(u.Notes or "")
                self.edit_category.setText(u.Category or "General")

                for i in range(self.combo_project.count()):
                    if self.combo_project.itemData(i) == u.PojectID:
                        self.combo_project.setCurrentIndex(i)
                        break
        else:
            if self.default_project_id != 0:
                for i in range(self.combo_project.count()):
                    if self.combo_project.itemData(i) == self.default_project_id:
                        self.combo_project.setCurrentIndex(i)
                        break

    def _save_url(self):
        name = self.edit_name.text().strip()
        url_text = self.edit_url.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Please provide a Bookmark Name.")
            self.edit_name.setFocus()
            return

        if not url_text:
            QMessageBox.warning(self, "Validation Error", "Please enter a valid URL.")
            self.edit_url.setFocus()
            return

        proj_id = self.combo_project.currentData() or 0
        proj_name = self.combo_project.currentText()
        cat = self.edit_category.text().strip() or "General"
        notes = self.edit_notes.toPlainText()

        try:
            if self.url_id:
                DataRepository.update_url(
                    self.url_id,
                    UrlName=name,
                    Url=url_text,
                    Category=cat,
                    PojectID=proj_id,
                    ProjectName=proj_name,
                    Notes=notes,
                )
                self.saved_url_id = self.url_id
            else:
                new_url = DataRepository.create_url(
                    url=url_text,
                    name=name,
                    notes=notes,
                    category=cat,
                    project_id=proj_id,
                    project_name=proj_name,
                )
                self.saved_url_id = new_url.UrlID

            self.accept()
        except Exception as e:
            logger.error(f"Error saving URL: {e}")
            QMessageBox.critical(self, "Save Error", f"Failed to save URL:\n{e}")
