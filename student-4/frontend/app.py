"""Student 4 — Interview scheduling frontend (Flask + HTMX).

Serves server-rendered pages that use HTMX to load fragments from the Student 4
backend. Authentication is handled entirely by the shared front-end runtime
(``/js/find-app.js``) against the shared authentication service — there is no
auth logic in this service.
"""

import os

from flask import Flask, render_template, send_from_directory

app = Flask(__name__, template_folder="templates")

LOCAL_CSS_DIR = os.path.join(os.path.dirname(__file__), "css")

# Browser-facing URLs (injected via the environment in docker-compose).
BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:16014")
SHARED_API_PUBLIC_URL = os.getenv("SHARED_API_PUBLIC_URL", "http://localhost:16002")
LOGIN_URL = os.getenv("LOGIN_URL", "http://localhost:16001/login")
HOME_URL = os.getenv("FIND_HOME_URL", "http://localhost:16001/dashboard")
# The Applications management screen lives in the Application service (Student 3).
APPLICATIONS_PUBLIC_URL = os.getenv("APPLICATIONS_PUBLIC_URL", "http://localhost:16010")


@app.context_processor
def inject_urls():
    return {
        "backend_url": BACKEND_PUBLIC_URL,
        "shared_api_url": SHARED_API_PUBLIC_URL,
        "login_url": LOGIN_URL,
        "home_url": HOME_URL,
        "applications_url": APPLICATIONS_PUBLIC_URL,
    }


@app.get("/css/<path:filename>")
def serve_css(filename):
    # Student-4-specific styles come from this service; the shared theme.css is
    # served from the mounted shared-css volume (single source of truth).
    if os.path.exists(os.path.join(LOCAL_CSS_DIR, filename)):
        return send_from_directory(LOCAL_CSS_DIR, filename)
    return send_from_directory("/app/shared-css", filename)


@app.get("/js/<path:filename>")
def serve_js(filename):
    # Shared front-end runtime served from the mounted shared-js volume.
    return send_from_directory("/app/shared-js", filename)


@app.get("/")
def calendar_page():
    return render_template("index.html", active_page="calendar")


@app.get("/list")
def list_page():
    return render_template("list.html", active_page="list")


@app.get("/applications")
def applications_page():
    return render_template("applications.html", active_page="applications", require_role="staff")


@app.get("/to-complete")
def to_complete_page():
    return render_template("to-complete.html", active_page="to-complete", require_role="staff")


@app.get("/schedule")
def schedule_page():
    return render_template("schedule.html", active_page="schedule", require_role="staff")


@app.get("/requests")
def requests_page():
    return render_template("requests.html", active_page="requests", require_role="applicant")


@app.get("/interview/<int:interview_id>")
def interview_detail_page(interview_id):
    return render_template("details.html", interview_id=interview_id, active_page="")


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "3004")))
