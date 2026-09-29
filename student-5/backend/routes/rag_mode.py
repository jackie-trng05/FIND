"""RAG-Mode routes — the frontend's access point to the shared RAG server.

The browser calls these backend endpoints (via HTMX / fetch); the backend
proxies to the shared, non-containerised RAG server through
``services.rag_api``. The frontend never talks to the RAG server directly.

Feature flags (read from the environment, default ``true`` locally):
    RAG_ENABLED      - master switch for RAG-Mode endpoints
    AI_MODE_ENABLED  - grounded generation switch (surfaced for the UI)

In CI both flags are set to ``false`` so the pipeline never needs the shared
RAG server or Ollama; the endpoints then return a clear "disabled" response.

Responses are shown as the raw tool JSON (Lab 08 RAG tab): every answer
carries source citations and a confidence category, and the pipeline returns
"Insufficient evidence." when the retrieved context cannot support an answer.
"""

import json
import os
from html import escape

from flask import Blueprint, request

from services import rag_api

rag_bp = Blueprint("rag_mode", __name__)


# --- Feature flags -------------------------------------------------------
def _flag(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


def rag_enabled() -> bool:
    return _flag("RAG_ENABLED")


def ai_mode_enabled() -> bool:
    return _flag("AI_MODE_ENABLED")


def rag_mode_is_active(req) -> bool:
    """RAG-Mode is active when the flag is on AND the UI toggle header is on."""
    if not rag_enabled():
        return False
    return req.headers.get("X-RAG-Mode", "on").strip().lower() in ("1", "true", "yes", "on")


def _disabled_fragment():
    return "<p class=\"feature-state feature-off\">RAG Mode is disabled.</p>", 403


# --- Fragment rendering (Lab 08 style: raw tool JSON) -------------------
def render_tool(tool: str, result: dict) -> str:
    """Show the RAG tool name and its JSON output, as the Lab 08 RAG tab does."""
    payload = escape(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return (
        f"<h3>RAG Tool: {escape(tool)}</h3>"
        f"<pre class=\"mcp-answer\" style=\"white-space:pre-wrap;overflow-wrap:anywhere;\">{payload}</pre>"
    )


# --- Helpers -------------------------------------------------------------
def _parse_k(raw: str, default: int = 5) -> int:
    try:
        k = int(str(raw).strip())
    except (TypeError, ValueError):
        return default
    return max(1, min(k, 10))


# --- Endpoints -----------------------------------------------------------
@rag_bp.get("/rag/status")
def rag_status():
    return {
        "rag_enabled": rag_enabled(),
        "ai_mode_enabled": ai_mode_enabled(),
    }, 200


@rag_bp.post("/rag/refresh")
def rag_refresh():
    if not rag_mode_is_active(request):
        return _disabled_fragment()
    try:
        result = rag_api.refresh_corpus()
    except rag_api.RAGServiceError as exc:
        return f"<p>RAG refresh failed.</p><pre>{escape(str(exc))}</pre>", 503
    return render_tool("refresh_corpus", result), 200


@rag_bp.post("/rag/retrieve")
def rag_retrieve():
    if not rag_mode_is_active(request):
        return _disabled_fragment()
    query = (request.form.get("query") or "").strip()
    if not query:
        return "<p>Enter a question to retrieve context.</p>", 400
    k = _parse_k(request.form.get("k", "5"))
    try:
        result = rag_api.retrieve_context(query, k=k)
    except rag_api.RAGServiceError as exc:
        return f"<p>RAG retrieval failed.</p><pre>{escape(str(exc))}</pre>", 503
    return render_tool("retrieve_context", result), 200


@rag_bp.post("/rag/answer")
def rag_answer():
    if not rag_mode_is_active(request):
        return _disabled_fragment()
    query = (request.form.get("query") or "").strip()
    if not query:
        return "<p>Enter a question to answer.</p>", 400
    k = _parse_k(request.form.get("k", "5"))
    try:
        result = rag_api.answer_question(query, k=k)
    except rag_api.RAGServiceError as exc:
        return f"<p>RAG answer failed.</p><pre>{escape(str(exc))}</pre>", 503
    return render_tool("answer_question", result), 200
