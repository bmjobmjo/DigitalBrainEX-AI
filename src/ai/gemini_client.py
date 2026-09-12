"""
Google Gemini AI Client for DigitalBrainEX AI.
Handles generation, embeddings, and document synthesis.
"""
import os
from typing import Optional, List
import numpy as np
from src.core.logger import logger

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class GeminiClient:
    """Wrapper for Google GenAI SDK (Gemini 2.0/1.5 & text-embedding-004)."""

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self._client = None
        if self._api_key and GEMINI_AVAILABLE:
            try:
                self._client = genai.Client(api_key=self._api_key)
            except Exception as e:
                logger.error(f"Error creating Gemini client: {e}")

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Generates a 768-dimensional vector embedding for text using text-embedding-004.
        Returns float32 numpy array or None on error.
        """
        if not self._client:
            return None
        try:
            res = self._client.models.embed_content(
                model="text-embedding-004",
                contents=text,
            )
            if res.embeddings and len(res.embeddings) > 0:
                values = res.embeddings[0].values
                return np.array(values, dtype=np.float32)
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
        return None

    def generate_chat_response(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        context: Optional[str] = None,
        model: str = "gemini-2.0-flash",
    ) -> str:
        """
        Generates a conversational AI response using Gemini.
        Appends RAG context if supplied.
        """
        if not self._client:
            return (
                "⚠️ **Gemini API Key is not configured.**\n\n"
                "Please configure your `GEMINI_API_KEY` in the **Settings** view "
                "or set it as a Windows environment variable."
            )

        full_prompt = prompt
        if context:
            full_prompt = (
                f"Reference context from user's diary and documents:\n"
                f"---\n{context}\n---\n\n"
                f"User question: {prompt}"
            )

        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction or (
                    "You are DigitalBrainEX AI, an intelligent desktop personal assistant and task companion. "
                    "Provide clear, well-structured, helpful answers referencing the user's diary, tasks, and documents."
                ),
                temperature=0.7,
            )
            response = self._client.models.generate_content(
                model=model,
                contents=full_prompt,
                config=config,
            )
            return response.text or ""
        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            return f"❌ **Error communicating with Gemini:** {e}"
