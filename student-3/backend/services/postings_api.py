"""HTTP client for the student-2 job-postings database service.

Applications need to know the job title, description and requirements of the
posting they're linked to. The student-2 database is the source of truth, so
we call it directly by container name (student-2-db:6002 in Docker Compose).
"""

import os

import requests

POSTINGS_DB_URL = os.getenv("POSTINGS_DB_URL", "http://student-2-db:6002")
TIMEOUT = 5


def list_job_postings(status: str | None = "Published") -> list[dict]:
    """Return a list of job postings, defaulting to Published only."""
    params = {"status": status} if status else {}
    try:
        resp = requests.get(
            f"{POSTINGS_DB_URL}/job-postings", params=params, timeout=TIMEOUT
        )
        resp.raise_for_status()
    except requests.RequestException:
        return []
    return resp.json() if isinstance(resp.json(), list) else []


def get_job_posting(job_posting_id: int) -> dict | None:
    try:
        resp = requests.get(
            f"{POSTINGS_DB_URL}/job-postings/{job_posting_id}", timeout=TIMEOUT
        )
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    return resp.json()


def get_postings_map(job_posting_ids: list[int]) -> dict[int, dict]:
    """Return {job_posting_id: posting_dict} for the given IDs.

    Uses a single list call so 20 applications don't cause 20 HTTP requests.
    Missing postings are simply omitted from the result.
    """
    if not job_posting_ids:
        return {}
    try:
        # No status filter -> we want Draft postings too (Withdrawn/Rejected
        # apps may still reference a posting that was later unpublished).
        resp = requests.get(
            f"{POSTINGS_DB_URL}/job-postings", timeout=TIMEOUT
        )
        resp.raise_for_status()
    except requests.RequestException:
        return {}
    body = resp.json()
    if not isinstance(body, list):
        return {}
    wanted = set(int(i) for i in job_posting_ids)
    return {p["JobPosting_Id"]: p for p in body if p.get("JobPosting_Id") in wanted}
