"""Data-access layer for the Application service's own database.

Returns raw ``requests.Response`` objects so callers can handle status codes
and render the appropriate HTML fragment. Cross-service calls (shared-api and
other students' databases) live in ``services.integration_api``.
"""

import requests

from services.config import DATABASE_SERVICE_URL, TIMEOUT


def list_applications_response(params=None):
    return requests.get(
        f"{DATABASE_SERVICE_URL}/applications", params=params or {}, timeout=TIMEOUT
    )


def get_application(application_id):
    """Raw response for a single application (callers handle status codes)."""
    return requests.get(
        f"{DATABASE_SERVICE_URL}/applications/{application_id}", timeout=TIMEOUT
    )


def create_application(payload):
    return requests.post(
        f"{DATABASE_SERVICE_URL}/applications", json=payload, timeout=TIMEOUT
    )


def update_application(application_id, payload):
    return requests.put(
        f"{DATABASE_SERVICE_URL}/applications/{application_id}", json=payload, timeout=TIMEOUT
    )


def submit_application(application_id):
    return requests.put(
        f"{DATABASE_SERVICE_URL}/applications/{application_id}/submit", timeout=TIMEOUT
    )


def withdraw_application(application_id):
    return requests.put(
        f"{DATABASE_SERVICE_URL}/applications/{application_id}/withdraw", timeout=TIMEOUT
    )


def delete_application(application_id):
    return requests.delete(
        f"{DATABASE_SERVICE_URL}/applications/{application_id}", timeout=TIMEOUT
    )
