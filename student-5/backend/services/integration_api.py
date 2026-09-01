"""Cross-service HTTP client for the Evaluation service.

Session validation goes to the shared auth API; everything else talks directly
to the other students' database services (never their backends): applications
(Student 3), interviews (Student 4), job postings (Student 2) and the shared
users database. All lookups are best-effort so a missing service degrades to
empty values rather than failing the request.
"""

import requests as http_requests
from flask import jsonify, request

from services.config import (
    APPLICATIONS_DB_URL,
    INTERVIEWS_DB_URL,
    POSTINGS_DB_URL,
    SHARED_API_URL,
    SHARED_DB_URL,
)


# --------------------------------------------------------------------------- #
# Session (shared authentication service)                                     #
# --------------------------------------------------------------------------- #

def require_session():
    """Return (user, None) for a valid session, or (None, error_response)."""
    cookie = request.headers.get("Cookie", "")
    auth_header = request.headers.get("Authorization", "")
    headers = {}
    if cookie:
        headers["Cookie"] = cookie
    if auth_header:
        headers["Authorization"] = auth_header
    if not headers:
        return None, (jsonify({"error": "Not authenticated"}), 401)
    resp = http_requests.get(f"{SHARED_API_URL}/api/auth/session", headers=headers)
    if resp.status_code != 200:
        return None, (jsonify({"error": "Invalid or expired session"}), 401)
    return resp.json()["user"], None


# --------------------------------------------------------------------------- #
# Applications (Student 3 DB)                                                 #
# --------------------------------------------------------------------------- #

def update_application_status(application_id, new_status):
    """Set the linked application's status (best-effort)."""
    try:
        http_requests.put(
            f"{APPLICATIONS_DB_URL}/applications/{application_id}",
            json={"application_status": new_status}, timeout=5,
        )
    except Exception:
        pass


def apply_decision(application_id, action):
    """Update a linked application's status to Hired or Rejected."""
    new_status = "Hired" if action == "Hired" else "Rejected"
    try:
        http_requests.put(
            f"{APPLICATIONS_DB_URL}/applications/{application_id}",
            json={"application_status": new_status}, timeout=5,
        )
    except Exception:
        pass


def list_applications_response():
    return http_requests.get(f"{APPLICATIONS_DB_URL}/applications", timeout=5)


# --------------------------------------------------------------------------- #
# Interviews (Student 4 DB)                                                   #
# --------------------------------------------------------------------------- #

def fetch_interview(application_id):
    """Find the completed interview for an application (best-effort)."""
    try:
        resp = http_requests.get(f"{INTERVIEWS_DB_URL}/interviews", timeout=3)
        if resp.status_code == 200:
            for iv in resp.json():
                if iv.get("application_id") == application_id:
                    return iv
    except Exception:
        pass
    return None


# --------------------------------------------------------------------------- #
# Users (shared DB) and job postings (Student 2 DB)                           #
# --------------------------------------------------------------------------- #

def evaluator_fields(user_id):
    """Derive the evaluator's display name and staff number (HR-00N) from User_Id."""
    if user_id is None:
        return "", ""
    number = f"HR-{int(user_id):03d}"
    name = ""
    try:
        resp = http_requests.get(f"{SHARED_DB_URL}/users/{user_id}", timeout=3)
        if resp.status_code == 200:
            u = resp.json()
            name = f"{u.get('user_first_name', '')} {u.get('user_last_name', '')}".strip()
    except Exception:
        pass
    return name, number


def enrich_evaluation(ev, include_application_status=False):
    """Add applicant/job-posting details onto an evaluation row (best-effort)."""
    try:
        app_resp = http_requests.get(
            f"{APPLICATIONS_DB_URL}/applications/{ev['Application_Id']}", timeout=3
        )
        if app_resp.status_code == 200:
            app_data = app_resp.json()
            ev["applicant_user_id"] = app_data.get("user_id")
            ev["job_posting_id"] = app_data.get("job_posting_id")
            if include_application_status:
                ev["application_status"] = app_data.get("application_status")
            user_resp = http_requests.get(
                f"{SHARED_DB_URL}/users/{app_data.get('user_id')}", timeout=3
            )
            if user_resp.status_code == 200:
                u = user_resp.json()
                ev["applicant_name"] = f"{u.get('user_first_name', '')} {u.get('user_last_name', '')}".strip()
            posting_resp = http_requests.get(
                f"{POSTINGS_DB_URL}/job-postings/{app_data.get('job_posting_id')}", timeout=3
            )
            if posting_resp.status_code == 200:
                ev["job_title"] = posting_resp.json().get("Job_Title", "")
    except Exception:
        pass
    return ev


def enrich_application(a):
    """Add the applicant name and job title onto an application row."""
    try:
        user_resp = http_requests.get(f"{SHARED_DB_URL}/users/{a.get('user_id')}", timeout=3)
        if user_resp.status_code == 200:
            u = user_resp.json()
            a["applicant_name"] = f"{u.get('user_first_name', '')} {u.get('user_last_name', '')}".strip()
        posting_resp = http_requests.get(
            f"{POSTINGS_DB_URL}/job-postings/{a.get('job_posting_id')}", timeout=3
        )
        if posting_resp.status_code == 200:
            a["job_title"] = posting_resp.json().get("Job_Title", "")
    except Exception:
        pass
    return a
