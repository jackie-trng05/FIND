"""Unit tests for the shared MCP server's ``applicant_profile`` tool (student-1).

These exercise ``tools.get_applicant_profile`` directly with the outbound HTTP
calls mocked, verifying the grounded retrieval-context contract: the profile
fields, resume metadata and extracted resume text are returned, citations
point at the real ``profiles``/``resumes`` fields, and the confidence category
follows the shared rule (complete profile + readable resume -> High,
partial -> Medium, none/unreachable/bad-id -> Low).
"""

import os
import sys

import pytest

MCP_SERVER_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "mcp-server")
)
if MCP_SERVER_DIR not in sys.path:
    sys.path.insert(0, MCP_SERVER_DIR)

import tools  # noqa: E402 (path is set up above)


class _FakeResponse:
    def __init__(self, payload, status_code=200, content=b""):
        self._payload = payload
        self.status_code = status_code
        self.content = content

    def json(self):
        return self._payload


def _complete_profile():
    return {
        "profile_id": 1,
        "user_id": 6,
        "phone": "+61400000006",
        "location": "Sydney, Australia",
        "professional_title": "Software Engineer",
        "summary": "Full-stack developer seeking new opportunities.",
        "interests": "Python, React, Cloud computing",
    }


def _resume_record():
    return {
        "resume_id": 1,
        "profile_id": 1,
        "file_name": "resume_profile_1.pdf",
        "file_type": "application/pdf",
        "uploaded_at": "2026-01-01T00:00:00",
    }


def _get_with_resume(file_content=b"%PDF fake bytes"):
    def _get(url, timeout=None, **kwargs):
        if url.endswith("/resumes"):
            return _FakeResponse([_resume_record()])
        if url.endswith("/file"):
            return _FakeResponse(None, content=file_content)
        return _FakeResponse(_complete_profile())

    return _get


def test_complete_profile_with_readable_resume_is_high_confidence_with_citations(monkeypatch):
    monkeypatch.setattr(tools.requests, "get", _get_with_resume())
    monkeypatch.setattr(
        tools, "_extract_resume_text", lambda data, mimetype: "Experienced engineer with Python skills."
    )
    ctx = tools.get_applicant_profile(6)

    assert ctx["confidence"] == "High"
    data = ctx["answer_data"]
    assert data["user_id"] == 6
    assert data["profile"]["professional_title"] == "Software Engineer"
    assert data["resume"]["file_name"] == "resume_profile_1.pdf"
    assert data["resume"]["text"] == "Experienced engineer with Python skills."

    fields = {s["field"] for s in ctx["sources"]}
    assert "professional_title" in fields
    assert "summary" in fields
    assert "file_name" in fields
    assert "file_data" in fields
    assert any(s["table"] == "profiles" for s in ctx["sources"])
    assert any(s["table"] == "resumes" for s in ctx["sources"])


def test_resume_with_unreadable_text_is_medium_confidence(monkeypatch):
    monkeypatch.setattr(tools.requests, "get", _get_with_resume())
    monkeypatch.setattr(tools, "_extract_resume_text", lambda data, mimetype: "")
    ctx = tools.get_applicant_profile(6)

    assert ctx["confidence"] == "Medium"
    assert ctx["answer_data"]["resume"]["text"] == ""
    fields = {s["field"] for s in ctx["sources"]}
    assert "file_data" not in fields


def test_profile_without_resume_is_medium_confidence(monkeypatch):
    def _get(url, timeout=None, **kwargs):
        if url.endswith("/resumes"):
            return _FakeResponse([])
        return _FakeResponse(_complete_profile())

    monkeypatch.setattr(tools.requests, "get", _get)
    ctx = tools.get_applicant_profile(6)

    assert ctx["confidence"] == "Medium"
    assert ctx["answer_data"]["resume"] is None


def test_incomplete_profile_is_medium_confidence(monkeypatch):
    def _get(url, timeout=None, **kwargs):
        if url.endswith("/resumes"):
            return _FakeResponse([_resume_record()])
        if url.endswith("/file"):
            return _FakeResponse(None, content=b"%PDF fake bytes")
        record = _complete_profile()
        record["interests"] = ""
        return _FakeResponse(record)

    monkeypatch.setattr(tools.requests, "get", _get)
    monkeypatch.setattr(tools, "_extract_resume_text", lambda data, mimetype: "Some resume text.")
    ctx = tools.get_applicant_profile(6)

    assert ctx["confidence"] == "Medium"
    assert ctx["answer_data"]["profile"]["interests"] == ""


def test_missing_profile_is_low_confidence(monkeypatch):
    monkeypatch.setattr(
        tools.requests, "get", lambda *a, **k: _FakeResponse({"error": "Profile not found"}, 404)
    )
    ctx = tools.get_applicant_profile(999)
    assert ctx["confidence"] == "Low"
    assert ctx["answer_data"]["profile"] is None


def test_service_unreachable_is_low_confidence(monkeypatch):
    def _boom(*a, **k):
        raise tools.requests.RequestException("connection refused")

    monkeypatch.setattr(tools.requests, "get", _boom)
    ctx = tools.get_applicant_profile(6)
    assert ctx["confidence"] == "Low"
    assert "error" in ctx["answer_data"]


def test_non_numeric_user_id_is_low_confidence():
    ctx = tools.get_applicant_profile("not-a-number")
    assert ctx["confidence"] == "Low"
    assert "error" in ctx["answer_data"]


def test_extract_resume_text_rejects_non_pdf_mimetype():
    assert tools._extract_resume_text(b"some bytes", "text/plain") == ""


def test_extract_resume_text_truncates_long_text(monkeypatch):
    long_page_text = "A" * (tools._RESUME_TEXT_MAX_CHARS + 500)

    class _FakePage:
        def extract_text(self):
            return long_page_text

    class _FakeReader:
        def __init__(self, _data):
            self.pages = [_FakePage()]

    monkeypatch.setattr(tools, "PdfReader", _FakeReader)
    text = tools._extract_resume_text(b"%PDF bytes", "application/pdf")

    assert text.startswith("A" * 100)
    assert text.endswith("[...truncated...]")
    assert len(text) <= tools._RESUME_TEXT_MAX_CHARS + len("\n[...truncated...]")
