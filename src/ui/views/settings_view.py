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
)
from PyQt6.QtCore import Qt
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
        self._init_ui()
        self.load_settings()

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

        self.tabs.addTab(self._create_general_tab(), "General & Startup")
        self.tabs.addTab(self._create_wellness_tab(), "Wellness & Health")
        self.tabs.addTab(self._create_genai_tab(), "GenAI & LLM")
        self.tabs.addTab(self._create_hotkeys_tab(), "Hotkeys & Shortcuts")
        self.tabs.addTab(self._create_watchfolders_tab(), "Watch Folders")
        self.tabs.addTab(self._create_paths_tab(), "Paths & Storage")
        self.tabs.addTab(self._create_about_tab(), "About & Diagnostics")

        main_layout.addWidget(self.tabs)

        # Bottom save button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_save_all = QPushButton("Save All Settings")
        self.btn_save_all.setIcon(IconHelper.get_icon("save", 16))
        self.btn_save_all.clicked.connect(self._save_all_settings)
        btn_layout.addWidget(self.btn_save_all)

        main_layout.addLayout(btn_layout)

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
        layout.setSpacing(14)

        # 1. Drink Water Reminder
        grp_water = QGroupBox("Drink Water (Hydration) Reminder")
        water_layout = QVBoxLayout(grp_water)
        self.chk_water_reminder = QCheckBox("Enable Drink Water Reminder")
        self.chk_water_reminder.setChecked(True)
        water_layout.addWidget(self.chk_water_reminder)

        w_form = QFormLayout()
        self.spin_water_interval = QSpinBox()
        self.spin_water_interval.setRange(1, 240)
        self.spin_water_interval.setValue(45)
        self.spin_water_interval.setSuffix(" minutes")
        self.spin_water_interval.setFixedWidth(140)
        w_form.addRow("Reminder Interval:", self.spin_water_interval)
        water_layout.addLayout(w_form)
        layout.addWidget(grp_water)

        # 2. Sedentary / Stand & Move Reminder
        grp_sed = QGroupBox("Sedentary / Stand & Move Reminder")
        sed_layout = QVBoxLayout(grp_sed)
        self.chk_sedentary_reminder = QCheckBox("Enable Sedentary / Stand & Move Reminder")
        self.chk_sedentary_reminder.setChecked(True)
        sed_layout.addWidget(self.chk_sedentary_reminder)

        s_form = QFormLayout()
        self.spin_sedentary_interval = QSpinBox()
        self.spin_sedentary_interval.setRange(1, 240)
        self.spin_sedentary_interval.setValue(60)
        self.spin_sedentary_interval.setSuffix(" minutes")
        self.spin_sedentary_interval.setFixedWidth(140)
        s_form.addRow("Reminder Interval:", self.spin_sedentary_interval)
        sed_layout.addLayout(s_form)
        layout.addWidget(grp_sed)

        # 3. Smart Inactivity & Lock Detection
        grp_activity = QGroupBox("Active Input & Inactivity Detection")
        act_layout = QVBoxLayout(grp_activity)

        lbl_desc = QLabel(
            "Timers ONLY accumulate when you are actively using keyboard or mouse and logged in.\n"
            "If mouse/keyboard becomes inactive or the screen is locked/logged out, the timer automatically stops and resets."
        )
        lbl_desc.setStyleSheet("color: #475569; font-size: 11px;")
        lbl_desc.setWordWrap(True)
        act_layout.addWidget(lbl_desc)

        a_form = QFormLayout()
        self.spin_idle_threshold = QSpinBox()
        self.spin_idle_threshold.setRange(10, 600)
        self.spin_idle_threshold.setValue(60)
        self.spin_idle_threshold.setSuffix(" seconds")
        self.spin_idle_threshold.setFixedWidth(140)
        a_form.addRow("Inactivity Reset Threshold:", self.spin_idle_threshold)
        act_layout.addLayout(a_form)
        layout.addWidget(grp_activity)

        # 4. Preview / Test Buttons
        grp_test = QGroupBox("Preview & Test Alerts")
        test_layout = QHBoxLayout(grp_test)

        btn_test_water = QPushButton("Preview Water Alert")
        btn_test_water.setIcon(IconHelper.get_icon("water_drop", 16))
        btn_test_water.clicked.connect(self._test_water_alert)
        test_layout.addWidget(btn_test_water)

        btn_test_sed = QPushButton("Preview Sedentary Alert")
        btn_test_sed.setIcon(IconHelper.get_icon("sedentary_walk", 16))
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
        or_layout = QVBoxLayout(grp_openrouter)
        or_layout.setSpacing(8)

        self.chk_openrouter_enable = QCheckBox("Enable OpenRouter for AskMe AI Assistant & Document Q&A")
        self.chk_openrouter_enable.setStyleSheet("font-weight: bold; color: #1e3a8a;")
        or_layout.addWidget(self.chk_openrouter_enable)

        or_form = QFormLayout()
        or_form.setSpacing(8)

        # API Key row with show/hide toggle
        key_layout = QHBoxLayout()
        self.edit_openrouter_key = QLineEdit()
        self.edit_openrouter_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_openrouter_key.setPlaceholderText("sk-or-v1-...")
        key_layout.addWidget(self.edit_openrouter_key)

        self.btn_toggle_key = QPushButton("Show")
        self.btn_toggle_key.setFixedWidth(60)
        self.btn_toggle_key.clicked.connect(self._toggle_key_visibility)
        key_layout.addWidget(self.btn_toggle_key)
        or_form.addRow("OpenRouter API Key:", key_layout)

        # Model Selector
        self.combo_openrouter_model = QComboBox()
        self.combo_openrouter_model.setEditable(True)
        self.combo_openrouter_model.addItems([
            "anthropic/claude-3.5-sonnet",
            "openai/gpt-4o-mini",
            "openai/gpt-4o",
            "google/gemini-2.0-flash-001",
            "meta-llama/llama-3.3-70b-instruct",
            "deepseek/deepseek-chat",
            "qwen/qwen-2.5-72b-instruct",
        ])
        or_form.addRow("Preferred Model:", self.combo_openrouter_model)
        or_layout.addLayout(or_form)

        test_row = QHBoxLayout()
        self.btn_test_openrouter = QPushButton("Test OpenRouter Connection")
        self.btn_test_openrouter.setIcon(IconHelper.get_icon("refresh", 16))
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
        embed_layout = QVBoxLayout(grp_embed)
        embed_layout.setSpacing(8)

        lbl_embed_info = QLabel(
            "Embeddings are computed locally on your device without sending document contents to external APIs."
        )
        lbl_embed_info.setStyleSheet("color: #64748b; font-size: 12px;")
        embed_layout.addWidget(lbl_embed_info)

        emb_form = QFormLayout()
        self.edit_embedding_model = QLineEdit()
        self.edit_embedding_model.setText("Qwen/Qwen3-Embedding-0.6B")
        emb_form.addRow("Local Model Name:", self.edit_embedding_model)

        self.edit_embedding_version = QLineEdit()
        self.edit_embedding_version.setText("1.0")
        emb_form.addRow("Model Version:", self.edit_embedding_version)
        embed_layout.addLayout(emb_form)

        # Process pending button and status
        proc_row = QHBoxLayout()
        self.btn_process_embeddings = QPushButton("Process Pending Embeddings Now")
        self.btn_process_embeddings.setIcon(IconHelper.get_icon("ai", 16))
        self.btn_process_embeddings.clicked.connect(self._process_pending_embeddings)
        proc_row.addWidget(self.btn_process_embeddings)

        self.lbl_pending_status = QLabel("")
        proc_row.addWidget(self.lbl_pending_status)
        proc_row.addStretch()
        embed_layout.addLayout(proc_row)

        layout.addWidget(grp_embed)

        # 3. Google Gemini Configuration (Optional Fallback)
        grp_gemini = QGroupBox("Google Gemini Configuration (Optional)")
        gemini_layout = QVBoxLayout(grp_gemini)

        gemini_layout.addWidget(QLabel("Gemini API Key (or set GEMINI_API_KEY environment variable):"))
        self.edit_gemini_key = QLineEdit()
        self.edit_gemini_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_gemini_key.setText(os.environ.get("GEMINI_API_KEY", ""))
        gemini_layout.addWidget(self.edit_gemini_key)

        gemini_layout.addWidget(QLabel("Default LLM Model:"))
        self.combo_llm_model = QComboBox()
        self.combo_llm_model.addItems(["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"])
        gemini_layout.addWidget(self.combo_llm_model)

        layout.addWidget(grp_gemini)

        # 4. Speech & Audio
        grp_audio = QGroupBox("Speech & Transcription")
        audio_layout = QVBoxLayout(grp_audio)

        audio_layout.addWidget(QLabel("Speech-to-Text Engine:"))
        self.combo_stt_engine = QComboBox()
        self.combo_stt_engine.addItems(["Local Whisper (Faster-Whisper)", "Gemini Cloud Audio API", "Vosk (Offline)"])
        audio_layout.addWidget(self.combo_stt_engine)

        layout.addWidget(grp_audio)
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
        self.btn_process_embeddings.setEnabled(False)
        self.lbl_pending_status.setStyleSheet("color: #2563eb;")
        self.lbl_pending_status.setText("Processing document embeddings in background...")

        from src.background.embedding_worker import EmbeddingWorker
        self._worker = EmbeddingWorker(parent=self)

        def on_finished(doc_id, name, success, err):
            if success:
                self.lbl_pending_status.setText(f"Indexed: {name}")
            else:
                self.lbl_pending_status.setText(f"Failed: {name}")

        def on_all(total, succeeded):
            self.btn_process_embeddings.setEnabled(True)
            self.lbl_pending_status.setStyleSheet("color: #16a34a; font-weight: bold;")
            self.lbl_pending_status.setText(f"Completed! {succeeded}/{total} documents indexed.")
            self._update_pending_count()

        self._worker.document_finished.connect(on_finished)
        self._worker.all_completed.connect(on_all)
        self._worker.start()

    def _update_pending_count(self):
        try:
            pending = DataRepository.get_documents_by_embedding_status("PENDING")
            failed = DataRepository.get_documents_by_embedding_status("FAILED")
            p_len, f_len = len(pending), len(failed)
            self.lbl_pending_status.setStyleSheet("color: #475569;")
            self.lbl_pending_status.setText(f"Queue: {p_len} pending, {f_len} failed")
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

        QMessageBox.information(self, "Settings Saved", "Application settings updated successfully!")
