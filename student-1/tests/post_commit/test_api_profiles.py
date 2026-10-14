"""Post-commit CI/CD endpoint tests for the Student 1 Profile API service.

Mirrors Lab 11's ``test_api_students.py``: live HTTP tests that run in GitHub
Actions after a push, against the running Student 1 database/API service
(``docker compose up`` first). Covers the service health check and two
Profile endpoint functions (get-by-id and get-by-user).
"""

import os

import requests


DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://localhost:16006")


def test_service_health():
    response = requests.get(f"{DATABASE_SERVICE_URL}/health", timeout=5)
    assert response.status_code == 200


def test_profile_by_id():
    response = requests.get(f"{DATABASE_SERVICE_URL}/profiles/1", timeout=5)
    assert response.status_code == 200
    assert response.json()["profile_id"] == 1


def test_profile_by_user():
    response = requests.get(f"{DATABASE_SERVICE_URL}/profiles/by-user/1", timeout=5)
    assert response.status_code == 200
    assert response.json()["user_id"] == 1
