"""Post-commit CI/CD endpoint tests for the Student 5 Evaluation API service.

Mirrors Lab 11's ``test_api_students.py``: live HTTP tests that run in GitHub
Actions after a push, against the running Student 5 database/API service
(``docker compose up`` first). Covers the service health check and two
Evaluation endpoint functions (list and get-by-id).
"""

import os

import requests


DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://localhost:16018")


def test_service_health():
    response = requests.get(f"{DATABASE_SERVICE_URL}/health", timeout=5)
    assert response.status_code == 200


def test_evaluations_exist():
    response = requests.get(f"{DATABASE_SERVICE_URL}/evaluations", timeout=5)
    assert response.status_code == 200
    evaluations = response.json()
    assert len(evaluations) > 0


def test_evaluation_by_id():
    response = requests.get(f"{DATABASE_SERVICE_URL}/evaluations/1", timeout=5)
    assert response.status_code == 200


def test_evaluations_by_status():
    response = requests.get(
        f"{DATABASE_SERVICE_URL}/evaluations",
        params={"status": "in_progress"},
        timeout=5,
    )
    assert response.status_code == 200
