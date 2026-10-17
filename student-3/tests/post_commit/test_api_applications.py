"""Post-commit CI/CD endpoint tests for the Student 3 Application API service.

Mirrors the reference ``test_api_students.py``: live HTTP tests that run in GitHub
Actions after a push, against the running Student 3 database/API service
(``docker compose up`` first). Covers the service health check and two
Application endpoint functions (list and get-by-id).
"""

import os

import requests


DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://localhost:16012")


def test_service_health():
    response = requests.get(f"{DATABASE_SERVICE_URL}/health", timeout=5)
    assert response.status_code == 200


def test_applications_exist():
    response = requests.get(f"{DATABASE_SERVICE_URL}/applications", timeout=5)
    assert response.status_code == 200
    applications = response.json()
    assert len(applications) > 0


def test_application_by_id():
    response = requests.get(f"{DATABASE_SERVICE_URL}/applications/1", timeout=5)
    assert response.status_code == 200


def test_applications_by_status():
    response = requests.get(
        f"{DATABASE_SERVICE_URL}/applications",
        params={"status": "Submitted"},
        timeout=5,
    )
    assert response.status_code == 200
