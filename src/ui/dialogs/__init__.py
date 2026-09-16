"""
Modal Editor and Creation Dialogs for DigitalBrainEX AI.
"""
from src.ui.dialogs.note_editor_dlg import NoteEditorDialog
from src.ui.dialogs.task_editor_dlg import TaskEditorDialog
from src.ui.dialogs.project_editor_dlg import ProjectEditorDialog
from src.ui.dialogs.document_editor_dlg import DocumentEditorDialog
from src.ui.dialogs.url_editor_dlg import UrlEditorDialog
from src.ui.dialogs.code_snippet_editor_dlg import CodeSnippetEditorDialog
from src.ui.dialogs.minutes_editor_dlg import MinutesEditorDialog
from src.ui.dialogs.secret_editor_dlg import SecretEditorDialog
from src.ui.dialogs.embedding_progress_dialog import EmbeddingProgressDialog

__all__ = [
    "NoteEditorDialog",
    "TaskEditorDialog",
    "ProjectEditorDialog",
    "DocumentEditorDialog",
    "UrlEditorDialog",
    "CodeSnippetEditorDialog",
    "MinutesEditorDialog",
    "SecretEditorDialog",
    "EmbeddingProgressDialog",
]
