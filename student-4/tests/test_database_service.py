"""Tests for the Student 4 database microservice (Interview storage).

The service loads its SQLite path from the module-level ``DATABASE_NAME``, which
points at the seeded container database in production. Each test loads a fresh
copy of the module against an isolated temporary database so the seeded data is
never touched.
"""

import importlib.util
import os
import sqlite3

import pytest

_DB_APP_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "app.py")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS interviews (
    interview_id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    interview_datetime TEXT NOT NULL,
    interview_link TEXT,
    interview_notes TEXT
)
"""

_SEED = [
    (1, 4, 1, "2026-09-10 10:00", "https://meet.find.app/int-1", "Frontend developer interview."),
    (2, 7, 1, "2026-09-04 14:00", "https://meet.find.app/int-2", "Completed — pending evaluation."),
]


def _load_database_app():
    """Load the database service's app.py under a unique module name.

    The backend service also defines an ``app.py``; importing by the bare name
    ``app`` is ambiguous, so we load this one from its explicit file path.
    """
    spec = importlib.util.spec_from_file_location("student4_db_app", _DB_APP_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "interview.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(_SCHEMA)
    conn.executemany(
        """
        INSERT INTO interviews (
            interview_id, application_id, user_id, interview_datetime,
            interview_link, interview_notes
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        _SEED,
    )
    conn.commit()
    conn.close()

    module = _load_database_app()
    module.DATABASE_NAME = str(db_path)
    module.app.config.update(TESTING=True)
    with module.app.test_client() as test_client:
        yield test_client


# --------------------------------------------------------------------------- #
# Health & seed                                                                #
# --------------------------------------------------------------------------- #

def test_health(client):
    body = client.get("/").get_json()
    assert body["service"] == "student-4-interview-db"
    assert body["status"] == "running"


def test_list_returns_seed_ordered_by_datetime(client):
    rows = client.get("/interviews").get_json()
    assert isinstance(rows, list)
    assert len(rows) == 2
    # Ordered ascending by interview_datetime: 09-04 before 09-10.
    assert [r["interview_id"] for r in rows] == [2, 1]


# --------------------------------------------------------------------------- #
# Read by id / status                                                          #
# --------------------------------------------------------------------------- #

def test_get_interview_found(client):
    row = client.get("/interviews/1").get_json()
    assert row["interview_id"] == 1
    assert row["application_id"] == 4


def test_get_interview_not_found(client):
    resp = client.get("/interviews/999")
    assert resp.status_code == 404
    assert "not found" in resp.get_json()["error"].lower()


# --------------------------------------------------------------------------- #
# Create                                                                       #
# --------------------------------------------------------------------------- #

def test_create_interview_success(client):
    resp = client.post("/interviews", json={
        "application_id": 12,
        "user_id": 3,
        "interview_datetime": "2026-10-01 09:30",
        "interview_link": "https://meet.find.app/int-9",
        "interview_notes": "Second round.",
    })
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["application_id"] == 12
    assert body["interview_id"] == 3


def test_create_applies_defaults_for_optional_fields(client):
    body = client.post("/interviews", json={
        "application_id": 15,
        "user_id": 2,
        "interview_datetime": "2026-10-02 11:00",
    }).get_json()
    assert body["interview_link"] == ""
    assert body["interview_notes"] == ""


def test_create_missing_required_fields_returns_400(client):
    resp = client.post("/interviews", json={"user_id": 2})
    assert resp.status_code == 400
    error = resp.get_json()["error"]
    assert "application_id" in error
    assert "interview_datetime" in error


# --------------------------------------------------------------------------- #
# Update                                                                       #
# --------------------------------------------------------------------------- #

def test_update_interview_partial(client):
    body = client.put("/interviews/1", json={
        "interview_notes": "Updated notes.",
    }).get_json()
    assert body["interview_notes"] == "Updated notes."
    # Untouched fields are preserved.
    assert body["application_id"] == 4


def test_update_interview_not_found(client):
    resp = client.put("/interviews/999", json={"interview_notes": "x"})
    assert resp.status_code == 404


# --------------------------------------------------------------------------- #
# Delete                                                                       #
# --------------------------------------------------------------------------- #

def test_delete_interview_success(client):
    resp = client.delete("/interviews/1")
    assert resp.status_code == 200
    assert resp.get_json()["deleted"] == 1
    assert client.get("/interviews/1").status_code == 404


def test_delete_interview_not_found(client):
    resp = client.delete("/interviews/999")
    assert resp.status_code == 404
