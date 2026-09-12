"""
Vector Search Engine for DigitalBrainEX AI.
Loads 768-dimensional float32 embeddings from SQLite and performs ultra-fast cosine similarity retrieval.
"""
from typing import List, Dict, Any, Optional
import numpy as np
from src.core.database import get_db_session
from src.core.models import Embedding
from src.core.logger import logger


class VectorSearchEngine:
    """In-memory cosine similarity search over document embeddings."""

    def __init__(self):
        self._matrix: Optional[np.ndarray] = None
        self._metadata: List[Dict[str, Any]] = []
        self._is_loaded = False

    def load_index(self, project_id: Optional[str] = None):
        """Loads vector embeddings from SQLite into contiguous numpy matrix."""
        logger.info("Loading vector embeddings into memory...")
        records = []
        vectors = []

        with get_db_session() as session:
            query = session.query(
                Embedding.FileName,
                Embedding.FileFullPath,
                Embedding.ProjectName,
                Embedding.TextPointer,
                Embedding.DocumentID,
                Embedding.Embedding,
            ).filter(Embedding.Embedding.isnot(None))

            if project_id and project_id != "0":
                query = query.filter(Embedding.ProjectID == str(project_id))

            # Fetch batch
            rows = query.all()
            for r in rows:
                raw_blob = r.Embedding
                if raw_blob and len(raw_blob) == 3072:  # 768 * 4 bytes
                    arr = np.frombuffer(raw_blob, dtype=np.float32)
                    vectors.append(arr)
                    records.append({
                        "file_name": r.FileName,
                        "file_path": r.FileFullPath,
                        "project_name": r.ProjectName,
                        "text_pointer": r.TextPointer,
                        "document_id": r.DocumentID,
                    })

        if vectors:
            raw_matrix = np.array(vectors, dtype=np.float32)
            # Normalize matrix for instant cosine dot-product
            norms = np.linalg.norm(raw_matrix, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            self._matrix = raw_matrix / norms
            self._metadata = records
            self._is_loaded = True
            logger.info(f"Vector search index loaded with {len(records)} vectors.")
        else:
            self._matrix = None
            self._metadata = []
            self._is_loaded = False
            logger.warning("No valid vector embeddings found in database.")

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Searches top_k most similar documents for the given 768-dim query vector.
        Returns list of matching metadata dictionaries with similarity scores.
        """
        if not self._is_loaded or self._matrix is None or len(self._metadata) == 0:
            return []

        # Normalize query vector
        norm = np.linalg.norm(query_vector)
        if norm > 0:
            q_norm = query_vector / norm
        else:
            q_norm = query_vector

        # Dot product search across entire matrix
        scores = np.dot(self._matrix, q_norm)
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(scores[idx])
            meta = dict(self._metadata[idx])
            meta["score"] = round(score, 4)
            results.append(meta)

        return results


# Global singleton vector search engine
vector_search_engine = VectorSearchEngine()
