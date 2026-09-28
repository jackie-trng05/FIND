"""Guard tests for Student 1 RAG-Mode endpoints.

These assert the CI/CD contract: when ``RAG_ENABLED=false`` (as set by the
GitHub Actions workflow) the RAG endpoints return a disabled response and never
attempt to reach the shared RAG server.

The blueprint is exercised in isolation (no flask-cors / requests needed) so the
test stays hermetic.
"""

import pytest
from flask import Flask

from routes.rag_mode import rag_bp


@pytest.fixture()
def client():
    app = Flask(__name__)
    app.register_blueprint(rag_bp)
    return app.test_client()


def test_rag_status_reports_disabled_flags(client, monkeypatch):
    monkeypatch.setenv("RAG_ENABLED", "false")
    monkeypatch.setenv("AI_MODE_ENABLED", "false")
    resp = client.get("/rag/status")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body == {"rag_enabled": False, "ai_mode_enabled": False}


def test_answer_disabled_when_rag_off(client, monkeypatch):
    monkeypatch.setenv("RAG_ENABLED", "false")
    resp = client.post("/rag/answer", data={"query": "hello"})
    assert resp.status_code == 403
    assert "disabled" in resp.get_data(as_text=True).lower()


def test_retrieve_disabled_when_rag_off(client, monkeypatch):
    monkeypatch.setenv("RAG_ENABLED", "false")
    resp = client.post("/rag/retrieve", data={"query": "hello"})
    assert resp.status_code == 403
    assert "disabled" in resp.get_data(as_text=True).lower()


def test_refresh_disabled_when_rag_off(client, monkeypatch):
    monkeypatch.setenv("RAG_ENABLED", "false")
    resp = client.post("/rag/refresh", data={})
    assert resp.status_code == 403
    assert "disabled" in resp.get_data(as_text=True).lower()


def test_answer_rejects_empty_query(client, monkeypatch):
    monkeypatch.setenv("RAG_ENABLED", "true")
    resp = client.post("/rag/answer", data={"query": " "})
    assert resp.status_code == 400


def test_retrieve_rejects_empty_query(client, monkeypatch):
    monkeypatch.setenv("RAG_ENABLED", "true")
    resp = client.post("/rag/retrieve", data={"query": ""})
    assert resp.status_code == 400


def test_answer_maps_service_error_to_503(client, monkeypatch):
    monkeypatch.setenv("RAG_ENABLED", "true")

    from services import rag_api

    def _boom(query, k=5):
        raise rag_api.RAGServiceError("rag server down")

    monkeypatch.setattr(rag_api, "answer_question", _boom)
    resp = client.post("/rag/answer", data={"query": "anything"})
    assert resp.status_code == 503


def test_answer_renders_confidence_badge_and_citations(client, monkeypatch):
    monkeypatch.setenv("RAG_ENABLED", "true")

    from services import rag_api

    def _fake_answer(query, k=5):
        return {
            "status": "success",
            "query": query,
            "answer": "Sophie Martinez is a Marketing Specialist.",
            "citations": [
                {"chunk_id": "db_student-1_profiles_10", "source_id": "student-1-db:/profiles/10", "authority_tier": "tier_1"},
            ],
            "confidence_category": "High",
        }

    monkeypatch.setattr(rag_api, "answer_question", _fake_answer)
    resp = client.post("/rag/answer", data={"query": "What is on Sophie Martinez's applicant profile?"})
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Confidence: High" in body
    assert "badge-success" in body
    assert "student-1-db:/profiles/10" in body
    assert "tier_1" in body
