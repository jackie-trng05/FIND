from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import requests as http_requests

from services.config import (
    DB_SERVICE_URL,
    APPLICATIONS_DB_URL,
    POSTINGS_DB_URL,
    SHARED_DB_URL,
)
from services.auth import require_session
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


# --- Evaluation CRUD ---

@app.get("/api/evaluations")
def list_evaluations():
    user, err = require_session()
    if err:
        return err
    if user["role"] != "staff":
        return jsonify({"error": "Staff access only"}), 403

    params = {}
    for key in ("status", "recommendation", "application_id"):
        if request.args.get(key):
            params[key] = request.args[key]

    resp = http_requests.get(f"{DB_SERVICE_URL}/evaluations", params=params)
    evaluations = resp.json()

    for ev in evaluations:
        try:
            app_resp = http_requests.get(f"{APPLICATIONS_DB_URL}/applications/{ev['Application_Id']}", timeout=3)
            if app_resp.status_code == 200:
                app_data = app_resp.json()
                ev["applicant_user_id"] = app_data.get("User_Id")
                ev["job_posting_id"] = app_data.get("JobPosting_Id")
                user_resp = http_requests.get(f"{SHARED_DB_URL}/users/{app_data.get('User_Id')}", timeout=3)
                if user_resp.status_code == 200:
                    u = user_resp.json()
                    ev["applicant_name"] = f"{u.get('user_first_name', '')} {u.get('user_last_name', '')}".strip()
                posting_resp = http_requests.get(f"{POSTINGS_DB_URL}/job-postings/{app_data.get('JobPosting_Id')}", timeout=3)
                if posting_resp.status_code == 200:
                    ev["job_title"] = posting_resp.json().get("Job_Title", "")
        except Exception:
            pass

    return jsonify(evaluations)


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
    try:
        app_resp = http_requests.get(f"{APPLICATIONS_DB_URL}/applications/{ev['Application_Id']}", timeout=3)
        if app_resp.status_code == 200:
            app_data = app_resp.json()
            ev["applicant_user_id"] = app_data.get("User_Id")
            ev["job_posting_id"] = app_data.get("JobPosting_Id")
            ev["application_status"] = app_data.get("Application_Status")
            user_resp = http_requests.get(f"{SHARED_DB_URL}/users/{app_data.get('User_Id')}", timeout=3)
            if user_resp.status_code == 200:
                u = user_resp.json()
                ev["applicant_name"] = f"{u.get('user_first_name', '')} {u.get('user_last_name', '')}".strip()
            posting_resp = http_requests.get(f"{POSTINGS_DB_URL}/job-postings/{app_data.get('JobPosting_Id')}", timeout=3)
            if posting_resp.status_code == 200:
                ev["job_title"] = posting_resp.json().get("Job_Title", "")
    except Exception:
        pass

    return jsonify(ev)


@app.post("/api/evaluations")
def create_evaluation():
    user, err = require_session()
    if err:
        return err
    if user["role"] != "staff":
        return jsonify({"error": "Staff access only"}), 403

    data = request.get_json() or {}
    data["Staff_Id"] = user["user_id"]

    if not data.get("HR_Staff_Name") or not str(data.get("HR_Staff_Name", "")).strip():
        return jsonify({"error": "HR Staff Name is required"}), 400
    if not data.get("HR_Staff_Number") or not str(data.get("HR_Staff_Number", "")).strip():
        return jsonify({"error": "HR Staff Number is required"}), 400

    resp = http_requests.post(f"{DB_SERVICE_URL}/evaluations", json=data)
    return jsonify(resp.json()), resp.status_code


@app.put("/api/evaluations/<int:evaluation_id>")
def update_evaluation(evaluation_id):
    user, err = require_session()
    if err:
        return err
    if user["role"] != "staff":
        return jsonify({"error": "Staff access only"}), 403

    data = request.get_json() or {}

    if "HR_Staff_Name" in data and not str(data["HR_Staff_Name"]).strip():
        return jsonify({"error": "HR Staff Name is required"}), 400
    if "HR_Staff_Number" in data and not str(data["HR_Staff_Number"]).strip():
        return jsonify({"error": "HR Staff Number is required"}), 400

    resp = http_requests.put(f"{DB_SERVICE_URL}/evaluations/{evaluation_id}", json=data)
    return jsonify(resp.json()), resp.status_code


@app.delete("/api/evaluations/<int:evaluation_id>")
def delete_evaluation(evaluation_id):
    user, err = require_session()
    if err:
        return err
    if user["role"] != "staff":
        return jsonify({"error": "Staff access only"}), 403

    resp = http_requests.delete(f"{DB_SERVICE_URL}/evaluations/{evaluation_id}")
    return jsonify(resp.json()), resp.status_code


# --- Eligible applications (interviewed, no existing evaluation) ---

@app.get("/api/eligible-applications")
def eligible_applications():
    user, err = require_session()
    if err:
        return err
    if user["role"] != "staff":
        return jsonify({"error": "Staff access only"}), 403

    try:
        apps_resp = http_requests.get(f"{APPLICATIONS_DB_URL}/applications", timeout=5)
        if apps_resp.status_code != 200:
            return jsonify([])
        all_apps = apps_resp.json()

        interviewed = [a for a in all_apps
                       if a.get("Application_Status") in ("Interview Completed", "Interviewed")]

        evals_resp = http_requests.get(f"{DB_SERVICE_URL}/evaluations", timeout=5)
        evaluated_app_ids = set()
        if evals_resp.status_code == 200:
            evaluated_app_ids = {e["Application_Id"] for e in evals_resp.json()}

        eligible = [a for a in interviewed if a.get("Application_Id") not in evaluated_app_ids]

        for a in eligible:
            try:
                user_resp = http_requests.get(f"{SHARED_DB_URL}/users/{a.get('User_Id')}", timeout=3)
                if user_resp.status_code == 200:
                    u = user_resp.json()
                    a["applicant_name"] = f"{u.get('user_first_name', '')} {u.get('user_last_name', '')}".strip()
                posting_resp = http_requests.get(f"{POSTINGS_DB_URL}/job-postings/{a.get('JobPosting_Id')}", timeout=3)
                if posting_resp.status_code == 200:
                    a["job_title"] = posting_resp.json().get("Job_Title", "")
            except Exception:
                pass

        return jsonify(eligible)
    except Exception:
        return jsonify([])


# --- Notification (SMTP stub) ---

@app.post("/api/evaluations/<int:evaluation_id>/notify")
def send_notification(evaluation_id):
    user, err = require_session()
    if err:
        return err
    if user["role"] != "staff":
        return jsonify({"error": "Staff access only"}), 403

    data = request.get_json() or {}
    action = data.get("action")
    if action not in ("Hired", "Rejected"):
        return jsonify({"error": "Action must be Hired or Rejected"}), 400

    ev_resp = http_requests.get(f"{DB_SERVICE_URL}/evaluations/{evaluation_id}")
    if ev_resp.status_code != 200:
        return jsonify({"error": "Evaluation not found"}), 404
    ev = ev_resp.json()

    try:
        app_resp = http_requests.get(f"{APPLICATIONS_DB_URL}/applications/{ev['Application_Id']}", timeout=3)
        if app_resp.status_code == 200:
            app_data = app_resp.json()
            new_status = "Hired" if action == "Hired" else "Rejected"
            http_requests.put(
                f"{APPLICATIONS_DB_URL}/applications/{ev['Application_Id']}",
                json={"Application_Status": new_status}, timeout=5
            )

            user_resp = http_requests.get(f"{SHARED_DB_URL}/users/{app_data.get('User_Id')}", timeout=3)
            applicant_email = ""
            if user_resp.status_code == 200:
                applicant_email = user_resp.json().get("user_email", "")

            return jsonify({
                "message": f"Application status updated to {new_status}. Notification would be sent to {applicant_email}.",
                "status": new_status,
                "email": applicant_email
            })
    except Exception as e:
        return jsonify({"error": f"Failed to update application: {str(e)}"}), 500

    return jsonify({"error": "Could not process notification"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005, debug=True)
