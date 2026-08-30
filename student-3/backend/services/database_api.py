"""Data-access layer for the Application service.

Centralises all outbound HTTP calls to other microservices: the shared-api
(session validation), the shared users database, the postings database, the
student-1 profile/resume database, and this service's own database. Following
the repo convention, cross-student reads go frontend -> own backend -> other
student's DB service (never another student's backend).
"""

import base64

import requests
from flask import request

from config import (
    DATABASE_SERVICE_URL,
    POSTINGS_DB_URL,
    SHARED_API_URL,
    SHARED_DB_URL,
    STUDENT_1_DB_URL,
    TIMEOUT,
)


# --------------------------------------------------------------------------- #
# Session / cross-service helpers                                             #
# --------------------------------------------------------------------------- #

def get_session_user():
    cookie = request.headers.get("Cookie", "")
    if not cookie:
        return None
    try:
        resp = requests.get(f"{SHARED_API_URL}/api/auth/session",
                            headers={"Cookie": cookie}, timeout=TIMEOUT)
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    return (resp.json() or {}).get("user")


def get_user(user_id):
    try:
        resp = requests.get(f"{SHARED_DB_URL}/users/{user_id}", timeout=TIMEOUT)
    except requests.RequestException:
        return None
    return resp.json() if resp.status_code == 200 else None


def get_users_map(user_ids):
    if not user_ids:
        return {}
    try:
        resp = requests.get(f"{SHARED_DB_URL}/users", timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException:
        return {}
    body = resp.json()
    if not isinstance(body, list):
        return {}
    wanted = {int(i) for i in user_ids}
    return {u["user_id"]: u for u in body if u.get("user_id") in wanted}


def get_job_posting(job_posting_id):
    try:
        resp = requests.get(f"{POSTINGS_DB_URL}/job-postings/{job_posting_id}", timeout=TIMEOUT)
    except requests.RequestException:
        return None
    return resp.json() if resp.status_code == 200 else None


def get_postings_map(job_posting_ids):
    if not job_posting_ids:
        return {}
    try:
        resp = requests.get(f"{POSTINGS_DB_URL}/job-postings", timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException:
        return {}
    body = resp.json()
    if not isinstance(body, list):
        return {}
    wanted = {int(i) for i in job_posting_ids}
    return {p["JobPosting_Id"]: p for p in body if p.get("JobPosting_Id") in wanted}


# --------------------------------------------------------------------------- #
# Applications (this service's own database)                                  #
# --------------------------------------------------------------------------- #

def get_application(application_id):
    """Raw response for a single application (callers handle status codes)."""
    return requests.get(
        f"{DATABASE_SERVICE_URL}/applications/{application_id}", timeout=TIMEOUT
    )


# --------------------------------------------------------------------------- #
# Student-1 resume integration                                                #
# --------------------------------------------------------------------------- #
#
# Calls student-1's database microservice directly (frontend -> own backend ->
# other student's DB is the convention used throughout this repo - see
# student-2/4/5's APPLICATIONS_DB_URL). The DB
# service does no authentication itself, so ownership checks below are
# reimplemented here rather than delegated to student-1.

def get_profile_by_user_id(user_id):
    try:
        resp = requests.get(f"{STUDENT_1_DB_URL}/profiles/by-user/{user_id}", timeout=TIMEOUT)
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    return resp.json() or None


def _get_student1_profile(profile_id):
    try:
        resp = requests.get(f"{STUDENT_1_DB_URL}/profiles/{profile_id}", timeout=TIMEOUT)
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    return resp.json() or None


def _get_student1_resume_meta(resume_id):
    try:
        resp = requests.get(f"{STUDENT_1_DB_URL}/resumes/{resume_id}", timeout=TIMEOUT)
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    return resp.json() or None


def get_latest_profile_resume(user_id):
    """The applicant's single stored resume from their student-1 profile, if any."""
    profile = get_profile_by_user_id(user_id)
    if not profile:
        return None
    profile_id = profile.get("profile_id")
    if not profile_id:
        return None

    try:
        resp = requests.get(f"{STUDENT_1_DB_URL}/profiles/{profile_id}/resumes", timeout=TIMEOUT)
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None

    resumes = resp.json() or []
    if not resumes:
        return None
    latest = resumes[0]  # one resume per profile, enforced by student-1's UNIQUE constraint
    return {
        "resume_id": latest.get("resume_id"),
        "file_name": latest.get("file_name", "resume.pdf"),
        "file_type": latest.get("file_type", "application/pdf"),
        "uploaded_at": latest.get("uploaded_at", ""),
        "from_profile": True,
    }


def upload_application_resume(filename, mimetype, raw_bytes):
    """Upload a one-off resume for this application only - NOT the applicant's
    profile default resume. profile_id is left NULL on student-1's side;
    ownership is tracked via applications.user_id on this side instead."""
    payload = {
        "file_name": filename,
        "file_type": mimetype,
        "file_data": base64.b64encode(raw_bytes).decode("utf-8"),
    }
    try:
        resp = requests.post(f"{STUDENT_1_DB_URL}/resumes", json=payload, timeout=15)
    except requests.RequestException:
        return None
    if resp.status_code != 201:
        return None
    return (resp.json() or {}).get("resume_id")


def _user_owns_application_resume(user_id, resume_id):
    """True if resume_id is attached to one of user_id's own applications
    (covers application-only resumes, which have no profile_id to check)."""
    if user_id is None:
        return False
    try:
        resp = requests.get(f"{DATABASE_SERVICE_URL}/applications", params={"user_id": user_id}, timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException:
        return False
    return any(a.get("resume_id") == resume_id for a in (resp.json() or []))


def get_resume_metadata(resume_id, role, current_user_id=None):
    if not resume_id:
        return None
    meta = _get_student1_resume_meta(resume_id)
    if not meta:
        return None
    meta = dict(meta)

    if role == "staff":
        return meta

    profile_id = meta.get("profile_id")
    if profile_id is None:
        # Application-only resume (not linked to a profile): verify it belongs
        # to one of the caller's own applications instead of trusting the caller.
        if not _user_owns_application_resume(current_user_id, resume_id):
            return None
        return meta

    if current_user_id is None:
        return None
    profile = _get_student1_profile(profile_id)
    if not profile or profile.get("user_id") != current_user_id:
        return None
    meta["from_profile"] = True
    return meta


def download_resume_stream(resume_id, role, current_user_id=None):
    if role != "staff":
        allowed = get_resume_metadata(resume_id, role, current_user_id)
        if not allowed:
            return None
    return requests.get(f"{STUDENT_1_DB_URL}/resumes/{resume_id}/file", timeout=15, stream=True)
