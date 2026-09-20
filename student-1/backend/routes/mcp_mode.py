"""MCP-Mode routes — the frontend's access point to the shared MCP server.

The browser calls these backend endpoints (via HTMX); the backend proxies to
the shared, non-containerised MCP server through ``services.mcp_client``. The
frontend never talks to the MCP server directly.

Feature flags (read from the environment, default ``true`` locally):
    MCP_ENABLED      - master switch for MCP-Mode endpoints
    AI_MODE_ENABLED  - master switch for grounded AI-Mode

In CI both flags are set to ``false`` so the pipeline never needs Ollama or the
MCP process; the endpoints then return a clear "disabled" response.

Step 1 exposes the two shared tools (project_files, ci_report). Each student's
own retrieval tool + grounded AI-Mode endpoint is added in Step 2.
"""

import os
from html import escape

from flask import Blueprint, request

from services import mcp_client

mcp_bp = Blueprint("mcp_mode", __name__)


# --- Feature flags -------------------------------------------------------
def _flag(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


def mcp_enabled() -> bool:
    return _flag("MCP_ENABLED")


def ai_mode_enabled() -> bool:
    return _flag("AI_MODE_ENABLED")


def mcp_mode_is_active(req) -> bool:
    """MCP-Mode is active when the flag is on AND the UI toggle header is on."""
    if not mcp_enabled():
        return False
    return req.headers.get("X-MCP-Mode", "on").strip().lower() in ("1", "true", "yes", "on")


def _disabled_fragment():
    return "<p class=\"feature-state feature-off\">MCP Mode is disabled.</p>", 403


# --- Fragment rendering (grounded: shows citations + confidence) ---------
def _confidence_badge(confidence: str) -> str:
    css = {
        "High": "badge-success",
        "Medium": "badge-warning",
        "Low": "badge-danger",
    }.get(confidence, "badge-warning")
    return f'<span class="badge {css}">Confidence: {escape(confidence or "Low")}</span>'


def _citations_list(sources) -> str:
    if not sources:
        return "<p class=\"muted\">No citations.</p>"
    items = []
    for src in sources:
        table = escape(str(src.get("table", "")))
        field = src.get("field")
        record_id = src.get("record_id")
        label = table
        if field:
            label += f".{escape(str(field))}"
        if record_id is not None:
            label += f" ({escape(str(record_id))})"
        items.append(f"<li>{label}</li>")
    return "<ul class=\"mcp-citations\">" + "".join(items) + "</ul>"


def render_context(title: str, context: dict) -> str:
    import json

    answer = context.get("answer_data", context)
    sources = context.get("sources", [])
    confidence = context.get("confidence", "Low")
    return (
        f"<h3>{escape(title)}</h3>"
        f"{_confidence_badge(confidence)}"
        f"<pre class=\"mcp-answer\">{escape(json.dumps(answer, indent=2))}</pre>"
        f"<h4>Citations</h4>{_citations_list(sources)}"
    )


def _run_tool(title: str, tool: str, arguments: dict):
    if not mcp_mode_is_active(request):
        return _disabled_fragment()
    try:
        context = mcp_client.call_tool(tool, arguments)
    except mcp_client.MCPClientError as exc:
        return f"<p>MCP {escape(tool)} failed.</p><pre>{escape(str(exc))}</pre>", 503
    return render_context(title, context), 200


# --- Endpoints -----------------------------------------------------------
@mcp_bp.get("/mcp/status")
def mcp_status():
    return {
        "mcp_enabled": mcp_enabled(),
        "ai_mode_enabled": ai_mode_enabled(),
    }, 200


@mcp_bp.post("/mcp/project-files")
def mcp_project_files():
    directory_path = request.form.get("directory_path", ".").strip() or "."
    return _run_tool("MCP Tool: project_files", "project_files", {"directory_path": directory_path})


@mcp_bp.post("/mcp/ci-report")
def mcp_ci_report():
    report_path = request.form.get("report_path", "").strip()
    return _run_tool("MCP Tool: ci_report", "ci_report", {"report_path": report_path})
