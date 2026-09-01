"""Cross-service HTTP client for the shared-api service.

Session validation and user-identity updates live in the shared service; this
module forwards the caller's session cookie to it and returns the result.
"""

import requests
from flask import request

from services.config import SHARED_API_URL, TIMEOUT


def get_session_user() -> dict | None:
    """Return the currently logged-in user dict, or None if unauthenticated."""
    cookie = request.headers.get("Cookie", "")
    if not cookie:
        return None
    try:
        resp = requests.get(
            f"{SHARED_API_URL}/api/auth/session", headers={"Cookie": cookie}, timeout=TIMEOUT
        )
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    return resp.json().get("user")


def update_user_identity(cookie: str, first_name: str, last_name: str) -> requests.Response:
    return requests.put(
        f"{SHARED_API_URL}/api/auth/user",
        json={"first_name": first_name, "last_name": last_name},
        headers={"Cookie": cookie},
        timeout=TIMEOUT,
    )
