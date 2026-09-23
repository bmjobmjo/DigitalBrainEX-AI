"""
Unit tests for NotesView tabbed interface, NoteTabEditor, default naming, and auto-save.
"""
import pytest
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt

from src.core.repository import DataRepository
from src.ui.views.notes_view import NotesView, NoteTabEditor
from src.ui.dialogs.save_note_dlg import SaveNoteMetadataDialog

# Ensure QApplication exists
app = QApplication.instance() or QApplication(["test_notes_tabs"])


@pytest.fixture
def sample_note():
    doc = DataRepository.create_document(
        name="Test Patient Notes 2026",
        desc="Initial observation notes.",
        notes="Initial observation notes.",
        project_id=0,
        project_name="General",
        category="Clinical",
        doc_type=2,
    )
    yield doc
    try:
        DataRepository.delete_document(doc.DocumentID)
    except Exception:
        pass


def test_notes_view_init():
    view = NotesView()
    assert view.tab_widget.count() >= 1
    assert "All Notes" in view.tab_widget.tabText(0)
    assert view.tab_widget.tabBar().tabButton(0, view.tab_widget.tabBar().ButtonPosition.RightSide) is None
    assert view.table.rowCount() >= 0


def test_create_new_note_tab_default_naming():
    view = NotesView()
    initial_tab_count = view.tab_widget.count()

    # Create first new note tab
    editor1 = view.create_new_note_tab()
    assert view.tab_widget.count() == initial_tab_count + 1
    assert editor1.title.startswith("Note ")
    tab1_title = editor1.title
    assert view.tab_widget.tabText(initial_tab_count) == tab1_title
    assert view.tab_widget.currentIndex() == initial_tab_count

    # Create second new note tab
    editor2 = view.create_new_note_tab()
    assert view.tab_widget.count() == initial_tab_count + 2
    tab2_title = editor2.title
    assert tab2_title != tab1_title
    assert tab2_title.startswith("Note ")
    assert view.tab_widget.currentIndex() == initial_tab_count + 1

    # Cleanup open tabs
    view.tab_widget.removeTab(initial_tab_count + 1)
    view.tab_widget.removeTab(initial_tab_count)


def test_open_existing_note_and_prevent_duplicates(sample_note):
    view = NotesView()
    initial_count = view.tab_widget.count()

    # 1. Open note in tab
    editor = view.open_note_tab(sample_note.DocumentID)
    assert editor is not None
    assert editor.note_id == sample_note.DocumentID
    assert editor.title == sample_note.DocumentName
    assert editor.category == "Clinical"
    assert "Initial observation notes." in editor.editor.toPlainText()
    assert view.tab_widget.count() == initial_count + 1
    open_idx = view.tab_widget.currentIndex()

    # 2. Try opening the same note again -> should switch to existing tab without adding another
    reopened = view.open_note_tab(sample_note.DocumentID)
    assert reopened is editor
    assert view.tab_widget.count() == initial_count + 1
    assert view.tab_widget.currentIndex() == open_idx

    # Close the tab
    view._on_tab_close_requested(open_idx)
    assert view.tab_widget.count() == initial_count


def test_save_note_with_metadata_dialog(sample_note, monkeypatch):
    view = NotesView()
    editor = view.open_note_tab(sample_note.DocumentID)
    tab_idx = view.tab_widget.indexOf(editor)

    # Edit body
    editor.editor.setPlainText("Updated clinical observations and notes.")
    assert editor.is_dirty is True
    assert "Unsaved changes" in editor.lbl_status.text()

    # Mock SaveNoteMetadataDialog.prompt to return new title and category
    monkeypatch.setattr(
        SaveNoteMetadataDialog,
        "prompt",
        lambda parent, initial_title, initial_category, initial_project_id: (
            "Renamed Clinical Study",
            "Research",
            0,
            "General",
        ),
    )

    success = editor.save_note(prompt_metadata=True)
    assert success is True
    assert editor.title == "Renamed Clinical Study"
    assert editor.category == "Research"
    assert editor.is_dirty is False
    assert "Saved at" in editor.lbl_status.text()
    assert view.tab_widget.tabText(tab_idx) == "Renamed Clinical Study"

    # Verify database was updated
    updated_doc = DataRepository.get_document_by_id(sample_note.DocumentID)
    assert updated_doc.DocumentName == "Renamed Clinical Study"
    assert updated_doc.Category == "Research"
    assert "Updated clinical observations" in updated_doc.Desc

    # Clean up tab
    view._on_tab_close_requested(tab_idx)


def test_auto_save_functionality(sample_note):
    view = NotesView()
    editor = view.open_note_tab(sample_note.DocumentID)
    tab_idx = view.tab_widget.indexOf(editor)

    editor.editor.setPlainText("Content auto-saved during active writing.")
    assert editor.is_dirty is True

    # Trigger auto_save directly (same as timer timeout)
    editor.auto_save()

    assert editor.is_dirty is False
    assert "Auto-saved at" in editor.lbl_status.text()

    # Verify persisted in database
    db_doc = DataRepository.get_document_by_id(sample_note.DocumentID)
    assert db_doc.Desc == "Content auto-saved during active writing."

    # Clean up tab
    view._on_tab_close_requested(tab_idx)


def test_delete_note_closes_open_tab(sample_note, monkeypatch):
    view = NotesView()
    editor = view.open_note_tab(sample_note.DocumentID)
    assert view.tab_widget.indexOf(editor) > 0

    # Ensure table has sample_note and select it
    found_row = -1
    for r in range(view.table.rowCount()):
        item = view.table.item(r, 0)
        if item and item.data(Qt.ItemDataRole.UserRole) == sample_note.DocumentID:
            found_row = r
            break

    assert found_row >= 0
    view.table.setCurrentCell(found_row, 0)
    view.table.selectRow(found_row)
    app.processEvents()

    # Mock confirmation to Yes, and mock information to no-op
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)

    view._delete_note()

    # Tab should be closed
    assert view.tab_widget.indexOf(editor) == -1
    # Document should be deleted from DB
    assert DataRepository.get_document_by_id(sample_note.DocumentID) is None
