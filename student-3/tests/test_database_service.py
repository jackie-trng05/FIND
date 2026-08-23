"""Tests for the Student 3 database microservice (Application Management)."""

import base64
import importlib.util
import os

import pytest

import init_db

_DB_APP_PATH = os.path.join(
    os.path.dirname(__file__), "..", "database", "app.py"
)


def _load_database_app():
    """Load the database service's app.py under a unique module name.

    The backend service also defines an ``app.py``; importing by the bare name
    ``app`` is ambiguous, so we load this one from its explicit file path.
    """
    spec = importlib.util.spec_from_file_location("student3_db_app", _DB_APP_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def client():
    # Rebuild a clean, seeded database, then load the app against it.
    init_db.initialise()
    app_module = _load_database_app()
    app_module.app.config.update(TESTING=True)
    with app_module.app.test_client() as test_client:
        yield test_client


# --------------------------------------------------------------------------- #
# Health & seed                                                                #
# --------------------------------------------------------------------------- #

def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_seed_has_at_least_ten_applications(client):
    applications = client.get("/applications").get_json()
    assert isinstance(applications, list)
    assert len(applications) >= 10, "Seed data must contain 10+ applications"


def test_seed_has_resumes(client):
    resumes = client.get("/resumes").get_json()
    assert isinstance(resumes, list)
    assert len(resumes) >= 5


# --------------------------------------------------------------------------- #
# List filters                                                                #
# --------------------------------------------------------------------------- #

def test_list_filter_by_user_id(client):
    rows = client.get("/applications?user_id=6").get_json()
    assert rows
    assert all(r["User_Id"] == 6 for r in rows)


def test_list_filter_by_status(client):
    rows = client.get("/applications?status=Submitted").get_json()
    assert all(r["Application_Status"] == "Submitted" for r in rows)


# --------------------------------------------------------------------------- #
# Create / update / submit / withdraw / delete                                #
# --------------------------------------------------------------------------- #

def test_create_defaults_to_draft(client):
    body = client.post("/applications", json={
        "User_Id": 6, "JobPosting_Id": 999,
        "Availability_Date": "2099-01-01",
    }).get_json()
    assert body["Application_Status"] == "Draft"
    assert body["Application_SubmittedAt"] is None


def test_duplicate_active_application_is_blocked(client):
    # user 6 already has a Submitted application for posting 1 in the seed.
    resp = client.post("/applications", json={
        "User_Id": 6, "JobPosting_Id": 1,
    })
    assert resp.status_code == 409
    assert "already" in resp.get_json()["error"].lower()


def test_submit_requires_resume_and_declaration(client):
    created = client.post("/applications", json={
        "User_Id": 6, "JobPosting_Id": 999,
    }).get_json()
    aid = created["Application_Id"]
    # Missing resume + declaration.
    resp = client.put(f"/applications/{aid}/submit")
    assert resp.status_code == 400


def test_submit_when_ready_transitions_to_submitted(client):
    # Upload a resume first.
    resume_body = client.post("/resumes", json={
        "User_Id": 6,
        "Resume_Filename": "test.pdf",
        "Resume_MimeType": "application/pdf",
        "Resume_Data_Base64": base64.b64encode(b"%PDF-1.4\ntest\n").decode(),
    }).get_json()
    resume_id = resume_body["Resume_Id"]
    # Create + fill + submit.
    created = client.post("/applications", json={
        "User_Id": 6, "JobPosting_Id": 999,
        "Resume_Id": resume_id,
        "Declaration_Accepted": 1,
    }).get_json()
    aid = created["Application_Id"]
    submitted = client.put(f"/applications/{aid}/submit").get_json()
    assert submitted["Application_Status"] == "Submitted"
    assert submitted["Application_SubmittedAt"] is not None


def test_withdraw_updates_status(client):
    # user 6 has a Shortlisted application in the seed.
    rows = client.get("/applications?user_id=6&status=Shortlisted").get_json()
    assert rows
    aid = rows[0]["Application_Id"]
    withdrawn = client.put(f"/applications/{aid}/withdraw").get_json()
    assert withdrawn["Application_Status"] == "Withdrawn"


def test_cannot_withdraw_terminal_status(client):
    hired = client.get("/applications?status=Hired").get_json()
    assert hired
    resp = client.put(f"/applications/{hired[0]['Application_Id']}/withdraw")
    assert resp.status_code == 400


def test_delete_only_allowed_for_draft(client):
    submitted = client.get("/applications?status=Submitted").get_json()
    assert submitted
    resp = client.delete(f"/applications/{submitted[0]['Application_Id']}")
    assert resp.status_code == 400


def test_delete_draft_succeeds(client):
    drafts = client.get("/applications?status=Draft").get_json()
    assert drafts
    aid = drafts[0]["Application_Id"]
    resp = client.delete(f"/applications/{aid}")
    assert resp.status_code in (200, 204)
    assert client.get(f"/applications/{aid}").status_code == 404


# --------------------------------------------------------------------------- #
# Resumes                                                                     #
# --------------------------------------------------------------------------- #

def test_upload_and_download_resume(client):
    payload = b"%PDF-1.4\nhello world\n"
    resp = client.post("/resumes", json={
        "User_Id": 6,
        "Resume_Filename": "my.pdf",
        "Resume_MimeType": "application/pdf",
        "Resume_Data_Base64": base64.b64encode(payload).decode(),
    })
    assert resp.status_code == 201
    resume_id = resp.get_json()["Resume_Id"]
    dl = client.get(f"/resumes/{resume_id}/download")
    assert dl.status_code == 200
    assert dl.data == payload


# --------------------------------------------------------------------------- #
# AI screenings                                                               #
# --------------------------------------------------------------------------- #

def test_upsert_and_get_screening(client):
    apps = client.get("/applications?status=Submitted").get_json()
    aid = apps[0]["Application_Id"]
    payload = {
        "Recommendation": "Yes",
        "Reasoning": "Strong overall fit.",
    }
    resp = client.put(f"/ai-screenings/{aid}", json=payload).get_json()
    assert resp["Recommendation"] == "Yes"
    got = client.get(f"/ai-screenings/{aid}").get_json()
    assert got["Reasoning"] == "Strong overall fit."


# --------------------------------------------------------------------------- #
# Favorite filters                                                            #
# --------------------------------------------------------------------------- #

def test_save_and_delete_favorite_filter(client):
    created = client.post("/favorite-filters", json={
        "Staff_UserId": 1, "Filter_Name": "Hot list", "Filter_Query": "status=Shortlisted",
    })
    assert created.status_code == 201
    filter_id = created.get_json()["Filter_Id"]
    listing = client.get("/favorite-filters?staff_user_id=1").get_json()
    assert any(f["Filter_Id"] == filter_id for f in listing)
    assert client.delete(f"/favorite-filters/{filter_id}").status_code == 200
