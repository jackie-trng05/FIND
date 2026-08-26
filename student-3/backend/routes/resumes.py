"""Resume download route (streams the file from student-1's database)."""

import requests
from flask import Blueprint, Response, stream_with_context

from services.database_api import download_resume_stream, get_session_user

resumes_bp = Blueprint("resumes", __name__)


@resumes_bp.get("/api/resumes/<int:resume_id>/download")
def download_resume(resume_id):
    user = get_session_user()
    if not user:
        return "Unauthorized", 401
    try:
        upstream = download_resume_stream(
            resume_id,
            user.get("role", "applicant"),
            user.get("user_id"),
        )
    except requests.RequestException:
        return "Backend unavailable", 502
    if upstream is None:
        return "Forbidden", 403
    if upstream.status_code == 404:
        return "Resume not found", 404
    if upstream.status_code != 200:
        return "Backend error", 502

    headers = {"Content-Type": upstream.headers.get("Content-Type", "application/octet-stream")}
    disposition = upstream.headers.get("Content-Disposition")
    if disposition:
        headers["Content-Disposition"] = disposition
    return Response(
        stream_with_context(upstream.iter_content(chunk_size=8192)),
        status=200, headers=headers,
    )
