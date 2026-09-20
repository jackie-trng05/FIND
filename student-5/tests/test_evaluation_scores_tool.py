"""Unit tests for the shared MCP server's ``evaluation_scores`` tool (student-5).

These exercise ``tools.get_evaluation_scores`` directly with the outbound HTTP
call mocked, verifying the grounded retrieval-context contract: the five scores,
overall and recommendation are returned, citations point at the real
``evaluations`` fields, and the confidence category follows the shared rule
(finalized -> High, draft -> Medium, none/unreachable/bad-id -> Low).
"""

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


def _finalized_record():
    return {
        "Evaluation_Id": 7,
        "Application_Id": 13,
        "User_Id": 1,
        "Evaluation_TechnicalScore": 5,
        "Evaluation_EducationScore": 4,
        "Evaluation_CommunicationScore": 4,
        "Evaluation_ProblemSolvingScore": 5,
        "Evaluation_ProfessionalismScore": 4,
        "Evaluation_OverallScore": 4.4,
        "Evaluation_FinalRecommendation": "Hire",
    }


def _draft_record():
    record = _finalized_record()
    record.update(
        {"Evaluation_Id": 8, "Application_Id": 14, "Evaluation_FinalRecommendation": None}
    )
    return record


def test_finalized_evaluation_is_high_confidence_with_citations(monkeypatch):
    monkeypatch.setattr(
        tools.requests, "get", lambda *a, **k: _FakeResponse([_finalized_record()])
    )
    ctx = tools.get_evaluation_scores(13)

    assert ctx["confidence"] == "High"
    data = ctx["answer_data"]
    assert data["application_id"] == 13
    assert data["recommendation"] == "Hire"
    assert data["overall_score"] == 4.4
    assert data["scores"] == {
        "technical": 5,
        "education": 4,
        "communication": 4,
        "problem_solving": 5,
        "professionalism": 4,
    }
    # Each score + overall + recommendation is cited to the evaluations record.
    fields = {s["field"] for s in ctx["sources"]}
    assert "Evaluation_TechnicalScore" in fields
    assert "Evaluation_OverallScore" in fields
    assert "Evaluation_FinalRecommendation" in fields
    assert all(s["table"] == "evaluations" for s in ctx["sources"])
    assert all(s["record_id"] == 7 for s in ctx["sources"])


def test_draft_evaluation_is_medium_confidence(monkeypatch):
    monkeypatch.setattr(
        tools.requests, "get", lambda *a, **k: _FakeResponse([_draft_record()])
    )
    ctx = tools.get_evaluation_scores(14)
    assert ctx["confidence"] == "Medium"
    assert ctx["answer_data"]["status"] == "in_progress"
    assert ctx["answer_data"]["recommendation"] is None


def test_missing_evaluation_is_low_confidence(monkeypatch):
    monkeypatch.setattr(tools.requests, "get", lambda *a, **k: _FakeResponse([]))
    ctx = tools.get_evaluation_scores(999)
    assert ctx["confidence"] == "Low"
    assert ctx["answer_data"]["evaluation"] is None


def test_service_unreachable_is_low_confidence(monkeypatch):
    def _boom(*a, **k):
        raise tools.requests.RequestException("connection refused")

    monkeypatch.setattr(tools.requests, "get", _boom)
    ctx = tools.get_evaluation_scores(13)
    assert ctx["confidence"] == "Low"
    assert "error" in ctx["answer_data"]


def test_non_numeric_application_id_is_low_confidence():
    ctx = tools.get_evaluation_scores("not-a-number")
    assert ctx["confidence"] == "Low"
    assert "error" in ctx["answer_data"]
