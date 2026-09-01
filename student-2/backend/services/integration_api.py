"""Cross-service HTTP client for the Student 2 backend.

Talks to the shared-api (session validation) and, following the repo
convention, directly to other students' database services (never their
backends) — here Student 3's applications database.
"""

import requests
from flask import request

from services.config import APPLICATIONS_DB_URL, SHARED_API_URL, TIMEOUT


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


def get_existing_application(user_id: int, posting_id: int) -> dict | None:
    """Return the applicant's existing active application for this posting,
    or None if there isn't one.

    Withdrawn/Rejected applications are treated as "no application" so the
    candidate can apply again.
    """
    try:
        resp = requests.get(
            f"{APPLICATIONS_DB_URL}/applications",
            params={"user_id": user_id, "job_posting_id": posting_id},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException:
        return None
    for row in resp.json() or []:
        status = row.get("application_status")
        if status not in ("Withdrawn", "Rejected"):
            return {
                "application_id": row.get("application_id"),
                "application_status": status,
            }
    return None
