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
        client = GeminiClient()
        if not client.is_configured:
            self.response_ready.emit(
                "⚠️ **Gemini API Key is not set.**\n\n"
                "Please configure your `GEMINI_API_KEY` in the **Settings** view "
                "or set it as a Windows environment variable to enable AI capabilities."
            )
            return

        context_str = ""
        if self.include_rag:
            try:
                # 1. Embed query
                q_vec = client.get_embedding(self.prompt)
                if q_vec is not None:
                    # 2. Search top documents in vector database
                    if not vector_search_engine._is_loaded:
                        vector_search_engine.load_index()

                    matches = vector_search_engine.search(q_vec, top_k=3)
                    if matches:
                        context_parts = []
                        for m in matches:
                            context_parts.append(
                                f"Document: {m['file_name']} (Relevance: {m['score']:.2f})\n"
                                f"Excerpt: {m.get('text_pointer', '')[:300]}"
                            )
                        context_str = "\n\n".join(context_parts)
            except Exception as e:
                logger.error(f"Error during RAG vector retrieval: {e}")

        answer = client.generate_chat_response(
            prompt=self.prompt,
            context=context_str if context_str else None,
        )
        self.response_ready.emit(answer)


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
