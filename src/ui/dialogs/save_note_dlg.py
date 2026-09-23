"""
Save Note Metadata Prompt Dialog for DigitalBrainEX AI.
Asks for Note Title / Name and Category (and Project) when Save is clicked in a note tab.
"""
from typing import Optional, Tuple
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QMessageBox,
)
from PyQt6.QtCore import Qt

from src.core.repository import DataRepository
from src.ui.icons import IconHelper
from src.core.logger import logger


class SaveNoteMetadataDialog(QDialog):
    def __init__(
        self,
        parent=None,
        initial_title: str = "",
        initial_category: str = "PlainNotes",
        initial_project_id: int = 0,
    ):
        super().__init__(parent)
        self.setWindowTitle("Save Note")
        self.setMinimumWidth(420)
        self.resize(460, 260)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self.initial_title = initial_title
        self.initial_category = initial_category or "PlainNotes"
        self.initial_project_id = initial_project_id

        self.result_title: str = self.initial_title
        self.result_category: str = self.initial_category
        self.result_project_id: int = self.initial_project_id
        self.result_project_name: str = "General"

        self._init_ui()
        self._load_defaults()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # Header Title
        header = QLabel("💾 Save Note Details")
        header.setObjectName("ViewTitleLabel")
        layout.addWidget(header)

        # Note Title Input
        lbl_title = QLabel("Note Name / Title:")
        layout.addWidget(lbl_title)
        self.edit_title = QLineEdit()
        self.edit_title.setPlaceholderText("e.g. Project Discussion, Todo list...")
        self.edit_title.setText(self.initial_title)
        layout.addWidget(self.edit_title)

        # Category and Project Row
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(12)

        # Category Column
        cat_col = QVBoxLayout()
        cat_col.addWidget(QLabel("Category:"))
        self.combo_cat = QComboBox()
        self.combo_cat.setEditable(True)
        cat_col.addWidget(self.combo_cat)
        meta_layout.addLayout(cat_col, stretch=1)

        # Project Column
        proj_col = QVBoxLayout()
        proj_col.addWidget(QLabel("Project:"))
        self.combo_proj = QComboBox()
        proj_col.addWidget(self.combo_proj)
        meta_layout.addLayout(proj_col, stretch=1)

        layout.addLayout(meta_layout)

        # Button Row
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save")
        self.btn_save.setIcon(IconHelper.get_icon("save", 16))
        self.btn_save.setObjectName("PrimaryButton")
        self.btn_save.clicked.connect(self._on_save_clicked)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _load_defaults(self):
        # 1. Populate categories
        categories = ["PlainNotes", "General", "Meeting", "Todo", "WorkLog", "Personal"]
        try:
            db_cats = DataRepository.get_document_categories()
            for c in db_cats:
                cname = getattr(c, "CatogoryName", None) or getattr(c, "CategoryName", None)
                if cname and cname not in categories:
                    categories.append(cname)
        except Exception as e:
            logger.error(f"Error fetching categories for note save dialog: {e}")

        self.combo_cat.clear()
        for cat in categories:
            self.combo_cat.addItem(cat)

        idx = self.combo_cat.findText(self.initial_category)
        if idx >= 0:
            self.combo_cat.setCurrentIndex(idx)
        else:
            self.combo_cat.setEditText(self.initial_category)

        # 2. Populate projects
        self.combo_proj.clear()
        self.combo_proj.addItem("General", userData=0)
        try:
            projects = DataRepository.get_all_projects()
            for p in projects:
                name = p.ProjectName.strip() if p.ProjectName else f"Project #{p.PojectID}"
                self.combo_proj.addItem(name, userData=p.PojectID)
        except Exception as e:
            logger.error(f"Error fetching projects for note save dialog: {e}")

        # Set project index
        for i in range(self.combo_proj.count()):
            if self.combo_proj.itemData(i) == self.initial_project_id:
                self.combo_proj.setCurrentIndex(i)
                break

        # Select title text for easy renaming
        self.edit_title.selectAll()
        self.edit_title.setFocus()

    def _on_save_clicked(self):
        title = self.edit_title.text().strip()
        if not title:
            QMessageBox.warning(self, "Validation Error", "Please enter a Note Name / Title.")
            self.edit_title.setFocus()
            return

        cat = self.combo_cat.currentText().strip() or "PlainNotes"
        proj_id = self.combo_proj.currentData() or 0
        proj_name = self.combo_proj.currentText()

        self.result_title = title
        self.result_category = cat
        self.result_project_id = proj_id
        self.result_project_name = proj_name

        self.accept()

    @classmethod
    def prompt(
        cls,
        parent=None,
        initial_title: str = "",
        initial_category: str = "PlainNotes",
        initial_project_id: int = 0,
    ) -> Optional[Tuple[str, str, int, str]]:
        """
        Helper method to show dialog and return (title, category, project_id, project_name)
        or None if cancelled.
        """
        dlg = cls(
            parent=parent,
            initial_title=initial_title,
            initial_category=initial_category,
            initial_project_id=initial_project_id,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            return (
                dlg.result_title,
                dlg.result_category,
                dlg.result_project_id,
                dlg.result_project_name,
            )
        return None
