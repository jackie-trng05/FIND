from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import json
import os
from urllib.parse import quote
import requests as http_requests

from services.config import (
    DB_SERVICE_URL,
    APPLICATIONS_DB_URL,
    INTERVIEWS_DB_URL,
    POSTINGS_DB_URL,
    SHARED_DB_URL,
)
from services.auth import require_session
from views.html_formatters import render_evaluations_rows, render_eligible_rows
from routes.ai_mode import ai_mode_bp


app = Flask(__name__)

frontend_origin = os.environ.get("FRONTEND_PUBLIC_URL", "http://localhost:16016")
CORS(app, resources={r"/api/*": {"origins": [frontend_origin, "http://localhost:16016"]}},
     supports_credentials=True,
     expose_headers=["HX-Redirect", "HX-Trigger"])

app.register_blueprint(ai_mode_bp)


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


def _require_staff():
    """Return (user, None) for authenticated staff, or (None, error_response)."""
    user, err = require_session()
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


_INT_FIELDS = (
    "Application_Id",
    "Evaluation_TechnicalScore",
    "Evaluation_EducationScore",
    "Evaluation_CommunicationScore",
    "Evaluation_ProblemSolvingScore",
    "Evaluation_ProfessionalismScore",
)


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


def _update_application_status(application_id, new_status):
    """Set the linked application's status (best-effort)."""
    try:
        http_requests.put(
            f"{APPLICATIONS_DB_URL}/applications/{application_id}",
            json={"application_status": new_status}, timeout=5,
        )
    except Exception:
        pass


def _fetch_interview(application_id):
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


def _apply_decision(application_id, action):
    """Update a linked application's status to Hired or Rejected."""
    new_status = "Hired" if action == "Hired" else "Rejected"
    try:
        http_requests.put(
            f"{APPLICATIONS_DB_URL}/applications/{application_id}",
            json={"application_status": new_status}, timeout=5,
        )
    except Exception:
        pass


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
            _apply_decision(application_id, action)
        except Exception:
            pass
        msg = f"Evaluation completed. Applicant has been marked {action}."
    else:
        _update_application_status(application_id, "Evaluation In Progress")
        msg = "Evaluation saved as draft."

    return _hx_redirect(f"{frontend_origin}/?toast=" + quote(msg))


def _evaluator_fields(user_id):
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


def _fetch_evaluations(params):
    """Fetch evaluations from the DB service and enrich with applicant/job info."""
    resp = http_requests.get(f"{DB_SERVICE_URL}/evaluations", params=params)
    evaluations = resp.json()

    evaluator_cache = {}
    for ev in evaluations:
        uid = ev.get("User_Id")
        if uid not in evaluator_cache:
            evaluator_cache[uid] = _evaluator_fields(uid)
        ev["evaluator_name"], ev["evaluator_number"] = evaluator_cache[uid]
        try:
            app_resp = http_requests.get(f"{APPLICATIONS_DB_URL}/applications/{ev['Application_Id']}", timeout=3)
            if app_resp.status_code == 200:
                app_data = app_resp.json()
                ev["applicant_user_id"] = app_data.get("user_id")
                ev["job_posting_id"] = app_data.get("job_posting_id")
                user_resp = http_requests.get(f"{SHARED_DB_URL}/users/{app_data.get('user_id')}", timeout=3)
                if user_resp.status_code == 200:
                    u = user_resp.json()
                    ev["applicant_name"] = f"{u.get('user_first_name', '')} {u.get('user_last_name', '')}".strip()
                posting_resp = http_requests.get(f"{POSTINGS_DB_URL}/job-postings/{app_data.get('job_posting_id')}", timeout=3)
                if posting_resp.status_code == 200:
                    ev["job_title"] = posting_resp.json().get("Job_Title", "")
        except Exception:
            pass

    return evaluations


def _evaluation_params():
    params = {}
    for key in ("status", "recommendation", "application_id"):
        if request.args.get(key):
            params[key] = request.args[key]
    return params


# --- Evaluation CRUD ---

@app.get("/api/evaluations")
def list_evaluations():
    user, err = _require_staff()
    if err:
        return err
    return jsonify(_fetch_evaluations(_evaluation_params()))


@app.get("/api/evaluations/rows")
def list_evaluations_rows():
    """HTMX fragment: the evaluations table body."""
    user, err = _require_staff()
    if err:
        return err
    rows = render_evaluations_rows(_fetch_evaluations(_evaluation_params()))
    return Response(rows, mimetype="text/html")


@app.get("/api/evaluations/<int:evaluation_id>")
def get_evaluation(evaluation_id):
    user, err = require_session()
    if err:
        return err
    if user["role"] != "staff":
        return jsonify({"error": "Staff access only"}), 403

    resp = http_requests.get(f"{DB_SERVICE_URL}/evaluations/{evaluation_id}")
    if resp.status_code != 200:
        return jsonify(resp.json()), resp.status_code

    ev = resp.json()
    ev["evaluator_name"], ev["evaluator_number"] = _evaluator_fields(ev.get("User_Id"))
    try:
        app_resp = http_requests.get(f"{APPLICATIONS_DB_URL}/applications/{ev['Application_Id']}", timeout=3)
        if app_resp.status_code == 200:
            app_data = app_resp.json()
            ev["applicant_user_id"] = app_data.get("user_id")
            ev["job_posting_id"] = app_data.get("job_posting_id")
            ev["application_status"] = app_data.get("application_status")
            user_resp = http_requests.get(f"{SHARED_DB_URL}/users/{app_data.get('user_id')}", timeout=3)
            if user_resp.status_code == 200:
                u = user_resp.json()
                ev["applicant_name"] = f"{u.get('user_first_name', '')} {u.get('user_last_name', '')}".strip()
            posting_resp = http_requests.get(f"{POSTINGS_DB_URL}/job-postings/{app_data.get('job_posting_id')}", timeout=3)
            if posting_resp.status_code == 200:
                ev["job_title"] = posting_resp.json().get("Job_Title", "")
    except Exception:
        pass

    iv = _fetch_interview(ev["Application_Id"])
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


@app.post("/api/evaluations")
def create_evaluation():
    user, err = _require_staff()
    if err:
        return err

    data = _read_payload()
    data["User_Id"] = user["user_id"]

    resp = http_requests.post(f"{DB_SERVICE_URL}/evaluations", json=data)
    return _finish_save(resp, data)


@app.put("/api/evaluations/<int:evaluation_id>")
def update_evaluation(evaluation_id):
    user, err = _require_staff()
    if err:
        return err

    data = _read_payload()

    resp = http_requests.put(f"{DB_SERVICE_URL}/evaluations/{evaluation_id}", json=data)
    return _finish_save(resp, data)


@app.delete("/api/evaluations/<int:evaluation_id>")
def delete_evaluation(evaluation_id):
    user, err = _require_staff()
    if err:
        return err

    # Capture the linked application before deleting so its status can be reverted.
    application_id = None
    try:
        get_resp = http_requests.get(f"{DB_SERVICE_URL}/evaluations/{evaluation_id}", timeout=3)
        if get_resp.status_code == 200:
            application_id = get_resp.json().get("Application_Id")
    except Exception:
        pass

    resp = http_requests.delete(f"{DB_SERVICE_URL}/evaluations/{evaluation_id}")

    # Deleting a draft frees the application to be evaluated again: revert its
    # status so it reappears under "Applications Ready for Evaluation".
    if resp.status_code < 400 and application_id is not None:
        _update_application_status(application_id, "Interview Completed")

    # HTMX list page: return an empty body (the row is removed) plus triggers to
    # toast and refresh the "ready for evaluation" panel.
    if request.headers.get("HX-Request") and resp.status_code < 400:
        return _hx_trigger({"showToast": "Evaluation deleted", "evaluationsChanged": True})

    return jsonify(resp.json()), resp.status_code


# --- Eligible applications (interviewed, no existing evaluation) ---

def _fetch_eligible():
    """Interview-completed applications that do not yet have an evaluation."""
    apps_resp = http_requests.get(f"{APPLICATIONS_DB_URL}/applications", timeout=5)
    if apps_resp.status_code != 200:
        return []
    all_apps = apps_resp.json()

    interviewed = [a for a in all_apps
                   if a.get("application_status") == "Interview Completed"]

    evals_resp = http_requests.get(f"{DB_SERVICE_URL}/evaluations", timeout=5)
    evaluated_app_ids = set()
    if evals_resp.status_code == 200:
        evaluated_app_ids = {e["Application_Id"] for e in evals_resp.json()}

    eligible = [a for a in interviewed if a.get("application_id") not in evaluated_app_ids]

    for a in eligible:
        try:
            user_resp = http_requests.get(f"{SHARED_DB_URL}/users/{a.get('user_id')}", timeout=3)
            if user_resp.status_code == 200:
                u = user_resp.json()
                a["applicant_name"] = f"{u.get('user_first_name', '')} {u.get('user_last_name', '')}".strip()
            posting_resp = http_requests.get(f"{POSTINGS_DB_URL}/job-postings/{a.get('job_posting_id')}", timeout=3)
            if posting_resp.status_code == 200:
                a["job_title"] = posting_resp.json().get("Job_Title", "")
        except Exception:
            pass

    return eligible


@app.get("/api/eligible-applications")
def eligible_applications():
    user, err = _require_staff()
    if err:
        return err
    try:
        return jsonify(_fetch_eligible())
    except Exception:
        return jsonify([])


@app.get("/api/interview/<int:application_id>")
def get_interview_for_application(application_id):
    user, err = _require_staff()
    if err:
        return err
    iv = _fetch_interview(application_id)
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


@app.get("/api/eligible-applications/rows")
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5005")), debug=True)
