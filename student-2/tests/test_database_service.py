"""Tests for the Student 2 database microservice (SQLite REST API)."""

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
    spec = importlib.util.spec_from_file_location("student2_db_app", _DB_APP_PATH)
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


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_seed_has_at_least_ten_records(client):
    postings = client.get("/job-postings").get_json()
    assert isinstance(postings, list)
    assert len(postings) >= 10


def test_applicant_filter_returns_only_published(client):
    published = client.get("/job-postings?status=Published").get_json()
    assert published, "expected at least one published posting in the seed data"
    assert all(p["JobPosting_Status"] == "Published" for p in published)


def test_create_defaults_to_draft(client):
    payload = {
        "User_Id": 1,
        "Job_Title": "Test Engineer",
        "Job_Description": "Write and run tests.",
        "Job_Type": "Full time",
        "Location": "Remote",
    }
    created = client.post("/job-postings", json=payload)
    assert created.status_code in (200, 201)
    body = created.get_json()
    assert body["Job_Title"] == "Test Engineer"
    assert body["JobPosting_Status"] == "Draft"


def test_publish_and_unpublish_roundtrip(client):
    created = client.post(
        "/job-postings",
        json={"User_Id": 1, "Job_Title": "Publishable", "Job_Type": "Casual"},
    ).get_json()
    pid = created["JobPosting_Id"]

    published = client.put(f"/job-postings/{pid}/publish").get_json()
    assert published["JobPosting_Status"] == "Published"
    assert published["JobPosting_PublishedAt"]

    unpublished = client.put(f"/job-postings/{pid}/unpublish").get_json()
    assert unpublished["JobPosting_Status"] == "Draft"


def test_update_and_delete(client):
    created = client.post(
        "/job-postings",
        json={"User_Id": 1, "Job_Title": "Temp", "Job_Type": "Contract"},
    ).get_json()
    pid = created["JobPosting_Id"]

    updated = client.put(
        f"/job-postings/{pid}", json={"Job_Title": "Updated Title"}
    ).get_json()
    assert updated["Job_Title"] == "Updated Title"

    assert client.delete(f"/job-postings/{pid}").status_code in (200, 204)
    assert client.get(f"/job-postings/{pid}").status_code == 404
