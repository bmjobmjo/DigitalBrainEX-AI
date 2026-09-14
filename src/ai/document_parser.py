"""
Document Parser and Text Chunker for DigitalBrainEX AI.
Extracts structured text from PDFs (page-by-page), Word documents (docx sections),
and plaintext files, then splits them into overlapping chunks with location metadata.
"""
import os
import re
from typing import List, Dict, Any, Tuple
from src.core.logger import logger


class DocumentParser:
    """Extracts text and produces overlapping chunks with page/section citations."""

    DEFAULT_CHUNK_SIZE = 1000     # characters per chunk (~150-200 words)
    DEFAULT_CHUNK_OVERLAP = 200   # overlap between adjacent chunks

    @classmethod
    def parse_and_chunk(
        cls,
        file_path: str,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> List[Dict[str, Any]]:
        """
        Parses the document at file_path and splits it into indexed chunks.
        Returns a list of dicts: [{'chunk_index': int, 'chunk_text': str, 'page_or_section': str}]
        """
        if not file_path or not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            sections = cls._extract_pdf(file_path)
        elif ext in (".docx", ".doc"):
            sections = cls._extract_docx(file_path)
        else:
            sections = cls._extract_plaintext(file_path)

        # Chunk the extracted sections
        all_chunks = []
        global_chunk_idx = 0

        for page_or_sec, text in sections:
            clean_text = text.strip()
            if not clean_text:
                continue

            section_chunks = cls._split_into_chunks(clean_text, chunk_size, chunk_overlap)
            for ch in section_chunks:
                all_chunks.append({
                    "chunk_index": global_chunk_idx,
                    "chunk_text": ch,
                    "page_or_section": page_or_sec,
                })
                global_chunk_idx += 1

        return all_chunks

    @classmethod
    def _extract_pdf(cls, file_path: str) -> List[Tuple[str, str]]:
        """Extracts text per page using PyPDF2."""
        sections = []
        try:
            import PyPDF2
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                num_pages = len(reader.pages)
                for page_idx in range(num_pages):
                    page = reader.pages[page_idx]
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        sections.append((f"Page {page_idx + 1}", page_text))
        except Exception as e:
            logger.error(f"Error parsing PDF '{file_path}': {e}")
            raise RuntimeError(f"Could not extract text from PDF: {e}") from e

        return sections

    @classmethod
    def _extract_docx(cls, file_path: str) -> List[Tuple[str, str]]:
        """Extracts text per section/heading using python-docx."""
        sections = []
        try:
            import docx
            doc = docx.Document(file_path)
            current_heading = "Introduction"
            current_paragraphs = []

            for p in doc.paragraphs:
                p_text = p.text.strip()
                if not p_text:
                    continue

                # Check if paragraph is a heading
                if p.style and p.style.name and p.style.name.startswith("Heading"):
                    if current_paragraphs:
                        sections.append((f"Section: {current_heading}", "\n\n".join(current_paragraphs)))
                        current_paragraphs = []
                    current_heading = p_text[:60]
                else:
                    current_paragraphs.append(p_text)

            if current_paragraphs:
                sections.append((f"Section: {current_heading}", "\n\n".join(current_paragraphs)))

            # Also check tables in docx
            for t_idx, table in enumerate(doc.tables, 1):
                table_rows = []
                for row in table.rows:
                    cells = [c.text.strip() for c in row.cells if c.text.strip()]
                    if cells:
                        table_rows.append(" | ".join(cells))
                if table_rows:
                    sections.append((f"Table {t_idx}", "\n".join(table_rows)))

        except Exception as e:
            logger.error(f"Error parsing DOCX '{file_path}': {e}")
            raise RuntimeError(f"Could not extract text from Word document: {e}") from e

        return sections

    @classmethod
    def _extract_plaintext(cls, file_path: str) -> List[Tuple[str, str]]:
        """Reads plain text / code / markdown files with multiple encoding fallbacks."""
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
        content = None
        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    content = f.read()
                    break
            except Exception:
                continue

        if content is None:
            raise ValueError(f"Could not decode text file {file_path} with supported encodings.")

        filename = os.path.basename(file_path)
        return [(f"File: {filename}", content)]

    @classmethod
    def _split_into_chunks(cls, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """
        Splits text into chunks of at most chunk_size characters with chunk_overlap,
        respecting paragraph or sentence boundaries where possible.
        """
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + chunk_size
            if end >= text_len:
                chunks.append(text[start:].strip())
                break

            # Find natural break point near end (paragraph break or period)
            cut_point = end
            para_break = text.rfind("\n\n", start, end)
            if para_break != -1 and para_break > start + (chunk_size // 2):
                cut_point = para_break + 2
            else:
                sent_break = text.rfind(". ", start, end)
                if sent_break != -1 and sent_break > start + (chunk_size // 2):
                    cut_point = sent_break + 2
                else:
                    space_break = text.rfind(" ", start, end)
                    if space_break != -1 and space_break > start + (chunk_size // 2):
                        cut_point = space_break + 1

            chunk = text[start:cut_point].strip()
            if chunk:
                chunks.append(chunk)

            # Advance start with overlap
            start = max(start + 1, cut_point - chunk_overlap)

        return chunks
