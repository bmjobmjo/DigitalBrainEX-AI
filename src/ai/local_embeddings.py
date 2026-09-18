"""
Local Embedding Engine for DigitalBrainEX AI.
Runs embedding models locally on the user's computer via sentence-transformers
without external network API calls. Handles vector serialization and similarity calculations.
"""
from typing import List, Optional
import threading
import numpy as np

# Ensure PyTorch DLL directories are properly registered in Windows process space
try:
    import torch
except Exception as _torch_init_err:
    pass

from src.utils.config_manager import get_embedding_settings
from src.core.logger import logger


class LocalEmbeddingManager:
    """Singleton manager for local text embedding generation and vector utilities."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(LocalEmbeddingManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, model_name: Optional[str] = None):
        if self._initialized:
            if model_name and model_name != self._model_name:
                self._model_name = model_name
                self._model = None  # Reload on demand
            return

        settings = get_embedding_settings()
        configured = model_name or settings.get("embedding_model_name", "sentence-transformers/all-MiniLM-L6-v2")
        # If set to Qwen, normalize to standard all-MiniLM-L6-v2
        if "qwen" in configured.lower():
            configured = "sentence-transformers/all-MiniLM-L6-v2"
        self._model_name = configured
        self._model_version = settings.get("embedding_model_version", "1.0")
        self._model = None
        self._dimension = 384
        self._initialized = True

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def model_version(self) -> str:
        return self._model_version

    def _ensure_model(self):
        """Lazy loads or automatically downloads the sentence-transformers model."""
        if self._model is not None:
            return

        with self._lock:
            if self._model is not None:
                return

            try:
                # Ensure torch is imported in current thread context
                import torch
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading local embedding model: {self._model_name}...")
                self._model = SentenceTransformer(self._model_name)
                test_emb = self._model.encode("test", normalize_embeddings=True)
                self._dimension = len(test_emb)
                logger.info(f"Local embedding model {self._model_name} loaded successfully (dimension={self._dimension}).")
            except Exception as e:
                logger.warning(f"Could not load primary model '{self._model_name}': {e}. Falling back to 'sentence-transformers/all-MiniLM-L6-v2'...")
                try:
                    import torch
                    from sentence_transformers import SentenceTransformer
                    fallback_name = "sentence-transformers/all-MiniLM-L6-v2"
                    self._model = SentenceTransformer(fallback_name)
                    self._model_name = fallback_name
                    test_emb = self._model.encode("test", normalize_embeddings=True)
                    self._dimension = len(test_emb)
                    logger.info(f"Fallback model {fallback_name} loaded successfully.")
                except Exception as ex2:
                    logger.error(f"Failed to load fallback embedding model: {ex2}")
                    raise RuntimeError(f"Could not initialize any local embedding model: {e} / {ex2}") from ex2

    def embed_text(self, text: str) -> np.ndarray:
        """Computes a normalized 1D float32 embedding vector for the given text string."""
        if not text or not text.strip():
            return np.zeros(self._dimension, dtype=np.float32)

        self._ensure_model()
        emb = self._model.encode(text.strip(), normalize_embeddings=True)
        vec = np.asarray(emb, dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Computes normalized float32 embeddings for a batch of text strings."""
        if not texts:
            return np.empty((0, self._dimension), dtype=np.float32)

        self._ensure_model()
        clean_texts = [t.strip() if t.strip() else "empty" for t in texts]
        embs = self._model.encode(clean_texts, normalize_embeddings=True, show_progress_bar=False)
        vecs = np.asarray(embs, dtype=np.float32)
        # Re-normalize just in case
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vecs / norms

    @staticmethod
    def vector_to_blob(vec: np.ndarray) -> bytes:
        """Serializes a numpy array to compact raw bytes for SQLite BLOB storage."""
        return np.asarray(vec, dtype=np.float32).tobytes()

    @staticmethod
    def blob_to_vector(blob: bytes) -> np.ndarray:
        """Deserializes raw bytes back into a numpy 1D float32 array."""
        if not blob:
            return np.empty(0, dtype=np.float32)
        return np.frombuffer(blob, dtype=np.float32)

    @staticmethod
    def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Computes cosine similarity between two normalized vectors."""
        if vec1.size == 0 or vec2.size == 0 or vec1.shape != vec2.shape:
            return 0.0
        # If already unit length, dot product is cosine similarity
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(vec1, vec2) / (norm1 * norm2))


def get_local_embedding_manager() -> LocalEmbeddingManager:
    """Returns the singleton instance of LocalEmbeddingManager."""
    return LocalEmbeddingManager()
