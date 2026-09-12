# DigitalBrainEX AI (Python Edition)

An enterprise-grade personal knowledge base, developer diary, task reminder system, and generative AI companion built with **Python 3.13**, **PyQt6**, **SQLAlchemy 2.0**, and **Google Gemini AI**.

This application is the complete modern re-architecture of the legacy C# DigitalBrainEX system, designed with **100% database compatibility**, **zero data loss**, and enhanced multimedia and generative AI capabilities.

---

## Key Features & Highlights

1. **100% Legacy SQLite Database Compatibility**
   - Connects directly to `database/DevDiary-10-09-2026.db3` (and your live `DevDiary.db3`).
   - Seamlessly queries all 15 tables with over 79k+ activity records, 18k+ vector embeddings, 10.7k+ documents, 1.8k+ tasks, and 8.3k+ clipboard items.
   - **Full Cryptography Compatibility**: Binary-compatible TripleDES (ECB, PKCS7) with MD5 key derivation allows unlocking all 94 existing credentials in the `secrets` table.

2. **Modern PyQt6 Dark Desktop Interface**
   - High-DPI optimized sleek dark theme with modern typography, smooth cards, and responsive states.
   - Global Top Bar with dynamic project selector (`All Projects` or filtered), global search, status badges, and quick actions.
   - Intuitive 12-module Navigation Sidebar.

3. **12 Integrated Functional Modules**
   1. **Projects**: Portfolio management with start dates, status tracking, and details.
   2. **Tasks & Reminders**: Filter by Today's Tasks, Active, Closed, and All. Configurable repeat intervals, due dates, and priorities.
   3. **Documents**: Document cataloging with categories, attachment linking, and direct OS file launching.
   4. **URLs & Web Links**: Browser bookmarks with category grouping and single-click browser launching.
   5. **Code Snippets**: Developer snippet repository with multi-language formatting and quick-copy.
   6. **Meeting Minutes**: Discussion logs, participant notes, and live audio attachment & transcription.
   7. **File Manager & TempPad**: Auto-collected files from watched folders and screenshots with instant preview and conversion to permanent project documents.
   8. **Personal Notes**: Freeform rich notes and developer scratchpad.
   9. **Secrets Vault**: Encrypted credential manager with master key protection and copy-to-clipboard.
   10. **TrackMe Analytics**: Automated application time tracking, productivity summaries, and active window timeline.
   11. **Ask Me (AI Assistant)**: Conversational assistant powered by Google Gemini 2.0/1.5 with in-memory vector search (RAG) over 18k+ embeddings.
   12. **Settings**: Multi-tab configuration for General startup, GenAI keys, Global hotkeys, Watch folders, and Storage paths.

4. **Background System Tray & Notification Blinker**
   - Persistent `QSystemTrayIcon` with context menu (*Open*, *Screenshot*, *Clipboard History*, *Record Audio*, *Exit*).
   - Minimizes to tray on close to maintain background tracking.
   - Non-focus-stealing flashing screen edge notification border (`NotificationBlinker`) for imminent task deadlines.

5. **Interactive Screenshot & Vector Annotation Overlay**
   - Full virtual desktop screen capture across multi-monitor setups.
   - Frameless transparent drawing canvas with 8-point resize handles (`TL`, `TC`, `TR`, `ML`, `MR`, `BL`, `BC`, `BR`).
   - Vector drawing tools: Freehand Pen, Arrow with vector arrowhead, Rectangle, Ellipse, and Text annotations with undo (`Ctrl+Z`).
   - Double-click capture finalization that automatically saves to disk and copies to the Windows clipboard.

6. **Audio Capture, Listening & AI Transcription**
   - Low-latency microphone recording via `sounddevice` with live RMS VU meter levels.
   - WAV audio generation saved in `recordings/`.
   - Transcription and executive summary generation via Gemini Audio API or local fallback.

7. **Native Win32 Background Monitors**
   - **Clipboard History**: Captures copied text and images, stores them in SQLite, and provides searchable quick retrieval (`Ctrl+H`).
   - **Window Tracker**: Logs foreground active application usage with idle detection (`GetLastInputInfo`).
   - **Watch Folder Service**: Monitors download/work directories with `watchdog` to catch new files automatically.

8. **USB & Hardware Extensibility**
   - Direct serial port discovery and peripheral communication support.

---

## Directory Structure

```
DigitalBrainEXAI/
├── database/
│   └── DevDiary-10-09-2026.db3       # Active SQLite database (15 tables)
├── logs/                              # Rotating application log files
├── recordings/                        # Recorded meeting audio files (.wav)
├── screenshots/                       # Captured screenshots and annotations (.png)
├── temp_pad/                          # Auto-collected temporary files
├── requirements.txt                   # Pinned Python package dependencies
├── README.md                          # Project documentation
├── src/
│   ├── app.py                         # Application entry point & service coordinator
│   ├── config.py                      # Configurations, directories, and paths
│   ├── core/                          # Core data & cryptography services
│   │   ├── database.py                # SQLAlchemy engine & session manager
│   │   ├── models.py                  # Exact ORM models for all 15 SQLite tables
│   │   ├── repository.py              # CRUD methods and transactional queries
│   │   ├── crypto.py                  # TripleDES & AES-256 encryption engine
│   │   ├── logger.py                  # Rotating logger configuration
│   │   └── event_bus.py               # Application-wide signal/event broker
│   ├── background/                    # Background services
│   │   ├── tray_manager.py            # Windows System Tray icon & balloon alerts
│   │   ├── clipboard_monitor.py       # Win32 clipboard listener & history recorder
│   │   ├── window_tracker.py          # Active window tracker with idle detection
│   │   ├── folder_watcher.py          # Watchdog file system observer
│   │   ├── task_scheduler.py          # Due deadline and reminder dispatcher
│   │   └── hotkey_manager.py          # System-wide global keyboard shortcuts
│   ├── media/                         # Media, graphics & hardware
│   │   ├── screen_capture.py          # High-performance desktop screen capture
│   │   ├── overlay_canvas.py          # Transparent 8-handle annotation canvas
│   │   ├── toolbar_widget.py          # Floating annotation action toolbar
│   │   ├── audio_recorder.py          # Sounddevice microphone capture engine
│   │   ├── audio_transcriber.py       # Speech-to-text transcription engine
│   │   └── usb_manager.py             # USB & serial port communication
│   ├── ai/                            # Generative AI & Semantic Retrieval
│   │   ├── gemini_client.py           # Google GenAI SDK (Gemini 2.0/1.5)
│   │   ├── vector_search.py           # 768-dim in-memory cosine similarity engine
│   │   └── agents.py                  # AskMeAgent, MeetingSummarizerAgent
│   └── ui/                            # Modern PyQt6 User Interface
│       ├── main_window.py             # Main application shell
│       ├── top_bar.py                 # Top project selector & search bar
│       ├── sidebar.py                 # 12-module navigation sidebar
│       ├── theme.py                   # Modern Dark theme QSS stylesheet
│       ├── components/
│       │   ├── notification_blinker.py# Top-most flashing border alert
│       │   └── clipboard_history_dlg.py# Searchable clipboard history modal
│       └── views/
│           ├── projects_view.py       # Module 1: Projects Portfolio
│           ├── tasks_view.py          # Module 2: Tasks & Reminders
│           ├── documents_view.py      # Module 3: Documents Catalog
│           ├── urls_view.py           # Module 4: URLs & Web Links
│           ├── code_snippets_view.py  # Module 5: Code Snippets
│           ├── minutes_view.py        # Module 6: Meeting Minutes & Audio
│           ├── file_manager_view.py   # Module 7: TempPad & File Manager
│           ├── notes_view.py          # Module 8: Personal Notes
│           ├── secrets_view.py        # Module 9: Secrets Vault
│           ├── trackme_view.py        # Module 10: TrackMe Analytics
│           ├── ask_me_view.py         # Module 11: Ask Me AI Chat
│           └── settings_view.py       # Module 12: Multi-tab Settings
└── tests/
    ├── run_all_tests.py               # Comprehensive test runner
    ├── test_crypto.py                 # TripleDES & AES256 verification
    ├── test_db_models.py              # Production database ORM tests
    ├── test_screen_capture.py         # Capture & overlay tests
    ├── test_audio.py                  # Audio recorder & transcriber tests
    ├── test_background_services.py    # Background monitors tests
    ├── test_ai.py                     # Vector search & Gemini client tests
    └── test_ui_smoke.py               # PyQt6 UI smoke test
```

---

## Installation & Setup

1. **Prerequisites**:
   - Python 3.10+ (tested on Python 3.13)
   - Windows 10 or 11

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run All Verification Tests**:
   ```bash
   python tests/run_all_tests.py
   ```
   *Expected result: 26 passed, 0 errors, 0 failures.*

4. **Launch Application**:
   ```bash
   python src/app.py
   ```

---

## Global Hotkeys

| Shortcut | Action |
| :--- | :--- |
| `Ctrl+P` / `PrintScreen` | Launch transparent screen capture and annotation overlay |
| `Ctrl+H` / `Ctrl+Shift+H` | Open searchable Clipboard History dialog |
| `Escape` | Close screenshot overlay without saving |
| `Enter` / Double Click | Finalize and copy screenshot selection |
| `Ctrl+Z` | Undo last drawn annotation stroke |
