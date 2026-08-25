"""HTTP client for the Student 3 database microservice.

Centralises the database-service URL and returns raw ``requests.Response``
objects so callers can handle status codes and render appropriate HTML.
Only the ``applications`` endpoints live here — resumes are now owned by
student-1 (see ``student1_api``) and the AI screening result is no longer
persisted.
"""

import os

import requests

DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://student-3-db:6003")
TIMEOUT = 5


def list_applications(params: dict | None = None) -> requests.Response:
    return requests.get(
        f"{DATABASE_SERVICE_URL}/applications", params=params or {}, timeout=TIMEOUT
    )


def get_application(application_id: int) -> requests.Response:
    return requests.get(
        f"{DATABASE_SERVICE_URL}/applications/{application_id}", timeout=TIMEOUT
    )


def create_application(payload: dict) -> requests.Response:
    return requests.post(
        f"{DATABASE_SERVICE_URL}/applications", json=payload, timeout=TIMEOUT
    )


def update_application(application_id: int, payload: dict) -> requests.Response:
    return requests.put(
        f"{DATABASE_SERVICE_URL}/applications/{application_id}",
        json=payload, timeout=TIMEOUT,
    )


def submit_application(application_id: int) -> requests.Response:
    return requests.put(
        f"{DATABASE_SERVICE_URL}/applications/{application_id}/submit", timeout=TIMEOUT
    )


def withdraw_application(application_id: int) -> requests.Response:
    return requests.put(
        f"{DATABASE_SERVICE_URL}/applications/{application_id}/withdraw",
        timeout=TIMEOUT,
    )


def delete_application(application_id: int) -> requests.Response:
    return requests.delete(
        f"{DATABASE_SERVICE_URL}/applications/{application_id}", timeout=TIMEOUT
    )
