"""Normal-mode routes for the Student 5 (Evaluation) backend.

Evaluation CRUD (JSON for API callers, HTMX fragments/triggers for the UI)
plus the "applications ready for evaluation" listings.
"""

import json
from urllib.parse import quote

from flask import Blueprint, Response, jsonify, request

from services import database_api, integration_api
from services.config import FRONTEND_PUBLIC_URL
from views.html_formatters import render_eligible_rows, render_evaluations_rows

evaluations_bp = Blueprint("evaluations", __name__)

_INT_FIELDS = (
    "Application_Id",
    "Evaluation_TechnicalScore",
    "Evaluation_EducationScore",
    "Evaluation_CommunicationScore",
    "Evaluation_ProblemSolvingScore",
    "Evaluation_ProfessionalismScore",
)


def _require_staff():
    """Return (user, None) for authenticated staff, or (None, error_response)."""
    user, err = integration_api.require_session()
    if err:
        return None, err
    if user["role"] != "staff":
        return None, (jsonify({"error": "Staff access only"}), 403)
    return user, None


def _hx_trigger(triggers, status=200):
    """Empty response carrying an HX-Trigger header for the HTMX front-end."""
    resp = Response("", status=status)
    resp.headers["HX-Trigger"] = json.dumps(triggers)
    return resp


def _hx_redirect(url):
    """Empty response instructing the HTMX front-end to navigate to ``url``."""
    resp = Response("", status=200)
    resp.headers["HX-Redirect"] = url
    return resp


def _read_payload():
    """Read the request body from JSON or an HTMX form submission."""
    if request.is_json:
        return dict(request.get_json() or {})
    data = request.form.to_dict()
    for field in _INT_FIELDS:
        if data.get(field, "") != "":
            try:
                data[field] = int(data[field])
            except (TypeError, ValueError):
                pass
    return data


def _validation_error(msg):
    """Return a form-friendly (HTMX toast) or JSON validation error."""
    if request.headers.get("HX-Request"):
        return _hx_trigger({"showErrorToast": msg})
    return jsonify({"error": msg}), 400


def _finish_save(resp, data):
    """Shared response handling for create/update.

    For HTMX form submissions this folds the notify-on-submit step in and
    returns an HX-Redirect back to the list. JSON callers get the raw result.
    """
    if not request.headers.get("HX-Request"):
        return jsonify(resp.json()), resp.status_code

    if resp.status_code >= 400:
        detail = ""
        try:
            detail = (resp.json() or {}).get("error", "")
        except Exception:
            pass
        return _hx_trigger({"showErrorToast": detail or "Failed to save evaluation"})

    saved = {}
    try:
        saved = resp.json() or {}
    except Exception:
        pass

    rec = data.get("Evaluation_FinalRecommendation")
    application_id = data.get("Application_Id") or saved.get("Application_Id")
    if rec in ("Hire", "Reject"):
        action = "Hired" if rec == "Hire" else "Rejected"
        try:
            integration_api.apply_decision(application_id, action)
        except Exception:
            pass
        msg = f"Evaluation completed. Applicant has been marked {action}."
    else:
        integration_api.update_application_status(application_id, "Evaluation In Progress")
        msg = "Evaluation saved as draft."

    return _hx_redirect(f"{FRONTEND_PUBLIC_URL}/?toast=" + quote(msg))


def _fetch_evaluations(params):
    """Fetch evaluations from the DB service and enrich with applicant/job info."""
    resp = database_api.list_evaluations_response(params)
    evaluations = resp.json()

    evaluator_cache = {}
    for ev in evaluations:
        uid = ev.get("User_Id")
        if uid not in evaluator_cache:
            evaluator_cache[uid] = integration_api.evaluator_fields(uid)
        ev["evaluator_name"], ev["evaluator_number"] = evaluator_cache[uid]
        integration_api.enrich_evaluation(ev)

    return evaluations


def _evaluation_params():
    params = {}
    for key in ("status", "recommendation", "application_id"):
        if request.args.get(key):
            params[key] = request.args[key]
    return params


@evaluations_bp.get("/health")
def health():
    return jsonify({"status": "ok"})


# --- Evaluation CRUD ---

@evaluations_bp.get("/api/evaluations")
def list_evaluations():
    user, err = _require_staff()
    if err:
        return err
    return jsonify(_fetch_evaluations(_evaluation_params()))


@evaluations_bp.get("/api/evaluations/rows")
def list_evaluations_rows():
    """HTMX fragment: the evaluations table body."""
    user, err = _require_staff()
    if err:
        return err
    rows = render_evaluations_rows(_fetch_evaluations(_evaluation_params()))
    return Response(rows, mimetype="text/html")


@evaluations_bp.get("/api/evaluations/<int:evaluation_id>")
def get_evaluation(evaluation_id):
    user, err = integration_api.require_session()
    if err:
        return err
    if user["role"] != "staff":
        return jsonify({"error": "Staff access only"}), 403

    resp = database_api.get_evaluation_response(evaluation_id)
    if resp.status_code != 200:
        return jsonify(resp.json()), resp.status_code

    ev = resp.json()
    ev["evaluator_name"], ev["evaluator_number"] = integration_api.evaluator_fields(ev.get("User_Id"))
    integration_api.enrich_evaluation(ev, include_application_status=True)

    iv = integration_api.fetch_interview(ev["Application_Id"])
    if iv:
        ev["interview_id"] = iv.get("interview_id")
        notes = iv.get("interview_notes")
        if isinstance(notes, str):
            try:
                notes = json.loads(notes)
            except Exception:
                notes = None
        ev["interview_notes"] = notes

    return jsonify(ev)


@evaluations_bp.post("/api/evaluations")
def create_evaluation():
    user, err = _require_staff()
    if err:
        return err

    data = _read_payload()
    data["User_Id"] = user["user_id"]

    resp = database_api.create_evaluation(data)
    return _finish_save(resp, data)


@evaluations_bp.put("/api/evaluations/<int:evaluation_id>")
def update_evaluation(evaluation_id):
    user, err = _require_staff()
    if err:
        return err

    data = _read_payload()

    resp = database_api.update_evaluation(evaluation_id, data)
    return _finish_save(resp, data)


@evaluations_bp.delete("/api/evaluations/<int:evaluation_id>")
def delete_evaluation(evaluation_id):
    user, err = _require_staff()
    if err:
        return err

    # Capture the linked application before deleting so its status can be reverted.
    application_id = None
    try:
        get_resp = database_api.get_evaluation_response(evaluation_id, timeout=3)
        if get_resp.status_code == 200:
            application_id = get_resp.json().get("Application_Id")
    except Exception:
        pass

    resp = database_api.delete_evaluation(evaluation_id)

    # Deleting a draft frees the application to be evaluated again: revert its
    # status so it reappears under "Applications Ready for Evaluation".
    if resp.status_code < 400 and application_id is not None:
        integration_api.update_application_status(application_id, "Interview Completed")

    # HTMX list page: return an empty body (the row is removed) plus triggers to
    # toast and refresh the "ready for evaluation" panel.
    if request.headers.get("HX-Request") and resp.status_code < 400:
        return _hx_trigger({"showToast": "Evaluation deleted", "evaluationsChanged": True})

    return jsonify(resp.json()), resp.status_code


# --- Eligible applications (interviewed, no existing evaluation) ---

def _fetch_eligible():
    """Interview-completed applications that do not yet have an evaluation."""
    apps_resp = integration_api.list_applications_response()
    if apps_resp.status_code != 200:
        return []
    all_apps = apps_resp.json()

    interviewed = [a for a in all_apps
                   if a.get("application_status") == "Interview Completed"]

    evals_resp = database_api.list_evaluations_response(timeout=5)
    evaluated_app_ids = set()
    if evals_resp.status_code == 200:
        evaluated_app_ids = {e["Application_Id"] for e in evals_resp.json()}

    eligible = [a for a in interviewed if a.get("application_id") not in evaluated_app_ids]

    for a in eligible:
        integration_api.enrich_application(a)

    return eligible


@evaluations_bp.get("/api/eligible-applications")
def eligible_applications():
    user, err = _require_staff()
    if err:
        return err
    try:
        return jsonify(_fetch_eligible())
    except Exception:
        return jsonify([])


@evaluations_bp.get("/api/interview/<int:application_id>")
def get_interview_for_application(application_id):
    user, err = _require_staff()
    if err:
        return err
    iv = integration_api.fetch_interview(application_id)
    if not iv:
        return jsonify({"error": "No interview found"}), 404
    notes = iv.get("interview_notes")
    if isinstance(notes, str):
        try:
            notes = json.loads(notes)
        except Exception:
            notes = None
    iv["interview_notes"] = notes
    return jsonify(iv)


@evaluations_bp.get("/api/eligible-applications/rows")
def eligible_applications_rows():
    """HTMX fragment: the 'ready for evaluation' table body."""
    user, err = _require_staff()
    if err:
        return err
    try:
        apps = _fetch_eligible()
    except Exception:
        apps = []
    return Response(render_eligible_rows(apps), mimetype="text/html")
