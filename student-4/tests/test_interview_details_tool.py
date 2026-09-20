"""Unit tests for the shared MCP server's ``interview_details`` tool (student-4).

These exercise ``tools.get_interview_details`` directly with the outbound HTTP
call mocked, verifying the grounded retrieval-context contract: the interview
datetime, link and structured feedback notes are returned, citations point at
the real ``interviews`` fields, and the confidence category follows the shared
rule (feedback written -> High, scheduled only -> Medium,
none/unreachable/bad-id -> Low).
"""

import json
import os
import sys

import pytest

MCP_SERVER_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "mcp-server")
)
if MCP_SERVER_DIR not in sys.path:
    sys.path.insert(0, MCP_SERVER_DIR)

import tools  # noqa: E402  (path is set up above)


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _notes(**areas):
    return json.dumps(areas)


def _completed_record():
    return {
        "interview_id": 4,
        "application_id": 7,
        "user_id": 2,
        "interview_datetime": "2026-08-10 11:00",
        "interview_link": "https://meet.find.app/int-4",
        "interview_notes": _notes(
            Technical="Solid hands-on knowledge.",
            Communication="Explained their reasoning clearly.",
        ),
    }


def _scheduled_record():
    return {
        "interview_id": 2,
        "application_id": 18,
        "user_id": 2,
        "interview_datetime": "2026-09-05 09:00",
        "interview_link": "https://meet.find.app/int-2",
        "interview_notes": "",
    }


def test_completed_interview_is_high_confidence_with_citations(monkeypatch):
    # The student-4 DB returns all interviews; the tool filters by application_id.
    payload = [_scheduled_record(), _completed_record()]
    monkeypatch.setattr(tools.requests, "get", lambda *a, **k: _FakeResponse(payload))
    ctx = tools.get_interview_details(7)

    assert ctx["confidence"] == "High"
    data = ctx["answer_data"]
    assert data["application_id"] == 7
    assert data["interview_id"] == 4
    assert data["status"] == "completed"
    assert data["interview_datetime"] == "2026-08-10 11:00"
    assert data["notes"]["Technical"] == "Solid hands-on knowledge."

    fields = {s.get("field") for s in ctx["sources"]}
    assert "interview_datetime" in fields
    assert "interview_link" in fields
    assert "interview_notes.Technical" in fields
    assert all(s["table"] == "interviews" for s in ctx["sources"])
    assert all(s["record_id"] == 4 for s in ctx["sources"])


def test_scheduled_interview_is_medium_confidence(monkeypatch):
    monkeypatch.setattr(
        tools.requests, "get", lambda *a, **k: _FakeResponse([_scheduled_record()])
    )
    ctx = tools.get_interview_details(18)
    assert ctx["confidence"] == "Medium"
    assert ctx["answer_data"]["status"] == "scheduled"
    assert ctx["answer_data"]["notes"] == {}
    # Only the schedule fields are cited when no feedback has been written yet.
    fields = {s.get("field") for s in ctx["sources"]}
    assert fields == {"interview_datetime", "interview_link"}


def test_missing_interview_is_low_confidence(monkeypatch):
    monkeypatch.setattr(
        tools.requests, "get", lambda *a, **k: _FakeResponse([_completed_record()])
    )
    ctx = tools.get_interview_details(999)
    assert ctx["confidence"] == "Low"
    assert ctx["answer_data"]["interview"] is None


def test_service_unreachable_is_low_confidence(monkeypatch):
    def _boom(*a, **k):
        raise tools.requests.RequestException("connection refused")

    monkeypatch.setattr(tools.requests, "get", _boom)
    ctx = tools.get_interview_details(7)
    assert ctx["confidence"] == "Low"
    assert "error" in ctx["answer_data"]


def test_non_numeric_application_id_is_low_confidence():
    ctx = tools.get_interview_details("not-a-number")
    assert ctx["confidence"] == "Low"
    assert "error" in ctx["answer_data"]
