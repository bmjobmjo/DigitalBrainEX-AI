"""
Dedicated Secret Vault Editor / Viewer Popup Dialog for DigitalBrainEX AI.
Matches original AddSecret.cs popup dialog.
"""
import string
import secrets
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
from PyQt6.QtCore import Qt

from src.core.repository import DataRepository
from src.core.logger import logger


class SecretEditorDialog(QDialog):
    def __init__(
        self,
        parent=None,
        secret_id: Optional[int] = None,
        default_project_id: int = 0,
        mode: str = "add",
    ):
        super().__init__(parent)
        self.secret_id = secret_id
        self.default_project_id = default_project_id
        self.mode = mode  # "add", "edit", "view"
        self.saved_secret_id: Optional[int] = None

        title = "New Secret" if mode == "add" else ("Secret Details" if mode == "view" else "Edit Secret")
        self.setWindowTitle(title)
        self.setMinimumSize(620, 520)
        self.resize(680, 560)
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # Header Title
        title_text = "🔐 New Secret Credential" if self.mode == "add" else "🔐 Secret Credential Details"
        header = QLabel(title_text)
        header.setObjectName("ViewTitleLabel")
        layout.addWidget(header)

        # Secret Name
        layout.addWidget(QLabel("Secret / Account Name:"))
        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("e.g. AWS Production Admin, GitHub Personal Access Token...")
        layout.addWidget(self.edit_name)

        # App / URL and Project Row
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(14)

        app_col = QVBoxLayout()
        app_col.addWidget(QLabel("Application / Website URL:"))
        self.edit_app = QLineEdit()
        self.edit_app.setPlaceholderText("https://aws.amazon.com or app name...")
        app_col.addWidget(self.edit_app)
        meta_layout.addLayout(app_col, stretch=2)

        proj_col = QVBoxLayout()
        proj_col.addWidget(QLabel("Project:"))
        self.combo_proj = QComboBox()
        self._populate_projects()
        proj_col.addWidget(self.combo_proj)
        meta_layout.addLayout(proj_col, stretch=1)

        layout.addLayout(meta_layout)

        # Username / Identity
        layout.addWidget(QLabel("Username / Email / Access Key ID:"))
        self.edit_user = QLineEdit()
        self.edit_user.setPlaceholderText("e.g. admin@company.com or AKIA...")
        layout.addWidget(self.edit_user)

        # Password / Secret Key row
        layout.addWidget(QLabel("Password / Secret Key / Token:"))
        pass_layout = QHBoxLayout()
        self.edit_pass = QLineEdit()
        self.edit_pass.setEchoMode(QLineEdit.EchoMode.Password)
        pass_layout.addWidget(self.edit_pass)

        self.btn_toggle_pass = QPushButton("👁")
        self.btn_toggle_pass.setFixedWidth(38)
        self.btn_toggle_pass.setToolTip("Show/Hide password")
        self.btn_toggle_pass.clicked.connect(self._toggle_password_visibility)
        pass_layout.addWidget(self.btn_toggle_pass)

        self.btn_copy_pass = QPushButton("📋 Copy")
        self.btn_copy_pass.setToolTip("Copy password to clipboard")
        self.btn_copy_pass.clicked.connect(self._copy_password)
        pass_layout.addWidget(self.btn_copy_pass)

        self.btn_gen_pass = QPushButton("🎲 Generate")
        self.btn_gen_pass.setToolTip("Generate strong random password")
        self.btn_gen_pass.clicked.connect(self._generate_password)
        pass_layout.addWidget(self.btn_gen_pass)

        layout.addLayout(pass_layout)

        # Description / Notes
        layout.addWidget(QLabel("Notes & Description:"))
        self.edit_desc = QTextEdit()
        self.edit_desc.setPlaceholderText("PIN codes, recovery keys, 2FA backup codes...")
        layout.addWidget(self.edit_desc, stretch=1)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Close" if self.mode == "view" else "Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("💾 Save Secret")
        self.btn_save.setObjectName("PrimaryButton")
        self.btn_save.clicked.connect(self._save_secret)
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
            logger.error(f"Error populating secret dialog projects: {e}")

    def _toggle_password_visibility(self):
        if self.edit_pass.echoMode() == QLineEdit.EchoMode.Password:
            self.edit_pass.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_toggle_pass.setText("🔒")
        else:
            self.edit_pass.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_toggle_pass.setText("👁")

    def _copy_password(self):
        pwd = self.edit_pass.text()
        if pwd:
            QApplication.clipboard().setText(pwd)
            QMessageBox.information(self, "Copied", "Password copied to clipboard!")

    def _generate_password(self):
        chars = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
        new_pwd = "".join(secrets.choice(chars) for _ in range(16))
        self.edit_pass.setText(new_pwd)
        self.edit_pass.setEchoMode(QLineEdit.EchoMode.Normal)
        self.btn_toggle_pass.setText("🔒")

    def _load_data(self):
        if self.secret_id:
            s = DataRepository.get_secret_by_id(self.secret_id)
            if s:
                self.edit_name.setText(s.SecretName or "")
                self.edit_app.setText(s.ApplicationURL or "")
                self.edit_user.setText(s.Identity or "")
                self.edit_desc.setPlainText(s.Desc or "")

                raw_pwd = DataRepository.decrypt_secret_password(s.Password or "")
                self.edit_pass.setText(raw_pwd)

                for i in range(self.combo_proj.count()):
                    if self.combo_proj.itemData(i) == s.PojectID:
                        self.combo_proj.setCurrentIndex(i)
                        break
        else:
            if self.default_project_id != 0:
                for i in range(self.combo_proj.count()):
                    if self.combo_proj.itemData(i) == self.default_project_id:
                        self.combo_proj.setCurrentIndex(i)
                        break

    def _save_secret(self):
        name = self.edit_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Please provide a Secret / Account Name.")
            self.edit_name.setFocus()
            return

        app_url = self.edit_app.text().strip()
        user = self.edit_user.text().strip()
        plain_pwd = self.edit_pass.text()
        enc_pwd = DataRepository.encrypt_secret_password(plain_pwd) if plain_pwd else ""
        proj_id = self.combo_proj.currentData() or 0
        proj_name = self.combo_proj.currentText()
        desc = self.edit_desc.toPlainText()

        try:
            if self.secret_id:
                DataRepository.update_secret(
                    self.secret_id,
                    SecretName=name,
                    ApplicationURL=app_url,
                    Identity=user,
                    Password=enc_pwd,
                    PojectID=proj_id,
                    ProjectName=proj_name,
                    Desc=desc,
                )
                self.saved_secret_id = self.secret_id
            else:
                new_sec = DataRepository.create_secret(
                    name=name,
                    identity=user,
                    password=plain_pwd,
                    app_url=app_url,
                    desc=desc,
                    project_id=proj_id,
                    project_name=proj_name,
                )
                self.saved_secret_id = new_sec.SecretID

            self.accept()
        except Exception as e:
            logger.error(f"Error saving secret: {e}")
            QMessageBox.critical(self, "Save Error", f"Failed to save secret:\n{e}")
