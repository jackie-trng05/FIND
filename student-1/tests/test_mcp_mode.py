"""Guard tests for Student 1 MCP-Mode endpoints.

These assert the CI/CD contract: when ``MCP_ENABLED=false`` (as set by the
GitHub Actions workflow) the MCP endpoints return a disabled response and never
attempt to reach the shared MCP server or Ollama.

The blueprint is exercised in isolation (no flask-cors / openai needed) so the
test stays hermetic.
"""

import os

import pytest
from flask import Flask

from routes.mcp_mode import mcp_bp


@pytest.fixture()
def client():
    app = Flask(__name__)
    app.register_blueprint(mcp_bp)
    return app.test_client()


def test_mcp_status_reports_disabled_flags(client, monkeypatch):
    monkeypatch.setenv("MCP_ENABLED", "false")
    monkeypatch.setenv("AI_MODE_ENABLED", "false")
    resp = client.get("/mcp/status")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body == {"mcp_enabled": False, "ai_mode_enabled": False}


def test_project_files_disabled_when_mcp_off(client, monkeypatch):
    monkeypatch.setenv("MCP_ENABLED", "false")
    resp = client.post("/mcp/project-files", data={"directory_path": "."})
    assert resp.status_code == 403
    assert "disabled" in resp.get_data(as_text=True).lower()


def test_ci_report_disabled_when_mcp_off(client, monkeypatch):
    monkeypatch.setenv("MCP_ENABLED", "false")
    resp = client.post("/mcp/ci-report", data={})
    assert resp.status_code == 403
    assert "disabled" in resp.get_data(as_text=True).lower()


def test_applicant_profile_disabled_when_mcp_off(client, monkeypatch):
    monkeypatch.setenv("MCP_ENABLED", "false")
    resp = client.post("/mcp/applicant-profile", data={})
    assert resp.status_code == 403
    assert "disabled" in resp.get_data(as_text=True).lower()


def test_strengths_summary_disabled_when_mcp_off(client, monkeypatch):
    monkeypatch.setenv("MCP_ENABLED", "false")
    resp = client.post("/mcp/strengths-summary", data={})
    assert resp.status_code == 403
    assert "disabled" in resp.get_data(as_text=True).lower()


def test_applicant_profile_requires_authentication(client, monkeypatch):
    monkeypatch.setenv("MCP_ENABLED", "true")
    monkeypatch.setattr("routes.mcp_mode.integration_api.get_session_user", lambda: None)
    resp = client.post("/mcp/applicant-profile", data={})
    assert resp.status_code == 401


def test_strengths_summary_requires_authentication(client, monkeypatch):
    monkeypatch.setenv("MCP_ENABLED", "true")
    monkeypatch.setattr("routes.mcp_mode.integration_api.get_session_user", lambda: None)
    resp = client.post("/mcp/strengths-summary", data={})
    assert resp.status_code == 401
