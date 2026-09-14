"""
Dedicated Secret Vault Editor / Viewer Popup Dialog for DigitalBrainEX AI.
Matches original AddSecret.cs popup dialog with TripleDES compatibility.
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
    QCheckBox,
    QGroupBox,
    QApplication,
    QMessageBox,
)
from PyQt6.QtCore import Qt

from src.core.repository import DataRepository
from src.core.crypto import encrypt_des3, decrypt_des3
from src.utils.config_manager import open_path_or_url
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

        self._raw_identity: str = ""
        self._raw_password: str = ""
        self._is_decrypted: bool = False

        title = "New Secret" if mode == "add" else ("Secret Details" if mode == "view" else "Edit Secret")
        self.setWindowTitle(title)
        self.setMinimumSize(660, 620)
        self.resize(700, 660)
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        # 1. Header Title
        title_text = "🔐 New Secret Credential" if self.mode == "add" else "🔐 Secret Vault Credential"
        header = QLabel(title_text)
        header.setObjectName("ViewTitleLabel")
        layout.addWidget(header)

        # 2. Secret Name
        layout.addWidget(QLabel("Secret / Account Name:"))
        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("e.g. AWS Production Admin, Personal Gmail, GitHub Token...")
        layout.addWidget(self.edit_name)

        # 3. Project & URL Row
        row_proj = QHBoxLayout()
        row_proj.setSpacing(10)

        col_proj = QVBoxLayout()
        col_proj.addWidget(QLabel("Project:"))
        self.combo_proj = QComboBox()
        self._populate_projects()
        col_proj.addWidget(self.combo_proj)
        row_proj.addLayout(col_proj, stretch=1)

        col_url = QVBoxLayout()
        col_url.addWidget(QLabel("Application / Website URL:"))
        url_box = QHBoxLayout()
        self.edit_app = QLineEdit()
        self.edit_app.setPlaceholderText("https://aws.amazon.com or app name...")
        url_box.addWidget(self.edit_app)

        self.btn_open_url = QPushButton("🌐 Open")
        self.btn_open_url.setToolTip("Open URL in default web browser")
        self.btn_open_url.clicked.connect(self._open_url)
        url_box.addWidget(self.btn_open_url)

        col_url.addLayout(url_box)
        row_proj.addLayout(col_url, stretch=2)

        layout.addLayout(row_proj)

        # 4. Secret Key Group (Matches C# groupBox2)
        grp_key = QGroupBox("🔑 Secret Master Key (for Encryption && Decryption)")
        key_layout = QVBoxLayout(grp_key)
        key_layout.setSpacing(6)

        key_input_row = QHBoxLayout()
        self.edit_key = QLineEdit()
        self.edit_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_key.setPlaceholderText("Enter your Secret Key to decrypt or encrypt credentials...")
        self.edit_key.returnPressed.connect(self._decrypt_credentials)
        key_input_row.addWidget(self.edit_key, stretch=1)

        self.chk_show_key = QCheckBox("Show")
        self.chk_show_key.toggled.connect(
            lambda checked: self.edit_key.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
        )
        key_input_row.addWidget(self.chk_show_key)

        self.btn_decrypt = QPushButton("🔓 Decrypt")
        self.btn_decrypt.setToolTip("Decrypt Identity and Password using the Secret Key entered")
        self.btn_decrypt.clicked.connect(self._decrypt_credentials)
        key_input_row.addWidget(self.btn_decrypt)

        self.btn_encrypt = QPushButton("🔒 Encrypt")
        self.btn_encrypt.setToolTip("Encrypt plaintext Identity and Password with this Secret Key")
        self.btn_encrypt.clicked.connect(self._encrypt_credentials)
        key_input_row.addWidget(self.btn_encrypt)

        key_layout.addLayout(key_input_row)

        self.lbl_crypto_status = QLabel("")
        self.lbl_crypto_status.setStyleSheet("font-size: 11px; color: #666;")
        key_layout.addWidget(self.lbl_crypto_status)

        layout.addWidget(grp_key)

        # 5. Encrypted Credentials Group (Matches C# groupBox1)
        grp_cred = QGroupBox("🛡️ Credentials (Protected)")
        cred_layout = QVBoxLayout(grp_cred)
        cred_layout.setSpacing(8)

        # Edit toggle checkbox (Matches C# checkBoxEdit)
        self.chk_edit = QCheckBox("✏️ Enable Editing Credentials")
        self.chk_edit.toggled.connect(self._toggle_credential_editing)
        cred_layout.addWidget(self.chk_edit)

        # User / Identity
        cred_layout.addWidget(QLabel("Username / Email / Access Key ID:"))
        user_row = QHBoxLayout()
        self.edit_user = QLineEdit()
        self.edit_user.setPlaceholderText("Username or email...")
        user_row.addWidget(self.edit_user)

        self.btn_copy_user = QPushButton("📋 Copy")
        self.btn_copy_user.setToolTip("Copy username to clipboard")
        self.btn_copy_user.clicked.connect(self._copy_username)
        user_row.addWidget(self.btn_copy_user)
        cred_layout.addLayout(user_row)

        # Password / Token
        cred_layout.addWidget(QLabel("Password / Secret Key / Token:"))
        pass_row = QHBoxLayout()
        self.edit_pass = QLineEdit()
        self.edit_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_pass.setPlaceholderText("Password or token...")
        pass_row.addWidget(self.edit_pass)

        self.chk_show_pass = QCheckBox("Show")
        self.chk_show_pass.toggled.connect(
            lambda checked: self.edit_pass.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
        )
        pass_row.addWidget(self.chk_show_pass)

        self.btn_copy_pass = QPushButton("📋 Copy")
        self.btn_copy_pass.setToolTip("Copy password to clipboard")
        self.btn_copy_pass.clicked.connect(self._copy_password)
        pass_row.addWidget(self.btn_copy_pass)

        self.btn_gen_pass = QPushButton("🎲 Generate")
        self.btn_gen_pass.setToolTip("Generate strong random password")
        self.btn_gen_pass.clicked.connect(self._generate_password)
        pass_row.addWidget(self.btn_gen_pass)

        cred_layout.addLayout(pass_row)
        layout.addWidget(grp_cred)

        # 6. Notes & Description
        layout.addWidget(QLabel("Notes & Description:"))
        self.edit_desc = QTextEdit()
        self.edit_desc.setPlaceholderText("PIN codes, recovery keys, 2FA backup codes...")
        self.edit_desc.setMaximumHeight(80)
        layout.addWidget(self.edit_desc)

        # 7. Bottom Action Buttons
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

    def _toggle_credential_editing(self, enabled: bool):
        self.edit_user.setEnabled(enabled)
        self.edit_pass.setEnabled(enabled)

    def _open_url(self):
        url = self.edit_app.text().strip()
        if url:
            open_path_or_url(url, self)

    def _copy_username(self):
        usr = self.edit_user.text()
        if usr:
            QApplication.clipboard().setText(usr)
            QMessageBox.information(self, "Copied", "Username / Identity copied to clipboard!")

    def _copy_password(self):
        pwd = self.edit_pass.text()
        if pwd:
            QApplication.clipboard().setText(pwd)
            QMessageBox.information(self, "Copied", "Password copied to clipboard!")

    def _generate_password(self):
        chars = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
        new_pwd = "".join(secrets.choice(chars) for _ in range(16))
        self.chk_edit.setChecked(True)
        self.edit_pass.setText(new_pwd)
        self.chk_show_pass.setChecked(True)
        self.edit_pass.setEchoMode(QLineEdit.EchoMode.Normal)
        self._is_decrypted = True
        self.lbl_crypto_status.setText("Generated new random password. Remember to enter a Secret Key before saving.")
        self.lbl_crypto_status.setStyleSheet("color: #e65100;")

    def _load_data(self):
        if self.secret_id:
            s = DataRepository.get_secret_by_id(self.secret_id)
            if s:
                self.edit_name.setText(s.SecretName or "")
                self.edit_app.setText(s.ApplicationURL or "")
                self.edit_desc.setPlainText(s.Desc or "")

                self._raw_identity = s.Identity or ""
                self._raw_password = s.Password or ""

                # Populate fields with stored values (masked by default)
                self.edit_user.setText(self._raw_identity)
                self.edit_pass.setText(self._raw_password)

                # Select project
                proj_id_val = 0
                try:
                    proj_id_val = int(s.ProjectID) if s.ProjectID else 0
                except (ValueError, TypeError):
                    proj_id_val = 0

                for i in range(self.combo_proj.count()):
                    if self.combo_proj.itemData(i) == proj_id_val:
                        self.combo_proj.setCurrentIndex(i)
                        break

                # For existing secrets, credentials start locked
                self.chk_edit.setChecked(False)
                self._toggle_credential_editing(False)
                self._is_decrypted = False

                if self._raw_identity or self._raw_password:
                    self.lbl_crypto_status.setText("🔒 Encrypted data in vault. Enter your Secret Key above and click Decrypt.")
                    self.lbl_crypto_status.setStyleSheet("color: #555;")
                else:
                    self.lbl_crypto_status.setText("No credentials stored.")
        else:
            # Mode "add": new secret
            if self.default_project_id != 0:
                for i in range(self.combo_proj.count()):
                    if self.combo_proj.itemData(i) == self.default_project_id:
                        self.combo_proj.setCurrentIndex(i)
                        break
            self.chk_edit.setChecked(True)
            self._toggle_credential_editing(True)
            self._is_decrypted = True
            self.lbl_crypto_status.setText("Enter credentials and provide a Secret Key to encrypt.")

    def _decrypt_credentials(self):
        key = self.edit_key.text().strip()
        if not key:
            QMessageBox.warning(self, "Secret Key Required", "Please enter the Secret Key into the key field to decrypt.")
            self.edit_key.setFocus()
            return

        if not self._raw_identity and not self._raw_password:
            QMessageBox.information(self, "Empty Credentials", "This secret has no encrypted credentials to decrypt.")
            return

        try:
            plain_user = decrypt_des3(key, self._raw_identity) if self._raw_identity else ""
            plain_pass = decrypt_des3(key, self._raw_password) if self._raw_password else ""

            self.edit_user.setText(plain_user)
            self.edit_pass.setText(plain_pass)
            self._is_decrypted = True
            self.chk_edit.setChecked(True)
            self.lbl_crypto_status.setText("✅ Decrypted successfully with your Secret Key.")
            self.lbl_crypto_status.setStyleSheet("color: #2e7d32; font-weight: bold;")
        except Exception as e:
            logger.warning(f"Failed to decrypt secret with provided key: {e}")
            self.lbl_crypto_status.setText("❌ Failed to decrypt. Secret Key does not match.")
            self.lbl_crypto_status.setStyleSheet("color: #c62828; font-weight: bold;")
            QMessageBox.warning(
                self,
                "Decryption Failed",
                "Failed to decrypt the secret data.\nPlease verify that your Secret Key is correct.",
            )

    def _encrypt_credentials(self):
        key = self.edit_key.text().strip()
        if not key:
            QMessageBox.warning(self, "Secret Key Required", "Please enter a Secret Key to encrypt your credentials.")
            self.edit_key.setFocus()
            return

        plain_user = self.edit_user.text()
        plain_pass = self.edit_pass.text()

        try:
            enc_user = encrypt_des3(key, plain_user) if plain_user else ""
            enc_pass = encrypt_des3(key, plain_pass) if plain_pass else ""

            self._raw_identity = enc_user
            self._raw_password = enc_pass
            self.edit_user.setText(enc_user)
            self.edit_pass.setText(enc_pass)
            self._is_decrypted = False
            self.chk_edit.setChecked(False)

            self.lbl_crypto_status.setText("🔒 Credentials encrypted successfully with your Secret Key.")
            self.lbl_crypto_status.setStyleSheet("color: #1565c0; font-weight: bold;")
            QMessageBox.information(self, "Encrypted", "Credentials encrypted successfully!")
        except Exception as e:
            logger.error(f"Error encrypting credentials: {e}")
            QMessageBox.critical(self, "Encryption Error", f"Failed to encrypt credentials:\n{e}")

    def _save_secret(self):
        name = self.edit_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Please provide a Secret / Account Name.")
            self.edit_name.setFocus()
            return

        app_url = self.edit_app.text().strip()
        desc = self.edit_desc.toPlainText().strip()
        proj_id = self.combo_proj.currentData() or 0
        proj_name = self.combo_proj.currentText()
        key = self.edit_key.text().strip()

        # Handle credentials
        identity_to_save = ""
        password_to_save = ""

        if self.secret_id:
            # Editing existing secret
            if not self._is_decrypted and not self.chk_edit.isChecked():
                # User did not decrypt or edit credentials; preserve existing ciphertext safely
                identity_to_save = self._raw_identity
                password_to_save = self._raw_password
            else:
                # Credentials were decrypted or modified
                plain_user = self.edit_user.text()
                plain_pass = self.edit_pass.text()
                if key:
                    identity_to_save = encrypt_des3(key, plain_user) if plain_user else ""
                    password_to_save = encrypt_des3(key, plain_pass) if plain_pass else ""
                else:
                    reply = QMessageBox.question(
                        self,
                        "Unencrypted Credentials",
                        "No Secret Key is entered. Do you want to enter a key to encrypt credentials before saving?\n\n"
                        "Click 'Yes' to enter a Secret Key, or 'No' to save credentials as plain text.",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        self.edit_key.setFocus()
                        return
                    identity_to_save = plain_user
                    password_to_save = plain_pass

            try:
                DataRepository.update_secret(
                    self.secret_id,
                    SecretName=name,
                    ApplicationURL=app_url,
                    Identity=identity_to_save,
                    Password=password_to_save,
                    ProjectID=str(proj_id),
                    ProjectName=proj_name,
                    Desc=desc,
                )
                self.saved_secret_id = self.secret_id
                self.accept()
            except Exception as e:
                logger.error(f"Error updating secret: {e}")
                QMessageBox.critical(self, "Save Error", f"Failed to update secret:\n{e}")
        else:
            # Adding a brand new secret
            plain_user = self.edit_user.text()
            plain_pass = self.edit_pass.text()

            if (plain_user or plain_pass) and not key:
                reply = QMessageBox.question(
                    self,
                    "Unencrypted Credentials",
                    "No Secret Key is entered to protect these credentials.\n\n"
                    "Do you want to enter a Secret Key before saving?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.edit_key.setFocus()
                    return

            try:
                new_sec = DataRepository.create_secret(
                    secret_name=name,
                    app_url=app_url,
                    identity=plain_user,
                    password=plain_pass,
                    desc=desc,
                    project_id=str(proj_id),
                    project_name=proj_name,
                    secret_key=key if key else None,
                )
                self.saved_secret_id = new_sec.SecretID
                self.accept()
            except Exception as e:
                logger.error(f"Error creating secret: {e}")
                QMessageBox.critical(self, "Save Error", f"Failed to create secret:\n{e}")
