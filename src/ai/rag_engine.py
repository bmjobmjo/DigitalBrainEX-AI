"""
5-Stage RAG Engine for DigitalBrainEX AI.
Orchestrates:
  Stage 1: Query reformulation, alternate queries & document scoping via OpenRouter.
  Stage 2: Local vector embedding computation via LocalEmbeddingManager.
  Stage 3: Cosine similarity vector search across SQLite document_chunks.
  Stage 4: Context expansion (adjacent chunk merging, small document inclusion, multi-doc scoring).
  Stage 5: Grounded answer synthesis via OpenRouter with preserved document and page citations.
"""
from typing import List, Dict, Any, Optional
import numpy as np

from src.ai.openrouter_client import OpenRouterClient
from src.ai.local_embeddings import get_local_embedding_manager, LocalEmbeddingManager
from src.core.repository import DataRepository
from src.core.logger import logger


class RAGEngine:
    """End-to-end 5-Stage Retrieval-Augmented Generation Engine."""

    def __init__(
        self,
        openrouter_client: Optional[OpenRouterClient] = None,
        embedding_manager: Optional[LocalEmbeddingManager] = None,
    ):
        self.client = openrouter_client or OpenRouterClient()
        self.emb_mgr = embedding_manager or get_local_embedding_manager()

    def query(self, user_question: str) -> str:
        """
        Executes the full 5-stage RAG query workflow.
        Returns the synthesized answer with citations.
        """
        if not self.client.is_configured:
            return (
                "⚠️ **OpenRouter is not configured or disabled.**\n\n"
                "To enable AskMe document Q&A:\n"
                "1. Go to **Settings** -> **GenAI & LLM**.\n"
                "2. Check **Enable OpenRouter for AskMe AI Assistant**.\n"
                "3. Enter your OpenRouter API key and click **Save All Settings**."
            )

        clean_question = user_question.strip()
        if not clean_question:
            return "Please enter a question to ask about your documents."

        # ---------------------------------------------------------------------
        # STAGE 1: Query Reformulation & Scoping via OpenRouter
        # ---------------------------------------------------------------------
        logger.info(f"RAG Stage 1: Reformulating query '{clean_question[:50]}...'")
        stage1_result = self.client.stage1_reformulate_query(clean_question)
        search_query = stage1_result.get("search_query") or clean_question
        alt_queries = stage1_result.get("alternate_queries") or []
        scope = stage1_result.get("scope") or "chunks"
        logger.info(f"Stage 1 Result: search_query='{search_query}', alt_count={len(alt_queries)}, scope='{scope}'")

        # ---------------------------------------------------------------------
        # STAGE 2: Local Vector Embedding
        # ---------------------------------------------------------------------
        queries_to_embed = [search_query] + alt_queries[:2]
        query_vectors = []
        for q in queries_to_embed:
            if q.strip():
                vec = self.emb_mgr.embed_text(q.strip())
                query_vectors.append(vec)

        if not query_vectors:
            query_vectors.append(self.emb_mgr.embed_text(clean_question))

        # ---------------------------------------------------------------------
        # STAGE 3: Local Vector Search across document_chunks
        # ---------------------------------------------------------------------
        all_chunks = DataRepository.get_all_chunks()
        if not all_chunks:
            return (
                "ℹ️ **No document chunks found in your AI database.**\n\n"
                "Please add documents in the **Documents** view and click **Process Pending Embeddings** "
                "to index them before asking questions."
            )

        # Build document ID to name map
        all_docs = DataRepository.get_documents()
        doc_map = {d.DocumentID: d.DocumentName or f"Document #{d.DocumentID}" for d in all_docs}

        scored_chunks = []
        for ch in all_chunks:
            chunk_vec = LocalEmbeddingManager.blob_to_vector(ch.embedding)
            if chunk_vec.size == 0:
                continue

            # Compute max cosine similarity across the query vectors
            max_sim = 0.0
            for qv in query_vectors:
                sim = LocalEmbeddingManager.cosine_similarity(qv, chunk_vec)
                if sim > max_sim:
                    max_sim = sim

            # Filter low relevance
            if max_sim >= 0.20:
                scored_chunks.append({
                    "chunk_id": ch.chunk_id,
                    "file_id": ch.file_id,
                    "chunk_index": ch.chunk_index,
                    "chunk_text": ch.chunk_text,
                    "page_or_section": ch.page_or_section,
                    "file_name": doc_map.get(ch.file_id, f"Doc #{ch.file_id}"),
                    "score": max_sim,
                })

        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        top_chunks = scored_chunks[:12]

        if not top_chunks:
            return (
                f"I searched all indexed document chunks for *\"{clean_question}\"*, but found no relevant content "
                "with sufficient similarity.\n\n"
                "Try phrasing your question differently or checking if the document has been fully indexed."
            )

        # ---------------------------------------------------------------------
        # STAGE 4: Context Expansion & Contiguity Merging
        # ---------------------------------------------------------------------
        expanded_excerpts = self._expand_and_merge_context(top_chunks, all_chunks, doc_map, scope)

        # ---------------------------------------------------------------------
        # STAGE 5: Grounded Answer Synthesis via OpenRouter
        # ---------------------------------------------------------------------
        logger.info(f"RAG Stage 5: Synthesizing answer with {len(expanded_excerpts)} context excerpts.")
        answer = self.client.stage5_synthesize_answer(clean_question, expanded_excerpts)
        return answer

    def _expand_and_merge_context(
        self,
        top_chunks: List[Dict[str, Any]],
        all_chunks: List[Any],
        doc_map: Dict[int, str],
        scope: str,
    ) -> List[Dict[str, Any]]:
        """
        Merges adjacent chunks from the same file, expands context to surrounding chunks,
        and if a file is small (<= 3 chunks), includes the entire document.
        """
        # Index all chunks by (file_id, chunk_index)
        chunk_by_file_idx = {(c.file_id, c.chunk_index): c for c in all_chunks}
        # Count chunks per file
        file_chunk_counts: Dict[int, int] = {}
        for c in all_chunks:
            file_chunk_counts[c.file_id] = file_chunk_counts.get(c.file_id, 0) + 1

        # Group matched chunks by file_id
        by_file: Dict[int, List[Dict[str, Any]]] = {}
        for tc in top_chunks:
            fid = tc["file_id"]
            if fid not in by_file:
                by_file[fid] = []
            by_file[fid].append(tc)

        excerpts = []

        for fid, chunks in by_file.items():
            file_name = doc_map.get(fid, f"Document #{fid}")
            total_file_chunks = file_chunk_counts.get(fid, 1)

            # If small document (<= 3 chunks) or scope is 'whole_document', include all chunks in order
            if total_file_chunks <= 3 or scope == "whole_document":
                ordered_file_chunks = [
                    c for c in all_chunks if c.file_id == fid
                ]
                ordered_file_chunks.sort(key=lambda x: x.chunk_index)
                full_text = "\n\n".join(c.chunk_text for c in ordered_file_chunks)
                top_score = max(ch["score"] for ch in chunks)
                excerpts.append({
                    "file_id": fid,
                    "file_name": file_name,
                    "page_or_section": "Entire Document",
                    "score": top_score,
                    "text": full_text,
                })
                continue

            # Sort matched chunks by chunk_index
            chunks.sort(key=lambda x: x["chunk_index"])

            # Merge contiguous or adjacent chunks
            merged_groups: List[List[Dict[str, Any]]] = []
            for ch in chunks:
                if not merged_groups:
                    merged_groups.append([ch])
                else:
                    last_group = merged_groups[-1]
                    last_idx = last_group[-1]["chunk_index"]
                    # If adjacent or separated by at most 1 chunk
                    if ch["chunk_index"] <= last_idx + 2:
                        # If separated by 1 chunk, fetch the intermediate chunk to ensure continuous text
                        if ch["chunk_index"] == last_idx + 2:
                            mid_chunk = chunk_by_file_idx.get((fid, last_idx + 1))
                            if mid_chunk:
                                last_group.append({
                                    "chunk_id": mid_chunk.chunk_id,
                                    "file_id": fid,
                                    "chunk_index": mid_chunk.chunk_index,
                                    "chunk_text": mid_chunk.chunk_text,
                                    "page_or_section": mid_chunk.page_or_section,
                                    "file_name": file_name,
                                    "score": ch["score"],
                                })
                        last_group.append(ch)
                    else:
                        merged_groups.append([ch])

            for grp in merged_groups:
                texts = [g["chunk_text"] for g in grp]
                locs = list(dict.fromkeys(g["page_or_section"] for g in grp if g.get("page_or_section")))
                loc_str = ", ".join(locs) if locs else f"Chunk #{grp[0]['chunk_index']}"
                max_score = max(g["score"] for g in grp)

                excerpts.append({
                    "file_id": fid,
                    "file_name": file_name,
                    "page_or_section": loc_str,
                    "score": max_score,
                    "text": "\n\n".join(texts),
                })

        # Sort excerpts by relevance score
        excerpts.sort(key=lambda x: x["score"], reverse=True)
        return excerpts[:8]
