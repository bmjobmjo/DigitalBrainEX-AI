"""
Ask Me AI Conversational Assistant View for DigitalBrainEX AI.
Powered by OpenRouter and Local Document Embedding RAG System.
Answers questions about stored documents with citations, or prompts user to configure OpenRouter.
"""
import re
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QCheckBox,
    QFrame,
    QApplication,
)
from PyQt6.QtCore import Qt, pyqtSignal
from src.ai.openrouter_client import OpenRouterClient
from src.utils.config_manager import get_openrouter_settings
from src.core.logger import logger


class AskMeView(QWidget):
    send_message_requested = pyqtSignal(str, bool)  # (prompt, include_docs)
    open_settings_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ViewContentWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._init_ui()
        self.refresh_configuration_state()

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

        self.lbl_model_badge = QLabel("Model: OpenRouter")
        self.lbl_model_badge.setStyleSheet(
            "background-color: #eff6ff; color: #1d4ed8; font-weight: bold; padding: 4px 8px; border-radius: 6px; border: 1px solid #bfdbfe;"
        )
        header_layout.addWidget(self.lbl_model_badge)

        self.chk_rag = QCheckBox("Query My Documents & Notes (RAG)")
        self.chk_rag.setChecked(True)
        self.chk_rag.setToolTip("Search across indexed document chunks and synthesize answers with citations")
        header_layout.addWidget(self.chk_rag)

        self.btn_clear = QPushButton("Clear Chat")
        self.btn_clear.clicked.connect(self._clear_chat)
        header_layout.addWidget(self.btn_clear)

        main_layout.addLayout(header_layout)

        # Warning / Configuration Banner (shown when OpenRouter is inactive)
        self.banner_frame = QFrame()
        self.banner_frame.setStyleSheet(
            "background-color: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 10px;"
        )
        banner_layout = QHBoxLayout(self.banner_frame)
        banner_layout.setContentsMargins(8, 6, 8, 6)

        self.lbl_banner_msg = QLabel(
            "⚠️ <b>OpenRouter Access Required:</b> AskMe document assistant is inactive because OpenRouter is not enabled or configured."
        )
        self.lbl_banner_msg.setStyleSheet("color: #991b1b; font-size: 13px;")
        banner_layout.addWidget(self.lbl_banner_msg)

        banner_layout.addStretch()

        self.btn_open_settings = QPushButton("Configure in Settings")
        self.btn_open_settings.setStyleSheet(
            "background-color: #dc2626; color: white; font-weight: bold; border-radius: 6px; padding: 6px 12px;"
        )
        self.btn_open_settings.clicked.connect(self.open_settings_requested.emit)
        banner_layout.addWidget(self.btn_open_settings)

        main_layout.addWidget(self.banner_frame)

        # Chat Conversation Display Area
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet(
            "padding: 10px; font-size: 13px; line-height: 1.4; background-color: #ffffff; border: 1px solid #7f9db9; border-radius: 6px;"
        )
        main_layout.addWidget(self.chat_display)

        # Welcome message
        self._append_ai_message(
            "Hello! I am your **DigitalBrainEX AskMe Companion** powered by **OpenRouter** and **Local Document RAG**.\n\n"
            "You can ask natural-language questions about any of your stored PDFs, Word documents, notes, and meeting minutes.\n"
            "I will search your document chunks locally and synthesize an answer citing exact documents and pages.\n\n"
            "Ask me anything below!"
        )

        # Input Prompt Bar
        input_layout = QHBoxLayout()
        self.edit_prompt = QLineEdit()
        self.edit_prompt.setPlaceholderText("Ask a question about your documents (e.g. 'What are the key terms in the contract?')...")
        self.edit_prompt.setMinimumHeight(40)
        self.edit_prompt.returnPressed.connect(self._on_send_clicked)
        input_layout.addWidget(self.edit_prompt)

        self.btn_send = QPushButton("Send Prompt 🚀")
        self.btn_send.setObjectName("PrimaryButton")
        self.btn_send.setMinimumHeight(40)
        self.btn_send.clicked.connect(self._on_send_clicked)
        input_layout.addWidget(self.btn_send)

        main_layout.addLayout(input_layout)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_configuration_state()

    def refresh_configuration_state(self):
        """Refreshes UI state based on OpenRouter configuration."""
        client = OpenRouterClient()
        settings = get_openrouter_settings()
        configured = client.is_configured

        if configured:
            self.banner_frame.hide()
            self.edit_prompt.setEnabled(True)
            self.btn_send.setEnabled(True)
            self.edit_prompt.setPlaceholderText(
                "Ask a question about your documents (e.g. 'What are the key deliverables in the project plan?')..."
            )
            model_name = settings.get("openrouter_model", "OpenRouter")
            self.lbl_model_badge.setText(f"OpenRouter: {model_name}")
            self.lbl_model_badge.setStyleSheet(
                "background-color: #eff6ff; color: #1d4ed8; font-weight: bold; padding: 4px 8px; border-radius: 6px; border: 1px solid #bfdbfe;"
            )
        else:
            self.banner_frame.show()
            self.edit_prompt.setEnabled(False)
            self.btn_send.setEnabled(False)
            self.edit_prompt.setPlaceholderText("OpenRouter configuration required. Click 'Configure in Settings' above to activate AskMe.")
            self.lbl_model_badge.setText("OpenRouter: Disabled")
            self.lbl_model_badge.setStyleSheet(
                "background-color: #fef2f2; color: #dc2626; font-weight: bold; padding: 4px 8px; border-radius: 6px; border: 1px solid #fecaca;"
            )

    def _on_send_clicked(self):
        text = self.edit_prompt.text().strip()
        if not text:
            return

        client = OpenRouterClient()
        if not client.is_configured:
            self.refresh_configuration_state()
            return

        self._append_user_message(text)
        self.edit_prompt.clear()
        include_rag = self.chk_rag.isChecked()

        self.btn_send.setEnabled(False)
        self.btn_send.setText("Thinking... ⏳")

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

    def _format_citations(self, text: str) -> str:
        """Styles citation tags like [Doc: ..., Page/Section: ...] into distinctive badges."""
        pattern = r"\[Doc:\s*([^,\]]+)(?:,\s*ID:\s*([^,\]]+))?(?:,\s*(?:Page|Section|Location):\s*([^\]]+))?\]"
        
        def replace_badge(match):
            doc = match.group(1).strip()
            loc = match.group(3).strip() if match.group(3) else ""
            badge_text = f"📄 {doc}" + (f" ({loc})" if loc else "")
            return (
                f"<span style='background-color: #e0e7ff; color: #3730a3; padding: 2px 6px; "
                f"border-radius: 4px; font-size: 11px; font-weight: bold; border: 1px solid #c7d2fe;'>"
                f"{badge_text}</span>"
            )

        formatted = re.sub(pattern, replace_badge, text)
        return formatted

    def _append_ai_message(self, text: str):
        styled_text = self._format_citations(text)
        formatted_text = styled_text.replace("\n", "<br>")
        html = (
            f"<div style='margin-bottom: 14px; text-align: left;'>"
            f"<div style='background-color: #f8fafc; color: #0f172a; padding: 12px 16px; "
            f"border-radius: 12px; border: 1px solid #cbd5e1; display: inline-block; max-width: 88%; font-size: 13px;'>"
            f"<span style='color: #2563eb; font-weight: bold;'>🤖 DigitalBrain AskMe:</span><br><br>"
            f"{formatted_text}</div></div>"
        )
        self.chat_display.append(html)

    def receive_ai_response(self, response_text: str):
        self._append_ai_message(response_text)
        self.btn_send.setEnabled(True)
        self.btn_send.setText("Send Prompt 🚀")

    def _clear_chat(self):
        self.chat_display.clear()
        self._append_ai_message("Chat history cleared. How can I assist you with your documents?")
