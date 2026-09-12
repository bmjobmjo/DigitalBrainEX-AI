"""
Unit tests for AI and Vector Search Engine.
"""
import unittest
import os
import sys
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ai.vector_search import VectorSearchEngine
from src.ai.gemini_client import GeminiClient


class TestAI(unittest.TestCase):

    def test_vector_search_engine(self):
        engine = VectorSearchEngine()
        engine.load_index()
        self.assertTrue(engine._is_loaded)
        self.assertGreater(len(engine._metadata), 0)
        print(f"Loaded {len(engine._metadata)} vectors into memory.")

        # Create dummy 768-dim query vector
        query = np.random.randn(768).astype(np.float32)
        matches = engine.search(query, top_k=3)
        self.assertEqual(len(matches), 3)
        print("Top 3 matches for test vector:")
        for m in matches:
            print(f"  - File: {m['file_name']}, Score: {m['score']}")

    def test_gemini_client_unconfigured_graceful(self):
        # When unconfigured, it returns a polite informative error message without raising an exception
        client = GeminiClient(api_key=None)
        res = client.generate_chat_response("Hello test")
        self.assertIn("Gemini API Key", res)
        print("GeminiClient unconfigured state verified!")


if __name__ == "__main__":
    unittest.main()
