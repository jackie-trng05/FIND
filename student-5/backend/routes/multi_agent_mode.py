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
assessment, and the pending human decision (Accept / Correction / Reject).
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
    workflow_id = str(result.get("workflow_id", ""))

    evidence_count = worker.get("evidence_count", 0)
    status = str(decision.get("status", "pending"))

    header = (
        f"<h3>Multi-Agent Workflow</h3>"
        f"<p class=\"mcp-desc\">Workflow <code>{escape(workflow_id)}</code> · "
        f"{escape(str(result.get('duration_ms', 0)))} ms · "
        f"<strong>{escape(str(evidence_count))}</strong> grounded evidence record(s)</p>"
    )
    planner_block = _agent_block("Planner Agent", str(planner.get("plan", "")))
    worker_block = _agent_block("Worker Agent", str(worker.get("output", "")))
    reviewer_block = _agent_block("Reviewer Agent", str(reviewer.get("review", "")))

    if status == "pending":
        reason_input = (
            "<input type=\"text\" id=\"multi-agent-reason\" class=\"input\" placeholder=\"Reason (required)\" "
            "style=\"width:100%;margin-bottom:0.25rem;padding:0.4rem 0.6rem;border:1px solid var(--border);border-radius:8px;font-size:0.85rem;\">"
            "<p id=\"multi-agent-reason-warn\" class=\"mcp-off\" style=\"display:none;margin:0 0 0.5rem;font-size:0.8rem;\"></p>"
        )
        evidence_input = (
            "<input type=\"text\" id=\"multi-agent-evidence\" class=\"input\" placeholder=\"Evidence Used (required)\" "
            "style=\"width:100%;margin-bottom:0.25rem;padding:0.4rem 0.6rem;border:1px solid var(--border);border-radius:8px;font-size:0.85rem;\">"
            "<p id=\"multi-agent-evidence-warn\" class=\"mcp-off\" style=\"display:none;margin:0 0 0.5rem;font-size:0.8rem;\"></p>"
        )
        decision_block = (
            "<h4>Human Decision (required)</h4>"
            "<p class=\"mcp-desc\">Status: <strong>pending</strong> — choose one:</p>"
            f"{reason_input}"
            f"{evidence_input}"
            "<div class=\"mcp-actions\">"
            f"<button type=\"button\" class=\"btn btn-primary btn-sm\" onclick=\"submitMultiAgentDecision('{escape(workflow_id)}','Accept')\">Accept</button>"
            f"<button type=\"button\" class=\"btn btn-secondary btn-sm\" onclick=\"submitMultiAgentDecision('{escape(workflow_id)}','Correction')\">Correction</button>"
            f"<button type=\"button\" class=\"btn btn-ghost btn-sm\" onclick=\"submitMultiAgentDecision('{escape(workflow_id)}','Reject')\">Reject</button>"
            "</div>"
        )
    else:
        reason = escape(str(decision.get("reason", "")))
        evidence_used = escape(str(decision.get("evidence_used", "")))
        decided_at = escape(str(decision.get("decided_at", "")))
        reason_html = f" — {reason}" if reason else ""
        evidence_html = f"<p class=\"mcp-desc\">Evidence used: {evidence_used}</p>" if evidence_used else ""
        decision_block = (
            "<h4>Human Decision</h4>"
            f"<p class=\"mcp-desc\">Status: <strong>{escape(status)}</strong>{reason_html} "
            f"<span class=\"mcp-state mcp-off\">(recorded {decided_at})</span></p>"
            f"{evidence_html}"
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


@multi_agent_bp.post("/multi-agent/decision")
def multi_agent_decision():
    if not multi_agent_mode_is_active(request):
        return _disabled_fragment()
    workflow_id = (request.form.get("workflow_id") or "").strip()
    decision = (request.form.get("decision") or "").strip()
    reason = (request.form.get("reason") or "").strip()
    evidence_used = (request.form.get("evidence_used") or "").strip()
    if not workflow_id or not decision:
        return "<p>Missing workflow ID or decision.</p>", 400
    if not reason:
        return "<p class=\"mcp-off\">A reason is required to record a decision.</p>", 400
    if not evidence_used:
        return "<p class=\"mcp-off\">Evidence Used is required to record a decision.</p>", 400
    try:
        result = multi_agent_api.submit_decision(workflow_id, decision, reason=reason, evidence_used=evidence_used)
    except multi_agent_api.MultiAgentServiceError as exc:
        return f"<p>Recording the decision failed.</p><pre>{escape(str(exc))}</pre>", 503
    if result.get("status") != "success":
        return f"<p>{escape(str(result.get('error', 'Decision could not be recorded.')))}</p>", 404
    return render_workflow(result["workflow"]), 200
