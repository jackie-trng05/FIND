"""Profile multi-agent human decisions require a reason and evidence for every option."""

import pytest

from routes.multi_agent_mode import render_workflow
from services import multi_agent_api


DECISIONS = ("Accept", "Correction", "Reject")


@pytest.fixture(autouse=True)
def enable_multi_agent(monkeypatch):
    monkeypatch.setenv("MULTI_AGENT_ENABLED", "true")


def test_pending_workflow_shows_both_required_fields():
    html = render_workflow({"workflow_id": "profile-1"})
    assert 'placeholder="Reason (required)"' in html
    assert 'placeholder="Evidence Used (required)"' in html
    assert 'id="multi-agent-reason-warn"' in html
    assert 'id="multi-agent-evidence-warn"' in html
    assert "required for Correction" not in html
    for decision in DECISIONS:
        assert f">{decision}</button>" in html


@pytest.mark.parametrize("decision", DECISIONS)
@pytest.mark.parametrize("field", ("reason", "evidence_used"))
@pytest.mark.parametrize("empty", (None, "", " \t "))
def test_decision_requires_both_fields(backend_client, requests_mock, decision, field, empty):
    data = {
        "workflow_id": "profile-1", "decision": decision,
        "reason": "Matches my profile", "evidence_used": "Profile summary",
    }
    if empty is None:
        del data[field]
    else:
        data[field] = empty
    response = backend_client.post("/multi-agent/decision", data=data)
    assert response.status_code == 400
    assert b"required" in response.data
    assert (b"reason" if field == "reason" else b"Evidence Used") in response.data
    assert not requests_mock.called


@pytest.mark.parametrize("decision", DECISIONS)
def test_decision_forwards_and_displays_reason_and_evidence(backend_client, requests_mock, decision):
    endpoint = requests_mock.post(
        f"{multi_agent_api.MULTI_AGENT_SERVER_URL}/workflow/profile-1/decision",
        json={
            "status": "success",
            "workflow": {
                "workflow_id": "profile-1",
                "human_decision": {
                    "status": decision, "reason": "<profile matches>",
                    "evidence_used": "<resume summary>", "decided_at": "2026-10-17",
                },
            },
        },
    )
    response = backend_client.post("/multi-agent/decision", data={
        "workflow_id": "profile-1", "decision": decision,
        "reason": "  <profile matches>  ", "evidence_used": "  <resume summary>  ",
    })
    assert response.status_code == 200
    assert endpoint.last_request.json() == {
        "decision": decision, "reason": "<profile matches>",
        "evidence_used": "<resume summary>", "caller": "student-1",
    }
    assert decision.encode() in response.data
    assert b"&lt;profile matches&gt;" in response.data
    assert b"Evidence used: &lt;resume summary&gt;" in response.data
    assert b"<resume summary>" not in response.data
    assert b'id="multi-agent-evidence"' not in response.data


def test_decision_service_failure_is_reported(backend_client, requests_mock):
    requests_mock.post(
        f"{multi_agent_api.MULTI_AGENT_SERVER_URL}/workflow/profile-1/decision",
        status_code=503, json={"status": "error", "error": "Service unavailable"},
    )
    response = backend_client.post("/multi-agent/decision", data={
        "workflow_id": "profile-1", "decision": "Accept",
        "reason": "Matches", "evidence_used": "Resume",
    })
    assert response.status_code == 503
    assert b"Recording the decision failed" in response.data


def test_disabled_decision_does_not_contact_server(backend_client, requests_mock, monkeypatch):
    monkeypatch.setenv("MULTI_AGENT_ENABLED", "false")
    response = backend_client.post("/multi-agent/decision")
    assert response.status_code == 403
    assert not requests_mock.called
