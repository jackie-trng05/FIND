"""Shared RAG retrieval-context helper for the FIND MCP server.

Every MCP tool returns a *retrieval context object* with a stable shape so the
student backends can ground AI-Mode answers and render citations + a confidence
category consistently:

    {
      "answer_data": <the tool result payload>,
      "sources":     [ {"table": ..., "record_id": ..., "field": ...}, ... ],
      "confidence":  "High" | "Medium" | "Low"
    }

Confidence rule (shared across all student tools):
    High   = an exact record match was returned
    Medium = a partial / filtered match was returned
    Low    = empty result or a fallback path was taken
"""

from typing import Any

HIGH = "High"
MEDIUM = "Medium"
LOW = "Low"


def source(table: str, record_id: Any = None, field: str | None = None) -> dict:
    """Build a single citation entry pointing at a real record/field."""
    entry: dict[str, Any] = {"table": table}
    if record_id is not None:
        entry["record_id"] = record_id
    if field is not None:
        entry["field"] = field
    return entry


def derive_confidence(*, exact: bool = False, partial: bool = False) -> str:
    """Map a match quality onto a confidence category.

    exact   -> High   (an exact record match was returned)
    partial -> Medium (a partial / filtered match was returned)
    neither -> Low    (empty result / fallback)
    """
    if exact:
        return HIGH
    if partial:
        return MEDIUM
    return LOW


def build_context(answer_data: Any, sources: list[dict] | None = None, confidence: str = LOW) -> dict:
    """Wrap a tool result in the shared retrieval-context object."""
    return {
        "answer_data": answer_data,
        "sources": sources or [],
        "confidence": confidence,
    }


def empty_context(reason: str, sources: list[dict] | None = None) -> dict:
    """Convenience for the Low-confidence / no-data path."""
    return build_context({"error": reason}, sources or [], LOW)
