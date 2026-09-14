"""
AI Agents and Asynchronous Query Workers for DigitalBrainEX AI.
Provides AskMeAgent, MeetingSummarizerAgent, and TaskAssistantAgent.
"""
from typing import Optional, List
from PyQt6.QtCore import QObject, QThread, pyqtSignal

from src.ai.gemini_client import GeminiClient
from src.ai.vector_search import vector_search_engine
from src.core.logger import logger


class AskMeWorker(QThread):
    response_ready = pyqtSignal(str)

    def __init__(self, prompt: str, include_rag: bool = True, parent=None):
        super().__init__(parent)
        self.prompt = prompt
        self.include_rag = include_rag

    def run(self):
        from src.ai.openrouter_client import OpenRouterClient
        from src.ai.rag_engine import RAGEngine

        openrouter = OpenRouterClient()
        if not openrouter.is_configured:
            self.response_ready.emit(
                "⚠️ **OpenRouter Access is not configured or disabled.**\n\n"
                "The AskMe assistant requires OpenRouter to be enabled and configured:\n\n"
                "1. Go to **Settings** -> **GenAI & LLM** tab.\n"
                "2. Check **Enable OpenRouter for AskMe AI Assistant**.\n"
                "3. Enter your **OpenRouter API Key** and choose your preferred model.\n"
                "4. Click **Save All Settings** to activate AskMe."
            )
            return

        try:
            if self.include_rag:
                rag = RAGEngine(openrouter_client=openrouter)
                answer = rag.query(self.prompt)
            else:
                messages = [
                    {"role": "system", "content": "You are DigitalBrainEX AI assistant. Provide helpful, accurate, and structured answers."},
                    {"role": "user", "content": self.prompt}
                ]
                answer = openrouter.generate_chat_completion(messages)
            self.response_ready.emit(answer)
        except Exception as e:
            logger.error(f"Error during AskMe processing: {e}", exc_info=True)
            self.response_ready.emit(f"❌ **Error generating response:**\n\n{str(e)}")


class AskMeAgent(QObject):
    """Controller agent managing asynchronous conversational AI interaction."""
    response_received = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_worker: Optional[AskMeWorker] = None

    def query(self, prompt: str, include_rag: bool = True):
        self._current_worker = AskMeWorker(prompt, include_rag, self)
        self._current_worker.response_ready.connect(self._on_worker_finished)
        self._current_worker.start()

    def _on_worker_finished(self, response: str):
        self.response_received.emit(response)


class MeetingSummarizerAgent:
    """Agent for structuring and synthesizing meeting discussions."""

    @staticmethod
    def summarize(transcript: str) -> str:
        client = GeminiClient()
        if not client.is_configured:
            return transcript

        prompt = (
            "Analyze and synthesize the following meeting discussion transcript. Produce:\n"
            "1. **Executive Summary** (2-3 sentences)\n"
            "2. **Key Decisions Made**\n"
            "3. **Action Items Table** (Task, Assignee, Priority)\n\n"
            f"Transcript:\n{transcript}"
        )
        return client.generate_chat_response(prompt)
