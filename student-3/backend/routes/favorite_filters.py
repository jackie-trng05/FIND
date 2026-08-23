"""Staff favorite filter routes.

Staff can save the current filter query string as a "Favorite Filter" for
quick recall in later sessions.
"""

from __future__ import annotations

import requests
from flask import Blueprint, request

from services import database_api, shared_api
from views.html_formatters import render_favorite_filters, render_message

favorite_filters_bp = Blueprint("favorite_filters", __name__)


def _current_staff() -> dict | None:
    user = shared_api.get_session_user(request.headers.get("Cookie", ""))
    if not user or user.get("role") != "staff":
        return None
    return user


@favorite_filters_bp.get("/api/favorite-filters")
def list_filters():
    user = _current_staff()
    if not user:
        return render_message("Staff only.", "error"), 200
    try:
        resp = database_api.list_favorite_filters(user["user_id"])
        resp.raise_for_status()
    except requests.RequestException:
        return render_message("Database unavailable.", "error"), 200
    return render_favorite_filters(resp.json()), 200


@favorite_filters_bp.post("/api/favorite-filters")
def create_filter():
    user = _current_staff()
    if not user:
        return render_message("Staff only.", "error"), 200
    name = request.form.get("Filter_Name", "").strip()
    query = request.form.get("Filter_Query", "").strip()
    if not name:
        return render_message("Name is required.", "error"), 200
    payload = {
        "Staff_UserId": user["user_id"],
        "Filter_Name": name,
        "Filter_Query": query,
    }
    try:
        resp = database_api.create_favorite_filter(payload)
        resp.raise_for_status()
    except requests.RequestException:
        return render_message("Database unavailable.", "error"), 200
    # Return the refreshed list so the container can just innerHTML-swap.
    all_resp = database_api.list_favorite_filters(user["user_id"])
    return render_favorite_filters(all_resp.json()), 200


@favorite_filters_bp.delete("/api/favorite-filters/<int:filter_id>")
def delete_filter(filter_id: int):
    user = _current_staff()
    if not user:
        return render_message("Staff only.", "error"), 200
    try:
        database_api.delete_favorite_filter(filter_id)
    except requests.RequestException:
        return render_message("Database unavailable.", "error"), 200
    all_resp = database_api.list_favorite_filters(user["user_id"])
    return render_favorite_filters(all_resp.json()), 200
