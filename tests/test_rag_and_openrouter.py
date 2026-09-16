"""
Comprehensive unit and integration tests for OpenRouter Client, Local Embeddings,
DocumentParser, document_chunks table schema migration, EmbeddingWorker, and RAGEngine.
"""
import os
import tempfile
import json
import pytest
import numpy as np
from unittest.mock import MagicMock, patch

from src.core.database import init_db, get_db_session
from src.core.models import Document, DocumentChunk
from src.core.repository import DataRepository
from src.utils.config_manager import (
    get_openrouter_settings,
    save_openrouter_settings,
    get_embedding_settings,
    save_embedding_settings,
)
from src.ai.openrouter_client import OpenRouterClient
from src.ai.local_embeddings import LocalEmbeddingManager, get_local_embedding_manager
from src.ai.document_parser import DocumentParser
from src.background.embedding_worker import EmbeddingWorker
from src.ai.rag_engine import RAGEngine


@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()


class TestOpenRouterClient:
    def test_configuration_state(self):
        client = OpenRouterClient(api_key="sk-or-test12345", model="openai/gpt-4o-mini", enabled=True)
        assert client.is_configured is True
        assert client.model == "openai/gpt-4o-mini"
        assert client._get_headers()["Authorization"] == "Bearer sk-or-test12345"

        disabled_client = OpenRouterClient(api_key="sk-or-test12345", enabled=False)
        assert disabled_client.is_configured is False

        empty_key_client = OpenRouterClient(api_key="", enabled=True)
        assert empty_key_client.is_configured is False

    @patch("requests.post")
    def test_test_connection_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        client = OpenRouterClient(api_key="sk-or-valid", enabled=True)
        ok, msg = client.test_connection()
        assert ok is True
        assert "successful" in msg.lower()

    @patch("requests.post")
    def test_test_connection_failure(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Invalid API Key"
        mock_resp.json.return_value = {"error": {"message": "Invalid API Key"}}
        mock_post.return_value = mock_resp

        client = OpenRouterClient(api_key="sk-or-invalid", enabled=True)
        ok, msg = client.test_connection()
        assert ok is False
        assert "401" in msg

    @patch("requests.post")
    def test_stage1_reformulate_query(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "search_query": "contract payment schedule terms",
                        "alternate_queries": ["payment milestones", "invoice billing schedule"],
                        "scope": "section",
                        "reasoning": "Focus on contractual payment obligations"
                    })
                }
            }]
        }
        mock_post.return_value = mock_resp

        client = OpenRouterClient(api_key="sk-or-valid", enabled=True)
        res = client.stage1_reformulate_query("When do we get paid under the contract?")
        assert res["search_query"] == "contract payment schedule terms"
        assert len(res["alternate_queries"]) == 2
        assert res["scope"] == "section"

    @patch("requests.post")
    def test_stage5_synthesize_answer_with_citations(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "choices": [{
                "message": {
                    "content": "According to the contract, net-30 applies [Doc: Contract.pdf, Page/Section: Page 3]."
                }
            }]
        }
        mock_post.return_value = mock_resp

        client = OpenRouterClient(api_key="sk-or-valid", enabled=True)
        contexts = [{
            "file_id": 1,
            "file_name": "Contract.pdf",
            "page_or_section": "Page 3",
            "score": 0.88,
            "text": "All payments shall be made within thirty (30) days of invoice date."
        }]
        answer = client.stage5_synthesize_answer("What are the payment terms?", contexts)
        assert "[Doc: Contract.pdf" in answer


class TestLocalEmbeddings:
    def test_vector_blob_roundtrip(self):
        vec = np.array([0.1, 0.2, -0.5, 0.88, 1.0], dtype=np.float32)
        blob = LocalEmbeddingManager.vector_to_blob(vec)
        restored = LocalEmbeddingManager.blob_to_vector(blob)
        assert np.allclose(vec, restored)

    def test_cosine_similarity(self):
        v1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        v2 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        assert pytest.approx(LocalEmbeddingManager.cosine_similarity(v1, v2), 0.001) == 1.0

        v3 = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        assert pytest.approx(LocalEmbeddingManager.cosine_similarity(v1, v3), 0.001) == 0.0

        v4 = np.array([-1.0, 0.0, 0.0], dtype=np.float32)
        assert pytest.approx(LocalEmbeddingManager.cosine_similarity(v1, v4), 0.001) == -1.0

    def test_singleton_and_embed(self):
        mgr = get_local_embedding_manager()
        assert mgr is not None
        assert mgr.model_name is not None


class TestDocumentParser:
    def test_plaintext_parsing_and_chunking(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Alpha paragraph. " * 30 + "\n\n" + "Beta paragraph. " * 30)
            tmp_path = f.name

        try:
            chunks = DocumentParser.parse_and_chunk(tmp_path, chunk_size=200, chunk_overlap=40)
            assert len(chunks) > 1
            assert chunks[0]["chunk_index"] == 0
            assert "chunk_text" in chunks[0]
            assert "page_or_section" in chunks[0]
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_nonexistent_file_raises(self):
        with pytest.raises(FileNotFoundError):
            DocumentParser.parse_and_chunk("D:\\non_existent_file_12345.pdf")


class TestDocumentChunksRepository:
    def test_save_and_retrieve_chunks(self):
        # Create a document
        doc = DataRepository.create_document(
            name="Test Architecture Doc",
            uri="arch.txt",
            desc="System architecture",
        )
        assert doc.DocumentID is not None
        assert doc.EmbeddingStatus == "PENDING"

        # Save chunks
        vec1 = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        vec2 = np.array([0.4, 0.5, 0.6], dtype=np.float32)

        chunks_data = [
            {
                "chunk_index": 0,
                "chunk_text": "System components overview",
                "embedding": LocalEmbeddingManager.vector_to_blob(vec1),
                "page_or_section": "Page 1",
                "model_name": "test-model",
                "model_version": "1.0",
            },
            {
                "chunk_index": 1,
                "chunk_text": "Database schema details",
                "embedding": LocalEmbeddingManager.vector_to_blob(vec2),
                "page_or_section": "Page 2",
                "model_name": "test-model",
                "model_version": "1.0",
            },
        ]

        count = DataRepository.save_document_chunks(doc.DocumentID, chunks_data)
        assert count == 2

        # Retrieve
        fetched = DataRepository.get_chunks_for_file(doc.DocumentID)
        assert len(fetched) == 2
        assert fetched[0].chunk_text == "System components overview"
        assert fetched[1].chunk_text == "Database schema details"

        # Update status
        DataRepository.update_document_embedding_status(doc.DocumentID, "COMPLETED")
        updated_doc = DataRepository.get_document_by_id(doc.DocumentID)
        assert updated_doc.EmbeddingStatus == "COMPLETED"

        # Cascade delete test
        DataRepository.delete_document(doc.DocumentID)
        remaining_chunks = DataRepository.get_chunks_for_file(doc.DocumentID)
        assert len(remaining_chunks) == 0


class TestEmbeddingWorker:
    def test_embedding_worker_execution(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("DigitalBrainEX AI provides offline document search and time tracking capabilities.")
            tmp_path = f.name

        try:
            doc = DataRepository.create_document(
                name="Temp Doc for Worker",
                uri=tmp_path,
                embedding_status="PENDING",
            )

            worker = EmbeddingWorker(target_doc_ids=[doc.DocumentID])

            # Mock embed_texts on local embedding manager to avoid model download during test
            with patch.object(LocalEmbeddingManager, "embed_texts") as mock_embed:
                mock_embed.return_value = np.array([[0.1, 0.2, 0.3]], dtype=np.float32)
                worker.run()

            reloaded = DataRepository.get_document_by_id(doc.DocumentID)
            assert reloaded.EmbeddingStatus == "COMPLETED"

            chunks = DataRepository.get_chunks_for_file(doc.DocumentID)
            assert len(chunks) >= 1
        finally:
            if 'doc' in locals() and doc:
                try:
                    DataRepository.delete_document(doc.DocumentID)
                except Exception:
                    pass
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


class TestRAGEngine:
    @patch.object(OpenRouterClient, "stage1_reformulate_query")
    @patch.object(OpenRouterClient, "stage5_synthesize_answer")
    def test_full_rag_pipeline(self, mock_stage5, mock_stage1):
        mock_stage1.return_value = {
            "search_query": "offline capabilities",
            "alternate_queries": ["local processing"],
            "scope": "chunks",
            "reasoning": "Searching for offline features"
        }
        mock_stage5.return_value = "DigitalBrainEX operates offline [Doc: Test Offline Manual, Page/Section: Page 1]."

        # Create dummy doc & chunk
        doc = DataRepository.create_document(
            name="Test Offline Manual",
            uri="dummy.txt",
            embedding_status="COMPLETED",
        )
        fake_vec = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        DataRepository.save_document_chunks(doc.DocumentID, [{
            "chunk_index": 0,
            "chunk_text": "The entire database runs locally on SQLite.",
            "embedding": LocalEmbeddingManager.vector_to_blob(fake_vec),
            "page_or_section": "Page 1",
            "model_name": "test-model",
            "model_version": "1.0",
        }])

        client = OpenRouterClient(api_key="sk-or-valid", enabled=True)
        rag = RAGEngine(openrouter_client=client)

        with patch.object(LocalEmbeddingManager, "embed_text") as mock_embed_text:
            mock_embed_text.return_value = fake_vec  # matches 1.0 perfectly
            answer = rag.query("Can this run without internet?")

        assert "[Doc: Test Offline Manual" in answer
        assert mock_stage1.called
        assert mock_stage5.called

        # Clean up
        DataRepository.delete_document(doc.DocumentID)
