"""HTTP client for the student-1 profile microservice.

Used to autofill the applicant apply form with the resume the candidate
already uploaded to their profile. When the applicant submits without picking
a new file, we copy the profile resume into the student-3 database so the
application row has its own ``Resume_Id`` (student-1 resumes stay private to
the applicant's profile feature).
"""

from __future__ import annotations

import os

import requests

STUDENT_1_BACKEND_URL = os.getenv(
    "STUDENT_1_BACKEND_URL", "http://find-student-1-backend:5001"
)
TIMEOUT = 5


def _forward(cookie: str) -> dict:
    return {"Cookie": cookie} if cookie else {}


def get_my_profile(cookie: str) -> dict | None:
    """Return the applicant's profile dict, or None if it can't be reached.

    The response shape from student-1's ``/api/profiles/me`` is
    ``{"profile": {..., "profile_id": int, "user_id": int}, "role": str, ...}``.
    """
    try:
        resp = requests.get(
            f"{STUDENT_1_BACKEND_URL}/api/profiles/me",
            headers=_forward(cookie),
            timeout=TIMEOUT,
        )
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    body = resp.json() or {}
    return body.get("profile")


def get_latest_profile_resume(cookie: str) -> dict | None:
    """Return the most recently uploaded resume attached to the applicant's
    profile, or None if none exists (or the profile service is unreachable).

    Returns a normalised dict with keys matching student-3's Resume shape:
        {"Resume_Filename": str, "Resume_MimeType": str,
         "Resume_SizeBytes": int, "profile_resume_id": int}
    """
    profile = get_my_profile(cookie)
    if not profile:
        return None
    profile_id = profile.get("profile_id")
    if not profile_id:
        return None
    try:
        resp = requests.get(
            f"{STUDENT_1_BACKEND_URL}/api/profiles/{profile_id}/resumes",
            headers=_forward(cookie),
            timeout=TIMEOUT,
        )
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    body = resp.json() or []
    if not isinstance(body, list) or not body:
        return None
    # Newest first — pick whichever has the latest uploaded_at timestamp.
    latest = max(body, key=lambda r: r.get("uploaded_at") or "")
    return {
        "profile_resume_id": latest.get("resume_id"),
        "Resume_Filename": latest.get("file_name", "resume.pdf"),
        "Resume_MimeType": latest.get("file_type", "application/pdf"),
        "Resume_SizeBytes": 0,  # not exposed by student-1's list endpoint
        "Resume_UploadedAt": latest.get("uploaded_at", ""),
        "from_profile": True,
    }


def download_profile_resume_bytes(cookie: str, profile_resume_id: int) -> tuple[bytes, str, str] | None:
    """Download a specific resume from the applicant's profile.

    Returns (raw_bytes, filename, mimetype) or None on failure.
    """
    try:
        resp = requests.get(
            f"{STUDENT_1_BACKEND_URL}/api/resumes/{profile_resume_id}/download",
            headers=_forward(cookie),
            timeout=15,
        )
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    mimetype = resp.headers.get("Content-Type", "application/pdf")
    # Try to extract filename from Content-Disposition; fall back to a stub.
    disposition = resp.headers.get("Content-Disposition", "")
    filename = "resume.pdf"
    if 'filename="' in disposition:
        filename = disposition.split('filename="', 1)[1].split('"', 1)[0]
    elif "filename=" in disposition:
        filename = disposition.split("filename=", 1)[1].split(";", 1)[0].strip()
    return resp.content, filename, mimetype
