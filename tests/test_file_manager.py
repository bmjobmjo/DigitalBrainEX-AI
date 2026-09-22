import os
import tempfile
import pytest
from PyQt6.QtWidgets import QApplication, QMessageBox, QTableWidget, QTableWidgetItem
from PyQt6.QtCore import Qt, QItemSelectionModel
from src.ui.views.file_manager_view import FileManagerView

app = QApplication.instance() or QApplication(["test_file_manager"])

@pytest.fixture
def temp_files():
    temp_dir = tempfile.TemporaryDirectory()
    p1 = os.path.join(temp_dir.name, "doc1.txt")
    p2 = os.path.join(temp_dir.name, "doc2.txt")
    p3 = os.path.join(temp_dir.name, "img1.png")
    with open(p1, "w") as f:
        f.write("Content 1")
    with open(p2, "w") as f:
        f.write("Content 2")
    with open(p3, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
    yield [p1, p2, p3]
    temp_dir.cleanup()


def test_file_manager_init_state():
    view = FileManagerView()
    assert view.table.selectionMode() == QTableWidget.SelectionMode.ExtendedSelection
    assert view.preview_container.isHidden()
    assert view.table.contextMenuPolicy() == Qt.ContextMenuPolicy.CustomContextMenu


def test_file_manager_preview_and_close(temp_files):
    view = FileManagerView()
    view._files = [
        {"name": os.path.basename(p), "path": p, "size": "1 KB", "modified": "2026-09-22 10:00", "source": "TempPad"}
        for p in temp_files
    ]
    view.table.setRowCount(len(view._files))
    for r, f in enumerate(view._files):
        item = QTableWidgetItem(f["name"])
        item.setData(Qt.ItemDataRole.UserRole, f["path"])
        view.table.setItem(r, 0, item)

    assert view.preview_container.isHidden()

    view.table.selectRow(0)
    app.processEvents()

    assert not view.preview_container.isHidden()
    assert os.path.basename(temp_files[0]) in view.lbl_selected_file.text()

    view.btn_close_preview.click()
    app.processEvents()

    assert view.preview_container.isHidden()


def test_file_manager_clipboard_actions(temp_files, monkeypatch):
    view = FileManagerView()
    view._files = [
        {"name": os.path.basename(p), "path": p, "size": "1 KB", "modified": "2026-09-22 10:00", "source": "TempPad"}
        for p in temp_files
    ]
    view.table.setRowCount(len(view._files))
    for r, f in enumerate(view._files):
        item = QTableWidgetItem(f["name"])
        item.setData(Qt.ItemDataRole.UserRole, f["path"])
        view.table.setItem(r, 0, item)

    # Multi-select rows 0 and 1
    sel_model = view.table.selectionModel()
    idx0 = view.table.model().index(0, 0)
    idx1 = view.table.model().index(1, 0)
    sel_model.select(idx0, QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
    sel_model.select(idx1, QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
    app.processEvents()

    selected = view._get_selected_file_paths()
    assert len(selected) == 2

    view._copy_selected_paths()
    clipboard_text = QApplication.clipboard().text()
    assert temp_files[0] in clipboard_text
    assert temp_files[1] in clipboard_text

    view._copy_selected_files_to_clipboard()
    mime = QApplication.clipboard().mimeData()
    assert mime.hasUrls()
    norm_urls = [os.path.normpath(u.toLocalFile()) for u in mime.urls()]
    assert os.path.normpath(temp_files[0]) in norm_urls
    assert os.path.normpath(temp_files[1]) in norm_urls


def test_file_manager_delete_remove_from_manager_only(temp_files, monkeypatch):
    view = FileManagerView()
    view._files = [
        {"name": os.path.basename(p), "path": p, "size": "1 KB", "modified": "2026-09-22 10:00", "source": "TempPad"}
        for p in temp_files
    ]
    view.table.setRowCount(len(view._files))
    for r, f in enumerate(view._files):
        item = QTableWidgetItem(f["name"])
        item.setData(Qt.ItemDataRole.UserRole, f["path"])
        view.table.setItem(r, 0, item)

    sel_model = view.table.selectionModel()
    idx0 = view.table.model().index(0, 0)
    idx1 = view.table.model().index(1, 0)
    sel_model.select(idx0, QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
    sel_model.select(idx1, QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
    app.processEvents()

    def mock_exec(msg_box):
        for btn in msg_box.buttons():
            if btn.text() == "Remove from File Manager":
                msg_box.done(0)
                msg_box._mock_clicked = btn
                return 0
        return 0

    monkeypatch.setattr(QMessageBox, "exec", lambda self: mock_exec(self))
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda self: getattr(self, "_mock_clicked", None))

    view._delete_file()

    assert os.path.exists(temp_files[0])
    assert os.path.exists(temp_files[1])
    assert os.path.normpath(temp_files[0]) in view._dismissed_paths
    assert os.path.normpath(temp_files[1]) in view._dismissed_paths


def test_file_manager_delete_from_disk(temp_files, monkeypatch):
    view = FileManagerView()
    view._files = [
        {"name": os.path.basename(p), "path": p, "size": "1 KB", "modified": "2026-09-22 10:00", "source": "TempPad"}
        for p in temp_files
    ]
    view.table.setRowCount(len(view._files))
    for r, f in enumerate(view._files):
        item = QTableWidgetItem(f["name"])
        item.setData(Qt.ItemDataRole.UserRole, f["path"])
        view.table.setItem(r, 0, item)

    sel_model = view.table.selectionModel()
    idx0 = view.table.model().index(0, 0)
    idx1 = view.table.model().index(1, 0)
    sel_model.select(idx0, QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
    sel_model.select(idx1, QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
    app.processEvents()

    def mock_exec(msg_box):
        for btn in msg_box.buttons():
            if btn.text() == "Delete from Disk":
                msg_box.done(0)
                msg_box._mock_clicked = btn
                return 0
        return 0

    monkeypatch.setattr(QMessageBox, "exec", lambda self: mock_exec(self))
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda self: getattr(self, "_mock_clicked", None))

    view._delete_file()

    assert not os.path.exists(temp_files[0])
    assert not os.path.exists(temp_files[1])
    assert os.path.exists(temp_files[2])


def test_file_manager_double_click(temp_files, monkeypatch):
    view = FileManagerView()
    view._files = [
        {"name": os.path.basename(p), "path": p, "size": "1 KB", "modified": "2026-09-22 10:00", "source": "TempPad"}
        for p in temp_files
    ]
    view.table.setRowCount(len(view._files))
    for r, f in enumerate(view._files):
        item = QTableWidgetItem(f["name"])
        item.setData(Qt.ItemDataRole.UserRole, f["path"])
        view.table.setItem(r, 0, item)

    opened = []
    monkeypatch.setattr(os, "startfile", lambda p: opened.append(p))

    item = view.table.item(0, 0)
    view._on_table_double_clicked(item)

    assert len(opened) == 1
    assert opened[0] == temp_files[0]
