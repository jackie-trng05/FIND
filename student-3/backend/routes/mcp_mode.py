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


# --- Student 3: Applications / Screening ---------------------------------
def _parse_int(raw: str):
    raw = (raw or "").strip()
    if not raw.isdigit():
        return None
    return int(raw)


@mcp_bp.post("/mcp/applications-for-job")
def mcp_applications_for_job():
    """Grounded retrieval of the applications submitted for a job posting."""
    if not mcp_mode_is_active(request):
        return _disabled_fragment()
    job_posting_id = _parse_int(request.form.get("job_posting_id", ""))
    if job_posting_id is None:
        return "<p>Enter a numeric job_posting_id.</p>", 400
    arguments = {"job_posting_id": job_posting_id}
    status = request.form.get("status", "").strip()
    if status:
        arguments["status"] = status
    return _run_tool(
        f"MCP Tool: applications_for_job (job {job_posting_id})",
        "applications_for_job",
        arguments,
    )


def _grounded_shortlist(job_posting_id: int, context: dict) -> str:
    """Build a grounded, cited shortlist answer from MCP application context.

    The answer is derived strictly from the retrieved application records (no
    invention): candidates in "Submitted" are awaiting a shortlist decision and
    those already "Shortlisted" are confirmed. When AI-Mode is enabled AND the
    local LLM is reachable, a short natural-language rationale is layered on top
    of the same grounded facts; otherwise a deterministic grounded summary is used
    so the endpoint still works in CI / without Ollama.
    """
    data = context.get("answer_data", {}) or {}
    applications = data.get("applications", []) or []

    if not applications:
        return (
            f"No applications are on record for job {job_posting_id}, so a "
            "shortlist cannot be grounded in application data yet."
        )

    awaiting = [a for a in applications if a.get("application_status") == "Submitted"]
    already = [a for a in applications if a.get("application_status") == "Shortlisted"]

    def _ids(items):
        return ", ".join(str(a.get("application_id")) for a in items)

    parts = [f"Job {job_posting_id} has {len(applications)} application(s) on record."]
    if awaiting:
        parts.append(
            f"Recommend shortlisting the {len(awaiting)} application(s) currently "
            f"\"Submitted\" (application {_ids(awaiting)})."
        )
    if already:
        parts.append(f"Already shortlisted: application {_ids(already)}.")
    if not awaiting and not already:
        parts.append(
            "No applications are in a shortlist-eligible state (Submitted/Shortlisted)."
        )
    verdict = " ".join(parts)

    if not ai_mode_enabled():
        return verdict

    try:  # Optional LLM narrative, grounded in the retrieved context only.
        import json

        from services.llm_client import OLLAMA_MODEL, client as ollama_client

        grounding = (
            "You are a recruitment assistant. Answer ONLY using the applications "
            "context provided as JSON. Do not invent candidates or statuses. "
            "Recommend shortlisting candidates whose status is 'Submitted'."
        )
        prompt = (
            f"Question: Who should be shortlisted for job {job_posting_id}?\n\n"
            f"Applications context (the only allowed source):\n{json.dumps(data, indent=2)}\n\n"
            "Give a 2-3 sentence grounded shortlist recommendation citing application ids."
        )
        # Bound the local-model latency: on a slow CPU host the narrative can
        # take minutes, so cap it and fall back to the deterministic verdict.
        response = ollama_client.with_options(timeout=25.0).chat.completions.create(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": grounding},
                {"role": "user", "content": prompt},
            ],
            max_tokens=160,
            temperature=0.2,
        )
        narrative = (response.choices[0].message.content or "").strip()
        if narrative:
            return narrative
    except Exception:  # noqa: BLE001 - fall back to the deterministic grounded verdict
        pass
    return verdict


@mcp_bp.post("/mcp/shortlist-recommendation")
def mcp_shortlist_recommendation():
    """Grounded RAG answer to "Who should be shortlisted for job X?"."""
    if not mcp_mode_is_active(request):
        return _disabled_fragment()
    job_posting_id = _parse_int(request.form.get("job_posting_id", ""))
    if job_posting_id is None:
        return "<p>Enter a numeric job_posting_id.</p>", 400

    try:
        context = mcp_client.call_tool(
            "applications_for_job", {"job_posting_id": job_posting_id}
        )
    except mcp_client.MCPClientError as exc:
        return (
            f"<p>MCP applications_for_job failed.</p><pre>{escape(str(exc))}</pre>",
            503,
        )

    answer = _grounded_shortlist(job_posting_id, context)
    confidence = context.get("confidence", "Low")
    sources = context.get("sources", [])
    fragment = (
        f"<h3>{escape(f'Who should be shortlisted for job {job_posting_id}?')}</h3>"
        f"{_confidence_badge(confidence)}"
        f"<p class=\"mcp-answer\">{escape(answer)}</p>"
        f"<h4>Citations</h4>{_citations_list(sources)}"
    )
    return fragment, 200
