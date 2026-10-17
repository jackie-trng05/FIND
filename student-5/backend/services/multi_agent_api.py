"""Thin HTTP client to the shared, non-containerised FIND multi-agent server.

The multi-agent server runs as a local host process on the JSON/HTTP transport
(``multi-agent-server/app.py``, default port 16080). Containerised student
backends reach it at ``http://host.docker.internal:16080`` (overridable with
``MULTI_AGENT_SERVER_URL``). This module exposes two synchronous helpers that
mirror the shared multi-agent workflow contract:

    run_workflow(user_request)   -> planner + worker + reviewer + human decision
    workflow_status()            -> history/audit counts + latest workflow

The frontend never talks to the multi-agent server directly — it always goes
through this backend/API (see ``routes/multi_agent_mode.py``).
"""

import os

import requests

MULTI_AGENT_SERVER_URL = os.getenv(
    "MULTI_AGENT_SERVER_URL", "http://host.docker.internal:16080"
)
# Planner/worker/reviewer run three local models in sequence, so allow a long
# timeout for the end-to-end workflow.
MULTI_AGENT_TIMEOUT = int(os.getenv("MULTI_AGENT_TIMEOUT", "240"))

# Identifies this feature in the shared server's audit log.
CALLER = "student-5"


class MultiAgentServiceError(RuntimeError):
    """Raised when the multi-agent server cannot be reached or a call fails."""


def _post(path: str, payload: dict) -> dict:
    url = f"{MULTI_AGENT_SERVER_URL.rstrip('/')}{path}"
    try:
        response = requests.post(url, json=payload, timeout=MULTI_AGENT_TIMEOUT)
    except requests.RequestException as exc:
        raise MultiAgentServiceError(f"Multi-agent request to {url} failed: {exc}") from exc
    return _parse(response, path)


def _get(path: str) -> dict:
    url = f"{MULTI_AGENT_SERVER_URL.rstrip('/')}{path}"
    try:
        response = requests.get(url, timeout=MULTI_AGENT_TIMEOUT)
    except requests.RequestException as exc:
        raise MultiAgentServiceError(f"Multi-agent request to {url} failed: {exc}") from exc
    return _parse(response, path)


def _parse(response, path: str) -> dict:
    try:
        data = response.json()
    except ValueError as exc:
        raise MultiAgentServiceError(f"Multi-agent server returned non-JSON response: {exc}") from exc
    if response.status_code >= 400 or data.get("status") == "error":
        error = data.get("error", f"HTTP {response.status_code}")
        raise MultiAgentServiceError(f"Multi-agent call '{path}' failed: {error}")
    return data


def run_workflow(user_request: str) -> dict:
    """Run the coordinated planner -> worker -> reviewer workflow.

    Always requests the "applications" evidence domain — this feature is
    Candidate Evaluation, so the Worker grounds every call in the candidate's
    application records (the shared Worker has no built-in knowledge of student
    features; that mapping lives here). Evaluations are a staff-facing review of
    applicants, so evidence is not scoped to a single applicant's own session
    (unlike student-1's profile domain).
    """
    payload = {"user_request": user_request, "caller": CALLER, "evidence_domain": "applications"}
    return _post("/workflow", payload)


def workflow_status() -> dict:
    """Return workflow history/audit counts and the latest workflow record."""
    return _get(f"/workflow/status?caller={CALLER}")


def submit_decision(workflow_id: str, decision: str, reason: str = "", evidence_used: str = "") -> dict:
    """Record the human reviewer's Accept / Correction / Reject decision."""
    return _post(
        f"/workflow/{workflow_id}/decision",
        {"decision": decision, "reason": reason, "evidence_used": evidence_used, "caller": CALLER},
    )
