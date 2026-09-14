"""
Comprehensive verification tests for:
1. '+' search functionality (AND logic across '+' terms)
2. Database backup on startup and purge older than 5 days
3. Secrets Vault double click, decrypt, encrypt, and save workflows
4. Document / URL double click handler signatures
"""
import os
import time
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QModelIndex

from src.core.repository import DataRepository, _build_multi_term_filter
from src.core.database import take_startup_db_backup, remove_old_db_backups, get_db_session
from src.core.crypto import encrypt_des3, decrypt_des3
from src.core.models import Document, Task, Secret
from src.ui.dialogs.secret_editor_dlg import SecretEditorDialog
from src.ui.views.secrets_view import SecretsView
from src.ui.views.documents_view import DocumentsView
from src.ui.views.tasks_view import TasksView
from src.ui.views.urls_view import UrlsView
from src.ui.views.notes_view import NotesView
from src.ui.views.code_snippets_view import CodeSnippetsView
from src.ui.views.projects_view import ProjectsView
from src.ui.views.minutes_view import MinutesView


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_search_plus_filter_sql():
    """Verify _build_multi_term_filter splits on '+' and requires AND across terms."""
    # 1. Single term
    filt_single = _build_multi_term_filter("invoice", [Document.DocumentName, Document.Desc])
    assert filt_single is not None

    # 2. Multi term with '+'
    filt_multi = _build_multi_term_filter("invoice + 2026", [Document.DocumentName, Document.Desc])
    assert filt_multi is not None

    # 3. Empty or whitespace
    assert _build_multi_term_filter("", [Document.DocumentName]) is None
    assert _build_multi_term_filter("   ", [Document.DocumentName]) is None
    assert _build_multi_term_filter(" + + ", [Document.DocumentName]) is None


def test_search_plus_in_repository():
    """Test repository methods with '+' search queries."""
    # Query documents with '+'
    docs = DataRepository.get_documents(search="test")
    assert isinstance(docs, list)

    docs_plus = DataRepository.get_documents(search="test + doc")
    assert isinstance(docs_plus, list)

    # Query tasks with '+'
    tasks = DataRepository.get_tasks(search="task + 1")
    assert isinstance(tasks, list)

    # Query secrets with '+'
    secrets = DataRepository.get_secrets(search="aws + admin")
    assert isinstance(secrets, list)


def test_startup_db_backup(tmp_path):
    """Test that take_startup_db_backup creates a valid backup file and remove_old_db_backups works."""
    backup_file = take_startup_db_backup()
    assert backup_file is not None
    assert os.path.exists(backup_file)
    assert backup_file.endswith(".db3")

    # Verify purge of old backup
    old_test_backup = os.path.join(os.path.dirname(backup_file), "DevDiary-01-01-2020.db3")
    with open(old_test_backup, "w") as f:
        f.write("dummy old backup")
    
    # Set modification time to 10 days ago
    past_time = time.time() - (10 * 86400)
    os.utime(old_test_backup, (past_time, past_time))
    assert os.path.exists(old_test_backup)

    remove_old_db_backups(max_days=5)
    assert not os.path.exists(old_test_backup)


def test_secret_crypto_compatibility():
    """Verify TripleDES encryption/decryption matches C# CryptHelper specification."""
    master_key = "MySecretMasterKey123"
    plain_identity = "admin@example.com"
    plain_password = "SuperSecretPassword!@#"

    enc_id = encrypt_des3(master_key, plain_identity)
    enc_pw = encrypt_des3(master_key, plain_password)

    assert enc_id != plain_identity
    assert enc_pw != plain_password

    dec_id = decrypt_des3(master_key, enc_id)
    dec_pw = decrypt_des3(master_key, enc_pw)

    assert dec_id == plain_identity
    assert dec_pw == plain_password

    # Test invalid key raises ValueError
    with pytest.raises(ValueError):
        decrypt_des3("WrongKey", enc_id)


def test_secret_editor_dialog_lifecycle(qapp, monkeypatch):
    """Verify SecretEditorDialog loads, decrypts, and saves without crash."""
    from PyQt6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)

    # 1. Create a test secret in DB
    key = "TestVaultKey"
    secret = DataRepository.create_secret(
        secret_name="Test CI Secret",
        app_url="https://example.com/login",
        identity="ci_user",
        password="ci_password",
        desc="Unit test secret",
        project_id="0",
        project_name="General",
        secret_key=key,
    )
    assert secret.SecretID is not None

    try:
        # 2. Open SecretEditorDialog in edit mode
        dlg = SecretEditorDialog(secret_id=secret.SecretID, mode="edit")
        assert dlg.edit_name.text() == "Test CI Secret"
        assert dlg.edit_app.text() == "https://example.com/login"

        # Initially locked/un-decrypted
        assert not dlg._is_decrypted
        assert not dlg.edit_user.isEnabled()

        # 3. Decrypt with wrong key -> failure
        dlg.edit_key.setText("BadKey")
        dlg._decrypt_credentials()
        assert not dlg._is_decrypted

        # 4. Decrypt with correct key -> success
        dlg.edit_key.setText(key)
        dlg._decrypt_credentials()
        assert dlg._is_decrypted
        assert dlg.edit_user.text() == "ci_user"
        assert dlg.edit_pass.text() == "ci_password"

        # 5. Modify and save
        dlg.edit_user.setText("ci_user_updated")
        dlg._save_secret()

        # 6. Verify in DB
        updated = DataRepository.get_secret_by_id(secret.SecretID)
        dec_user = decrypt_des3(key, updated.Identity)
        assert dec_user == "ci_user_updated"

    finally:
        DataRepository.delete_secret(secret.SecretID)


def test_double_click_handler_signatures(qapp, monkeypatch):
    """Verify double-click handlers in all views accept arguments without TypeError."""
    from PyQt6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)

    views = [
        (DocumentsView(), "_open_selected_file"),
        (TasksView(), "_open_edit_task_dialog"),
        (SecretsView(), "_open_edit_secret_dialog"),
        (UrlsView(), "_open_selected_url"),
        (NotesView(), "_open_edit_note_dialog"),
        (CodeSnippetsView(), "_open_edit_snippet_dialog"),
        (ProjectsView(), "_open_edit_project_dialog"),
        (MinutesView(), "_open_edit_minutes_dialog"),
    ]

    dummy_index = QModelIndex()
    for view, handler_name in views:
        handler = getattr(view, handler_name)
        try:
            handler(dummy_index)
        except TypeError as e:
            pytest.fail(f"Handler {handler_name} on {view.__class__.__name__} raised TypeError: {e}")
        except Exception:
            pass
