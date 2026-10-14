"""Multi-Agent-Mode routes — the frontend's access point to the shared server.

The browser calls these backend endpoints (via fetch); the backend proxies to
the shared, non-containerised multi-agent server through
``services.multi_agent_api``. The frontend never talks to the server directly.

Feature flags (read from the environment, default ``true`` locally):
    MULTI_AGENT_ENABLED  - master switch for Multi-Agent-Mode endpoints

In CI this flag is set to ``false`` so the pipeline never needs the shared
server or Ollama; the endpoints then return a clear "disabled" response.

Responses are rendered as HTML fragments (Multi-Agent panel): the planner
plan, the worker output with its grounded evidence count, the reviewer
assessment, and the pending human decision (Accept / Partially Accept / Reject).
"""

import json
import os
from html import escape

from flask import Blueprint, request

from services import multi_agent_api

multi_agent_bp = Blueprint("multi_agent_mode", __name__)


# --- Feature flags -------------------------------------------------------
def _flag(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


def multi_agent_enabled() -> bool:
    return _flag("MULTI_AGENT_ENABLED")


def multi_agent_mode_is_active(req) -> bool:
    """Active when the flag is on AND the UI toggle header is on."""
    if not multi_agent_enabled():
        return False
    return req.headers.get("X-Multi-Agent-Mode", "on").strip().lower() in ("1", "true", "yes", "on")


def _disabled_fragment():
    return "<p class=\"mcp-off\">Multi-Agent Mode is disabled.</p>", 403


# --- Fragment rendering --------------------------------------------------
def _agent_block(title: str, body: str) -> str:
    return f"<h4>{escape(title)}</h4><pre class=\"mcp-answer\">{escape(body)}</pre>"


def render_workflow(result: dict) -> str:
    planner = result.get("planner_result", {}) or {}
    worker = result.get("worker_result", {}) or {}
    reviewer = result.get("reviewer_result", {}) or {}
    decision = result.get("human_decision", {}) or {}

    evidence_count = worker.get("evidence_count", 0)
    allowed = ", ".join(decision.get("allowed_values", [])) or "Accept, Partially Accept, Reject"

    header = (
        f"<h3>Multi-Agent Workflow</h3>"
        f"<p class=\"mcp-desc\">Workflow <code>{escape(str(result.get('workflow_id', '')))}</code> · "
        f"{escape(str(result.get('duration_ms', 0)))} ms · "
        f"<strong>{escape(str(evidence_count))}</strong> grounded evidence record(s)</p>"
    )
    planner_block = _agent_block("Planner Agent", str(planner.get("plan", "")))
    worker_block = _agent_block("Worker Agent", str(worker.get("output", "")))
    reviewer_block = _agent_block("Reviewer Agent", str(reviewer.get("review", "")))
    decision_block = (
        "<h4>Human Decision (required)</h4>"
        f"<p class=\"mcp-desc\">Status: <strong>{escape(str(decision.get('status', 'pending')))}</strong> · "
        f"Choose one: {escape(allowed)}</p>"
    )
    return header + planner_block + worker_block + reviewer_block + decision_block


def render_status(status: dict) -> str:
    pretty = json.dumps(status, indent=2, ensure_ascii=False)
    return (
        "<h3>Multi-Agent Workflow Status</h3>"
        f"<pre class=\"mcp-answer\">{escape(pretty)}</pre>"
    )


# --- Endpoints -----------------------------------------------------------
@multi_agent_bp.get("/multi-agent/status")
def multi_agent_status():
    return {"multi_agent_enabled": multi_agent_enabled()}, 200


@multi_agent_bp.post("/multi-agent/workflow")
def multi_agent_workflow():
    if not multi_agent_mode_is_active(request):
        return _disabled_fragment()
    user_request = (request.form.get("user_request") or "").strip()
    if not user_request:
        return "<p>Enter a request to run the workflow.</p>", 400
    try:
        result = multi_agent_api.run_workflow(user_request)
    except multi_agent_api.MultiAgentServiceError as exc:
        return f"<p>Multi-Agent workflow failed.</p><pre>{escape(str(exc))}</pre>", 503
    return render_workflow(result), 200


@multi_agent_bp.get("/multi-agent/workflow/status")
def multi_agent_workflow_status():
    if not multi_agent_mode_is_active(request):
        return _disabled_fragment()
    try:
        status = multi_agent_api.workflow_status()
    except multi_agent_api.MultiAgentServiceError as exc:
        return f"<p>Multi-Agent status failed.</p><pre>{escape(str(exc))}</pre>", 503
    return render_status(status), 200
