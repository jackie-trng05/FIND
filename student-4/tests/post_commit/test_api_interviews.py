"""Post-commit CI/CD endpoint tests for the Student 4 Interview API service.

Mirrors the reference ``test_api_students.py``: live HTTP tests that run in GitHub
Actions after a push, against the running Student 4 database/API service
(``docker compose up`` first). Covers the service health check and two
Interview endpoint functions (list and get-by-id).
"""

import os

import requests


DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://localhost:16015")


def test_service_health():
    response = requests.get(f"{DATABASE_SERVICE_URL}/", timeout=5)
    assert response.status_code == 200


def test_interviews_exist():
    response = requests.get(f"{DATABASE_SERVICE_URL}/interviews", timeout=5)
    assert response.status_code == 200
    interviews = response.json()
    assert len(interviews) > 0


def test_interview_by_id():
    response = requests.get(f"{DATABASE_SERVICE_URL}/interviews/1", timeout=5)
    assert response.status_code == 200
