"""HTTP client for the Student 3 database microservice.

Centralises the database-service URL and returns raw ``requests.Response``
objects so callers can handle status codes and render appropriate HTML.
"""

import os

import requests

DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://student-3-db:6003")
TIMEOUT = 5


# ------------- Applications --------------------------------------------------

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


# ------------- Resumes -------------------------------------------------------

def list_resumes(user_id: int | None = None) -> requests.Response:
    params = {"user_id": user_id} if user_id else {}
    return requests.get(
        f"{DATABASE_SERVICE_URL}/resumes", params=params, timeout=TIMEOUT
    )


def get_resume(resume_id: int) -> requests.Response:
    return requests.get(
        f"{DATABASE_SERVICE_URL}/resumes/{resume_id}", timeout=TIMEOUT
    )


def create_resume(payload: dict) -> requests.Response:
    return requests.post(
        f"{DATABASE_SERVICE_URL}/resumes", json=payload, timeout=15
    )


def download_resume_stream(resume_id: int) -> requests.Response:
    """Return a streaming Response the caller can pipe to the client."""
    return requests.get(
        f"{DATABASE_SERVICE_URL}/resumes/{resume_id}/download",
        timeout=15, stream=True,
    )


# ------------- AI screenings -------------------------------------------------

def get_screening(application_id: int) -> requests.Response:
    return requests.get(
        f"{DATABASE_SERVICE_URL}/ai-screenings/{application_id}", timeout=TIMEOUT
    )


def upsert_screening(application_id: int, payload: dict) -> requests.Response:
    return requests.put(
        f"{DATABASE_SERVICE_URL}/ai-screenings/{application_id}",
        json=payload, timeout=TIMEOUT,
    )


# ------------- Favorite filters ---------------------------------------------

def list_favorite_filters(staff_user_id: int | None = None) -> requests.Response:
    params = {"staff_user_id": staff_user_id} if staff_user_id else {}
    return requests.get(
        f"{DATABASE_SERVICE_URL}/favorite-filters", params=params, timeout=TIMEOUT
    )


def create_favorite_filter(payload: dict) -> requests.Response:
    return requests.post(
        f"{DATABASE_SERVICE_URL}/favorite-filters", json=payload, timeout=TIMEOUT
    )


def delete_favorite_filter(filter_id: int) -> requests.Response:
    return requests.delete(
        f"{DATABASE_SERVICE_URL}/favorite-filters/{filter_id}", timeout=TIMEOUT
    )
