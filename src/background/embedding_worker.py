"""
Background Embedding Worker for DigitalBrainEX AI.
Asynchronously processes pending or retry document embeddings in the background
without blocking the PyQt GUI, updating status and storing chunks in SQLite.
"""
import os
from typing import Optional, List
from PyQt6.QtCore import QThread, pyqtSignal

from src.core.repository import DataRepository
from src.config import resolve_document_path
from src.ai.document_parser import DocumentParser
from src.ai.local_embeddings import get_local_embedding_manager, LocalEmbeddingManager
from src.core.logger import logger


class EmbeddingWorker(QThread):
    """Background worker thread for indexing documents into local vector chunks."""

    document_started = pyqtSignal(int, str)                # doc_id, doc_name
    progress_updated = pyqtSignal(int, int, str, str)      # current, total, doc_name, status_message
    document_finished = pyqtSignal(int, str, bool, str)    # doc_id, doc_name, success, error_message
    all_completed = pyqtSignal(int, int)                   # total, succeeded

    def __init__(self, target_doc_ids: Optional[List[int]] = None, parent=None):
        super().__init__(parent)
        self.target_doc_ids = target_doc_ids
        self._is_cancelled = False

    def cancel(self):
        """Signals the worker to stop processing further documents."""
        self._is_cancelled = True

    def run(self):
        self._is_cancelled = False
        docs_to_process = []
        if self.target_doc_ids:
            for doc_id in self.target_doc_ids:
                d = DataRepository.get_document_by_id(doc_id)
                if d:
                    docs_to_process.append(d)
        else:
            # Query all documents with PENDING status
            docs_to_process = DataRepository.get_documents_by_embedding_status("PENDING")

        total = len(docs_to_process)
        succeeded = 0

        if total == 0:
            self.all_completed.emit(0, 0)
            return

        emb_mgr = get_local_embedding_manager()

        for idx, doc in enumerate(docs_to_process, 1):
            if self._is_cancelled:
                logger.info(f"EmbeddingWorker cancelled by user at document {idx}/{total}.")
                break

            doc_id = doc.DocumentID
            doc_name = doc.DocumentName or f"Document #{doc_id}"
            self.document_started.emit(doc_id, doc_name)
            self.progress_updated.emit(idx, total, doc_name, "Parsing content...")

            # Mark PROCESSING
            DataRepository.update_document_embedding_status(doc_id, "PROCESSING")

            try:
                raw_uri = doc.DocumentURI or ""
                resolved_path = resolve_document_path(raw_uri) if raw_uri.strip() else ""
                raw_chunks = []

                # 1. Try file extraction if a local file exists
                if resolved_path and os.path.exists(resolved_path):
                    try:
                        raw_chunks = DocumentParser.parse_and_chunk(resolved_path)
                    except Exception as pe:
                        logger.warning(f"File parser warning for {doc_name} ({resolved_path}): {pe}")

                # 2. Fallback to document text/notes (for PlainNotes, URLs, images, or metadata)
                if not raw_chunks:
                    parts = []
                    if doc.DocumentName and doc.DocumentName.strip():
                        parts.append(f"Document: {doc.DocumentName.strip()}")
                    if doc.Category and doc.Category.strip():
                        parts.append(f"Category: {doc.Category.strip()}")
                    if doc.Desc and doc.Desc.strip():
                        parts.append(f"Description:\n{doc.Desc.strip()}")
                    if doc.Notes and doc.Notes.strip():
                        parts.append(f"Notes:\n{doc.Notes.strip()}")

                    meta_text = "\n\n".join(parts).strip()
                    if meta_text:
                        raw_chunks = DocumentParser.parse_and_chunk_text(
                            meta_text,
                            source_title=f"Notes / Metadata: {doc_name}"
                        )

                if not raw_chunks:
                    err = f"No extractable text or notes found in document."
                    DataRepository.update_document_embedding_status(doc_id, "FAILED", err)
                    self.document_finished.emit(doc_id, doc_name, False, err)
                    self.progress_updated.emit(idx, total, doc_name, "No text found")
                    continue

                self.progress_updated.emit(idx, total, doc_name, f"Embedding {len(raw_chunks)} chunk(s)...")

                # Compute local embeddings in batch
                chunk_texts = [c["chunk_text"] for c in raw_chunks]
                vectors = emb_mgr.embed_texts(chunk_texts)

                # Prepare records for SQLite document_chunks table
                chunk_records = []
                for i, c in enumerate(raw_chunks):
                    blob = LocalEmbeddingManager.vector_to_blob(vectors[i])
                    chunk_records.append({
                        "chunk_index": c["chunk_index"],
                        "chunk_text": c["chunk_text"],
                        "embedding": blob,
                        "page_or_section": c.get("page_or_section"),
                        "model_name": emb_mgr.model_name,
                        "model_version": emb_mgr.model_version,
                    })

                # Atomically save chunks
                DataRepository.save_document_chunks(doc_id, chunk_records)

                # Mark COMPLETED
                DataRepository.update_document_embedding_status(doc_id, "COMPLETED", None)
                succeeded += 1
                self.document_finished.emit(doc_id, doc_name, True, "")
                self.progress_updated.emit(idx, total, doc_name, f"Completed ({len(raw_chunks)} chunks)")

            except Exception as e:
                err_msg = str(e)
                logger.error(f"Failed to embed document {doc_id} ('{doc_name}'): {err_msg}", exc_info=True)
                DataRepository.update_document_embedding_status(doc_id, "FAILED", err_msg)
                self.document_finished.emit(doc_id, doc_name, False, err_msg)
                self.progress_updated.emit(idx, total, doc_name, f"Failed: {err_msg[:40]}")

        self.all_completed.emit(total, succeeded)
