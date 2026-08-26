"""Profile fragment routes (create/view/edit/delete)."""

import json
import os

from flask import Blueprint, make_response, request

from services import database_api, shared_api
from views.html_formatters import render_message, render_profile_panel

profile_bp = Blueprint("profile_pages", __name__)

BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:16005")

EDITABLE_FIELDS = ("phone", "location", "professional_title", "summary", "interests")


def _cookie() -> str:
    return request.headers.get("Cookie", "")


def _payload_from_form() -> dict:
    return {field: request.form.get(field, "").strip() for field in EDITABLE_FIELDS}


def _get_my_profile(user_id: int) -> dict | None:
    resp = database_api.get_profile_by_user(user_id)
    return resp.json() if resp.status_code == 200 else None


def _panel_response(profile, role, *, message="", kind="error", toast=None, profile_changed=False):
    html = render_profile_panel(profile, backend_url=BACKEND_PUBLIC_URL, role=role, message=message, kind=kind)
    response = make_response(html, 200)
    triggers = {}
    if toast:
        triggers["showToast"] = toast
    if profile_changed:
        triggers["profileChanged"] = True
    if triggers:
        response.headers["HX-Trigger"] = json.dumps(triggers)
    return response


@profile_bp.get("/profile")
def get_profile_panel():
    user = shared_api.get_session_user(_cookie())
    if not user:
        return {"error": "Not authenticated"}, 401
    profile = _get_my_profile(user["user_id"])
    return _panel_response(profile, user["role"])


@profile_bp.post("/profile")
def create_profile():
    user = shared_api.get_session_user(_cookie())
    if not user:
        return {"error": "Not authenticated"}, 401

    payload = _payload_from_form()
    if not payload["phone"]:
        return _panel_response(None, user["role"], message="Phone is required.")

    payload["user_id"] = user["user_id"]
    resp = database_api.create_profile(payload)
    if resp.status_code not in (200, 201):
        error = (resp.json() or {}).get("error", "Failed to create profile.")
        return _panel_response(None, user["role"], message=error)

    profile = resp.json()
    return _panel_response(profile, user["role"], message="Profile created.", kind="success", profile_changed=True)


@profile_bp.put("/profile/<int:profile_id>")
def update_profile(profile_id):
    user = shared_api.get_session_user(_cookie())
    if not user:
        return {"error": "Not authenticated"}, 401

    check = database_api.get_profile(profile_id)
    if check.status_code != 200:
        return render_message("Profile not found.", "error"), 200
    if check.json()["user_id"] != user["user_id"]:
        return {"error": "Forbidden"}, 403

    payload = _payload_from_form()
    if not payload["phone"]:
        return _panel_response(check.json(), user["role"], message="Phone is required.")

    resp = database_api.update_profile(profile_id, payload)
    if resp.status_code != 200:
        error = (resp.json() or {}).get("error", "Failed to update profile.")
        return _panel_response(check.json(), user["role"], message=error)

    return _panel_response(resp.json(), user["role"], message="Profile updated.", kind="success")


@profile_bp.delete("/profile/<int:profile_id>")
def delete_profile(profile_id):
    user = shared_api.get_session_user(_cookie())
    if not user:
        return {"error": "Not authenticated"}, 401

    check = database_api.get_profile(profile_id)
    if check.status_code != 200:
        return render_message("Profile not found.", "error"), 200
    if check.json()["user_id"] != user["user_id"]:
        return {"error": "Forbidden"}, 403

    database_api.delete_profile(profile_id)
    return _panel_response(None, user["role"], toast="Profile deleted.", profile_changed=True)
