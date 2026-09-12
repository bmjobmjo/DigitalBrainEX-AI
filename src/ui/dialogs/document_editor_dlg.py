"""
Dedicated Document Editor Popup Dialog for DigitalBrainEX AI.
Matches original AddDocumentFrm.cs popup dialog.
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
    QFileDialog,
    QCheckBox,
    QMessageBox,
)
from PyQt6.QtCore import Qt

from src.core.repository import DataRepository
from src.core.logger import logger


class DocumentEditorDialog(QDialog):
    def __init__(self, parent=None, doc_id: Optional[int] = None, default_project_id: int = 0):
        super().__init__(parent)
        self.doc_id = doc_id
        self.default_project_id = default_project_id
        self.saved_doc_id: Optional[int] = None

        self.setWindowTitle("Edit Document" if self.doc_id else "Add Document")
        self.setMinimumSize(660, 520)
        self.resize(700, 560)
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # Header Title
        title_text = "✏️ Edit Document Details" if self.doc_id else "📄 Add New Document / File"
        header = QLabel(title_text)
        header.setObjectName("ViewTitleLabel")
        layout.addWidget(header)

        # Document Name
        layout.addWidget(QLabel("Document Name:"))
        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("Enter document title or file name...")
        layout.addWidget(self.edit_name)

        # File Path / URI row with Browse
        layout.addWidget(QLabel("File Path / URI:"))
        uri_layout = QHBoxLayout()
        self.edit_uri = QLineEdit()
        self.edit_uri.setPlaceholderText("Select file path or enter URI...")
        uri_layout.addWidget(self.edit_uri)

        self.btn_browse = QPushButton("Browse...")
        self.btn_browse.clicked.connect(self._browse_file)
        uri_layout.addWidget(self.btn_browse)
        layout.addLayout(uri_layout)

        # Category and Project Row
        cat_proj_layout = QHBoxLayout()
        cat_proj_layout.setSpacing(14)

        cat_col = QVBoxLayout()
        cat_col.addWidget(QLabel("Category:"))
        self.combo_cat = QComboBox()
        self.combo_cat.setEditable(True)
        self._populate_categories()
        cat_col.addWidget(self.combo_cat)
        cat_proj_layout.addLayout(cat_col, stretch=1)

        proj_col = QVBoxLayout()
        proj_col.addWidget(QLabel("Project:"))
        self.combo_proj = QComboBox()
        self._populate_projects()
        proj_col.addWidget(self.combo_proj)
        cat_proj_layout.addLayout(proj_col, stretch=1)

        layout.addLayout(cat_proj_layout)

        # Description / Notes
        layout.addWidget(QLabel("Description & Keywords:"))
        self.edit_desc = QTextEdit()
        self.edit_desc.setPlaceholderText("Enter summary, keywords, or content preview...")
        layout.addWidget(self.edit_desc, stretch=1)

        # LLM Flag
        self.chk_llm = QCheckBox("Index in AI Semantic Search (Vector RAG)")
        self.chk_llm.setChecked(True)
        layout.addWidget(self.chk_llm)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("💾 Save Document")
        self.btn_save.setObjectName("PrimaryButton")
        self.btn_save.clicked.connect(self._save_document)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _browse_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select Document File",
            "",
            "All Files (*.*);;PDF Documents (*.pdf);;Office Files (*.docx *.xlsx *.pptx);;Images (*.png *.jpg *.bmp)",
        )
        if filepath:
            self.edit_uri.setText(filepath)
            if not self.edit_name.text().strip():
                import os
                self.edit_name.setText(os.path.basename(filepath))

    def _populate_categories(self):
        self.combo_cat.clear()
        try:
            cats = DataRepository.get_document_categories()
            for c in cats:
                if c.CatogoryName:
                    self.combo_cat.addItem(c.CatogoryName)
        except Exception as e:
            logger.error(f"Error populating document categories: {e}")

    def _populate_projects(self):
        self.combo_proj.clear()
        self.combo_proj.addItem("General", userData=0)
        try:
            projects = DataRepository.get_all_projects()
            for p in projects:
                name = p.ProjectName.strip() if p.ProjectName else f"Project #{p.PojectID}"
                self.combo_proj.addItem(name, userData=p.PojectID)
        except Exception as e:
            logger.error(f"Error populating document projects: {e}")

    def _load_data(self):
        if self.doc_id:
            d = DataRepository.get_document_by_id(self.doc_id)
            if d:
                self.edit_name.setText(d.DocumentName or "")
                self.edit_uri.setText(d.DocumentURI or "")
                self.edit_desc.setPlainText(d.Desc or "")
                self.chk_llm.setChecked(bool(d.AddToLLM == 1))

                idx_cat = self.combo_cat.findText(d.Category or "General")
                if idx_cat >= 0:
                    self.combo_cat.setCurrentIndex(idx_cat)
                else:
                    self.combo_cat.setEditText(d.Category or "General")

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

    def _save_document(self):
        name = self.edit_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Please provide a Document Name.")
            self.edit_name.setFocus()
            return

        uri = self.edit_uri.text().strip()
        cat = self.combo_cat.currentText().strip() or "General"
        proj_id = self.combo_proj.currentData() or 0
        proj_name = self.combo_proj.currentText()
        desc = self.edit_desc.toPlainText()
        add_to_llm = 1 if self.chk_llm.isChecked() else 0

        try:
            if self.doc_id:
                DataRepository.update_document(
                    self.doc_id,
                    DocumentName=name,
                    DocumentURI=uri,
                    Category=cat,
                    PojectID=proj_id,
                    ProjectName=proj_name,
                    Desc=desc,
                    AddToLLM=add_to_llm,
                )
                self.saved_doc_id = self.doc_id
            else:
                new_doc = DataRepository.create_document(
                    name=name,
                    uri=uri,
                    desc=desc,
                    project_id=proj_id,
                    project_name=proj_name,
                    category=cat,
                    doc_type=0,
                )
                if add_to_llm:
                    DataRepository.update_document(new_doc.DocumentID, AddToLLM=1)
                self.saved_doc_id = new_doc.DocumentID

            self.accept()
        except Exception as e:
            logger.error(f"Error saving document: {e}")
            QMessageBox.critical(self, "Save Error", f"Failed to save document:\n{e}")
