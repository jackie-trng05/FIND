"""Guard tests for Student 2 MCP-Mode endpoints.

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


def test_job_postings_disabled_when_mcp_off(client, monkeypatch):
    monkeypatch.setenv("MCP_ENABLED", "false")
    resp = client.post("/mcp/job-postings", data={"query": "python"})
    assert resp.status_code == 403
    assert "disabled" in resp.get_data(as_text=True).lower()


def test_role_recommendation_disabled_when_mcp_off(client, monkeypatch):
    monkeypatch.setenv("MCP_ENABLED", "false")
    resp = client.post("/mcp/role-recommendation", data={"query": "python"})
    assert resp.status_code == 403
    assert "disabled" in resp.get_data(as_text=True).lower()


def test_role_recommendation_requires_query(client, monkeypatch):
    monkeypatch.setenv("MCP_ENABLED", "true")
    resp = client.post("/mcp/role-recommendation", data={"query": "  "})
    assert resp.status_code == 400
