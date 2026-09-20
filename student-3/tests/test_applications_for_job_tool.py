"""Unit tests for the shared MCP server's ``applications_for_job`` tool (student-3).

These exercise ``tools.get_applications_for_job`` directly with the outbound HTTP
call mocked, verifying the grounded retrieval-context contract: the matching
application records (with their soft resume link) are returned, citations point at
the real ``applications`` fields, and the confidence category follows the shared
rule (filtered query -> High, unfiltered-with-records -> Medium,
none/unreachable/bad-id -> Low).
"""

import os
import sys

MCP_SERVER_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "mcp-server")
)
if MCP_SERVER_DIR not in sys.path:
    sys.path.insert(0, MCP_SERVER_DIR)

import tools  # noqa: E402 (path is set up above)


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _application(application_id, status, user_id=6, resume_id=6):
    return {
        "application_id": application_id,
        "user_id": user_id,
        "job_posting_id": 1,
        "resume_id": resume_id,
        "application_status": status,
        "submitted_at": "2026-09-01T00:00:00+00:00",
    }


def test_filtered_query_is_high_confidence_with_citations(monkeypatch):
    records = [
        _application(1, "Submitted"),
        _application(20, "Submitted", user_id=7, resume_id=7),
    ]
    monkeypatch.setattr(tools.requests, "get", lambda *a, **k: _FakeResponse(records))
    ctx = tools.get_applications_for_job(1, status="Submitted")

    assert ctx["confidence"] == "High"
    data = ctx["answer_data"]
    assert data["job_posting_id"] == 1
    assert data["status_filter"] == "Submitted"
    assert data["count"] == 2
    assert [a["application_id"] for a in data["applications"]] == [1, 20]
    # Each application's status and its soft resume link are cited.
    fields = {s["field"] for s in ctx["sources"]}
    assert "application_status" in fields
    assert "resume_id" in fields
    assert all(s["table"] == "applications" for s in ctx["sources"])


def test_unfiltered_query_with_records_is_medium_confidence(monkeypatch):
    records = [_application(1, "Submitted"), _application(2, "Shortlisted")]
    monkeypatch.setattr(tools.requests, "get", lambda *a, **k: _FakeResponse(records))
    ctx = tools.get_applications_for_job(1)
    assert ctx["confidence"] == "Medium"
    assert ctx["answer_data"]["status_filter"] is None
    assert ctx["answer_data"]["count"] == 2


def test_no_applications_is_low_confidence(monkeypatch):
    monkeypatch.setattr(tools.requests, "get", lambda *a, **k: _FakeResponse([]))
    ctx = tools.get_applications_for_job(999)
    assert ctx["confidence"] == "Low"
    assert ctx["answer_data"]["applications"] == []


def test_service_unreachable_is_low_confidence(monkeypatch):
    def _boom(*a, **k):
        raise tools.requests.RequestException("connection refused")

    monkeypatch.setattr(tools.requests, "get", _boom)
    ctx = tools.get_applications_for_job(1)
    assert ctx["confidence"] == "Low"
    assert "error" in ctx["answer_data"]


def test_non_numeric_job_posting_id_is_low_confidence():
    ctx = tools.get_applications_for_job("not-a-number")
    assert ctx["confidence"] == "Low"
    assert "error" in ctx["answer_data"]
