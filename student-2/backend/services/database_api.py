"""HTTP client for the Student 2 database microservice.

Centralises the database-service URL and returns raw ``requests.Response``
objects so callers can handle status codes and render appropriate HTML.
"""

import os

import requests
from flask import request

DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://student-2-db:6002")
SHARED_API_URL = os.getenv("SHARED_API_URL", "http://find-shared-api:5000")
TIMEOUT = 5


def get_session_user() -> dict | None:
    """Return the currently logged-in user dict, or None if unauthenticated."""
    cookie = request.headers.get("Cookie", "")
    if not cookie:
        return None
    try:
        resp = requests.get(
            f"{SHARED_API_URL}/api/auth/session",
            headers={"Cookie": cookie},
            timeout=TIMEOUT,
        )
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    return resp.json().get("user")


def list_job_postings(params: dict | None = None) -> requests.Response:
    return requests.get(
        f"{DATABASE_SERVICE_URL}/job-postings", params=params or {}, timeout=TIMEOUT
    )


def get_job_posting(posting_id: int) -> requests.Response:
    return requests.get(
        f"{DATABASE_SERVICE_URL}/job-postings/{posting_id}", timeout=TIMEOUT
    )


def create_job_posting(payload: dict) -> requests.Response:
    return requests.post(
        f"{DATABASE_SERVICE_URL}/job-postings", json=payload, timeout=TIMEOUT
    )


def update_job_posting(posting_id: int, payload: dict) -> requests.Response:
    return requests.put(
        f"{DATABASE_SERVICE_URL}/job-postings/{posting_id}", json=payload, timeout=TIMEOUT
    )


def publish_job_posting(posting_id: int) -> requests.Response:
    return requests.put(
        f"{DATABASE_SERVICE_URL}/job-postings/{posting_id}/publish", timeout=TIMEOUT
    )


def unpublish_job_posting(posting_id: int) -> requests.Response:
    return requests.put(
        f"{DATABASE_SERVICE_URL}/job-postings/{posting_id}/unpublish", timeout=TIMEOUT
    )


def delete_job_posting(posting_id: int) -> requests.Response:
    return requests.delete(
        f"{DATABASE_SERVICE_URL}/job-postings/{posting_id}", timeout=TIMEOUT
    )
