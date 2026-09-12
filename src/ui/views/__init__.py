"""UI Views package."""
from .projects_view import ProjectsView
from .tasks_view import TasksView
from .documents_view import DocumentsView
from .urls_view import UrlsView
from .code_snippets_view import CodeSnippetsView
from .minutes_view import MinutesView
from .file_manager_view import FileManagerView
from .notes_view import NotesView
from .secrets_view import SecretsView
from .trackme_view import TrackMeView
from .ask_me_view import AskMeView
from .settings_view import SettingsView

__all__ = [
    "ProjectsView",
    "TasksView",
    "DocumentsView",
    "UrlsView",
    "CodeSnippetsView",
    "MinutesView",
    "FileManagerView",
    "NotesView",
    "SecretsView",
    "TrackMeView",
    "AskMeView",
    "SettingsView",
]
