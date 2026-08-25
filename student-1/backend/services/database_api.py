"""HTTP client for the Student 1 database microservice.

Centralises the database-service URL and returns raw ``requests.Response``
objects so callers can handle status codes and render appropriate HTML.
"""

import os

import requests

DB_SERVICE_URL = os.environ["DB_SERVICE_URL"]
TIMEOUT = 5


def get_profile_by_user(user_id: int) -> requests.Response:
    return requests.get(f"{DB_SERVICE_URL}/profiles/by-user/{user_id}", timeout=TIMEOUT)


def get_profile(profile_id: int) -> requests.Response:
    return requests.get(f"{DB_SERVICE_URL}/profiles/{profile_id}", timeout=TIMEOUT)


def create_profile(payload: dict) -> requests.Response:
    return requests.post(f"{DB_SERVICE_URL}/profiles", json=payload, timeout=TIMEOUT)


def update_profile(profile_id: int, payload: dict) -> requests.Response:
    return requests.put(f"{DB_SERVICE_URL}/profiles/{profile_id}", json=payload, timeout=TIMEOUT)


def delete_profile(profile_id: int) -> requests.Response:
    return requests.delete(f"{DB_SERVICE_URL}/profiles/{profile_id}", timeout=TIMEOUT)


def list_resumes(profile_id: int) -> requests.Response:
    return requests.get(f"{DB_SERVICE_URL}/profiles/{profile_id}/resumes", timeout=TIMEOUT)


def upload_resume(profile_id: int, payload: dict) -> requests.Response:
    return requests.post(f"{DB_SERVICE_URL}/profiles/{profile_id}/resumes", json=payload, timeout=TIMEOUT)


def get_resume(resume_id: int) -> requests.Response:
    return requests.get(f"{DB_SERVICE_URL}/resumes/{resume_id}", timeout=TIMEOUT)


def get_resume_file(resume_id: int) -> requests.Response:
    return requests.get(f"{DB_SERVICE_URL}/resumes/{resume_id}/file", timeout=TIMEOUT)


def delete_resume(resume_id: int) -> requests.Response:
    return requests.delete(f"{DB_SERVICE_URL}/resumes/{resume_id}", timeout=TIMEOUT)
