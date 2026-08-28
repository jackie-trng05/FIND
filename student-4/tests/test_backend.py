"""Tests for the Student 4 backend (Interview scheduling service).

Covers three layers without touching the network or the LLM:

* ``views.html_formatters`` — pure HTML fragment builders.
* ``routes.normal_ui`` validation helpers.
* ``routes.normal_ui`` HTTP handlers, with the database/integration service
  calls stubbed out so only this service's logic is exercised.
"""

from datetime import datetime, timedelta

import pytest
import requests
from flask import Flask

from routes import normal_ui
from routes.normal_ui import normal_ui_bp
from services import integration_api
from views import html_formatters as fmt


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

class _FakeResponse:
    """Minimal stand-in for ``requests.Response`` used by the stubbed services."""

    def __init__(self, json_data=None, status_code=200):
        self._json = {} if json_data is None else json_data
        self.status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")


def _future_dt(days=7):
    return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M")


def _past_dt(days=7):
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M")


@pytest.fixture()
def client():
    app = Flask(__name__)
    # Register only the normal UI blueprint so the AI/LLM route (and its
    # ``openai`` dependency) is never imported during testing.
    app.register_blueprint(normal_ui_bp)
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def stub_integration(monkeypatch):
    """Neutralise cross-service enrichment/status writes by default."""
    monkeypatch.setattr(integration_api, "enrich_interviews", lambda rows: rows)
    monkeypatch.setattr(integration_api, "enrich_one", lambda row: row)
    monkeypatch.setattr(integration_api, "set_application_status", lambda *a, **k: True)


@pytest.fixture(autouse=True)
def stub_session(monkeypatch):
    """Treat every request as an authenticated staff member.

    Authentication itself lives in the shared service; these tests only need
    the session gate to pass so the route logic can be exercised.
    """
    fake_user = {"user_id": 1, "role": "staff", "first_name": "Test", "last_name": "Staff"}
    monkeypatch.setattr(normal_ui, "get_session_user", lambda: fake_user)


# --------------------------------------------------------------------------- #
# HTML formatters                                                              #
# --------------------------------------------------------------------------- #

def test_format_interviews_html_empty():
    assert fmt.format_interviews_html([]) == "<p>No interviews found.</p>"


def test_format_interviews_html_renders_rows():
    out = fmt.format_interviews_html([
        {
            "interview_id": 1, "application_id": 4, "user_id": 1,
            "interview_datetime": "2026-09-10 10:00",
            "application_status": "Scheduled", "interview_notes": "Round 1",
        }
    ])
    assert "data-table" in out
    assert "2026-09-10 10:00" in out
    assert "Round 1" in out
    assert "status-scheduled" in out


def test_status_badge_maps_known_status_and_escapes():
    assert 'status-completed' in fmt._status_badge("Completed")
    # Unknown status falls back to the scheduled class.
    assert 'status-scheduled' in fmt._status_badge("Mystery")


def test_formatters_escape_untrusted_values():
    out = fmt.format_interviews_html([
        {"interview_id": 1, "interview_notes": "<script>alert(1)</script>"}
    ])
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_format_interview_html_with_and_without_link():
    with_link = fmt.format_interview_html({
        "interview_id": 1, "interview_link": "https://meet.find.app/x",
    })
    assert 'href="https://meet.find.app/x"' in with_link

    without_link = fmt.format_interview_html({"interview_id": 1})
    assert "No link provided" in without_link


# --------------------------------------------------------------------------- #
# Validation helpers                                                           #
# --------------------------------------------------------------------------- #

def test_positive_int():
    assert normal_ui._positive_int("5") is True
    assert normal_ui._positive_int(" 3 ") is True
    assert normal_ui._positive_int("0") is False
    assert normal_ui._positive_int("-1") is False
    assert normal_ui._positive_int("abc") is False
    assert normal_ui._positive_int(None) is False


def test_valid_datetime():
    assert normal_ui._valid_datetime("2026-09-10 10:00") is True
    assert normal_ui._valid_datetime("2026/09/10 10:00") is False
    assert normal_ui._valid_datetime("not a date") is False


def test_is_future():
    assert normal_ui._is_future(_future_dt()) is True
    assert normal_ui._is_future(_past_dt()) is False


def test_valid_link():
    assert normal_ui._valid_link("") is True
    assert normal_ui._valid_link("https://x.com") is True
    assert normal_ui._valid_link("http://x.com") is True
    assert normal_ui._valid_link("ftp://x.com") is False


# --------------------------------------------------------------------------- #
# Routes: list / get                                                          #
# --------------------------------------------------------------------------- #

def test_list_interviews_filters_by_status(client, monkeypatch):
    rows = [
        {"interview_id": 1, "user_id": 1, "applicant_id": 4, "application_status": "Interview Scheduled"},
        {"interview_id": 2, "user_id": 1, "applicant_id": 5, "application_status": "Interview Completed"},
    ]
    monkeypatch.setattr(normal_ui, "get_interviews_response", lambda f: _FakeResponse(rows))

    resp = client.get("/interviews?status=Interview Completed")
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body) == 1
    assert body[0]["interview_id"] == 2


def test_list_interviews_filters_by_staff(client, monkeypatch):
    rows = [
        {"interview_id": 1, "user_id": 1, "applicant_id": 4},
        {"interview_id": 2, "user_id": 2, "applicant_id": 5},
    ]
    monkeypatch.setattr(normal_ui, "get_interviews_response", lambda f: _FakeResponse(rows))

    body = client.get("/interviews?user_id=2").get_json()
    assert [r["interview_id"] for r in body] == [2]


def test_list_interviews_db_unreachable_returns_503(client, monkeypatch):
    def _boom(_filters):
        raise requests.ConnectionError("down")
    monkeypatch.setattr(normal_ui, "get_interviews_response", _boom)

    resp = client.get("/interviews")
    assert resp.status_code == 503
    assert resp.get_json()["error"]


def test_get_interview_not_found(client, monkeypatch):
    monkeypatch.setattr(
        normal_ui, "get_interview_response", lambda i: _FakeResponse(status_code=404)
    )
    resp = client.get("/interviews/999")
    assert resp.status_code == 404


# --------------------------------------------------------------------------- #
# Routes: schedule (create)                                                    #
# --------------------------------------------------------------------------- #

def test_schedule_interview_validation_errors(client):
    resp = client.post("/interviews", json={
        "application_id": "0",
        "user_id": "",
        "interview_datetime": "bad",
        "interview_link": "ftp://nope",
    })
    assert resp.status_code == 400
    errors = resp.get_json()["errors"]
    assert set(errors) >= {"application_id", "user_id", "interview_datetime", "interview_link"}


def test_schedule_interview_rejects_past_datetime(client):
    resp = client.post("/interviews", json={
        "application_id": "4",
        "user_id": "1",
        "interview_datetime": _past_dt(),
    })
    assert resp.status_code == 400
    assert "interview_datetime" in resp.get_json()["errors"]


def test_schedule_interview_success(client, monkeypatch):
    captured = {}

    def _create(payload):
        captured.update(payload)
        return _FakeResponse({**payload, "interview_id": 10}, status_code=201)

    def _set_status(app_id, status):
        captured["status_synced"] = (app_id, status)
        return True

    monkeypatch.setattr(normal_ui, "create_interview", _create)
    monkeypatch.setattr(integration_api, "set_application_status", _set_status)

    resp = client.post("/interviews", json={
        "application_id": "4",
        "user_id": "1",
        "interview_datetime": _future_dt(),
    })
    assert resp.status_code == 201
    # Interview creation does not carry a status; the linked application does.
    assert "interview_status" not in captured
    assert captured["status_synced"] == ("4", "Interview Requested")


# --------------------------------------------------------------------------- #
# Routes: lifecycle transitions                                                #
# --------------------------------------------------------------------------- #

def test_accept_interview_sets_scheduled(client, monkeypatch):
    seen = {}

    monkeypatch.setattr(
        normal_ui, "get_interview_response",
        lambda i: _FakeResponse({"interview_id": i, "application_id": 4}),
    )
    monkeypatch.setattr(
        integration_api, "set_application_status",
        lambda app_id, status: seen.setdefault("synced", (app_id, status)),
    )

    resp = client.post("/interviews/1/accept")
    assert resp.status_code == 200
    assert seen["synced"] == (4, "Interview Scheduled")


def _full_notes():
    return {
        "Technical": "Solid.",
        "Education": "Relevant degree.",
        "Communication": "Clear.",
        "Problem Solving": "Methodical.",
        "Professionalism": "Punctual.",
    }


def test_complete_interview_saves_notes_and_completes(client, monkeypatch):
    seen = {}
    monkeypatch.setattr(
        normal_ui, "get_interview_response",
        lambda i: _FakeResponse({
            "interview_id": i, "application_id": 4,
            "application_status": "Interview Scheduled",
            "interview_datetime": _past_dt(),
        }),
    )

    def _update(i, payload):
        seen["payload"] = payload
        return _FakeResponse({"interview_id": i, "application_id": 4, **payload})

    monkeypatch.setattr(normal_ui, "update_interview", _update)
    monkeypatch.setattr(
        integration_api, "set_application_status",
        lambda app_id, status: seen.setdefault("synced", (app_id, status)),
    )

    resp = client.post("/interviews/1/complete", json={"interview_notes": _full_notes()})
    assert resp.status_code == 200
    assert seen["synced"] == (4, "Interview Completed")
    assert "interview_status" not in seen["payload"]
    # Notes are persisted as a JSON string containing all five sections.
    assert '"Technical"' in seen["payload"]["interview_notes"]


def test_complete_requires_all_note_sections(client):
    resp = client.post("/interviews/1/complete", json={
        "interview_notes": {"Technical": "ok"},
    })
    assert resp.status_code == 400
    errors = resp.get_json()["errors"]
    assert "Education" in errors


def test_complete_requires_notes_object(client):
    resp = client.post("/interviews/1/complete", json={})
    assert resp.status_code == 400
    assert "notes are required" in resp.get_json()["error"].lower()


def test_complete_rejects_future_interview(client, monkeypatch):
    monkeypatch.setattr(
        normal_ui, "get_interview_response",
        lambda i: _FakeResponse({
            "interview_id": i, "application_id": 4,
            "application_status": "Interview Scheduled",
            "interview_datetime": _future_dt(),
        }),
    )
    resp = client.post("/interviews/1/complete", json={"interview_notes": _full_notes()})
    assert resp.status_code == 400
    assert "not taken place" in resp.get_json()["error"].lower()


def test_complete_rejects_non_scheduled_interview(client, monkeypatch):
    monkeypatch.setattr(
        normal_ui, "get_interview_response",
        lambda i: _FakeResponse({
            "interview_id": i, "application_id": 4,
            "application_status": "Interview Requested",
            "interview_datetime": _past_dt(),
        }),
    )
    resp = client.post("/interviews/1/complete", json={"interview_notes": _full_notes()})
    assert resp.status_code == 400
    assert "scheduled" in resp.get_json()["error"].lower()


def test_update_requires_some_payload(client):
    resp = client.put("/interviews/1", json={})
    assert resp.status_code == 400
    assert "No update details" in resp.get_json()["error"]


def test_update_rejects_detail_edits(client):
    # Interview details (date/time, link) are fixed after creation.
    resp = client.put("/interviews/1", json={"interview_datetime": _future_dt()})
    assert resp.status_code == 400
    assert "interview_details" in resp.get_json()["errors"]


def test_cancel_interview_not_found(client, monkeypatch):
    monkeypatch.setattr(
        normal_ui, "get_interview_response", lambda i: _FakeResponse(status_code=404)
    )
    resp = client.delete("/interviews/999")
    assert resp.status_code == 404


def test_cancel_interview_success(client, monkeypatch):
    monkeypatch.setattr(
        normal_ui, "get_interview_response",
        lambda i: _FakeResponse({"interview_id": i, "application_status": "Interview Requested"}),
    )
    monkeypatch.setattr(
        normal_ui, "delete_interview", lambda i: _FakeResponse({"deleted": i})
    )
    resp = client.delete("/interviews/1")
    assert resp.status_code == 200
    assert resp.get_json()["cancelled"] == 1


def test_cancel_interview_rejects_past_scheduled(client, monkeypatch):
    # A scheduled interview that has already happened is completed, not cancelled.
    monkeypatch.setattr(
        normal_ui, "get_interview_response",
        lambda i: _FakeResponse({
            "interview_id": i,
            "application_status": "Interview Scheduled",
            "interview_datetime": _past_dt(),
        }),
    )
    resp = client.delete("/interviews/1")
    assert resp.status_code == 400


# --------------------------------------------------------------------------- #
# Routes: schedulable applications                                             #
# --------------------------------------------------------------------------- #

def test_schedulable_requires_valid_user_id(client):
    resp = client.get("/schedulable-applications?user_id=abc")
    assert resp.status_code == 400


def test_schedulable_excludes_already_scheduled(client, monkeypatch):
    monkeypatch.setattr(integration_api, "shortlisted_for_staff", lambda s: [
        {"application_id": 4}, {"application_id": 7},
    ])
    # Interview already exists for application 4, so it is filtered out.
    monkeypatch.setattr(
        normal_ui, "get_interviews_response",
        lambda f: _FakeResponse([{"application_id": 4}]),
    )

    body = client.get("/schedulable-applications?user_id=1").get_json()
    ids = [a["application_id"] for a in body["applications"]]
    assert ids == [7]
