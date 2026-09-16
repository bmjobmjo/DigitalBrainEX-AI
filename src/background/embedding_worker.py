"""
Background Embedding Worker for DigitalBrainEX AI.
Asynchronously processes pending or retry document embeddings in the background
without blocking the PyQt GUI, updating status and storing chunks in SQLite.
"""
import os
from typing import Optional, List
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from src.core.repository import DataRepository
from src.config import resolve_document_path
from src.ai.document_parser import DocumentParser
from src.ai.local_embeddings import get_local_embedding_manager, LocalEmbeddingManager
from src.core.logger import logger


class EmbeddingWorker(QThread):
    """Background worker thread for indexing documents into local vector chunks."""

    # Fine-grained signals for dual-bar modal progress dialog
    overall_progress = pyqtSignal(int, int, int, int)      # current, total, succeeded, failed
    item_progress = pyqtSignal(str, str, int, int)         # doc_name, stage_desc, current_step, total_steps
    activity_logged = pyqtSignal(str)                     # message

    # Backwards-compatible signals
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
        failed = 0

        if total == 0:
            self.overall_progress.emit(0, 0, 0, 0)
            self.all_completed.emit(0, 0)
            return

        emb_mgr = get_local_embedding_manager()

        for idx, doc in enumerate(docs_to_process, 1):
            if self._is_cancelled:
                logger.info(f"EmbeddingWorker cancelled by user at document {idx}/{total}.")
                self.activity_logged.emit("🛑 Indexing cancelled by user.")
                break

            doc_id = doc.DocumentID
            doc_name = doc.DocumentName or f"Document #{doc_id}"
            self.document_started.emit(doc_id, doc_name)
            self.progress_updated.emit(idx, total, doc_name, "Parsing content...")
            self.item_progress.emit(doc_name, "Inspecting document and notes...", 10, 100)
            self.overall_progress.emit(idx - 1, total, succeeded, failed)

            # Mark PROCESSING
            DataRepository.update_document_embedding_status(doc_id, "PROCESSING")

            try:
                raw_uri = doc.DocumentURI or ""
                resolved_path = resolve_document_path(raw_uri) if raw_uri.strip() else ""
                raw_chunks = []

                # 1. Try file extraction if a local file exists
                if resolved_path and os.path.exists(resolved_path):
                    ext = os.path.splitext(resolved_path)[1].lower() or "file"
                    self.item_progress.emit(doc_name, f"Extracting {ext} content...", 25, 100)
                    try:
                        raw_chunks = DocumentParser.parse_and_chunk(resolved_path)
                        self.item_progress.emit(doc_name, f"Parsed file content ({len(raw_chunks)} chunks)", 45, 100)
                    except Exception as pe:
                        logger.warning(f"File parser warning for {doc_name} ({resolved_path}): {pe}")

                # 2. Extract and append chunks from user notes and description if present
                notes_parts = []
                if doc.Desc and doc.Desc.strip():
                    notes_parts.append(f"Description:\n{doc.Desc.strip()}")
                if doc.Notes and doc.Notes.strip():
                    notes_parts.append(f"Notes:\n{doc.Notes.strip()}")

                if notes_parts:
                    self.item_progress.emit(doc_name, "Extracting user notes & description...", 55, 100)
                    notes_text = "\n\n".join(notes_parts).strip()
                    note_chunks = DocumentParser.parse_and_chunk_text(
                        notes_text,
                        source_title="User Notes & Description"
                    )
                    start_idx = len(raw_chunks)
                    for i, nc in enumerate(note_chunks):
                        nc["chunk_index"] = start_idx + i
                        raw_chunks.append(nc)
                    self.item_progress.emit(doc_name, f"Appended notes (Total: {len(raw_chunks)} chunks)", 65, 100)

                # 3. If neither file nor notes yielded chunks, fallback to title and category metadata
                if not raw_chunks:
                    parts = []
                    if doc.DocumentName and doc.DocumentName.strip():
                        parts.append(f"Document: {doc.DocumentName.strip()}")
                    if doc.Category and doc.Category.strip():
                        parts.append(f"Category: {doc.Category.strip()}")

                    meta_text = "\n\n".join(parts).strip()
                    if meta_text:
                        self.item_progress.emit(doc_name, "Indexing metadata fallback...", 65, 100)
                        raw_chunks = DocumentParser.parse_and_chunk_text(
                            meta_text,
                            source_title=f"Metadata: {doc_name}"
                        )

                if not raw_chunks:
                    err = "No extractable text or notes found in document."
                    DataRepository.update_document_embedding_status(doc_id, "FAILED", err)
                    failed += 1
                    self.document_finished.emit(doc_id, doc_name, False, err)
                    self.progress_updated.emit(idx, total, doc_name, "No text found")
                    self.item_progress.emit(doc_name, "No extractable text or notes found", 100, 100)
                    self.overall_progress.emit(idx, total, succeeded, failed)
                    self.activity_logged.emit(f"⚠️ [{idx}/{total}] {doc_name}: No text found")
                    continue

                num_chunks = len(raw_chunks)
                self.progress_updated.emit(idx, total, doc_name, f"Embedding {num_chunks} chunk(s)...")

                # Compute local embeddings (micro-batching if many chunks so intra-item bar visibly progresses)
                chunk_texts = [c["chunk_text"] for c in raw_chunks]
                if num_chunks <= 16:
                    self.item_progress.emit(doc_name, f"Vectorizing {num_chunks} chunk(s)...", 75, 100)
                    vectors = emb_mgr.embed_texts(chunk_texts)
                else:
                    batch_size = 16
                    all_vecs = []
                    for b_start in range(0, num_chunks, batch_size):
                        b_end = min(b_start + batch_size, num_chunks)
                        pct = 70 + int(20 * (b_end / num_chunks))
                        self.item_progress.emit(doc_name, f"Vectorizing chunks {b_start+1}-{b_end} of {num_chunks}...", pct, 100)
                        b_vecs = emb_mgr.embed_texts(chunk_texts[b_start:b_end])
                        all_vecs.append(b_vecs)
                    vectors = np.vstack(all_vecs)

                self.item_progress.emit(doc_name, f"Saving {num_chunks} chunks to database...", 95, 100)

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
                self.progress_updated.emit(idx, total, doc_name, f"Completed ({num_chunks} chunks)")
                self.item_progress.emit(doc_name, f"Completed ({num_chunks} chunks indexed)", 100, 100)
                self.overall_progress.emit(idx, total, succeeded, failed)
                self.activity_logged.emit(f"✅ [{idx}/{total}] {doc_name} ({num_chunks} chunks)")

            except Exception as e:
                err_msg = str(e)
                logger.error(f"Failed to embed document {doc_id} ('{doc_name}'): {err_msg}", exc_info=True)
                DataRepository.update_document_embedding_status(doc_id, "FAILED", err_msg)
                failed += 1
                self.document_finished.emit(doc_id, doc_name, False, err_msg)
                self.progress_updated.emit(idx, total, doc_name, f"Failed: {err_msg[:40]}")
                self.item_progress.emit(doc_name, f"Failed: {err_msg[:40]}", 100, 100)
                self.overall_progress.emit(idx, total, succeeded, failed)
                self.activity_logged.emit(f"❌ [{idx}/{total}] {doc_name}: {err_msg[:50]}")

        self.overall_progress.emit(total if not self._is_cancelled else idx, total, succeeded, failed)
        self.all_completed.emit(total, succeeded)
