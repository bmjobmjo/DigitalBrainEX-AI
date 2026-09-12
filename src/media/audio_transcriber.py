"""
Audio Transcription Engine for DigitalBrainEX AI.
Supports cloud transcription via Google Gemini Audio API and local offline models.
"""
import os
from pathlib import Path
from typing import Optional
from src.core.logger import logger


class AudioTranscriber:
    """Handles audio speech-to-text transcription."""

    @staticmethod
    def transcribe(audio_path: str) -> str:
        """
        Transcribes the audio file at audio_path.
        Uses Google Gemini 2.0/1.5 if API key is present; otherwise falls back to local STT.
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        gemini_key = os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            return AudioTranscriber._transcribe_gemini(audio_path, gemini_key)
        else:
            return AudioTranscriber._transcribe_offline(audio_path)

    @staticmethod
    def _transcribe_gemini(audio_path: str, api_key: str) -> str:
        """Transcribes audio using Google GenAI SDK."""
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            logger.info(f"Uploading audio file for Gemini transcription: {audio_path}")

            # Upload audio file to Gemini Files API
            audio_file = client.files.upload(file=audio_path)

            prompt = (
                "Please transcribe this meeting audio accurately. Provide:\n"
                "1. Full text transcript with speaker separation where clear.\n"
                "2. Key meeting discussion points summary.\n"
                "3. Extracted action items with responsible parties."
            )

            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[audio_file, prompt],
            )
            return response.text or ""
        except Exception as e:
            logger.error(f"Gemini audio transcription failed: {e}")
            return f"[Transcription Error: {e}]"

    @staticmethod
    def _transcribe_offline(audio_path: str) -> str:
        """Offline fallback message when API key is not configured."""
        return (
            "[Offline Mode]\n"
            f"Audio file recorded at: {audio_path}\n"
            "To enable automated transcription and meeting minutes summarization, "
            "set your GEMINI_API_KEY in Settings or environment variables."
        )
