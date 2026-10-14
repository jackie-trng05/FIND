"""Post-commit CI/CD endpoint tests for the Student 2 Job Posting API service.

Mirrors Lab 11's ``test_api_students.py``: live HTTP tests that run in GitHub
Actions after a push, against the running Student 2 database/API service
(``docker compose up`` first). Covers the service health check and two
Job Posting endpoint functions (list and get-by-id).
"""

import os

import requests


DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://localhost:16009")


def test_service_health():
    response = requests.get(f"{DATABASE_SERVICE_URL}/health", timeout=5)
    assert response.status_code == 200


def test_job_postings_exist():
    response = requests.get(f"{DATABASE_SERVICE_URL}/job-postings", timeout=5)
    assert response.status_code == 200
    postings = response.json()
    assert len(postings) > 0


def test_job_posting_by_id():
    response = requests.get(f"{DATABASE_SERVICE_URL}/job-postings/1", timeout=5)
    assert response.status_code == 200


def test_job_postings_by_status():
    response = requests.get(
        f"{DATABASE_SERVICE_URL}/job-postings",
        params={"status": "Published"},
        timeout=5,
    )
    assert response.status_code == 200
