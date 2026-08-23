import os

import requests


SHARED_DB_URL = os.getenv("SHARED_DB_URL", "http://localhost:16003")
REQUEST_TIMEOUT = 5  # seconds


def _validate_user(user: dict) -> tuple[bool, str]:
    if not isinstance(user.get("user_id"), int):
        return False, "user_id must be an integer"
    if not user.get("user_email"):
        return False, "user_email is required"
    if user.get("user_role") not in ("applicant", "staff"):
        return False, "user_role must be 'applicant' or 'staff'"
    return True, "ok"


def collect(app_dir, repo_root) -> tuple[bool, str]:
    """Collect live evidence from the shared database service over HTTP."""
    url = f"{SHARED_DB_URL}/users"
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        return False, (
            f"Shared database not reachable at {url} ({exc}). "
            "Start the stack with docker-compose up --build, then rerun the loop."
        )

    if resp.status_code != 200:
        return False, f"{url} returned HTTP {resp.status_code}"

    try:
        users = resp.json()
    except ValueError:
        return False, f"{url} did not return JSON"

    if len(users) != 10:
        return False, f"Expected 10 seed users, found {len(users)}"

    staff = [u for u in users if u.get("user_role") == "staff"]
    applicants = [u for u in users if u.get("user_role") == "applicant"]
    if len(staff) != 5 or len(applicants) != 5:
        return False, (
            f"Expected 5 staff and 5 applicants, found "
            f"{len(staff)} staff and {len(applicants)} applicants"
        )

    for user in users:
        ok, reason = _validate_user(user)
        if not ok:
            return False, reason

    return True, (
        "Database evidence: shared users table has 10 valid rows "
        "(5 staff, 5 applicants); fields include user_id, user_email, user_role, "
        "user_first_name, user_last_name."
    )
