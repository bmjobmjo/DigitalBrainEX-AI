"""
OpenRouter API Client for DigitalBrainEX AI.
Handles communication with OpenRouter LLM models for Stage 1 query reformulation
and Stage 5 grounded answer synthesis with strict document citations.
"""
import json
import os
from typing import List, Dict, Any, Optional, Tuple
import requests
from src.utils.config_manager import get_openrouter_settings
from src.core.logger import logger

OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "anthropic/claude-3.5-sonnet"


class OpenRouterClient:
    """Client for OpenRouter OpenAI-compatible REST API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        enabled: Optional[bool] = None,
    ):
        settings = get_openrouter_settings()
        self.api_key = (api_key if api_key is not None else settings.get("openrouter_api_key", "")).strip()
        self.model = (model if model is not None else settings.get("openrouter_model", DEFAULT_MODEL)).strip() or DEFAULT_MODEL
        self.enabled = enabled if enabled is not None else settings.get("openrouter_enabled", False)

    @property
    def is_configured(self) -> bool:
        """Returns True if OpenRouter is enabled and has a non-empty API key."""
        return bool(self.enabled and self.api_key)

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/bmjobmjo/DigitalBrainEX-AI",
            "X-Title": "DigitalBrainEX AI",
            "Content-Type": "application/json",
        }

    def test_connection(self) -> Tuple[bool, str]:
        """Tests the OpenRouter API key and model connectivity."""
        if not self.api_key:
            return False, "OpenRouter API Key is empty. Please enter your API key in Settings."

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 5,
        }

        try:
            resp = requests.post(
                OPENROUTER_ENDPOINT,
                headers=self._get_headers(),
                json=payload,
                timeout=15,
            )
            if resp.status_code == 200:
                return True, f"Connection successful! Connected to {self.model} via OpenRouter."
            else:
                try:
                    err_data = resp.json()
                    err_msg = err_data.get("error", {}).get("message", resp.text)
                except Exception:
                    err_msg = resp.text
                return False, f"OpenRouter API Error (HTTP {resp.status_code}): {err_msg}"
        except requests.exceptions.Timeout:
            return False, "Connection timed out connecting to OpenRouter. Check your internet connection."
        except Exception as e:
            return False, f"Connection failed: {str(e)}"

    def generate_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> str:
        """Sends chat messages to OpenRouter and returns the text response."""
        if not self.is_configured:
            raise ValueError("OpenRouter is not enabled or API key is not configured.")

        chosen_model = model or self.model
        payload = {
            "model": chosen_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            resp = requests.post(
                OPENROUTER_ENDPOINT,
                headers=self._get_headers(),
                json=payload,
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices", [])
            if choices and "message" in choices[0]:
                return choices[0]["message"].get("content", "").strip()
            return ""
        except requests.exceptions.HTTPError as e:
            err_detail = ""
            try:
                err_data = resp.json()
                err_detail = err_data.get("error", {}).get("message", "")
            except Exception:
                pass
            msg = f"OpenRouter HTTP Error {resp.status_code}: {err_detail or str(e)}"
            logger.error(msg)
            raise RuntimeError(msg) from e
        except Exception as e:
            logger.error(f"OpenRouter request exception: {e}")
            raise

    def stage1_reformulate_query(self, user_question: str) -> Dict[str, Any]:
        """
        Stage 1: Sends the user question to OpenRouter to produce:
          - search_query: Refined, keyword-rich query for local semantic vector search
          - alternate_queries: Paraphrases or alternative formulations
          - scope: Document scope hint ('chunks', 'section', or 'whole_document')
        """
        system_prompt = (
            "You are a search query formulation expert in a Document Retrieval Augmented Generation (RAG) system.\n"
            "Analyze the user's natural language question about their personal documents (PDFs, Word docs, notes).\n"
            "Generate an optimized search formulation in strictly valid JSON format with the following keys:\n"
            "- 'search_query': A concise, keyword-dense search query best suited for semantic vector embedding matching.\n"
            "- 'alternate_queries': A list of 2 to 3 alternative paraphrases or synonym queries.\n"
            "- 'scope': One of ['chunks', 'section', 'whole_document'] indicating the best granularity to answer the question.\n"
            "- 'reasoning': Brief one-sentence explanation of the query focus.\n"
            "Return ONLY the JSON object, with no markdown code blocks or additional text."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_question},
        ]

        try:
            raw_response = self.generate_chat_completion(messages, temperature=0.1, max_tokens=500)
            clean_text = raw_response.strip()
            if clean_text.startswith("```"):
                lines = clean_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                clean_text = "\n".join(lines).strip()

            parsed = json.loads(clean_text)
            return {
                "search_query": str(parsed.get("search_query") or user_question),
                "alternate_queries": list(parsed.get("alternate_queries") or []),
                "scope": str(parsed.get("scope") or "chunks"),
                "reasoning": str(parsed.get("reasoning") or ""),
            }
        except Exception as e:
            logger.warning(f"Stage 1 query reformulation failed to parse JSON: {e}. Falling back to raw prompt.")
            return {
                "search_query": user_question,
                "alternate_queries": [],
                "scope": "chunks",
                "reasoning": "Fallback to raw user question",
            }

    def stage5_synthesize_answer(
        self,
        user_question: str,
        context_excerpts: List[Dict[str, Any]],
    ) -> str:
        """
        Stage 5: Sends the original question + retrieved & expanded document contexts
        to OpenRouter to synthesize a grounded answer with preserved citations.
        """
        if not context_excerpts:
            return (
                "I searched your indexed documents but could not find any relevant information "
                f"matching your question: *\"{user_question}\"*.\n\n"
                "Please verify that the document is added to DigitalBrainEX and that its embedding status is **COMPLETED**."
            )

        # Build context prompt
        context_blocks = []
        for i, ctx in enumerate(context_excerpts, 1):
            file_name = ctx.get("file_name", "Unknown File")
            file_id = ctx.get("file_id", "N/A")
            page_sec = ctx.get("page_or_section") or "General"
            score = ctx.get("score", 0.0)
            text = ctx.get("text", "").strip()

            block = (
                f"--- [SOURCE {i}] ---\n"
                f"Document: {file_name} (DocumentID: {file_id})\n"
                f"Location: {page_sec}\n"
                f"Relevance Score: {score:.2f}\n"
                f"Content:\n{text}\n"
            )
            context_blocks.append(block)

        combined_context = "\n".join(context_blocks)

        system_prompt = (
            "You are DigitalBrainEX AI, an intelligent desktop assistant for managing and searching personal documents.\n"
            "Your task is to answer the user's question accurately using ONLY the provided document sources.\n\n"
            "CRITICAL CITATION RULES:\n"
            "1. Every factual statement, data point, or quotation MUST cite its exact source.\n"
            "2. Use the format: `[Doc: <DocumentName>, Page/Section: <Location>]`.\n"
            "3. If multiple documents or sections support a statement, cite all of them: `[Doc: A.pdf, Page 2] [Doc: B.docx, Section: Summary]`.\n"
            "4. Do NOT make up information or speculate beyond what is explicitly stated in the excerpts.\n"
            "5. If the excerpts only partially answer the question, state what is known and clarify what information is missing.\n"
            "6. Present your answer with clean markdown, bullet points, and headings where helpful."
        )

        user_content = (
            f"Here are the relevant excerpts retrieved from my documents:\n\n"
            f"{combined_context}\n\n"
            f"Question:\n{user_question}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        return self.generate_chat_completion(messages, temperature=0.2, max_tokens=2500)
