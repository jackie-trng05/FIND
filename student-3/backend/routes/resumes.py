"""Resume routes.

The database service stores resume BLOBs. The backend exposes a simple
download proxy so the frontend can link to it without needing to know the
internal Docker DNS.
"""

from __future__ import annotations

import requests
from flask import Blueprint, Response, stream_with_context

from services import database_api, shared_api

resumes_bp = Blueprint("resumes", __name__)


@resumes_bp.get("/api/resumes/<int:resume_id>/download")
def download_resume(resume_id: int):
    from flask import request
    user = shared_api.get_session_user(request.headers.get("Cookie", ""))
    if not user:
        return "Unauthorized", 401

    # Ownership check: applicants can only download their own resume; staff
    # can download any resume.
    meta_resp = database_api.get_resume(resume_id)
    if meta_resp.status_code == 404:
        return "Resume not found", 404
    if meta_resp.status_code != 200:
        return "Database unavailable", 502
    meta = meta_resp.json()
    if user.get("role") == "applicant" and meta.get("User_Id") != user["user_id"]:
        return "Forbidden", 403

    try:
        upstream = database_api.download_resume_stream(resume_id)
    except requests.RequestException:
        return "Database unavailable", 502
    if upstream.status_code != 200:
        return "Resume not found", 404

    headers = {
        "Content-Type": upstream.headers.get("Content-Type", meta["Resume_MimeType"]),
        "Content-Disposition": upstream.headers.get(
            "Content-Disposition",
            f'attachment; filename="{meta["Resume_Filename"]}"',
        ),
    }
    return Response(
        stream_with_context(upstream.iter_content(chunk_size=8192)),
        status=200,
        headers=headers,
    )
