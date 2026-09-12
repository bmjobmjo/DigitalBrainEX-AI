"""
Integration Tests for Database Models and Repository.
Validates read-only access against live production database DevDiary-10-09-2026.db3.
"""
import unittest
import os
import sys

# Ensure src is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.repository import DataRepository
from src.core.models import (
    Project,
    Document,
    DocumentCategory,
    Url,
    Task,
    Secret,
    TrackMe,
    ClipboardHistory,
    WatchFolder,
)


class TestDatabaseModels(unittest.TestCase):

    def test_load_projects(self):
        projects = DataRepository.get_all_projects()
        self.assertGreater(len(projects), 0)
        print(f"\nLoaded {len(projects)} projects. First 3:")
        for p in projects[:3]:
            print(f"  - [{p.PojectID}] {p.ProjectName} (Status: {p.Status})")

    def test_load_tasks(self):
        tasks = DataRepository.get_tasks(status="All")
        self.assertGreater(len(tasks), 0)
        active_tasks = DataRepository.get_tasks(status="Active")
        print(f"Loaded {len(tasks)} total tasks ({len(active_tasks)} active).")

    def test_load_documents(self):
        docs = DataRepository.get_documents()
        self.assertGreater(len(docs), 0)
        # Check types distribution
        types = {}
        for d in docs:
            types[d.Type] = types.get(d.Type, 0) + 1
        print(f"Loaded {len(docs)} documents. Type distribution: {types}")

    def test_load_document_categories(self):
        categories = DataRepository.get_document_categories()
        self.assertGreater(len(categories), 0)
        print(f"Loaded {len(categories)} categories:")
        for c in categories[:5]:
            print(f"  - [{c.CatgoryID}] {c.CatogoryName}")

    def test_load_urls(self):
        urls = DataRepository.get_urls()
        self.assertGreater(len(urls), 0)
        print(f"Loaded {len(urls)} URLs. First 3:")
        for u in urls[:3]:
            print(f"  - [{u.UrlID}] {u.UrlName} -> {u.Url}")

    def test_load_secrets(self):
        secrets = DataRepository.get_secrets()
        self.assertGreater(len(secrets), 0)
        print(f"Loaded {len(secrets)} active secrets. First 3 names:")
        for s in secrets[:3]:
            print(f"  - [{s.SecretID}] {s.SecretName} (URL: {s.ApplicationURL})")

    def test_load_trackme_activity(self):
        recent = DataRepository.get_recent_activity(limit=10)
        self.assertGreater(len(recent), 0)
        print(f"Loaded {len(recent)} recent TrackMe entries. Top entry:")
        safe_title = (recent[0].WindowTitle or "").encode("ascii", "replace").decode("ascii")
        print(f"  - App: {recent[0].Application} | Title: {safe_title} | Secs: {recent[0].Seconds}")

    def test_load_clipboard_history(self):
        history = DataRepository.get_clipboard_history(limit=10)
        self.assertGreater(len(history), 0)
        print(f"Loaded {len(history)} recent clipboard history entries.")

    def test_load_watch_folders(self):
        folders = DataRepository.get_watch_folders()
        print(f"Loaded {len(folders)} watch folders: {folders}")

    def test_load_notes(self):
        notes = DataRepository.get_notes()
        self.assertGreater(len(notes), 0)
        self.assertEqual(notes[0].Category, "PlainNotes")
        print(f"Loaded {len(notes)} PlainNotes. Top note: [{notes[0].DocumentID}] {notes[0].DocumentName}")

    def test_load_minutes(self):
        minutes = DataRepository.get_minutes()
        self.assertGreater(len(minutes), 0)
        self.assertEqual(minutes[0].Category, "Minutes")
        print(f"Loaded {len(minutes)} Minutes. Top meeting: [{minutes[0].DocumentID}] {minutes[0].DocumentName}")

    def test_load_code_snippets(self):
        snippets = DataRepository.get_code_snippets()
        self.assertGreater(len(snippets), 0)
        self.assertIn(snippets[0].Type, [4, 5])
        print(f"Loaded {len(snippets)} Code Snippets. Top snippet: [{snippets[0].DocumentID}] {snippets[0].DocumentName}")


if __name__ == "__main__":
    unittest.main()
