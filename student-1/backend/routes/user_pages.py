"""User identity fragment routes (first/last name, on the shared users table)."""

import json
import os

from flask import Blueprint, make_response, request

from services import shared_api
from views.html_formatters import render_user_details_panel

user_bp = Blueprint("user_pages", __name__)

BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:16005")


def _cookie() -> str:
    return request.headers.get("Cookie", "")


@user_bp.get("/user")
def get_user_details():
    user = shared_api.get_session_user(_cookie())
    if not user:
        return {"error": "Not authenticated"}, 401
    return render_user_details_panel(user, backend_url=BACKEND_PUBLIC_URL), 200


@user_bp.put("/user")
def update_user_details():
    user = shared_api.get_session_user(_cookie())
    if not user:
        return {"error": "Not authenticated"}, 401

    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    if not first_name or not last_name:
        merged = dict(user, first_name=first_name, last_name=last_name)
        return render_user_details_panel(
            merged, backend_url=BACKEND_PUBLIC_URL, error="First name and last name are required."
        ), 200

    resp = shared_api.update_user_identity(_cookie(), first_name, last_name)
    if resp.status_code != 200:
        return render_user_details_panel(
            dict(user, first_name=first_name, last_name=last_name),
            backend_url=BACKEND_PUBLIC_URL, error="Failed to update details.",
        ), 200

    html = render_user_details_panel(dict(user, first_name=first_name, last_name=last_name), backend_url=BACKEND_PUBLIC_URL)
    response = make_response(html, 200)
    # userUpdated lets the navbar (outside this fragment's swap target) refresh
    # without a page reload.
    response.headers["HX-Trigger"] = json.dumps({
        "showToast": "Details updated.",
        "userUpdated": {"first_name": first_name, "last_name": last_name},
    })
    return response
