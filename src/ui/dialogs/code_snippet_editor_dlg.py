"""
Dedicated Code Snippet Editor Popup Dialog for DigitalBrainEX AI.
Matches original AddCodeSnippet.cs popup dialog.
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
    QApplication,
    QMessageBox,
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from src.core.repository import DataRepository
from src.core.logger import logger


class CodeSnippetEditorDialog(QDialog):
    LANGUAGES = [
        "Python", "C#", "JavaScript", "TypeScript", "SQL",
        "HTML/CSS", "Bash", "C/C++", "Rust", "Go", "JSON/YAML", "Plain",
    ]

    def __init__(self, parent=None, snippet_id: Optional[int] = None, default_project_id: int = 0):
        super().__init__(parent)
        self.snippet_id = snippet_id
        self.default_project_id = default_project_id
        self.saved_snippet_id: Optional[int] = None

        self.setWindowTitle("Edit Code Snippet" if self.snippet_id else "New Code Snippet")
        self.setMinimumSize(740, 580)
        self.resize(800, 640)
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # Header Title
        title_text = "✏️ Edit Code Snippet" if self.snippet_id else "💻 Create New Code Snippet"
        header = QLabel(title_text)
        header.setObjectName("ViewTitleLabel")
        layout.addWidget(header)

        # Title Row
        layout.addWidget(QLabel("Snippet Title:"))
        self.edit_title = QLineEdit()
        self.edit_title.setPlaceholderText("e.g. Database Connection Helper, QuickSort Implementation...")
        layout.addWidget(self.edit_title)

        # Metadata Row: Language + Project
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(14)

        lang_col = QVBoxLayout()
        lang_col.addWidget(QLabel("Programming Language:"))
        self.combo_lang = QComboBox()
        self.combo_lang.addItems(self.LANGUAGES)
        lang_col.addWidget(self.combo_lang)
        meta_layout.addLayout(lang_col, stretch=1)

        proj_col = QVBoxLayout()
        proj_col.addWidget(QLabel("Project:"))
        self.combo_proj = QComboBox()
        self._populate_projects()
        proj_col.addWidget(self.combo_proj)
        meta_layout.addLayout(proj_col, stretch=1)

        layout.addLayout(meta_layout)

        # Code Editor
        code_header = QHBoxLayout()
        code_header.addWidget(QLabel("Source Code:"))
        code_header.addStretch()

        self.btn_copy_code = QPushButton("📋 Copy Code")
        self.btn_copy_code.clicked.connect(self._copy_code)
        code_header.addWidget(self.btn_copy_code)
        layout.addLayout(code_header)

        self.edit_code = QTextEdit()
        font = QFont("Consolas, Courier New, monospace", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.edit_code.setFont(font)
        self.edit_code.setPlaceholderText("// Paste or type your code here...")
        layout.addWidget(self.edit_code, stretch=2)

        # Description / Notes
        layout.addWidget(QLabel("Notes & Description:"))
        self.edit_desc = QTextEdit()
        self.edit_desc.setMaximumHeight(80)
        self.edit_desc.setPlaceholderText("Add usage instructions, prerequisites, or notes...")
        layout.addWidget(self.edit_desc, stretch=1)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("💾 Save Snippet")
        self.btn_save.setObjectName("PrimaryButton")
        self.btn_save.clicked.connect(self._save_snippet)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _populate_projects(self):
        self.combo_proj.clear()
        self.combo_proj.addItem("General", userData=0)
        try:
            projects = DataRepository.get_all_projects()
            for p in projects:
                name = p.ProjectName.strip() if p.ProjectName else f"Project #{p.PojectID}"
                self.combo_proj.addItem(name, userData=p.PojectID)
        except Exception as e:
            logger.error(f"Error populating snippet dialog projects: {e}")

    def _copy_code(self):
        code = self.edit_code.toPlainText()
        if code:
            QApplication.clipboard().setText(code)
            QMessageBox.information(self, "Copied", "Code snippet copied to clipboard!")

    def _load_data(self):
        if self.snippet_id:
            d = DataRepository.get_document_by_id(self.snippet_id)
            if d:
                self.edit_title.setText(d.DocumentName or "")
                code = d.Notes if d.Notes else (d.Desc or "")
                self.edit_code.setPlainText(code)
                self.edit_desc.setPlainText(d.Desc if d.Notes else "")

                idx = self.combo_lang.findText(d.Language or "Python")
                if idx >= 0:
                    self.combo_lang.setCurrentIndex(idx)

                for i in range(self.combo_proj.count()):
                    if self.combo_proj.itemData(i) == d.PojectID:
                        self.combo_proj.setCurrentIndex(i)
                        break
        else:
            if self.default_project_id != 0:
                for i in range(self.combo_proj.count()):
                    if self.combo_proj.itemData(i) == self.default_project_id:
                        self.combo_proj.setCurrentIndex(i)
                        break

    def _save_snippet(self):
        title = self.edit_title.text().strip()
        if not title:
            QMessageBox.warning(self, "Validation Error", "Please provide a Snippet Title.")
            self.edit_title.setFocus()
            return

        code = self.edit_code.toPlainText()
        lang = self.combo_lang.currentText()
        proj_id = self.combo_proj.currentData() or 0
        proj_name = self.combo_proj.currentText()
        desc = self.edit_desc.toPlainText() or code

        try:
            if self.snippet_id:
                DataRepository.update_document(
                    self.snippet_id,
                    DocumentName=title,
                    Desc=desc,
                    Notes=code,
                    Language=lang,
                    PojectID=proj_id,
                    ProjectName=proj_name,
                )
                self.saved_snippet_id = self.snippet_id
            else:
                new_doc = DataRepository.create_document(
                    name=title,
                    desc=desc,
                    notes=code,
                    language=lang,
                    project_id=proj_id,
                    project_name=proj_name,
                    category="Code",
                    doc_type=4,
                )
                self.saved_snippet_id = new_doc.DocumentID

            self.accept()
        except Exception as e:
            logger.error(f"Error saving snippet: {e}")
            QMessageBox.critical(self, "Save Error", f"Failed to save snippet:\n{e}")
