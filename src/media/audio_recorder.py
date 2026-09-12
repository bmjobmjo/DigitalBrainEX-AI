"""
Audio Recording and Listening Module for DigitalBrainEX AI.
Captures microphone and loopback audio using sounddevice and numpy.
"""
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import numpy as np
import sounddevice as sd
from scipy.io import wavfile
from PyQt6.QtCore import QObject, pyqtSignal

from src.config import RECORDINGS_DIR, AUDIO_SAMPLE_RATE, AUDIO_CHANNELS
from src.core.logger import logger


class AudioRecorder(QObject):
    level_updated = pyqtSignal(float)      # RMS level (0.0 to 1.0)
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal(str)     # (saved_wav_filepath)
    error_occurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_recording = False
        self._is_paused = False
        self._stream = None
        self._audio_frames: List[np.ndarray] = []
        self._lock = threading.Lock()
        self._sample_rate = AUDIO_SAMPLE_RATE
        self._channels = AUDIO_CHANNELS

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def start_recording(self, device_index: Optional[int] = None, sample_rate: int = AUDIO_SAMPLE_RATE):
        """Starts recording audio from microphone in background thread."""
        if self._is_recording:
            return

        self._sample_rate = sample_rate
        self._audio_frames.clear()
        self._is_recording = True
        self._is_paused = False

        def audio_callback(indata, frames, time_info, status):
            if status:
                logger.warning(f"Audio stream status: {status}")
            if not self._is_recording or self._is_paused:
                return

            with self._lock:
                self._audio_frames.append(indata.copy())

            # Compute RMS amplitude for live VU meter
            rms = np.sqrt(np.mean(indata**2))
            # Normalize to ~0.0 - 1.0 range
            normalized = min(1.0, float(rms * 10))
            self.level_updated.emit(normalized)

        try:
            self._stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype="int16",
                device=device_index,
                callback=audio_callback,
            )
            self._stream.start()
            self.recording_started.emit()
            logger.info("Audio recording started.")
        except Exception as e:
            self._is_recording = False
            logger.error(f"Failed to start audio stream: {e}")
            self.error_occurred.emit(str(e))

    def stop_recording(self, filename_prefix: str = "MeetingAudio") -> Optional[str]:
        """Stops the audio recording and saves to a WAV file."""
        if not self._is_recording:
            return None

        self._is_recording = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.error(f"Error closing audio stream: {e}")
            self._stream = None

        with self._lock:
            if not self._audio_frames:
                logger.warning("No audio frames recorded.")
                return None
            full_audio = np.concatenate(self._audio_frames, axis=0)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_{timestamp}.wav"
        filepath = str(RECORDINGS_DIR / filename)

        try:
            wavfile.write(filepath, self._sample_rate, full_audio)
            logger.info(f"Audio recorded and saved to: {filepath}")
            self.recording_stopped.emit(filepath)
            return filepath
        except Exception as e:
            logger.error(f"Failed to write audio file: {e}")
            self.error_occurred.emit(str(e))
            return None

    def pause_recording(self):
        self._is_paused = True

    def resume_recording(self):
        self._is_paused = False
