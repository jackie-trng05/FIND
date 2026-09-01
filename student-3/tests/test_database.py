"""Tests for the Student 3 database microservice (applications-only)."""

import importlib.util
import sqlite3
from pathlib import Path

import pytest


APP_PATH = Path(__file__).resolve().parents[1] / "database" / "app.py"


def _load_database_module():
    spec = importlib.util.spec_from_file_location("student3_database_app", APP_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _seed_database(db_path: Path):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE applications (
            application_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            job_posting_id INTEGER NOT NULL,
            resume_id INTEGER,
            application_status TEXT NOT NULL DEFAULT 'Draft',
            availability_date TEXT NOT NULL DEFAULT '',
            declaration_accepted INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            submitted_at TEXT
        )
        """
    )

    seed = [
        (6, 1, 6, "Submitted", "2099-01-01", 1, "2026-01-01T00:00:00"),
        (6, 2, 6, "Shortlisted", "2099-01-10", 1, "2026-01-02T00:00:00"),
        (6, 3, 6, "Draft", "2099-01-15", 0, None),
        (7, 1, 7, "Interview Completed", "2099-01-20", 1, "2026-01-03T00:00:00"),
        (8, 4, 8, "Rejected", "2099-01-25", 1, "2026-01-04T00:00:00"),
    ]
    conn.executemany(
        """
        INSERT INTO applications (
            user_id, job_posting_id, resume_id, application_status,
            availability_date, declaration_accepted, submitted_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        seed,
    )
    conn.commit()
    conn.close()


@pytest.fixture()
def client(tmp_path):
    db_file = tmp_path / "student3_test.db"
    _seed_database(db_file)

    app_module = _load_database_module()
    app_module.DATABASE_NAME = str(db_file)
    app_module.app.config.update(TESTING=True)

    with app_module.app.test_client() as test_client:
        yield test_client


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"


def test_list_filter_by_user_and_status(client):
    by_user = client.get("/applications?user_id=6").get_json()
    assert by_user
    assert all(r["user_id"] == 6 for r in by_user)

    by_status = client.get("/applications?status=Submitted").get_json()
    assert by_status
    assert all(r["application_status"] == "Submitted" for r in by_status)


def test_create_defaults_to_draft(client):
    body = client.post(
        "/applications",
        json={"user_id": 10, "job_posting_id": 77},
    ).get_json()
    assert body["application_status"] == "Draft"
    assert body["submitted_at"] is None


def test_duplicate_active_application_is_blocked(client):
    res = client.post("/applications", json={"user_id": 6, "job_posting_id": 1})
    assert res.status_code == 409
    assert "already" in res.get_json()["error"].lower()


def test_submit_requires_resume_and_declaration(client):
    created = client.post(
        "/applications",
        json={"user_id": 11, "job_posting_id": 88},
    ).get_json()
    aid = created["application_id"]

    res = client.put(f"/applications/{aid}/submit")
    assert res.status_code == 400


def test_submit_when_ready_transitions_to_submitted(client):
    created = client.post(
        "/applications",
        json={
            "user_id": 12,
            "job_posting_id": 89,
            "resume_id": 123,
            "declaration_accepted": 1,
        },
    ).get_json()
    aid = created["application_id"]

    submitted = client.put(f"/applications/{aid}/submit")
    assert submitted.status_code == 200
    out = submitted.get_json()
    assert out["application_status"] == "Submitted"
    assert out["submitted_at"] is not None


def test_withdraw_and_delete_rules(client):
    shortlisted = client.get("/applications?user_id=6&status=Shortlisted").get_json()
    aid_shortlisted = shortlisted[0]["application_id"]
    withdrawn = client.put(f"/applications/{aid_shortlisted}/withdraw")
    assert withdrawn.status_code == 200
    assert withdrawn.get_json()["application_status"] == "Withdrawn"

    rejected = client.get("/applications?status=Rejected").get_json()[0]["application_id"]
    cannot_withdraw = client.put(f"/applications/{rejected}/withdraw")
    assert cannot_withdraw.status_code == 400

    submitted = client.get("/applications?status=Submitted").get_json()[0]["application_id"]
    cannot_delete = client.delete(f"/applications/{submitted}")
    assert cannot_delete.status_code == 400

    draft = client.get("/applications?status=Draft").get_json()[0]["application_id"]
    deleted = client.delete(f"/applications/{draft}")
    assert deleted.status_code == 200
    assert client.get(f"/applications/{draft}").status_code == 404


def test_update_status_via_generic_update_endpoint(client):
    submitted = client.get("/applications?status=Submitted").get_json()[0]["application_id"]
    res = client.put(
        f"/applications/{submitted}",
        json={"application_status": "Interview Scheduled"},
    )
    assert res.status_code == 200
    assert res.get_json()["application_status"] == "Interview Scheduled"
