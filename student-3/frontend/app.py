"""Student 3 Frontend microservice (Application Management).

A small Flask server that renders the HTMX pages. The backend URL (used by
all HTMX ``hx-*`` attributes in the browser) is injected from an environment
variable so the same image works in any environment.

Pages:
  /                                  Applicant My Applications / Staff All Applications
  /apply/<job_posting_id>             Applicant apply / edit-draft form
  /applications/<application_id>      Applicant application detail page
  /applications/<application_id>/edit Applicant edit-draft page (Draft only)
  /staff/applications/<id>            Staff candidate profile page

Container port: 3003 (host port 16010 per the canonical port table).
"""

import os
from datetime import date, datetime

import requests
from flask import Flask, make_response, render_template, request, send_from_directory

app = Flask(__name__, template_folder="templates")
LOCAL_CSS_DIR = os.path.join(os.path.dirname(__file__), "css")


@app.get("/css/<path:filename>")
def serve_css(filename):
    # Local styles.css is served from this service; the shared theme.css comes
    # from the mounted shared-css volume (single source of truth).
    if os.path.exists(os.path.join(LOCAL_CSS_DIR, filename)):
        return send_from_directory(LOCAL_CSS_DIR, filename)
    return send_from_directory("/app/shared-css", filename)


@app.get("/js/<path:filename>")
def serve_js(filename):
    # Shared front-end runtime served from the mounted shared-js volume.
    return send_from_directory("/app/shared-js", filename)


# Browser-facing URLs.
BACKEND_PUBLIC_URL = os.environ["BACKEND_PUBLIC_URL"]
SHARED_API_PUBLIC_URL = os.environ["SHARED_API_PUBLIC_URL"]
LOGIN_URL = os.environ["LOGIN_URL"]
HOME_URL = os.environ["FIND_HOME_URL"]
JOB_POSTINGS_URL = os.environ["JOB_POSTINGS_URL"]

# Internal backend service URL for server-side context fetches.
BACKEND_SERVICE_URL = os.environ["BACKEND_SERVICE_URL"]
PORT = int(os.getenv("PORT", "3003"))
TIMEOUT = 8


STATUS_CLASS = {
    "Draft": "badge-warning",
    "Submitted": "badge-info",
    "Shortlisted": "badge-accent",
    "Interview Requested": "badge-warning",
    "Interview Scheduled": "badge-info",
    "Interview Completed": "badge-accent",
    "Evaluation Completed": "badge-accent",
    "Hired": "badge-success",
    "Rejected": "badge-danger",
    "Withdrawn": "badge-muted",
}


def format_date(value, fallback="-"):
    if not value:
        return fallback
    try:
        if len(value) == 10:
            return date.fromisoformat(value).strftime("%d %b %Y")
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%d %b %Y")
    except ValueError:
        return value


def requirements_list(text):
    items = []
    for line in str(text or "").splitlines():
        item = line.strip().lstrip("-•* ").strip()
        if item:
            items.append(item)
    return items


def _backend_get(path, params=None):
    headers = {}
    cookie = request.headers.get("Cookie", "")
    if cookie:
        headers["Cookie"] = cookie
    return requests.get(
        f"{BACKEND_SERVICE_URL}{path}",
        params=params,
        headers=headers,
        timeout=TIMEOUT,
    )


def _render_fragment_error(message, status=200):
    return make_response(
        f'<div class="alert alert-error">{message}</div>',
        status,
    )


def _context(**extra):
    ctx = {
        "backend_url": BACKEND_PUBLIC_URL,
        "shared_api_public_url": SHARED_API_PUBLIC_URL,
        "login_url": LOGIN_URL,
        "home_url": HOME_URL,
        "job_postings_url": JOB_POSTINGS_URL,
    }
    ctx.update(extra)
    return ctx


@app.get("/")
def index():
    return render_template("list.html", **_context())


@app.get("/apply/<int:job_posting_id>")
def apply(job_posting_id: int):
    return render_template("apply.html", **_context(job_posting_id=job_posting_id))


@app.get("/applications/<int:application_id>")
def application_detail(application_id: int):
    return render_template("detail.html", **_context(application_id=application_id))


@app.get("/staff/applications/<int:application_id>")
def staff_candidate_profile(application_id: int):
    return render_template(
        "candidate.html", **_context(application_id=application_id)
    )


@app.get("/fragments/apply/<int:job_posting_id>")
def apply_fragment(job_posting_id: int):
    try:
        resp = _backend_get(f"/api/context/apply/{job_posting_id}")
    except requests.RequestException:
        return _render_fragment_error("Backend unavailable.")
    if resp.status_code == 401:
        return _render_fragment_error("Please log in first.", status=401)
    if resp.status_code != 200:
        return _render_fragment_error("Could not load application form.")

    body = resp.json() or {}
    if not body.get("ok"):
        kind = body.get("kind", "error")
        klass = "alert-error" if kind == "error" else "text-sm"
        return f'<div class="alert {klass}">{body.get("message", "Could not load form.")}</div>'

    return render_template(
        "fragments/apply_form.html",
        **_context(
            data=body["data"],
            status_class=STATUS_CLASS,
            format_date=format_date,
            requirements_list=requirements_list,
        ),
    )


@app.get("/fragments/applications/<int:application_id>/detail")
def detail_fragment(application_id: int):
    try:
        resp = _backend_get(f"/api/context/applications/{application_id}/detail")
    except requests.RequestException:
        return _render_fragment_error("Backend unavailable.")
    if resp.status_code == 401:
        return _render_fragment_error("Please log in first.", status=401)
    if resp.status_code != 200:
        return _render_fragment_error("Could not load application details.")

    body = resp.json() or {}
    if not body.get("ok"):
        kind = body.get("kind", "error")
        klass = "alert-error" if kind == "error" else "text-sm"
        return f'<div class="alert {klass}">{body.get("message", "Could not load details.")}</div>'

    return render_template(
        "fragments/application_detail.html",
        **_context(
            data=body["data"],
            status_class=STATUS_CLASS,
            format_date=format_date,
            requirements_list=requirements_list,
        ),
    )


@app.get("/fragments/staff/applications/<int:application_id>/profile")
def profile_fragment(application_id: int):
    try:
        resp = _backend_get(f"/api/context/staff/applications/{application_id}/profile")
    except requests.RequestException:
        return _render_fragment_error("Backend unavailable.")
    if resp.status_code == 401:
        return _render_fragment_error("Please log in first.", status=401)
    if resp.status_code != 200:
        return _render_fragment_error("Could not load candidate profile.")

    body = resp.json() or {}
    if not body.get("ok"):
        kind = body.get("kind", "error")
        klass = "alert-error" if kind == "error" else "text-sm"
        return f'<div class="alert {klass}">{body.get("message", "Could not load profile.")}</div>'

    return render_template(
        "fragments/candidate_profile.html",
        **_context(
            data=body["data"],
            status_class=STATUS_CLASS,
            format_date=format_date,
            requirements_list=requirements_list,
            valid_statuses=body["data"].get("valid_statuses", []),
        ),
    )


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)
