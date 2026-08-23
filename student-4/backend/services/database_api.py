import os

import requests

DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://student-4-db:5002")

TIMEOUT = 5


def get_interviews():
    response = requests.get(f"{DATABASE_SERVICE_URL}/interviews", timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def get_interviews_response(filters=None):
    return requests.get(
        f"{DATABASE_SERVICE_URL}/interviews", params=filters or {}, timeout=TIMEOUT
    )


def get_interview_response(interview_id):
    return requests.get(
        f"{DATABASE_SERVICE_URL}/interviews/{interview_id}", timeout=TIMEOUT
    )


def get_interviews_by_status_response(status):
    return requests.get(
        f"{DATABASE_SERVICE_URL}/interviews/by-status",
        params={"status": status},
        timeout=TIMEOUT,
    )


def create_interview(payload):
    return requests.post(
        f"{DATABASE_SERVICE_URL}/interviews", json=payload, timeout=TIMEOUT
    )


def update_interview(interview_id, payload):
    return requests.put(
        f"{DATABASE_SERVICE_URL}/interviews/{interview_id}",
        json=payload,
        timeout=TIMEOUT,
    )


def delete_interview(interview_id):
    return requests.delete(
        f"{DATABASE_SERVICE_URL}/interviews/{interview_id}", timeout=TIMEOUT
    )
