"""Shared helpers for the route blueprints.

Small HTTP-response builders (auth failures, toasts, redirects, JSON context
envelopes) plus loaders/validators reused across applicant, staff, resume and
AI-mode routes.
"""

import json

import requests
from flask import jsonify, make_response

from config import (
    ALLOWED_RESUME_EXTS,
    ALLOWED_RESUME_MIME,
    FRONTEND_PUBLIC_URL,
    MAX_RESUME_BYTES,
    _DB_UNAVAILABLE,
)
from services import database_api
from views.html_formatters import render_message


# --------------------------------------------------------------------------- #
# Response helpers                                                            #
# --------------------------------------------------------------------------- #

def unauthorized():
    return render_message("Please log in first.", "error"), 401


def forbidden(msg="Not allowed."):
    return render_message(msg, "error"), 200


def toast_response(message, kind="success"):
    resp = make_response("", 200)
    event = "showErrorToast" if kind == "error" else "showToast"
    resp.headers["HX-Trigger"] = json.dumps({event: message})
    return resp


def redirect_response(path, toast=None):
    url = f"{FRONTEND_PUBLIC_URL}{path}"
    if toast:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}toast={requests.utils.quote(toast)}"
    resp = make_response("", 200)
    resp.headers["HX-Redirect"] = url
    return resp


def context_error(message, kind="error", status=200):
    return jsonify({"ok": False, "kind": kind, "message": message}), status


def context_ok(data):
    return jsonify({"ok": True, "data": data}), 200


# --------------------------------------------------------------------------- #
# Validation / loading helpers                                               #
# --------------------------------------------------------------------------- #

def validate_resume(file_storage):
    filename = (file_storage.filename or "").lower()
    if not any(filename.endswith(ext) for ext in ALLOWED_RESUME_EXTS):
        return "Resume must be a PDF file."
    mimetype = (file_storage.mimetype or "").lower()
    if mimetype and mimetype not in ALLOWED_RESUME_MIME:
        if not any(filename.endswith(ext) for ext in ALLOWED_RESUME_EXTS):
            return "Resume must be a PDF file."
    try:
        file_storage.stream.seek(0, 2)
        size = file_storage.stream.tell()
        file_storage.stream.seek(0)
    except Exception:
        size = 0
    if size > MAX_RESUME_BYTES:
        return "Resume must be 5 MB or smaller."
    return None


def load_application(application_id):
    try:
        resp = database_api.get_application(application_id)
        if resp.status_code == 404:
            return None, (render_message("Application not found.", "error"), 200)
        resp.raise_for_status()
    except requests.RequestException:
        return None, (render_message(_DB_UNAVAILABLE, "error"), 200)
    return resp.json(), None


def load_resume(resume_id, role, current_user_id=None):
    if not resume_id:
        return None
    return database_api.get_resume_metadata(int(resume_id), role, current_user_id)
