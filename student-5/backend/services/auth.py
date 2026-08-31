"""Session/auth helper for the Student-5 (Evaluation) backend.

``require_session`` forwards the session cookie/Authorization header to the
shared auth API and returns the authenticated user. Used by ``app.py`` and
the AI-Mode blueprint.
"""

import requests as http_requests
from flask import jsonify, request

from services.config import SHARED_API_URL


def require_session():
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
