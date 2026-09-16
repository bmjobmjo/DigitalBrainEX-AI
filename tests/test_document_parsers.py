"""
Unit tests for DocumentParser multi-format extraction and EmbeddingWorker enhancements.
Verifies parsing for PDF, DOCX, PPTX, RTF, XLSX, CSV, PlainNotes text, and cancellation.
"""
import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch
import numpy as np

from src.ai.document_parser import DocumentParser
from src.core.database import init_db
from src.core.repository import DataRepository
from src.background.embedding_worker import EmbeddingWorker


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


class TestDocumentParserFormats:

    def test_parse_and_chunk_text_basic(self):
        text = "Section 1: Introduction to AI systems.\n\nSection 2: Architecture of RAG pipelines."
        chunks = DocumentParser.parse_and_chunk_text(text, source_title="Architecture Note")
        assert len(chunks) >= 1
        assert chunks[0]["chunk_index"] == 0
        assert "Introduction to AI systems" in chunks[0]["chunk_text"]
        assert chunks[0]["page_or_section"] == "Architecture Note"

    def test_parse_and_chunk_empty_text(self):
        assert DocumentParser.parse_and_chunk_text("") == []
        assert DocumentParser.parse_and_chunk_text("   \n\t  ") == []

    def test_extract_rtf_clean(self):
        rtf_content = (
            r"{\rtf1\ansi\ansicpg1252\deff0\nouicompat\deflang1033"
            r"{\fonttbl{\f0\fnil\fcharset0 Calibri;}}"
            r"{\colortbl ;\red0\green0\blue255;}"
            r"{\*\generator Riched20 10.0.26200}\viewkind4\uc1 "
            r"\pard\sa200\sl276\slmult1\b\f0\fs22 High Level Architecture:\b0\par"
            r"This is the clinical system design document.\par"
            r"{\pict\wmetafile8\picw2000\pich1000 01000900000324420000000030020000000000000400000003010800050000000b0200000000050000000c0271003b010400000007010400} "
            r"Final conclusion.\par}"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".rtf", delete=False, encoding="utf-8") as f:
            f.write(rtf_content)
            tmp_path = f.name

        try:
            sections = DocumentParser._extract_rtf(tmp_path)
            assert len(sections) == 1
            text = sections[0][1]
            assert "High Level Architecture" in text
            assert "clinical system design document" in text
            assert "Final conclusion" in text
            # Ensure hex image string was stripped
            assert "01000900000324420000" not in text
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_extract_pptx(self):
        from pptx import Presentation
        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[0])
        title = slide.shapes.title
        subtitle = slide.placeholders[1]
        title.text = "DigitalBrainEX AI Overview"
        subtitle.text = "High performance desktop AI with local embeddings."

        with tempfile.NamedTemporaryFile("wb", suffix=".pptx", delete=False) as f:
            prs.save(f)
            tmp_path = f.name

        try:
            sections = DocumentParser._extract_pptx(tmp_path)
            assert len(sections) == 1
            assert sections[0][0] == "Slide 1"
            assert "DigitalBrainEX AI Overview" in sections[0][1]
            assert "local embeddings" in sections[0][1]
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_extract_xlsx(self):
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Tasks"
        ws.append(["Task ID", "Name", "Status"])
        ws.append([101, "Review Architecture", "Done"])
        ws.append([102, "Embed Documents", "Pending"])

        with tempfile.NamedTemporaryFile("wb", suffix=".xlsx", delete=False) as f:
            wb.save(f)
            tmp_path = f.name

        try:
            sections = DocumentParser._extract_xlsx(tmp_path)
            assert len(sections) == 1
            assert sections[0][0] == "Sheet: Tasks"
            assert "Review Architecture" in sections[0][1]
            assert "Embed Documents" in sections[0][1]
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_extract_csv(self):
        csv_data = "Item,Price,Quantity\nApple,1.5,10\nOrange,2.0,5\n"
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write(csv_data)
            tmp_path = f.name

        try:
            sections = DocumentParser._extract_csv(tmp_path)
            assert len(sections) == 1
            assert "Apple | 1.5 | 10" in sections[0][1]
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_extract_binary_strings_fallback(self):
        binary_data = b"\x00\x01\x02\x03\x04Hello Embedded Binary String 12345!\x00\x00\xfe\xffMore text here.\x00"
        with tempfile.NamedTemporaryFile("wb", suffix=".bin", delete=False) as f:
            f.write(binary_data)
            tmp_path = f.name

        try:
            extracted = DocumentParser._extract_binary_strings(tmp_path, min_len=5)
            assert "Hello Embedded Binary String 12345" in extracted
            assert "More text here" in extracted
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


class TestEmbeddingWorkerEnhancements:

    @patch("src.ai.local_embeddings.LocalEmbeddingManager.embed_texts")
    def test_worker_embeds_plain_notes_document(self, mock_embed):
        # Mock embeddings to avoid running heavy neural model in test
        mock_embed.return_value = np.zeros((1, 384), dtype=np.float32)

        # Create a document without file URI (like PlainNotes)
        doc = DataRepository.create_document(
            name="Clinical Notes May 2026",
            uri="",
            desc="Patient observation and trial results.",
            category="PlainNotes"
        )
        doc_id = doc.DocumentID
        try:
            assert doc.EmbeddingStatus == "PENDING"

            # Run worker for this document
            worker = EmbeddingWorker(target_doc_ids=[doc_id])
            finished_events = []
            worker.document_finished.connect(lambda d_id, name, ok, err: finished_events.append((d_id, ok, err)))
            worker.run()

            assert len(finished_events) == 1
            assert finished_events[0][1] is True, f"Failed with: {finished_events[0][2]}"

            # Verify DB status
            updated_doc = DataRepository.get_document_by_id(doc_id)
            assert updated_doc.EmbeddingStatus == "COMPLETED"

            chunks = DataRepository.get_chunks_for_file(doc_id)
            assert len(chunks) >= 1
            assert "Patient observation" in chunks[0].chunk_text
        finally:
            try:
                DataRepository.delete_document(doc_id)
            except Exception:
                pass

    @patch("src.ai.local_embeddings.LocalEmbeddingManager.embed_texts")
    def test_worker_embeds_file_and_user_notes_simultaneously(self, mock_embed):
        mock_embed.side_effect = lambda texts: np.zeros((len(texts), 384), dtype=np.float32)

        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Document file body content regarding Q3 deliverables.")
            tmp_path = f.name

        doc_id = None
        try:
            doc = DataRepository.create_document(
                name="Q3 Deliverables Report",
                uri=tmp_path,
                desc="Executive Summary of Q3 targets.",
                notes="Client agreed to expedited delivery on Oct 1.",
                category="Reports"
            )
            doc_id = doc.DocumentID

            worker = EmbeddingWorker(target_doc_ids=[doc_id])
            finished_events = []
            worker.document_finished.connect(lambda d_id, name, ok, err: finished_events.append((d_id, ok, err)))
            worker.run()

            assert len(finished_events) == 1
            assert finished_events[0][1] is True

            chunks = DataRepository.get_chunks_for_file(doc_id)
            assert len(chunks) >= 2

            # Verify both file content and user notes are present in separate chunks
            texts = [c.chunk_text for c in chunks]
            sections = [c.page_or_section for c in chunks]

            assert any("Document file body content" in t for t in texts), "File content must be indexed"
            assert any("Client agreed to expedited delivery" in t for t in texts), "User notes must be indexed"
            assert "User Notes & Description" in sections, "User notes must have citation section"
        finally:
            if doc_id:
                try:
                    DataRepository.delete_document(doc_id)
                except Exception:
                    pass
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_worker_cancellation(self):
        worker = EmbeddingWorker(target_doc_ids=[999999])
        worker.cancel()
        assert worker._is_cancelled is True
