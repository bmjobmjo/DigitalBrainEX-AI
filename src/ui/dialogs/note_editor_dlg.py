"""
Dedicated Note Editor Popup Dialog for DigitalBrainEX AI.
Matches original AddNoteForm.cs popup dialog.
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


class NoteEditorDialog(QDialog):
    def __init__(self, parent=None, note_id: Optional[int] = None, default_project_id: int = 0):
        super().__init__(parent)
        self.note_id = note_id
        self.default_project_id = default_project_id
        self.saved_note_id: Optional[int] = None

        self.setWindowTitle("Edit Note" if self.note_id else "New Note")
        self.setMinimumSize(680, 520)
        self.resize(720, 560)
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # Header Title
        title_text = "✏️ Edit Diary Note" if self.note_id else "📝 Create New Note"
        header = QLabel(title_text)
        header.setObjectName("ViewTitleLabel")
        layout.addWidget(header)

        # Metadata Form Row (Title + Project)
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(14)

        title_col = QVBoxLayout()
        title_col.addWidget(QLabel("Note Title:"))
        self.edit_title = QLineEdit()
        self.edit_title.setPlaceholderText("Enter note title or summary...")
        title_col.addWidget(self.edit_title)
        meta_layout.addLayout(title_col, stretch=2)

        proj_col = QVBoxLayout()
        proj_col.addWidget(QLabel("Project:"))
        self.combo_project = QComboBox()
        self._populate_projects()
        proj_col.addWidget(self.combo_project)
        meta_layout.addLayout(proj_col, stretch=1)

        layout.addLayout(meta_layout)

        # Content / Body
        layout.addWidget(QLabel("Note Body / Content:"))
        self.edit_content = QTextEdit()
        self.edit_content.setPlaceholderText("Write your notes, diary entry, logs, or thoughts here...")
        layout.addWidget(self.edit_content, stretch=1)

        # Bottom Button Bar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("💾 Save Note")
        self.btn_save.setObjectName("PrimaryButton")
        self.btn_save.clicked.connect(self._save_note)
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
            logger.error(f"Error populating note dialog projects: {e}")

    def _load_data(self):
        if self.note_id:
            d = DataRepository.get_document_by_id(self.note_id)
            if d:
                self.edit_title.setText(d.DocumentName or "")
                content = d.Desc if d.Desc else (d.Notes or "")
                self.edit_content.setPlainText(content)

                for i in range(self.combo_project.count()):
                    if self.combo_project.itemData(i) == d.PojectID:
                        self.combo_project.setCurrentIndex(i)
                        break
        else:
            if self.default_project_id != 0:
                for i in range(self.combo_project.count()):
                    if self.combo_project.itemData(i) == self.default_project_id:
                        self.combo_project.setCurrentIndex(i)
                        break

    def _save_note(self):
        title = self.edit_title.text().strip()
        if not title:
            QMessageBox.warning(self, "Validation Error", "Please enter a Note Title.")
            self.edit_title.setFocus()
            return

        content = self.edit_content.toPlainText()
        proj_id = self.combo_project.currentData() or 0
        proj_name = self.combo_project.currentText()

        try:
            if self.note_id:
                DataRepository.update_document(
                    self.note_id,
                    DocumentName=title,
                    Desc=content,
                    Notes=content,
                    PojectID=proj_id,
                    ProjectName=proj_name,
                    Category="PlainNotes",
                )
                self.saved_note_id = self.note_id
            else:
                new_doc = DataRepository.create_document(
                    name=title,
                    desc=content,
                    notes=content,
                    project_id=proj_id,
                    project_name=proj_name,
                    category="PlainNotes",
                    doc_type=2,
                )
                self.saved_note_id = new_doc.DocumentID

            self.accept()
        except Exception as e:
            logger.error(f"Error saving note: {e}")
            QMessageBox.critical(self, "Save Error", f"Failed to save note:\n{e}")
