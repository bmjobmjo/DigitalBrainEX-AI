"""
Settings View for DigitalBrainEX AI.
Multi-tab settings dialog matching reference screenshots (Profile, General, Hotkeys, Paths, GenAI, Audio).
"""
import os
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QCheckBox,
    QComboBox,
    QListWidget,
    QFileDialog,
    QMessageBox,
    QGroupBox,
    QApplication,
    QSpinBox,
    QFormLayout,
    QScrollArea,
    QFrame,
    QSizePolicy,
    QProgressBar,
)
from PyQt6.QtCore import Qt, QTimer
from src.config import DB_PATH, TEMP_PAD_DIR, SCREENSHOTS_DIR, APP_VERSION, DEFAULT_THEME
from src.ui.theme import apply_theme
from src.core.repository import DataRepository
from src.ui.icons import IconHelper
from src.utils.startup_manager import is_auto_startup_enabled, set_auto_startup
from src.core.logger import logger


class SettingsView(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ViewContentWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(1000)
        self._refresh_timer.timeout.connect(self.update_reminder_next_times)
        self._init_ui()
        self.load_settings()
        self.update_reminder_next_times()

    def _wrap_scrollable(self, content_widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setWidget(content_widget)
        return scroll

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(8)

        # Title
        title_label = QLabel("Settings")
        title_label.setObjectName("ViewTitleLabel")
        main_layout.addWidget(title_label)

        # Tab Widget
        self.tabs = QTabWidget()

        self.tabs.addTab(self._wrap_scrollable(self._create_general_tab()), "General & Startup")
        self.tabs.addTab(self._wrap_scrollable(self._create_wellness_tab()), "Wellness & Health")
        self.tabs.addTab(self._wrap_scrollable(self._create_genai_tab()), "GenAI & LLM")
        self.tabs.addTab(self._wrap_scrollable(self._create_hotkeys_tab()), "Hotkeys & Shortcuts")
        self.tabs.addTab(self._create_watchfolders_tab(), "Watch Folders")
        self.tabs.addTab(self._wrap_scrollable(self._create_paths_tab()), "Paths & Storage")
        self.tabs.addTab(self._wrap_scrollable(self._create_about_tab()), "About & Diagnostics")

        self.tabs.currentChanged.connect(self._on_tab_changed)
        main_layout.addWidget(self.tabs)

        # Bottom save button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_save_all = QPushButton("Save All Settings")
        self.btn_save_all.setIcon(IconHelper.get_icon("save", 16))
        self.btn_save_all.clicked.connect(self._save_all_settings)
        btn_layout.addWidget(self.btn_save_all)

        main_layout.addLayout(btn_layout)

    def _on_tab_changed(self, index: int):
        if index == 1:  # Wellness & Health
            self.update_reminder_next_times()

    def _create_general_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        self.chk_start_windows = QCheckBox("Start DigitalBrainEX on Windows Startup")
        self.chk_minimize_tray = QCheckBox("Minimize to System Tray when closing the window")
        self.chk_minimize_tray.setChecked(True)
        self.chk_enable_tracking = QCheckBox("Enable active window time tracking (TrackMe)")
        self.chk_enable_tracking.setChecked(True)
        self.chk_enable_clipboard = QCheckBox("Enable background clipboard history monitoring")
        self.chk_enable_clipboard.setChecked(True)
        self.chk_enable_reminder_blinker = QCheckBox("Enable flashing screen edge blinker for due task reminders")
        self.chk_enable_reminder_blinker.setChecked(True)

        for chk in (
            self.chk_start_windows,
            self.chk_minimize_tray,
            self.chk_enable_tracking,
            self.chk_enable_clipboard,
            self.chk_enable_reminder_blinker,
        ):
            layout.addWidget(chk)

        layout.addSpacing(10)
        theme_box = QGroupBox("Appearance & Theme")
        theme_layout = QHBoxLayout(theme_box)
        theme_layout.addWidget(QLabel("Color Theme:"))
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["Light (Default)", "Dark"])
        self.combo_theme.setCurrentIndex(0 if DEFAULT_THEME == "light" else 1)
        self.combo_theme.currentIndexChanged.connect(self._on_theme_changed)
        self.combo_theme.setFixedWidth(160)
        theme_layout.addWidget(self.combo_theme)
        theme_layout.addStretch()
        layout.addWidget(theme_box)

        layout.addStretch()
        return widget

    def _on_theme_changed(self, index: int):
        theme_name = "light" if index == 0 else "dark"
        app = QApplication.instance()
        if app:
            apply_theme(app, theme_name)

    def _create_wellness_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Row 1: Drink Water Reminder & Sedentary Reminder side-by-side
        timers_row = QHBoxLayout()
        timers_row.setSpacing(12)

        # 1. Drink Water Reminder
        grp_water = QGroupBox("Drink Water (Hydration) Reminder")
        grp_water.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        water_layout = QVBoxLayout(grp_water)
        water_layout.setContentsMargins(14, 14, 14, 14)
        water_layout.setSpacing(8)

        self.chk_water_reminder = QCheckBox("Enable Drink Water Reminder")
        self.chk_water_reminder.setChecked(True)
        self.chk_water_reminder.toggled.connect(self.update_reminder_next_times)
        water_layout.addWidget(self.chk_water_reminder)

        w_form = QFormLayout()
        self.spin_water_interval = QSpinBox()
        self.spin_water_interval.setRange(1, 240)
        self.spin_water_interval.setValue(45)
        self.spin_water_interval.setSuffix(" minutes")
        self.spin_water_interval.setFixedWidth(120)
        self.spin_water_interval.valueChanged.connect(self.update_reminder_next_times)
        w_form.addRow("Reminder Interval:", self.spin_water_interval)

        self.lbl_water_next_time = QLabel("--:-- --")
        self.lbl_water_next_time.setStyleSheet("font-weight: 600; color: #0284c7;")
        w_form.addRow("Next Reminder Time:", self.lbl_water_next_time)

        water_layout.addLayout(w_form)
        timers_row.addWidget(grp_water)

        # 2. Sedentary / Stand & Move Reminder
        grp_sed = QGroupBox("Sedentary / Stand & Move Reminder")
        grp_sed.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sed_layout = QVBoxLayout(grp_sed)
        sed_layout.setContentsMargins(14, 14, 14, 14)
        sed_layout.setSpacing(8)

        self.chk_sedentary_reminder = QCheckBox("Enable Sedentary Reminder")
        self.chk_sedentary_reminder.setChecked(True)
        self.chk_sedentary_reminder.toggled.connect(self.update_reminder_next_times)
        sed_layout.addWidget(self.chk_sedentary_reminder)

        s_form = QFormLayout()
        self.spin_sedentary_interval = QSpinBox()
        self.spin_sedentary_interval.setRange(1, 240)
        self.spin_sedentary_interval.setValue(60)
        self.spin_sedentary_interval.setSuffix(" minutes")
        self.spin_sedentary_interval.setFixedWidth(120)
        self.spin_sedentary_interval.valueChanged.connect(self.update_reminder_next_times)
        s_form.addRow("Reminder Interval:", self.spin_sedentary_interval)

        self.lbl_sedentary_next_time = QLabel("--:-- --")
        self.lbl_sedentary_next_time.setStyleSheet("font-weight: 600; color: #0284c7;")
        s_form.addRow("Next Reminder Time:", self.lbl_sedentary_next_time)

        sed_layout.addLayout(s_form)
        timers_row.addWidget(grp_sed)

        layout.addLayout(timers_row)

        # 3. Smart Inactivity & Lock Detection
        grp_activity = QGroupBox("Active Input & Inactivity Detection")
        grp_activity.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        act_layout = QVBoxLayout(grp_activity)
        act_layout.setContentsMargins(14, 14, 14, 14)
        act_layout.setSpacing(8)

        lbl_desc = QLabel(
            "Timers accumulate while you are actively using keyboard or mouse and logged in.\n"
            "If mouse/keyboard becomes inactive, counting pauses until you resume. If workstation is locked or during extended absence, timers reset."
        )
        lbl_desc.setStyleSheet("color: #475569; font-size: 11px;")
        lbl_desc.setWordWrap(True)
        act_layout.addWidget(lbl_desc)

        a_form = QFormLayout()
        self.spin_idle_threshold = QSpinBox()
        self.spin_idle_threshold.setRange(10, 600)
        self.spin_idle_threshold.setValue(60)
        self.spin_idle_threshold.setSuffix(" seconds")
        self.spin_idle_threshold.setFixedWidth(120)
        a_form.addRow("Inactivity Pause Threshold:", self.spin_idle_threshold)
        act_layout.addLayout(a_form)
        layout.addWidget(grp_activity)

        # 4. Preview / Test Buttons
        grp_test = QGroupBox("Preview & Test Alerts")
        grp_test.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        test_layout = QHBoxLayout(grp_test)
        test_layout.setContentsMargins(14, 14, 14, 14)
        test_layout.setSpacing(10)

        btn_test_water = QPushButton("Preview Water Alert")
        btn_test_water.setIcon(IconHelper.get_icon("water_drop", 16))
        btn_test_water.setMinimumHeight(28)
        btn_test_water.clicked.connect(self._test_water_alert)
        test_layout.addWidget(btn_test_water)

        btn_test_sed = QPushButton("Preview Sedentary Alert")
        btn_test_sed.setIcon(IconHelper.get_icon("sedentary_walk", 16))
        btn_test_sed.setMinimumHeight(28)
        btn_test_sed.clicked.connect(self._test_sedentary_alert)
        test_layout.addWidget(btn_test_sed)

        test_layout.addStretch()
        layout.addWidget(grp_test)

        layout.addStretch()
        return widget

    def _test_water_alert(self):
        from src.ui.components.wellness_alert_banner import flash_wellness_alert
        flash_wellness_alert(
            "water",
            "Hydration Reminder (Test)",
            f"You have been working actively for {self.spin_water_interval.value()} minutes. Time to drink a glass of water!"
        )

    def _test_sedentary_alert(self):
        from src.ui.components.wellness_alert_banner import flash_wellness_alert
        flash_wellness_alert(
            "sedentary",
            "Stand Up & Stretch (Test)",
            f"You have been sitting for {self.spin_sedentary_interval.value()} minutes. Stand up, stretch, and move around!"
        )

    def _create_genai_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. OpenRouter Configuration (Primary AskMe Provider)
        grp_openrouter = QGroupBox("OpenRouter AI Assistant Configuration (AskMe)")
        grp_openrouter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        or_layout = QVBoxLayout(grp_openrouter)
        or_layout.setContentsMargins(14, 14, 14, 14)
        or_layout.setSpacing(8)

        self.chk_openrouter_enable = QCheckBox("Enable OpenRouter for AskMe AI Assistant & Document Q&A")
        self.chk_openrouter_enable.setStyleSheet("font-weight: bold; color: #1e3a8a;")
        or_layout.addWidget(self.chk_openrouter_enable)

        # API Key row
        or_layout.addWidget(QLabel("OpenRouter API Key (or set OPENROUTER_API_KEY environment variable):"))
        key_widget = QWidget()
        key_layout = QHBoxLayout(key_widget)
        key_layout.setContentsMargins(0, 0, 0, 0)
        key_layout.setSpacing(6)

        self.edit_openrouter_key = QLineEdit()
        self.edit_openrouter_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_openrouter_key.setPlaceholderText("sk-or-v1-...")
        self.edit_openrouter_key.setMinimumHeight(28)
        key_layout.addWidget(self.edit_openrouter_key)

        self.btn_toggle_key = QPushButton("Show")
        self.btn_toggle_key.setFixedWidth(65)
        self.btn_toggle_key.setMinimumHeight(28)
        self.btn_toggle_key.clicked.connect(self._toggle_key_visibility)
        key_layout.addWidget(self.btn_toggle_key)
        or_layout.addWidget(key_widget)

        # Model Selector
        or_layout.addWidget(QLabel("Preferred Model:"))
        self.combo_openrouter_model = QComboBox()
        self.combo_openrouter_model.setEditable(True)
        self.combo_openrouter_model.setMinimumHeight(28)
        self.combo_openrouter_model.addItems([
            "anthropic/claude-3.5-sonnet",
            "openai/gpt-4o-mini",
            "openai/gpt-4o",
            "google/gemini-2.0-flash-001",
            "meta-llama/llama-3.3-70b-instruct",
            "deepseek/deepseek-chat",
            "qwen/qwen-2.5-72b-instruct",
        ])
        or_layout.addWidget(self.combo_openrouter_model)

        # Test Connection Row
        test_row = QHBoxLayout()
        test_row.setSpacing(10)
        self.btn_test_openrouter = QPushButton("Test OpenRouter Connection")
        self.btn_test_openrouter.setIcon(IconHelper.get_icon("refresh", 16))
        self.btn_test_openrouter.setMinimumHeight(28)
        self.btn_test_openrouter.clicked.connect(self._test_openrouter_connection)
        test_row.addWidget(self.btn_test_openrouter)

        self.lbl_test_result = QLabel("")
        self.lbl_test_result.setStyleSheet("font-weight: 500;")
        test_row.addWidget(self.lbl_test_result)
        test_row.addStretch()
        or_layout.addLayout(test_row)

        layout.addWidget(grp_openrouter)

        # 2. Local Document Embedding Configuration
        grp_embed = QGroupBox("Local Document Embedding Engine (100% On-Device RAG)")
        grp_embed.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        embed_layout = QVBoxLayout(grp_embed)
        embed_layout.setContentsMargins(14, 14, 14, 14)
        embed_layout.setSpacing(8)

        lbl_embed_info = QLabel(
            "Embeddings are computed locally on your device without sending document contents to external APIs."
        )
        lbl_embed_info.setStyleSheet("color: #64748b; font-size: 11px;")
        embed_layout.addWidget(lbl_embed_info)

        # 2-column row for Model Name & Version
        mv_row = QHBoxLayout()
        mv_row.setSpacing(12)

        col_name = QVBoxLayout()
        col_name.setSpacing(4)
        col_name.addWidget(QLabel("Local Model Name:"))
        self.edit_embedding_model = QLineEdit()
        self.edit_embedding_model.setText("Qwen/Qwen3-Embedding-0.6B")
        self.edit_embedding_model.setMinimumHeight(28)
        col_name.addWidget(self.edit_embedding_model)
        mv_row.addLayout(col_name, stretch=3)

        col_ver = QVBoxLayout()
        col_ver.setSpacing(4)
        col_ver.addWidget(QLabel("Model Version:"))
        self.edit_embedding_version = QLineEdit()
        self.edit_embedding_version.setText("1.0")
        self.edit_embedding_version.setMinimumHeight(28)
        col_ver.addWidget(self.edit_embedding_version)
        mv_row.addLayout(col_ver, stretch=1)

        embed_layout.addLayout(mv_row)

        # Process pending button and status
        proc_row = QHBoxLayout()
        proc_row.setSpacing(10)
        self.btn_process_embeddings = QPushButton("Index All Unindexed Documents Now")
        self.btn_process_embeddings.setIcon(IconHelper.get_icon("ai", 16))
        self.btn_process_embeddings.setMinimumHeight(28)
        self.btn_process_embeddings.clicked.connect(self._process_pending_embeddings)
        proc_row.addWidget(self.btn_process_embeddings)

        self.btn_cancel_embeddings = QPushButton("Cancel")
        self.btn_cancel_embeddings.setIcon(IconHelper.get_icon("delete", 14))
        self.btn_cancel_embeddings.setMinimumHeight(28)
        self.btn_cancel_embeddings.setVisible(False)
        self.btn_cancel_embeddings.clicked.connect(self._cancel_embeddings)
        proc_row.addWidget(self.btn_cancel_embeddings)

        self.lbl_pending_status = QLabel("")
        self.lbl_pending_status.setStyleSheet("color: #475569; font-weight: 500;")
        proc_row.addWidget(self.lbl_pending_status)
        proc_row.addStretch()
        embed_layout.addLayout(proc_row)

        self.prog_embeddings = QProgressBar()
        self.prog_embeddings.setRange(0, 100)
        self.prog_embeddings.setValue(0)
        self.prog_embeddings.setTextVisible(True)
        self.prog_embeddings.setFixedHeight(18)
        self.prog_embeddings.setVisible(False)
        embed_layout.addWidget(self.prog_embeddings)

        layout.addWidget(grp_embed)

        # 3. Side-by-side row for Gemini & Audio Fallbacks
        row_extra = QHBoxLayout()
        row_extra.setSpacing(12)

        grp_gemini = QGroupBox("Google Gemini Configuration (Optional)")
        grp_gemini.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        gemini_layout = QVBoxLayout(grp_gemini)
        gemini_layout.setContentsMargins(14, 14, 14, 14)
        gemini_layout.setSpacing(8)

        gemini_layout.addWidget(QLabel("Gemini API Key (or set GEMINI_API_KEY environment variable):"))
        self.edit_gemini_key = QLineEdit()
        self.edit_gemini_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_gemini_key.setPlaceholderText("AIzaSy...")
        self.edit_gemini_key.setMinimumHeight(28)
        self.edit_gemini_key.setText(os.environ.get("GEMINI_API_KEY", ""))
        gemini_layout.addWidget(self.edit_gemini_key)

        gemini_layout.addWidget(QLabel("Default LLM Model:"))
        self.combo_llm_model = QComboBox()
        self.combo_llm_model.setMinimumHeight(28)
        self.combo_llm_model.addItems(["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"])
        gemini_layout.addWidget(self.combo_llm_model)
        gemini_layout.addStretch()

        row_extra.addWidget(grp_gemini)

        # 4. Speech & Audio
        grp_audio = QGroupBox("Speech & Transcription")
        grp_audio.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        audio_layout = QVBoxLayout(grp_audio)
        audio_layout.setContentsMargins(14, 14, 14, 14)
        audio_layout.setSpacing(8)

        audio_layout.addWidget(QLabel("Speech-to-Text Engine:"))
        self.combo_stt_engine = QComboBox()
        self.combo_stt_engine.setMinimumHeight(28)
        self.combo_stt_engine.addItems(["Local Whisper (Faster-Whisper)", "Gemini Cloud Audio API", "Vosk (Offline)"])
        audio_layout.addWidget(self.combo_stt_engine)

        lbl_aud = QLabel("Whisper provides offline speech-to-text without cloud dependencies.")
        lbl_aud.setStyleSheet("color: #64748b; font-size: 11px;")
        lbl_aud.setWordWrap(True)
        audio_layout.addWidget(lbl_aud)
        audio_layout.addStretch()

        row_extra.addWidget(grp_audio)

        layout.addLayout(row_extra)
        layout.addStretch()
        return widget

    def _create_hotkeys_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Screenshot Region / Screen Capture Hotkey:"))
        self.edit_hk_screenshot = QLineEdit("Ctrl+P")
        layout.addWidget(self.edit_hk_screenshot)

        layout.addWidget(QLabel("Clipboard History Dialog Hotkey:"))
        self.edit_hk_clipboard = QLineEdit("Ctrl+H")
        layout.addWidget(self.edit_hk_clipboard)

        layout.addWidget(QLabel("Quick Task Note Hotkey:"))
        self.edit_hk_quick_task = QLineEdit("Ctrl+Shift+T")
        layout.addWidget(self.edit_hk_quick_task)

        layout.addStretch()
        return widget

    def _create_watchfolders_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Monitored Folders (Files are automatically tracked in TempPad):"))

        self.list_watchfolders = QListWidget()
        layout.addWidget(self.list_watchfolders)

        btn_bar = QHBoxLayout()
        self.btn_add_wf = QPushButton("+ Add Folder...")
        self.btn_add_wf.clicked.connect(self._add_watchfolder)
        btn_bar.addWidget(self.btn_add_wf)

        self.btn_remove_wf = QPushButton("- Remove Selected")
        self.btn_remove_wf.setObjectName("DangerButton")
        self.btn_remove_wf.clicked.connect(self._remove_watchfolder)
        btn_bar.addWidget(self.btn_remove_wf)

        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        return widget

    def _create_paths_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # DocFolder
        layout.addWidget(QLabel("Document Storage Root Folder (DocFolder):"))
        doc_folder_layout = QHBoxLayout()
        from src.utils.config_manager import get_doc_folder
        self.edit_doc_folder = QLineEdit(get_doc_folder())
        doc_folder_layout.addWidget(self.edit_doc_folder)

        btn_browse_doc = QPushButton("Browse...")
        btn_browse_doc.setIcon(IconHelper.get_icon("browse", 16))
        btn_browse_doc.clicked.connect(self._browse_doc_folder)
        doc_folder_layout.addWidget(btn_browse_doc)
        layout.addLayout(doc_folder_layout)

        lbl_doc_hint = QLabel(
            "All relative document paths in the database (e.g. \\3\\document.pdf) "
            "are resolved against this directory."
        )
        lbl_doc_hint.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(lbl_doc_hint)
        layout.addSpacing(6)

        layout.addWidget(QLabel("Active SQLite Database Path:"))
        db_path_layout = QHBoxLayout()
        self.edit_db_path = QLineEdit(str(DB_PATH))
        self.edit_db_path.setReadOnly(True)
        db_path_layout.addWidget(self.edit_db_path)
        layout.addLayout(db_path_layout)

        layout.addWidget(QLabel("Screenshots Output Folder:"))
        self.edit_screen_dir = QLineEdit(str(SCREENSHOTS_DIR))
        layout.addWidget(self.edit_screen_dir)

        layout.addWidget(QLabel("TempPad Working Folder:"))
        self.edit_temppad_dir = QLineEdit(str(TEMP_PAD_DIR))
        layout.addWidget(self.edit_temppad_dir)

        layout.addStretch()
        return widget

    def _create_about_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        about_text = (
            f"<h2>DigitalBrainEX AI</h2>"
            f"<p><b>Version:</b> {APP_VERSION}</p>"
            f"<p><b>Architecture:</b> Python 3.13 + PyQt6 Native Desktop App</p>"
            f"<p><b>Database:</b> SQLite 3 with SQLAlchemy 2.0 ORM</p>"
            f"<p><b>AI Engine:</b> Google Gemini API 2.0 / 1.5</p>"
            f"<p>Re-engineered with 100% database compatibility, zero data loss, "
            f"native system tray, transparent screenshot overlay, audio transcription, "
            f"and productivity analytics.</p>"
        )
        lbl_about = QLabel(about_text)
        lbl_about.setTextFormat(Qt.TextFormat.RichText)
        lbl_about.setStyleSheet("line-height: 1.6;")
        layout.addWidget(lbl_about)

        layout.addStretch()
        return widget

    def _toggle_key_visibility(self):
        if self.edit_openrouter_key.echoMode() == QLineEdit.EchoMode.Password:
            self.edit_openrouter_key.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_toggle_key.setText("Hide")
        else:
            self.edit_openrouter_key.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_toggle_key.setText("Show")

    def _test_openrouter_connection(self):
        key = self.edit_openrouter_key.text().strip()
        model = self.combo_openrouter_model.currentText().strip()
        if not key:
            self.lbl_test_result.setStyleSheet("color: #dc2626; font-weight: bold;")
            self.lbl_test_result.setText("Please enter an OpenRouter API key.")
            return

        self.lbl_test_result.setStyleSheet("color: #2563eb;")
        self.lbl_test_result.setText("Testing connection...")
        QApplication.processEvents()

        from src.ai.openrouter_client import OpenRouterClient
        client = OpenRouterClient(api_key=key, model=model, enabled=True)
        ok, msg = client.test_connection()
        if ok:
            self.lbl_test_result.setStyleSheet("color: #16a34a; font-weight: bold;")
            self.lbl_test_result.setText("Connection successful! Key and model verified.")
        else:
            self.lbl_test_result.setStyleSheet("color: #dc2626; font-weight: bold;")
            self.lbl_test_result.setText(f"Failed: {msg[:60]}...")

    def _process_pending_embeddings(self):
        pending = DataRepository.get_documents_by_embedding_status("PENDING")
        if not pending:
            QMessageBox.information(self, "No Pending Documents", "All documents in the system already have embeddings!")
            return

        self.btn_process_embeddings.setEnabled(False)
        self.btn_cancel_embeddings.setVisible(True)
        self.prog_embeddings.setVisible(True)
        self.prog_embeddings.setRange(0, len(pending))
        self.prog_embeddings.setValue(0)
        self.lbl_pending_status.setStyleSheet("color: #2563eb;")
        self.lbl_pending_status.setText(f"Starting indexing for {len(pending)} documents...")

        from src.background.embedding_worker import EmbeddingWorker
        self._worker = EmbeddingWorker(parent=self)

        def on_progress(current, total, doc_name, status_msg):
            self.prog_embeddings.setValue(current)
            self.lbl_pending_status.setText(f"[{current}/{total}] {doc_name[:35]}: {status_msg}")

        def on_all(total, succeeded):
            self.btn_process_embeddings.setEnabled(True)
            self.btn_cancel_embeddings.setVisible(False)
            self.prog_embeddings.setVisible(False)
            self.lbl_pending_status.setStyleSheet("color: #16a34a; font-weight: bold;")
            self.lbl_pending_status.setText(f"Completed! {succeeded}/{total} documents indexed.")
            self._update_pending_count()

        self._worker.progress_updated.connect(on_progress)
        self._worker.all_completed.connect(on_all)
        self._worker.start()

    def _cancel_embeddings(self):
        if hasattr(self, "_worker") and self._worker and self._worker.isRunning():
            self._worker.cancel()
            self.lbl_pending_status.setStyleSheet("color: #d97706; font-weight: bold;")
            self.lbl_pending_status.setText("Cancelling after current document completes...")
            self.btn_cancel_embeddings.setEnabled(False)

    def _update_pending_count(self):
        try:
            pending = DataRepository.get_documents_by_embedding_status("PENDING")
            failed = DataRepository.get_documents_by_embedding_status("FAILED")
            completed = DataRepository.get_documents_by_embedding_status("COMPLETED")
            c_len, p_len, f_len = len(completed), len(pending), len(failed)
            self.lbl_pending_status.setStyleSheet("color: #475569;")
            self.lbl_pending_status.setText(f"Indexed: {c_len} | Queue: {p_len} pending, {f_len} failed")
        except Exception:
            pass

    def load_settings(self):
        """Populates watch folders and active configurations."""
        self.list_watchfolders.clear()
        try:
            self.chk_start_windows.setChecked(is_auto_startup_enabled())
            folders = DataRepository.get_watch_folders()
            for f in folders:
                self.list_watchfolders.addItem(f)
        except Exception as e:
            logger.error(f"Error loading watch folders: {e}")

        # Load Wellness Settings
        try:
            from src.utils.config_manager import get_wellness_settings
            w_cfg = get_wellness_settings()
            self.chk_water_reminder.setChecked(w_cfg["water_reminder_enabled"])
            self.spin_water_interval.setValue(w_cfg["water_reminder_interval_min"])
            self.chk_sedentary_reminder.setChecked(w_cfg["sedentary_reminder_enabled"])
            self.spin_sedentary_interval.setValue(w_cfg["sedentary_reminder_interval_min"])
            self.spin_idle_threshold.setValue(w_cfg["wellness_idle_timeout_sec"])
        except Exception as e:
            logger.error(f"Error loading wellness settings: {e}")

        # Load OpenRouter & Embedding Settings
        try:
            from src.utils.config_manager import get_openrouter_settings, get_embedding_settings
            or_cfg = get_openrouter_settings()
            self.chk_openrouter_enable.setChecked(or_cfg["openrouter_enabled"])
            self.edit_openrouter_key.setText(or_cfg["openrouter_api_key"])
            idx = self.combo_openrouter_model.findText(or_cfg["openrouter_model"])
            if idx >= 0:
                self.combo_openrouter_model.setCurrentIndex(idx)
            else:
                self.combo_openrouter_model.setCurrentText(or_cfg["openrouter_model"])

            emb_cfg = get_embedding_settings()
            self.edit_embedding_model.setText(emb_cfg["embedding_model_name"])
            self.edit_embedding_version.setText(emb_cfg["embedding_model_version"])
            self._update_pending_count()
        except Exception as e:
            logger.error(f"Error loading OpenRouter/Embedding settings: {e}")

    def _add_watchfolder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Watch")
        if folder:
            DataRepository.add_watch_folder(folder)
            self.load_settings()

    def _remove_watchfolder(self):
        item = self.list_watchfolders.currentItem()
        if item:
            DataRepository.remove_watch_folder(item.text())
            self.load_settings()

    def _browse_doc_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Document Storage Root Folder", self.edit_doc_folder.text())
        if folder:
            self.edit_doc_folder.setText(folder)

    def _save_all_settings(self):
        # Update auto-startup in Windows registry
        set_auto_startup(self.chk_start_windows.isChecked())

        # Update Document Storage Folder
        new_doc_folder = self.edit_doc_folder.text().strip()
        if new_doc_folder:
            from src.utils.config_manager import set_doc_folder
            set_doc_folder(new_doc_folder)

        gemini_key = self.edit_gemini_key.text().strip()
        if gemini_key:
            os.environ["GEMINI_API_KEY"] = gemini_key

        # Update Wellness Settings
        try:
            from src.utils.config_manager import save_wellness_settings
            from src.background.wellness_reminders import wellness_engine
            save_wellness_settings({
                "water_reminder_enabled": self.chk_water_reminder.isChecked(),
                "water_reminder_interval_min": self.spin_water_interval.value(),
                "sedentary_reminder_enabled": self.chk_sedentary_reminder.isChecked(),
                "sedentary_reminder_interval_min": self.spin_sedentary_interval.value(),
                "wellness_idle_timeout_sec": self.spin_idle_threshold.value(),
            })
            wellness_engine.reload_settings()
        except Exception as e:
            logger.error(f"Error saving wellness settings: {e}")

        # Update OpenRouter & Embedding Settings
        try:
            from src.utils.config_manager import save_openrouter_settings, save_embedding_settings
            save_openrouter_settings({
                "openrouter_enabled": self.chk_openrouter_enable.isChecked(),
                "openrouter_api_key": self.edit_openrouter_key.text().strip(),
                "openrouter_model": self.combo_openrouter_model.currentText().strip(),
            })
            save_embedding_settings({
                "embedding_model_name": self.edit_embedding_model.text().strip(),
                "embedding_model_version": self.edit_embedding_version.text().strip(),
            })
        except Exception as e:
            logger.error(f"Error saving OpenRouter/Embedding settings: {e}")

        # Update displayed next reminder times immediately
        self.update_reminder_next_times()

        QMessageBox.information(self, "Settings Saved", "Application settings updated successfully!")

    def on_enter_screen(self):
        """Called whenever the user enters the Settings screen."""
        self.load_settings()
        self.update_reminder_next_times()
        if hasattr(self, "_refresh_timer") and not self._refresh_timer.isActive():
            self._refresh_timer.start()

    def showEvent(self, event):
        super().showEvent(event)
        self.on_enter_screen()

    def hideEvent(self, event):
        super().hideEvent(event)
        if hasattr(self, "_refresh_timer") and self._refresh_timer.isActive():
            self._refresh_timer.stop()

    def update_reminder_next_times(self):
        """Calculates and updates next scheduled reminder times for water and sedentary reminders."""
        import datetime
        now = datetime.datetime.now()

        from src.background.wellness_reminders import wellness_engine, get_idle_seconds

        idle_threshold = self.spin_idle_threshold.value() if hasattr(self, "spin_idle_threshold") else 60
        idle_sec = get_idle_seconds()
        is_idle = idle_sec >= idle_threshold

        # 1. Water Reminder
        if hasattr(self, "chk_water_reminder") and hasattr(self, "lbl_water_next_time"):
            if not self.chk_water_reminder.isChecked():
                self.lbl_water_next_time.setText("Disabled")
                self.lbl_water_next_time.setStyleSheet("color: #94a3b8; font-style: italic;")
            else:
                interval_min = self.spin_water_interval.value()
                target_sec = interval_min * 60
                active_sec = getattr(wellness_engine, "_water_active_seconds", 0.0)
                rem_sec = max(0.0, target_sec - active_sec)
                next_dt = now + datetime.timedelta(seconds=rem_sec)

                time_str = next_dt.strftime("%I:%M %p")
                rem_m = int(rem_sec // 60)
                rem_s = int(rem_sec % 60)

                if rem_sec <= 0:
                    countdown_str = "Due now"
                elif rem_m > 0:
                    countdown_str = f"in {rem_m}m {rem_s}s"
                else:
                    countdown_str = f"in {rem_s}s"

                status_note = " [Paused - Idle]" if is_idle else ""
                self.lbl_water_next_time.setText(f"{time_str} ({countdown_str}{status_note})")
                self.lbl_water_next_time.setStyleSheet("font-weight: 600; color: #0284c7;")

        # 2. Sedentary Reminder
        if hasattr(self, "chk_sedentary_reminder") and hasattr(self, "lbl_sedentary_next_time"):
            if not self.chk_sedentary_reminder.isChecked():
                self.lbl_sedentary_next_time.setText("Disabled")
                self.lbl_sedentary_next_time.setStyleSheet("color: #94a3b8; font-style: italic;")
            else:
                interval_min = self.spin_sedentary_interval.value()
                target_sec = interval_min * 60
                active_sec = getattr(wellness_engine, "_sedentary_active_seconds", 0.0)
                rem_sec = max(0.0, target_sec - active_sec)
                next_dt = now + datetime.timedelta(seconds=rem_sec)

                time_str = next_dt.strftime("%I:%M %p")
                rem_m = int(rem_sec // 60)
                rem_s = int(rem_sec % 60)

                if rem_sec <= 0:
                    countdown_str = "Due now"
                elif rem_m > 0:
                    countdown_str = f"in {rem_m}m {rem_s}s"
                else:
                    countdown_str = f"in {rem_s}s"

                status_note = " [Paused - Idle]" if is_idle else ""
                self.lbl_sedentary_next_time.setText(f"{time_str} ({countdown_str}{status_note})")
                self.lbl_sedentary_next_time.setStyleSheet("font-weight: 600; color: #0284c7;")

