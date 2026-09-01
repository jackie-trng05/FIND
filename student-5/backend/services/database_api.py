"""Data-access layer for the Evaluation service's own database.

Returns raw ``requests.Response`` objects so callers can handle status codes.
Cross-service calls (shared-api and other students' databases) live in
``services.integration_api``.
"""

import requests as http_requests

from services.config import DB_SERVICE_URL


def list_evaluations_response(params=None, timeout=None):
    return http_requests.get(
        f"{DB_SERVICE_URL}/evaluations", params=params or {}, timeout=timeout
    )


def get_evaluation_response(evaluation_id, timeout=None):
    return http_requests.get(
        f"{DB_SERVICE_URL}/evaluations/{evaluation_id}", timeout=timeout
    )


def create_evaluation(payload):
    return http_requests.post(f"{DB_SERVICE_URL}/evaluations", json=payload)


def update_evaluation(evaluation_id, payload):
    return http_requests.put(
        f"{DB_SERVICE_URL}/evaluations/{evaluation_id}", json=payload
    )


def delete_evaluation(evaluation_id):
    return http_requests.delete(f"{DB_SERVICE_URL}/evaluations/{evaluation_id}")
