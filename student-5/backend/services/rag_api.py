"""Thin HTTP client to the shared, non-containerised FIND RAG server.

The RAG server runs as a local host process on the JSON/HTTP transport
(``rag-server/rag_http_server.py``, default port 16070). Containerised student
backends reach it at ``http://host.docker.internal:16070`` (overridable with
``RAG_SERVER_URL``). This module exposes three synchronous helpers that mirror
the shared RAG tool contracts:

    refresh_corpus(caller)        -> rebuild corpus + vector index
    retrieve_context(query, k)    -> top-k grounded chunks
    answer_question(query, k)     -> grounded answer + citations + confidence

The frontend never talks to the RAG server directly — it always goes through
this backend/API (see ``routes/rag_mode.py``).
"""

import os

import requests

from services.config import OLLAMA_MODEL

RAG_SERVER_URL = os.getenv("RAG_SERVER_URL", "http://host.docker.internal:16070")
RAG_TIMEOUT = int(os.getenv("RAG_TIMEOUT", "130"))

# Identifies this feature in the shared RAG server's audit log.
CALLER = "student-5"


class RAGServiceError(RuntimeError):
    """Raised when the RAG server cannot be reached or a call fails."""


def _post(path: str, payload: dict) -> dict:
    url = f"{RAG_SERVER_URL.rstrip('/')}{path}"
    try:
        response = requests.post(url, json=payload, timeout=RAG_TIMEOUT)
    except requests.RequestException as exc:  # transport failure -> 503 upstream
        raise RAGServiceError(f"RAG request to {url} failed: {exc}") from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise RAGServiceError(f"RAG server returned non-JSON response: {exc}") from exc

    if response.status_code >= 400 or data.get("status") == "error":
        error = data.get("error", f"HTTP {response.status_code}")
        raise RAGServiceError(f"RAG call '{path}' failed: {error}")
    return data


def refresh_corpus() -> dict:
    """Rebuild the shared corpus and vector index from FIND evidence."""
    return _post("/refresh", {"caller": CALLER})


def retrieve_context(query: str, k: int = 5) -> dict:
    """Retrieve the top-k grounded chunks for a query."""
    return _post("/retrieve", {"query": query, "k": k, "caller": CALLER})


def answer_question(query: str, k: int = 5) -> dict:
    """Answer a question grounded only in retrieved context (with citations)."""
    # Send this feature's OLLAMA_MODEL so the shared server generates with it.
    return _post("/answer", {"query": query, "k": k, "caller": CALLER, "model": OLLAMA_MODEL})
