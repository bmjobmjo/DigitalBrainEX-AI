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
    app.processEvents()
    clipboard_text = QApplication.clipboard().text()
    assert temp_files[0] in clipboard_text
    assert temp_files[1] in clipboard_text

    captured = {}
    orig_set_mime = QApplication.clipboard().setMimeData
    def mock_set_mime(m):
        captured["has_urls"] = m.hasUrls()
        captured["urls"] = [u.toLocalFile() for u in m.urls()]
        orig_set_mime(m)
    monkeypatch.setattr(QApplication.clipboard(), "setMimeData", mock_set_mime)

    view._copy_selected_files_to_clipboard()
    assert captured.get("has_urls") is True
    norm_urls = [os.path.normpath(u) for u in captured.get("urls", [])]
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


def test_file_manager_excludes_clipboard_images_and_screenshots(monkeypatch):
    """Verify that clipboard images, screenshots, and temp lock files are strictly excluded from File Manager."""
    with tempfile.TemporaryDirectory() as temp_watch_dir:
        # Create various files in the watch folder
        valid_doc = os.path.join(temp_watch_dir, "QuarterlyReport.pdf")
        clip_img = os.path.join(temp_watch_dir, "ClipImage_20260922_101010.png")
        screen_img = os.path.join(temp_watch_dir, "Screenshot_20260922_101010.png")
        lock_file = os.path.join(temp_watch_dir, "~$DraftReport.docx")
        temp_dl = os.path.join(temp_watch_dir, "bigfile.crdownload")

        for p in [valid_doc, clip_img, screen_img, lock_file, temp_dl]:
            with open(p, "w") as f:
                f.write("test data")

        # Mock watch folders to return this folder
        monkeypatch.setattr(
            "src.ui.views.file_manager_view.DataRepository.get_watch_folders",
            lambda: [temp_watch_dir],
        )

        view = FileManagerView()
        app.processEvents()

        file_names = [f["name"] for f in view._files]
        assert "QuarterlyReport.pdf" in file_names
        assert "ClipImage_20260922_101010.png" not in file_names
        assert "Screenshot_20260922_101010.png" not in file_names
        assert "~$DraftReport.docx" not in file_names
        assert "bigfile.crdownload" not in file_names

        # Find row with QuarterlyReport.pdf
        found = False
        for r in range(view.table.rowCount()):
            if view.table.item(r, 0).text() == "QuarterlyReport.pdf":
                assert view.table.item(r, 3).text() == "WatchFolder"
                found = True
        assert found, "QuarterlyReport.pdf was not found in File Manager table"


def test_file_manager_watch_folder_event_bus(monkeypatch):
    """Verify that EVT_WATCH_FOLDER_FILE automatically triggers File Manager data reload."""
    from src.core.event_bus import event_bus, EVT_WATCH_FOLDER_FILE

    with tempfile.TemporaryDirectory() as temp_watch_dir:
        doc1 = os.path.join(temp_watch_dir, "Initial.pdf")
        with open(doc1, "w") as f:
            f.write("initial")

        monkeypatch.setattr(
            "src.ui.views.file_manager_view.DataRepository.get_watch_folders",
            lambda: [temp_watch_dir],
        )

        view = FileManagerView()
        app.processEvents()
        assert any(f["name"] == "Initial.pdf" for f in view._files)

        # Now simulate a new file arriving in the watch folder
        doc2 = os.path.join(temp_watch_dir, "ArrivedLater.pdf")
        with open(doc2, "w") as f:
            f.write("arrived later")

        event_bus.publish(EVT_WATCH_FOLDER_FILE, file_path=doc2)
        app.processEvents()

        # Check that ArrivedLater.pdf now appears in File Manager
        file_names = [f["name"] for f in view._files]
        assert "ArrivedLater.pdf" in file_names
        view.close()
