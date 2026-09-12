"""
Unit tests for AudioRecorder and AudioTranscriber.
"""
import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication
from src.media.audio_recorder import AudioRecorder
from src.media.audio_transcriber import AudioTranscriber

app = QApplication.instance() or QApplication(["test_audio"])


class TestAudio(unittest.TestCase):

    def test_audio_recorder_init(self):
        recorder = AudioRecorder()
        self.assertFalse(recorder.is_recording)
        print("AudioRecorder initialized successfully!")

    def test_transcriber_offline_fallback(self):
        # When called on a dummy or non-existent file or test wav
        msg = AudioTranscriber._transcribe_offline("dummy_test.wav")
        self.assertIn("Offline Mode", msg)
        print("AudioTranscriber offline fallback verified!")


if __name__ == "__main__":
    unittest.main()
