"""
Ask Me AI Conversational Assistant View for DigitalBrainEX AI.
Provides direct Gemini LLM chat, diary retrieval, and semantic document Q&A.
"""
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QComboBox,
    QCheckBox,
    QScrollArea,
    QFrame,
    QApplication,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from src.core.logger import logger


class AskMeView(QWidget):
    send_message_requested = pyqtSignal(str, bool)  # (prompt, include_docs)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ViewContentWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(8)

        # Header bar
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        title_label = QLabel("Ask Me")
        title_label.setObjectName("ViewTitleLabel")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        header_layout.addWidget(QLabel("Model:"))
        self.combo_model = QComboBox()
        self.combo_model.addItems(["Gemini 2.0 Flash", "Gemini 1.5 Pro", "Local Whisper STT"])
        header_layout.addWidget(self.combo_model)

        self.chk_rag = QCheckBox("Query My Documents & Notes (RAG)")
        self.chk_rag.setChecked(True)
        header_layout.addWidget(self.chk_rag)

        self.btn_clear = QPushButton("Clear Chat")
        self.btn_clear.clicked.connect(self._clear_chat)
        header_layout.addWidget(self.btn_clear)

        main_layout.addLayout(header_layout)

        # Chat Conversation Display Area
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet(
            "padding: 10px; font-size: 13px; line-height: 1.4; background-color: #ffffff; border: 1px solid #7f9db9;"
        )
        main_layout.addWidget(self.chat_display)

        # Welcome message
        self._append_ai_message(
            "Hello! I am your **DigitalBrainEX AI Companion**.\n\n"
            "I can assist you with:\n"
            "- Finding notes, meeting minutes, and tasks in your diary\n"
            "- Summarizing project progress and application time tracking\n"
            "- Extracting action items and drafting documentation\n\n"
            "Ask me anything below!"
        )

        # Input Prompt Bar
        input_layout = QHBoxLayout()
        self.edit_prompt = QLineEdit()
        self.edit_prompt.setPlaceholderText("Ask a question or enter a command (e.g. 'What tasks are due this week?')...")
        self.edit_prompt.setMinimumHeight(40)
        self.edit_prompt.returnPressed.connect(self._on_send_clicked)
        input_layout.addWidget(self.edit_prompt)

        self.btn_send = QPushButton("Send Prompt 🚀")
        self.btn_send.setObjectName("PrimaryButton")
        self.btn_send.setMinimumHeight(40)
        self.btn_send.clicked.connect(self._on_send_clicked)
        input_layout.addWidget(self.btn_send)

        main_layout.addLayout(input_layout)

    def _on_send_clicked(self):
        text = self.edit_prompt.text().strip()
        if not text:
            return

        self._append_user_message(text)
        self.edit_prompt.clear()
        include_rag = self.chk_rag.isChecked()

        # Emit signal to controller/agent
        self.send_message_requested.emit(text, include_rag)

    def _append_user_message(self, text: str):
        html = (
            f"<div style='margin-bottom: 12px; text-align: right;'>"
            f"<span style='background-color: #2563eb; color: #ffffff; padding: 8px 14px; "
            f"border-radius: 12px; display: inline-block; max-width: 80%; font-weight: 500; font-size: 13px;'>"
            f"👤 <b>You:</b> {text}</span></div>"
        )
        self.chat_display.append(html)

    def _append_ai_message(self, text: str):
        formatted_text = text.replace("\n", "<br>")
        html = (
            f"<div style='margin-bottom: 14px; text-align: left;'>"
            f"<div style='background-color: #f1f5f9; color: #0f172a; padding: 12px 16px; "
            f"border-radius: 12px; border: 1px solid #cbd5e1; display: inline-block; max-width: 85%; font-size: 13px;'>"
            f"<span style='color: #2563eb; font-weight: bold;'>🤖 DigitalBrain AI:</span><br><br>"
            f"{formatted_text}</div></div>"
        )
        self.chat_display.append(html)

    def receive_ai_response(self, response_text: str):
        self._append_ai_message(response_text)

    def _clear_chat(self):
        self.chat_display.clear()
        self._append_ai_message("Chat history cleared. How can I assist you?")
