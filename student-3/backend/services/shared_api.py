"""HTTP client for the shared-api service.

Used to look up applicant/staff user records so the frontend can render
candidate names on the staff table and pre-fill the applicant form.
"""

import os

import requests

SHARED_API_URL = os.getenv("SHARED_API_URL", "http://find-shared-api:5000")
TIMEOUT = 5


def get_users_map(user_ids: list[int]) -> dict[int, dict]:
    """Return {user_id: user_row_dict} for the requested user IDs.

    Falls back to an empty dict if the shared-db cannot be reached; callers
    should be prepared to render an "Unknown candidate" label.
    """
    if not user_ids:
        return {}
    try:
        # Call the shared-db directly through the shared-api service is not
        # exposed; instead we hit the shared-db container directly. It exposes
        # /users which returns every user row.
        shared_db_url = os.getenv("SHARED_DB_URL", "http://find-shared-db:6000")
        resp = requests.get(f"{shared_db_url}/users", timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException:
        return {}
    body = resp.json()
    if not isinstance(body, list):
        return {}
    wanted = set(int(i) for i in user_ids)
    return {u["user_id"]: u for u in body if u.get("user_id") in wanted}


def get_user(user_id: int) -> dict | None:
    try:
        shared_db_url = os.getenv("SHARED_DB_URL", "http://find-shared-db:6000")
        resp = requests.get(f"{shared_db_url}/users/{user_id}", timeout=TIMEOUT)
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    return resp.json()


def get_session_user(cookie_header: str) -> dict | None:
    """Validate a request Cookie against shared-api and return the user dict.

    Returns None on any failure (network error, no cookie, invalid cookie).
    """
    if not cookie_header:
        return None
    try:
        resp = requests.get(
            f"{SHARED_API_URL}/api/auth/session",
            headers={"Cookie": cookie_header},
            timeout=TIMEOUT,
        )
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    payload = resp.json() or {}
    return payload.get("user")
