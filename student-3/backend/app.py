"""Student 3 Backend/API microservice (Application Management).

Flask API that renders HTML fragments for the HTMX frontend, proxies data
operations to the student-3 database service, validates sessions against the
shared-api, and hosts an AI-Mode candidate screening endpoint (Ollama).

Container port 5003 (host 16011).
"""

from flask import Flask, Response, jsonify, make_response, request, stream_with_context
from flask_cors import CORS
from openai import OpenAI
from html import escape
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
import base64
import json
import os

import requests

try:
    from pypdf import PdfReader  # type: ignore
except Exception:  # pragma: no cover
    PdfReader = None  # type: ignore

app = Flask(__name__)
FRONTEND_PUBLIC_URL = os.getenv("FRONTEND_PUBLIC_URL", "http://localhost:16010")
CORS(app, supports_credentials=True, origins=[FRONTEND_PUBLIC_URL],
     expose_headers=["HX-Redirect", "HX-Trigger"])

DATABASE_SERVICE_URL = os.environ["DATABASE_SERVICE_URL"]
SHARED_API_URL = os.environ["SHARED_API_URL"]
SHARED_DB_URL = os.environ["SHARED_DB_URL"]
POSTINGS_DB_URL = os.environ["POSTINGS_DB_URL"]
STUDENT_1_DB_URL = os.environ["STUDENT_1_DB_URL"]
BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:16011")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
PORT = int(os.getenv("PORT", "5003"))
TIMEOUT = 5

PROMPT_DIR = Path(__file__).resolve().parent / "prompts"
ollama_client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama", timeout=120.0)

_DB_UNAVAILABLE = (
    "Could not reach the database service. Make sure the student-3-db "
    "container is running."
)

INTERVIEWS_URL = os.getenv("INTERVIEWS_PUBLIC_URL", "http://localhost:16013")
EVALUATIONS_URL = os.getenv("EVALUATIONS_PUBLIC_URL", "http://localhost:16016")

MAX_RESUME_BYTES = 5 * 1024 * 1024
ALLOWED_RESUME_MIME = {
    "application/pdf": "PDF",
}
ALLOWED_RESUME_EXTS = (".pdf",)

VALID_STATUSES = (
    "Draft", "Submitted", "Shortlisted", "Interview Requested",
    "Interview Scheduled", "Interview Completed", "Evaluation Completed",
    "Hired", "Rejected", "Withdrawn",
)
WITHDRAWABLE_STATUSES = (
    "Submitted", "Shortlisted", "Interview Requested", "Interview Scheduled",
    "Interview Completed", "Evaluation Completed",
)
DELETABLE_STATUSES = ("Draft",)
INTERVIEW_ACTION_STATUSES = ("Shortlisted",)


# --------------------------------------------------------------------------- #
# Session / cross-service helpers                                             #
# --------------------------------------------------------------------------- #

def get_session_user():
    cookie = request.headers.get("Cookie", "")
    if not cookie:
        return None
    try:
        resp = requests.get(f"{SHARED_API_URL}/api/auth/session",
                            headers={"Cookie": cookie}, timeout=TIMEOUT)
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    return (resp.json() or {}).get("user")


def _forward_cookie():
    cookie = request.headers.get("Cookie", "")
    return {"Cookie": cookie} if cookie else {}


def get_user(user_id):
    try:
        resp = requests.get(f"{SHARED_DB_URL}/users/{user_id}", timeout=TIMEOUT)
    except requests.RequestException:
        return None
    return resp.json() if resp.status_code == 200 else None


def get_users_map(user_ids):
    if not user_ids:
        return {}
    try:
        resp = requests.get(f"{SHARED_DB_URL}/users", timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException:
        return {}
    body = resp.json()
    if not isinstance(body, list):
        return {}
    wanted = {int(i) for i in user_ids}
    return {u["user_id"]: u for u in body if u.get("user_id") in wanted}


def get_job_posting(job_posting_id):
    try:
        resp = requests.get(f"{POSTINGS_DB_URL}/job-postings/{job_posting_id}", timeout=TIMEOUT)
    except requests.RequestException:
        return None
    return resp.json() if resp.status_code == 200 else None


def get_postings_map(job_posting_ids):
    if not job_posting_ids:
        return {}
    try:
        resp = requests.get(f"{POSTINGS_DB_URL}/job-postings", timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException:
        return {}
    body = resp.json()
    if not isinstance(body, list):
        return {}
    wanted = {int(i) for i in job_posting_ids}
    return {p["JobPosting_Id"]: p for p in body if p.get("JobPosting_Id") in wanted}


# --------------------------------------------------------------------------- #
# Student-1 resume integration                                                #
# --------------------------------------------------------------------------- #
#
# Calls student-1's database microservice directly (frontend -> own backend ->
# other student's DB is the convention used throughout this repo - see
# student-2's APPLICATIONS_DB_URL, student-4/5's APPLICATION_DB_URL). The DB
# service does no authentication itself, so ownership checks below are
# reimplemented here rather than delegated to student-1.

def _get_student1_profile_by_user_id(user_id):
    try:
        resp = requests.get(f"{STUDENT_1_DB_URL}/profiles/by-user/{user_id}", timeout=TIMEOUT)
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    return resp.json() or None


def _get_student1_profile(profile_id):
    try:
        resp = requests.get(f"{STUDENT_1_DB_URL}/profiles/{profile_id}", timeout=TIMEOUT)
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    return resp.json() or None


def _get_student1_resume_meta(resume_id):
    try:
        resp = requests.get(f"{STUDENT_1_DB_URL}/resumes/{resume_id}", timeout=TIMEOUT)
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    return resp.json() or None


def get_latest_profile_resume(user_id):
    """The applicant's single stored resume from their student-1 profile, if any."""
    profile = _get_student1_profile_by_user_id(user_id)
    if not profile:
        return None
    profile_id = profile.get("profile_id")
    if not profile_id:
        return None

    try:
        resp = requests.get(f"{STUDENT_1_DB_URL}/profiles/{profile_id}/resumes", timeout=TIMEOUT)
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None

    resumes = resp.json() or []
    if not resumes:
        return None
    latest = resumes[0]  # one resume per profile, enforced by student-1's UNIQUE constraint
    return {
        "resume_id": latest.get("resume_id"),
        "file_name": latest.get("file_name", "resume.pdf"),
        "file_type": latest.get("file_type", "application/pdf"),
        "uploaded_at": latest.get("uploaded_at", ""),
        "from_profile": True,
    }


def upload_application_resume(filename, mimetype, raw_bytes):
    """Upload a one-off resume for this application only - NOT the applicant's
    profile default resume. profile_id is left NULL on student-1's side;
    ownership is tracked via applications.user_id on this side instead."""
    payload = {
        "file_name": filename,
        "file_type": mimetype,
        "file_data": base64.b64encode(raw_bytes).decode("utf-8"),
    }
    try:
        resp = requests.post(f"{STUDENT_1_DB_URL}/resumes", json=payload, timeout=15)
    except requests.RequestException:
        return None
    if resp.status_code != 201:
        return None
    return (resp.json() or {}).get("resume_id")


def _user_owns_application_resume(user_id, resume_id):
    """True if resume_id is attached to one of user_id's own applications
    (covers application-only resumes, which have no profile_id to check)."""
    if user_id is None:
        return False
    try:
        resp = requests.get(f"{DATABASE_SERVICE_URL}/applications", params={"user_id": user_id}, timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException:
        return False
    return any(a.get("resume_id") == resume_id for a in (resp.json() or []))


def get_resume_metadata(resume_id, role, current_user_id=None):
    if not resume_id:
        return None
    meta = _get_student1_resume_meta(resume_id)
    if not meta:
        return None

    if role == "staff":
        return meta

    profile_id = meta.get("profile_id")
    if profile_id is None:
        # Application-only resume (not linked to a profile): verify it belongs
        # to one of the caller's own applications instead of trusting the caller.
        if not _user_owns_application_resume(current_user_id, resume_id):
            return None
        return meta

    if current_user_id is None:
        return None
    profile = _get_student1_profile(profile_id)
    if not profile or profile.get("user_id") != current_user_id:
        return None
    return meta


def download_resume_stream(resume_id, role, current_user_id=None):
    if role != "staff":
        allowed = get_resume_metadata(resume_id, role, current_user_id)
        if not allowed:
            return None
    return requests.get(f"{STUDENT_1_DB_URL}/resumes/{resume_id}/file", timeout=15, stream=True)


# --------------------------------------------------------------------------- #
# Prompt loading + resume text extraction                                     #
# --------------------------------------------------------------------------- #

def load_prompt(filename):
    return (PROMPT_DIR / filename).read_text(encoding="utf-8").strip()


def extract_resume_text(data, mimetype):
    text = ""
    mt = (mimetype or "").lower()
    if "pdf" in mt and PdfReader is not None:
        try:
            reader = PdfReader(BytesIO(data))
            pages = []
            for page in reader.pages[:10]:
                try:
                    pages.append(page.extract_text() or "")
                except Exception:
                    continue
            text = "\n".join(p.strip() for p in pages if p.strip())
        except Exception:
            text = ""
    if not text:
        try:
            text = data.decode("utf-8", errors="ignore")
        except Exception:
            text = ""
    text = text.strip()
    if len(text) > 4000:
        text = text[:4000] + "\n[...truncated...]"
    return text


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


# --------------------------------------------------------------------------- #
# HTML rendering helpers                                                      #
# --------------------------------------------------------------------------- #

def _e(value):
    return escape(str(value if value is not None else ""))


def _status_badge(status):
    css_map = {
        "Draft": "badge-warning", "Submitted": "badge-info",
        "Shortlisted": "badge-accent", "Interview Requested": "badge-warning",
        "Interview Scheduled": "badge-info", "Interview Completed": "badge-accent",
        "Evaluation Completed": "badge-accent", "Hired": "badge-success",
        "Rejected": "badge-danger", "Withdrawn": "badge-muted",
    }
    return f'<span class="badge {css_map.get(status, "badge-muted")}">{_e(status)}</span>'


def _format_date(value, fallback="—"):
    if not value:
        return fallback
    try:
        if len(value) == 10:
            return date.fromisoformat(value).strftime("%d %b %Y")
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%d %b %Y")
    except ValueError:
        return _e(value)


def render_message(message, kind="info"):
    if kind == "error":
        return f'<div class="alert alert-error">{_e(message)}</div>'
    if kind == "success":
        return f'<div class="alert alert-success">{_e(message)}</div>'
    return f'<p class="text-sm">{_e(message)}</p>'


def render_my_applications_table(applications, postings):
    if not applications:
        return '<tr><td colspan="4" class="empty-state">No applications found.</td></tr>'
    rows = []
    for a in applications:
        aid = a["application_id"]
        posting = postings.get(a["job_posting_id"]) or {}
        title = posting.get("Job_Title", f"Posting #{a['job_posting_id']}")
        if a["application_status"] == "Draft":
            row_link = f"{FRONTEND_PUBLIC_URL}/apply/{a['job_posting_id']}"
        else:
            row_link = f"{FRONTEND_PUBLIC_URL}/applications/{aid}"

        action_btn = ""
        if a["application_status"] in DELETABLE_STATUSES:
            action_btn = (
                f'<button class="btn btn-danger btn-sm delete-btn"'
                f' hx-delete="{BACKEND_PUBLIC_URL}/api/applications/{aid}"'
                f' hx-target="#toast-area" hx-swap="none"'
                f' hx-confirm="Are you sure you want to delete this draft application? This cannot be undone.">'
                f'Delete</button>'
            )
        elif a["application_status"] in WITHDRAWABLE_STATUSES:
            action_btn = (
                f'<button class="btn btn-secondary btn-sm withdraw-btn"'
                f' hx-put="{BACKEND_PUBLIC_URL}/api/applications/{aid}/withdraw"'
                f' hx-target="#toast-area" hx-swap="none"'
                f' hx-confirm="Are you sure you want to withdraw this application?">'
                f'Withdraw</button>'
            )

        rows.append(f"""
        <tr class="application-row" data-href="{row_link}">
            <td class="cell-id">#{aid}</td>
            <td class="cell-title">{_e(title)}</td>
            <td>{_status_badge(a['application_status'])}</td>
            <td class="cell-action-center cell-interactive">{action_btn}</td>
        </tr>""")
    return "".join(rows)


_REQ = '<span class="req" title="Required">*</span>'


def _render_requirements_bullets(text):
    items = []
    for line in str(text or "").splitlines():
        item = line.strip().lstrip("-•* ").strip()
        if item:
            items.append(item)
    if not items:
        return "<p>—</p>"
    lis = "".join(f"<li>{_e(item)}</li>" for item in items)
    return f'<ul class="requirements-list">{lis}</ul>'


def _render_posting_summary(posting):
    reqs = _render_requirements_bullets(posting.get("Requirements", ""))
    return f"""
    <div class="card posting-summary">
        <div class="posting-summary-head">
            <h1>{_e(posting['Job_Title'])}</h1>
            <span class="badge badge-info">{_e(posting.get('Job_Type', ''))}</span>
        </div>
        <p class="posting-summary-desc">{_e(posting.get('Job_Description', ''))}</p>
        <div class="posting-summary-grid">
            <div><span class="label">Location</span><span>{_e(posting.get('Location', '—'))}</span></div>
            <div><span class="label">Salary</span><span>{_e(posting.get('Salary_Range', '—'))}</span></div>
            <div><span class="label">Deadline</span><span>{_format_date(posting.get('Application_Deadline', ''))}</span></div>
        </div>
        <div class="posting-summary-reqs">
            <h4>Requirements</h4>
            {reqs}
        </div>
    </div>
    """


def render_apply_form(posting, user, application=None, resume=None, error=""):
    editing = application is not None
    a = application or {}
    declaration_checked = " checked" if a.get("declaration_accepted") else ""

    if editing:
        aid = a["application_id"]
        save_url = f"/api/applications/{aid}/save"
        submit_url = f"/api/applications/{aid}/submit"
        delete_url = f"{BACKEND_PUBLIC_URL}/api/applications/{aid}"
        heading = "Edit draft application"
    else:
        save_url = "/api/applications/save"
        submit_url = "/api/applications/submit"
        delete_url = None
        heading = "Apply for this position"

    resume_summary_html = ""
    if resume:
        source_note = ""
        if resume.get("from_profile"):
            source_note = (
                '<span class="resume-current-source">'
                "&mdash; auto-filled from your profile</span>"
            )
        resume_summary_html = f"""
        <div class="resume-current">
            <span class="resume-current-label">Current file:</span>
            <span class="resume-current-name">{_e(resume.get('file_name', 'resume.pdf'))}</span>
            {source_note}
        </div>"""

    error_html = render_message(error, "error") if error else ""
    delete_btn = ""
    if editing and a.get("application_status") == "Draft":
        delete_btn = f"""
        <button type="button" class="btn btn-danger"
                hx-delete="{delete_url}" hx-target="#form-msg" hx-swap="innerHTML"
                hx-confirm="Are you sure you want to delete this draft application? This cannot be undone.">
            Delete draft
        </button>"""

    posting_summary = _render_posting_summary(posting)
    return f"""
    <div class="apply-page">
        {posting_summary}
        <div class="card">
            <div class="card-header"><h2 class="card-title">{_e(heading)}</h2></div>
            <div id="form-msg" class="form-alert">{error_html}</div>

            <form id="apply-form" class="apply-form" enctype="multipart/form-data">
                <input type="hidden" name="job_posting_id" value="{_e(posting['JobPosting_Id'])}">

                <fieldset class="form-section">
                    <legend>Your details</legend>
                    <div class="grid grid-2">
                        <div class="form-group">
                            <label class="form-label">First name</label>
                            <input class="form-input" value="{_e(user.get('first_name', ''))}" disabled>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Last name</label>
                            <input class="form-input" value="{_e(user.get('last_name', ''))}" disabled>
                        </div>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Email address</label>
                        <input class="form-input" value="{_e(user.get('email', ''))}" disabled>
                    </div>
                </fieldset>

                <fieldset class="form-section">
                    <legend>Resume</legend>
                    {resume_summary_html}
                    <div class="form-group">
                        <label class="form-label">
                            {"Replace resume" if resume else f"Upload resume {_REQ}"}
                        </label>
                        <input class="form-input" type="file" name="resume_file"
                               accept=".pdf,application/pdf">
                        <p class="form-help">PDF only, maximum 5 MB.</p>
                    </div>
                </fieldset>

                <fieldset class="form-section">
                    <legend>Declaration</legend>
                    <label class="form-checkbox">
                        <input type="checkbox" name="declaration_accepted" value="1"{declaration_checked}>
                        <span>I confirm that the information provided in this application is accurate to the best of my knowledge. {_REQ}</span>
                    </label>
                </fieldset>

                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" data-action="save" data-endpoint="{save_url}">Save Draft</button>
                    <button type="button" class="btn btn-primary" id="apply-submit-btn" data-action="submit" data-endpoint="{submit_url}">Submit Application</button>
                    {delete_btn}
                    <a class="btn btn-ghost" href="/">Cancel</a>
                </div>
            </form>
        </div>
    </div>
    """


def render_application_detail(application, posting, user, resume):
    aid = application["application_id"]
    status = application["application_status"]

    actions = []
    if status in WITHDRAWABLE_STATUSES:
        actions.append(
            f'<button class="btn btn-danger"'
            f' hx-put="{BACKEND_PUBLIC_URL}/api/applications/{aid}/withdraw"'
            f' hx-target="#detail-actions-msg" hx-swap="innerHTML"'
            f' hx-confirm="Are you sure you want to withdraw this application?">'
            f'Withdraw Application</button>'
        )
    if status in INTERVIEW_ACTION_STATUSES:
        actions.append(
            f'<a class="btn btn-secondary" target="_blank" rel="noopener"'
            f' href="{INTERVIEWS_URL}/?application={aid}">Schedule Interview</a>'
        )
    actions_html = f'<div class="panel-actions">{"".join(actions)}</div>' if actions else ""

    if resume is not None:
        resume_block = f"""
        <div class="resume-current">
            <span class="resume-current-label">Uploaded file:</span>
            <a class="resume-current-name" target="_blank"
               href="{BACKEND_PUBLIC_URL}/api/resumes/{resume['resume_id']}/download">
                {_e(resume.get('file_name', 'resume.pdf'))}
            </a>
        </div>"""
    else:
        resume_block = '<p class="form-help">No resume uploaded.</p>'

    submitted_display = _format_date(application.get("submitted_at") or "")
    posting_summary = _render_posting_summary(posting)
    declaration_check = "checked" if application.get("declaration_accepted") else ""

    return f"""
    <div id="detail-actions-msg"></div>
    <div class="apply-page">
        <div class="detail-status-bar">
            <div class="detail-status-info">
                <span class="detail-status-label">Status</span>
                {_status_badge(status)}
            </div>
            <div class="detail-status-info">
                <span class="detail-status-label">Date submitted</span>
                <span class="detail-status-value">{_e(submitted_display)}</span>
            </div>
            <div class="detail-status-info">
                <span class="detail-status-label">Application ID</span>
                <span class="detail-status-value">#{aid}</span>
            </div>
            {actions_html}
        </div>

        {posting_summary}

        <div class="card">
            <div class="card-header"><h2 class="card-title">Your submitted application</h2></div>
            <form class="apply-form" onsubmit="event.preventDefault()">
                <fieldset class="form-section">
                    <legend>Your details</legend>
                    <div class="grid grid-2">
                        <div class="form-group">
                            <label class="form-label">First name</label>
                            <input class="form-input" value="{_e(user.get('first_name', ''))}" disabled>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Last name</label>
                            <input class="form-input" value="{_e(user.get('last_name', ''))}" disabled>
                        </div>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Email address</label>
                        <input class="form-input" value="{_e(user.get('email', ''))}" disabled>
                    </div>
                </fieldset>
                <fieldset class="form-section">
                    <legend>Resume</legend>
                    {resume_block}
                </fieldset>
                <fieldset class="form-section">
                    <legend>Declaration</legend>
                    <label class="form-checkbox">
                        <input type="checkbox" {declaration_check} disabled>
                        <span>I confirm that the information provided in this application is accurate to the best of my knowledge.</span>
                    </label>
                </fieldset>
            </form>
        </div>
    </div>
    """


def _render_status_select(application_id, current):
    selectable = {"Shortlisted", "Rejected"}
    opts = []
    for status in VALID_STATUSES:
        if status == "Draft":
            continue
        attrs = []
        if status == current:
            attrs.append("selected")
        if status not in selectable and status != current:
            attrs.append("disabled")
        elif status == current and status not in selectable:
            attrs.append("disabled")
        attr_str = (" " + " ".join(attrs)) if attrs else ""
        opts.append(f'<option value="{_e(status)}"{attr_str}>{_e(status)}</option>')
    return f"""
    <select class="form-select form-select-sm status-select"
            data-application-id="{application_id}"
            data-current="{_e(current)}"
            hx-put="{BACKEND_PUBLIC_URL}/api/applications/{application_id}/status"
            hx-vals='js:{{"application_status": event.target.value}}'
            hx-target="#toast-area" hx-swap="none"
            hx-trigger="change">
        {"".join(opts)}
    </select>
    """


def _render_header_status_select(application_id, current):
    selectable = ("Shortlisted", "Rejected")
    opts = []
    if current not in selectable:
        opts.append(f'<option value="{_e(current)}" selected disabled>{_e(current)}</option>')
    for status in selectable:
        selected = " selected" if status == current else ""
        opts.append(f'<option value="{_e(status)}"{selected}>{_e(status)}</option>')
    return f"""
    <select class="form-select form-select-sm status-select header-status-select"
            data-application-id="{application_id}"
            data-current="{_e(current)}"
            hx-put="{BACKEND_PUBLIC_URL}/api/applications/{application_id}/status"
            hx-vals='js:{{"application_status": event.target.value}}'
            hx-target="#toast-area" hx-swap="none"
            hx-trigger="change">
        {"".join(opts)}
    </select>
    """


def render_staff_applications_table(applications, postings, users):
    if not applications:
        return '<tr><td colspan="5" class="empty-state">No applications found.</td></tr>'
    rows = []
    for a in applications:
        aid = a["application_id"]
        posting = postings.get(a["job_posting_id"]) or {}
        candidate = users.get(a["user_id"]) or {}
        title = posting.get("Job_Title", f"Posting #{a['job_posting_id']}")
        candidate_name = (
            f"{candidate.get('user_first_name', '')} "
            f"{candidate.get('user_last_name', '')}".strip()
            or "Unknown candidate"
        )
        detail_link = f"{FRONTEND_PUBLIC_URL}/staff/applications/{aid}"
        status_select = _render_status_select(aid, a["application_status"])

        interview_btn = ""
        if a["application_status"] == "Shortlisted":
            interview_btn = (
                f'<a class="btn btn-accent btn-sm" target="_blank" rel="noopener"'
                f' href="{INTERVIEWS_URL}/?application={aid}">Interview</a>'
            )
        evaluate_btn = ""
        if a["application_status"] == "Interview Completed":
            evaluate_btn = (
                f'<a class="btn btn-primary btn-sm" target="_blank" rel="noopener"'
                f' href="{EVALUATIONS_URL}/evaluate/{aid}">Evaluate</a>'
            )
        actions_html = interview_btn + evaluate_btn
        rows.append(f"""
        <tr class="application-row" data-href="{detail_link}">
            <td class="cell-id">#{aid}</td>
            <td class="cell-title">{_e(title)}</td>
            <td>{_e(candidate_name)}</td>
            <td class="cell-interactive">{status_select}</td>
            <td class="cell-action-center cell-interactive">{actions_html}</td>
        </tr>""")
    return "".join(rows)


def render_pending_interviews_bar(applications):
    to_schedule = [a for a in applications if a["application_status"] == "Shortlisted"]
    to_evaluate = [a for a in applications if a["application_status"] == "Interview Completed"]
    if not to_schedule and not to_evaluate:
        return ('<div class="pending-bar">'
                '<span class="pending-empty">No pending interviews to schedule or evaluate.</span>'
                '</div>')
    parts = []
    if to_schedule:
        parts.append(
            f'<span class="pending-item"><strong>{len(to_schedule)}</strong> '
            "candidates awaiting interview scheduling</span>"
        )
    if to_evaluate:
        parts.append(
            f'<span class="pending-item"><strong>{len(to_evaluate)}</strong> '
            "candidates ready to evaluate</span>"
        )
    return f'<div class="pending-bar">{"".join(parts)}</div>'


def _render_resume_row(resume):
    if resume is None:
        return "<p>No resume uploaded.</p>"
    return f"""
    <table class="detail-table">
        <tr><th>File</th>
            <td>
                <a class="btn btn-secondary btn-sm" target="_blank"
                   href="{BACKEND_PUBLIC_URL}/api/resumes/{resume['resume_id']}/download">
                   Download {_e(resume.get('file_name', 'resume.pdf'))}
                </a>
            </td>
        </tr>
        <tr><th>Uploaded</th><td>{_format_date(resume.get('uploaded_at') or '')}</td></tr>
    </table>
    """


def render_ai_screening_panel(application_id, screening):
    generate_button = (
        f'<button class="btn btn-accent"'
        f' hx-post="{BACKEND_PUBLIC_URL}/api/applications/{application_id}/screen"'
        f' hx-target="#ai-screening-panel" hx-swap="innerHTML"'
        f' hx-indicator="#ai-spinner" hx-disabled-elt="this">'
        f'Generate AI recommendation</button>'
        f'<span id="ai-spinner" class="htmx-indicator ai-spinner">'
        f'<span class="spinner"></span> Thinking…</span>'
    )
    if screening is None:
        return f"""
        <div class="ai-empty">
            <p>No AI recommendation yet. Ask the AI for a shortlist suggestion based on job and resume match.</p>
            <div class="ai-actions-row">{generate_button}</div>
        </div>"""

    recommendation = str(screening.get("Recommendation", "No")).strip() or "No"
    if recommendation not in ("Yes", "No"):
        recommendation = "No"
    reasoning = str(screening.get("Reasoning", "")).strip() or "No reasoning provided."
    rec_class = {"Yes": "rec-yes", "No": "rec-no"}[recommendation]
    rec_label = {
        "Yes": "Recommend shortlist",
        "No": "Do not shortlist",
    }[recommendation]

    return f"""
    <div class="ai-result-card {rec_class}">
        <div class="ai-recommendation">
            <span class="ai-recommendation-label">Recommendation</span>
            <span class="ai-recommendation-value">{_e(recommendation)}</span>
            <span class="ai-recommendation-caption">{_e(rec_label)}</span>
        </div>
        <div class="ai-reasoning">
            <h4>Reasoning</h4>
            <p>{_e(reasoning)}</p>
        </div>
        <div class="ai-result-actions">
            {generate_button}
        </div>
    </div>
    """


def render_candidate_profile(application, posting, user, resume, screening):
    aid = application["application_id"]
    status = application["application_status"]
    ai_html = render_ai_screening_panel(aid, screening)
    resume_html = _render_resume_row(resume)
    header_status_select = _render_header_status_select(aid, status)

    return f"""
    <div id="profile-msg"></div>
    <div class="panel-head">
        <div class="panel-heading">
            <h2>{_e(user.get('user_first_name', ''))} {_e(user.get('user_last_name', ''))}</h2>
            {_status_badge(status)}
            <label class="header-status-label">Change status:</label>
            {header_status_select}
        </div>
    </div>

    <div class="detail-grid detail-grid-single">
        <section>
            <h3>Candidate Information</h3>
            <table class="detail-table">
                <tr><th>First name</th><td>{_e(user.get('user_first_name', '—'))}</td></tr>
                <tr><th>Last name</th><td>{_e(user.get('user_last_name', '—'))}</td></tr>
                <tr><th>Email</th><td>{_e(user.get('user_email', '—'))}</td></tr>
                <tr><th>Applied position</th><td>{_e(posting.get('Job_Title', '—'))}</td></tr>
                <tr><th>Date submitted</th><td>{_format_date(application.get('submitted_at') or '')}</td></tr>
            </table>
            <h4 class="section-subhead">Uploaded Resume</h4>
            {resume_html}
        </section>
    </div>

    <section class="ai-section">
        <h3>AI Screening</h3>
        <div id="ai-screening-panel">{ai_html}</div>
    </section>
    """


def parse_screening_response(text):
    """Parse LLM output into {Recommendation, Reasoning}."""
    recommendation = "No"
    reasoning_lines = []
    current = None
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        low = line.lower()
        if low.startswith("recommendation"):
            after = line.split(":", 1)[1].strip() if ":" in line else ""
            token = after.split()[0] if after else ""
            token_lc = token.lower().strip(".,!?")
            if token_lc.startswith("yes"):
                recommendation = "Yes"
            else:
                recommendation = "No"
            current = None
        elif low.startswith("reasoning"):
            after = line.split(":", 1)[1].strip() if ":" in line else ""
            if after:
                reasoning_lines.append(after)
            current = "reasoning"
        else:
            if current == "reasoning":
                reasoning_lines.append(line)
            elif not reasoning_lines:
                reasoning_lines.append(line)
    reasoning = " ".join(reasoning_lines).strip()
    if len(reasoning) > 800:
        reasoning = reasoning[:800].rstrip() + "…"
    return {"Recommendation": recommendation, "Reasoning": reasoning}


# --------------------------------------------------------------------------- #
# Validation helpers                                                          #
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
        resp = requests.get(f"{DATABASE_SERVICE_URL}/applications/{application_id}", timeout=TIMEOUT)
        if resp.status_code == 404:
            return None, (render_message("Application not found.", "error"), 200)
        resp.raise_for_status()
    except requests.RequestException:
        return None, (render_message(_DB_UNAVAILABLE, "error"), 200)
    return resp.json(), None


def load_resume(resume_id, role, current_user_id=None):
    if not resume_id:
        return None
    return get_resume_metadata(int(resume_id), role, current_user_id)


def context_error(message, kind="error", status=200):
    return jsonify({"ok": False, "kind": kind, "message": message}), status


def context_ok(data):
    return jsonify({"ok": True, "data": data}), 200


# --------------------------------------------------------------------------- #
# Health                                                                      #
# --------------------------------------------------------------------------- #

@app.get("/")
def index():
    return "<p>student-3 backend (Application Management) running</p>", 200


@app.get("/health")
def health():
    return {"status": "ok"}, 200


# --------------------------------------------------------------------------- #
# Applicant: list / detail / apply form                                       #
# --------------------------------------------------------------------------- #

@app.get("/api/context/apply/<int:job_posting_id>")
def apply_form_context(job_posting_id):
    user = get_session_user()
    if not user:
        return context_error("Please log in first.", status=401)
    if user.get("role") != "applicant":
        return context_error("Only applicants can submit applications.")

    posting = get_job_posting(job_posting_id)
    if not posting:
        return context_error("Job posting not found.")
    if posting.get("JobPosting_Status") != "Published":
        return context_error("This job posting is no longer accepting applications.")

    try:
        resp = requests.get(
            f"{DATABASE_SERVICE_URL}/applications",
            params={"user_id": user["user_id"], "job_posting_id": job_posting_id},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException:
        return context_error(_DB_UNAVAILABLE)

    applicant_ctx = {
        "first_name": user.get("first_name", ""),
        "last_name": user.get("last_name", ""),
        "email": user.get("email", ""),
    }

    application = None
    resume = None
    for existing in resp.json():
        if existing["application_status"] in ("Withdrawn", "Rejected"):
            continue
        if existing["application_status"] == "Draft":
            application = existing
            resume = load_resume(existing.get("resume_id"), user.get("role", "applicant"), user.get("user_id"))
            if resume is None:
                resume = get_latest_profile_resume(user.get("user_id"))
            break
        return context_error(
            f"You already applied for this job (status: {existing['application_status']}).",
            kind="info",
        )

    if resume is None:
        resume = get_latest_profile_resume(user.get("user_id"))

    return context_ok({
        "posting": posting,
        "user": applicant_ctx,
        "application": application,
        "resume": resume,
    })


@app.get("/api/context/applications/<int:application_id>/detail")
def applicant_application_detail_context(application_id):
    user = get_session_user()
    if not user:
        return context_error("Please log in first.", status=401)

    application, error = load_application(application_id)
    if error:
        return context_error("Application not found.")
    if application["user_id"] != user["user_id"]:
        return context_error("You can only view your own applications.")

    posting = get_job_posting(application["job_posting_id"]) or {}
    resume = load_resume(application.get("resume_id"), user.get("role", "applicant"), user.get("user_id"))
    return context_ok({
        "application": application,
        "posting": posting,
        "user": {
            "first_name": user.get("first_name", ""),
            "last_name": user.get("last_name", ""),
            "email": user.get("email", ""),
        },
        "resume": resume,
        "withdrawable_statuses": list(WITHDRAWABLE_STATUSES),
        "interview_action_statuses": list(INTERVIEW_ACTION_STATUSES),
        "interviews_url": INTERVIEWS_URL,
    })


@app.get("/api/context/staff/applications/<int:application_id>/profile")
def candidate_profile_context(application_id):
    user = get_session_user()
    if not user:
        return context_error("Please log in first.", status=401)
    if user.get("role") != "staff":
        return context_error("Staff view only.")

    application, error = load_application(application_id)
    if error:
        return context_error("Application not found.")
    if application.get("application_status") == "Withdrawn":
        return context_error("Application not found.")

    posting = get_job_posting(application["job_posting_id"]) or {}
    candidate = get_user(application["user_id"]) or {}
    resume = load_resume(application.get("resume_id"), "staff")

    return context_ok({
        "application": application,
        "posting": posting,
        "candidate": candidate,
        "resume": resume,
        "valid_statuses": [status for status in VALID_STATUSES if status != "Draft"],
    })

@app.get("/api/my-applications")
def my_applications():
    user = get_session_user()
    if not user:
        return unauthorized()
    try:
        resp = requests.get(f"{DATABASE_SERVICE_URL}/applications",
                            params={"user_id": user["user_id"]}, timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException:
        return render_message(_DB_UNAVAILABLE, "error"), 200
    apps = resp.json()
    postings = get_postings_map([a["job_posting_id"] for a in apps])
    return render_my_applications_table(apps, postings), 200


@app.get("/api/applications/<int:application_id>/detail")
def applicant_application_detail(application_id):
    user = get_session_user()
    if not user:
        return unauthorized()
    application, error = load_application(application_id)
    if error:
        return error
    if application["user_id"] != user["user_id"]:
        return forbidden("You can only view your own applications.")
    posting = get_job_posting(application["job_posting_id"]) or {}
    resume = load_resume(application.get("resume_id"), user.get("role", "applicant"), user.get("user_id"))
    return render_application_detail(application, posting, user, resume), 200


@app.get("/api/apply/<int:job_posting_id>")
def apply_form(job_posting_id):
    user = get_session_user()
    if not user:
        return unauthorized()
    if user.get("role") != "applicant":
        return forbidden("Only applicants can submit applications.")

    posting = get_job_posting(job_posting_id)
    if not posting:
        return render_message("Job posting not found.", "error"), 200
    if posting.get("JobPosting_Status") != "Published":
        return render_message("This job posting is no longer accepting applications.", "error"), 200

    try:
        resp = requests.get(f"{DATABASE_SERVICE_URL}/applications",
                            params={"user_id": user["user_id"], "job_posting_id": job_posting_id},
                            timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException:
        return render_message(_DB_UNAVAILABLE, "error"), 200

    applicant_ctx = {
        "first_name": user.get("first_name", ""),
        "last_name": user.get("last_name", ""),
        "email": user.get("email", ""),
    }
    for existing in resp.json():
        if existing["application_status"] in ("Withdrawn", "Rejected"):
            continue
        if existing["application_status"] == "Draft":
            resume = load_resume(existing.get("resume_id"), user.get("role", "applicant"), user.get("user_id"))
            if resume is None:
                resume = get_latest_profile_resume(user.get("user_id"))
            return render_apply_form(posting, applicant_ctx, existing, resume), 200
        return render_message(
            f"You already applied for this job (status: {existing['application_status']}).",
            "info",
        ), 200

    profile_resume = get_latest_profile_resume(user.get("user_id"))
    return render_apply_form(posting, applicant_ctx, resume=profile_resume), 200


# --------------------------------------------------------------------------- #
# Applicant: save-draft / submit                                              #
# --------------------------------------------------------------------------- #

def _save_or_submit(action, application_id):
    user = get_session_user()
    if not user:
        return unauthorized()
    if user.get("role") != "applicant":
        return forbidden("Only applicants can submit applications.")

    try:
        job_posting_id = int(request.form.get("job_posting_id", "0"))
    except (TypeError, ValueError):
        return render_message("Invalid job posting.", "error"), 200

    declaration = request.form.get("declaration_accepted") in ("1", "true", "on")
    resume_file = request.files.get("resume_file")

    if action == "submit" and not declaration:
        return render_message("You must confirm the declaration before submitting.", "error"), 200

    resume_id_new = None
    if resume_file and resume_file.filename:
        error = validate_resume(resume_file)
        if error:
            return render_message(error, "error"), 200
        raw = resume_file.read()
        resume_id_new = upload_application_resume(
            resume_file.filename, resume_file.mimetype or "application/pdf", raw,
        )
        if resume_id_new is None:
            return render_message(
                "Could not save your resume to your profile. Please try again.", "error"), 200

    if application_id is None:
        if action == "submit" and resume_id_new is None:
            latest = get_latest_profile_resume(user.get("user_id"))
            resume_id_new = int(latest["resume_id"]) if latest and latest.get("resume_id") else None
            if resume_id_new is None:
                return render_message("Please upload your resume before submitting.", "error"), 200
        create_payload = {
            "user_id": user["user_id"],
            "job_posting_id": job_posting_id,
            "resume_id": resume_id_new,
            "declaration_accepted": 1 if declaration else 0,
            "application_status": "Draft",
        }
        try:
            resp = requests.post(f"{DATABASE_SERVICE_URL}/applications",
                                 json=create_payload, timeout=TIMEOUT)
            if resp.status_code == 409:
                return redirect_response(f"/apply/{job_posting_id}",
                                         toast="You already have an application for this posting.")
            if resp.status_code >= 400:
                return render_message(resp.json().get("error", "Invalid data."), "error"), 200
            resp.raise_for_status()
        except requests.RequestException:
            return render_message(_DB_UNAVAILABLE, "error"), 200
        application_id = resp.json()["application_id"]
    else:
        existing, error = load_application(application_id)
        if error:
            return error
        if existing["user_id"] != user["user_id"]:
            return forbidden("You can only edit your own applications.")
        if existing["application_status"] != "Draft":
            return render_message("Only Draft applications can be edited.", "error"), 200
        if action == "submit" and resume_id_new is None and not existing.get("resume_id"):
            latest = get_latest_profile_resume(user.get("user_id"))
            resume_id_new = int(latest["resume_id"]) if latest and latest.get("resume_id") else None
            if resume_id_new is None:
                return render_message("Please upload your resume before submitting.", "error"), 200
        update_payload = {"declaration_accepted": 1 if declaration else 0}
        if resume_id_new is not None:
            update_payload["resume_id"] = resume_id_new
        try:
            resp = requests.put(f"{DATABASE_SERVICE_URL}/applications/{application_id}",
                                json=update_payload, timeout=TIMEOUT)
            if resp.status_code >= 400:
                return render_message(resp.json().get("error", "Invalid data."), "error"), 200
        except requests.RequestException:
            return render_message(_DB_UNAVAILABLE, "error"), 200

    if action == "submit":
        try:
            resp = requests.put(f"{DATABASE_SERVICE_URL}/applications/{application_id}/submit",
                                timeout=TIMEOUT)
            if resp.status_code >= 400:
                return render_message(resp.json().get("error", "Cannot submit."), "error"), 200
        except requests.RequestException:
            return render_message(_DB_UNAVAILABLE, "error"), 200
        return redirect_response(f"/applications/{application_id}",
                                 toast="Application submitted successfully.")

    return redirect_response(f"/apply/{job_posting_id}", toast="Draft saved.")


@app.post("/api/applications/save")
def save_new_draft():
    return _save_or_submit("save", None)


@app.post("/api/applications/submit")
def submit_new_application():
    return _save_or_submit("submit", None)


@app.put("/api/applications/<int:application_id>/save")
def save_existing_draft(application_id):
    return _save_or_submit("save", application_id)


@app.put("/api/applications/<int:application_id>/submit")
def submit_existing_draft(application_id):
    return _save_or_submit("submit", application_id)


# --------------------------------------------------------------------------- #
# Applicant: withdraw / delete                                                #
# --------------------------------------------------------------------------- #

@app.put("/api/applications/<int:application_id>/withdraw")
def withdraw(application_id):
    user = get_session_user()
    if not user:
        return unauthorized()
    application, error = load_application(application_id)
    if error:
        return error
    if user.get("role") == "applicant" and application["user_id"] != user["user_id"]:
        return forbidden("You can only withdraw your own applications.")
    if application["application_status"] not in WITHDRAWABLE_STATUSES:
        return render_message(
            f"Cannot withdraw an application in status '{application['application_status']}'.",
            "error"), 200
    try:
        resp = requests.put(f"{DATABASE_SERVICE_URL}/applications/{application_id}/withdraw",
                            timeout=TIMEOUT)
        if resp.status_code >= 400:
            return render_message(resp.json().get("error", "Cannot withdraw."), "error"), 200
    except requests.RequestException:
        return render_message(_DB_UNAVAILABLE, "error"), 200

    resp_out = make_response("", 200)
    resp_out.headers["HX-Trigger"] = json.dumps({
        "showToast": "Your application has been successfully withdrawn.",
        "applicationWithdrawn": application_id,
    })
    return resp_out


@app.delete("/api/applications/<int:application_id>")
def delete_draft(application_id):
    user = get_session_user()
    if not user:
        return unauthorized()
    application, error = load_application(application_id)
    if error:
        return error
    if user.get("role") == "applicant" and application["user_id"] != user["user_id"]:
        return forbidden("You can only delete your own applications.")
    if application["application_status"] != "Draft":
        return render_message(
            "Only Draft applications can be deleted. Withdraw instead.", "error"), 200
    try:
        resp = requests.delete(f"{DATABASE_SERVICE_URL}/applications/{application_id}",
                               timeout=TIMEOUT)
        if resp.status_code >= 400:
            return render_message(resp.json().get("error", "Cannot delete."), "error"), 200
    except requests.RequestException:
        return render_message(_DB_UNAVAILABLE, "error"), 200

    if request.headers.get("HX-Current-URL", "").rstrip("/").endswith(
        f"/apply/{application['job_posting_id']}"
    ):
        return redirect_response("/", toast="Draft application deleted.")

    resp_out = make_response("", 200)
    resp_out.headers["HX-Trigger"] = json.dumps({
        "showToast": "Draft application deleted.",
        "applicationDeleted": application_id,
    })
    return resp_out


# --------------------------------------------------------------------------- #
# Staff views                                                                 #
# --------------------------------------------------------------------------- #

@app.get("/api/all-applications")
def all_applications():
    user = get_session_user()
    if not user:
        return unauthorized()
    if user.get("role") != "staff":
        return forbidden("Staff view only.")

    params = {}
    for key in ("status", "job_posting_id"):
        v = request.args.get(key, "").strip()
        if v:
            params[key] = v

    try:
        resp = requests.get(f"{DATABASE_SERVICE_URL}/applications", params=params, timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException:
        return render_message(_DB_UNAVAILABLE, "error"), 200

    apps = [a for a in resp.json() if a.get("application_status") not in ("Draft", "Withdrawn")]
    q = request.args.get("q", "").strip().lower()
    sort = request.args.get("sort", "").strip()
    order = request.args.get("order", "desc").strip().lower()

    postings = get_postings_map([a["job_posting_id"] for a in apps])
    users = get_users_map([a["user_id"] for a in apps])

    def matches(a):
        posting = postings.get(a["job_posting_id"]) or {}
        candidate = users.get(a["user_id"]) or {}
        title = (posting.get("Job_Title") or "").lower()
        name = (
            f"{candidate.get('user_first_name', '')} "
            f"{candidate.get('user_last_name', '')}"
        ).lower()
        if q and not any(q in field for field in (name, title)):
            return False
        return True

    apps = [a for a in apps if matches(a)]

    if sort:
        reverse = order == "desc"
        key_map = {
            "id": lambda a: a["application_id"],
            "title": lambda a: (postings.get(a["job_posting_id"]) or {}).get("Job_Title", ""),
            "candidate": lambda a: (users.get(a["user_id"]) or {}).get("user_last_name", ""),
            "status": lambda a: a.get("application_status", ""),
        }
        if sort in key_map:
            apps = sorted(apps, key=key_map[sort], reverse=reverse)

    return render_staff_applications_table(apps, postings, users), 200


@app.get("/api/pending-summary")
def pending_summary():
    user = get_session_user()
    if not user:
        return unauthorized()
    if user.get("role") != "staff":
        return forbidden("Staff view only.")
    try:
        resp = requests.get(f"{DATABASE_SERVICE_URL}/applications", timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException:
        return render_message(_DB_UNAVAILABLE, "error"), 200
    apps = [a for a in resp.json() if a.get("application_status") != "Withdrawn"]
    return render_pending_interviews_bar(apps), 200


@app.get("/api/staff/applications/<int:application_id>/profile")
def candidate_profile(application_id):
    user = get_session_user()
    if not user:
        return unauthorized()
    if user.get("role") != "staff":
        return forbidden("Staff view only.")

    application, error = load_application(application_id)
    if error:
        return error
    if application.get("application_status") == "Withdrawn":
        return render_message("Application not found.", "error"), 200
    posting = get_job_posting(application["job_posting_id"]) or {}
    candidate = get_user(application["user_id"]) or {}
    resume = load_resume(application.get("resume_id"), "staff")
    return render_candidate_profile(application, posting, candidate, resume, screening=None), 200


@app.put("/api/applications/<int:application_id>/status")
def update_status(application_id):
    user = get_session_user()
    if not user:
        return unauthorized()
    if user.get("role") != "staff":
        return forbidden("Only staff can change application status.")

    new_status = ""
    if request.is_json:
        new_status = str((request.get_json(silent=True) or {}).get("application_status", "")).strip()
    if not new_status:
        new_status = request.args.get("application_status", "").strip()
    if not new_status:
        new_status = request.form.get("application_status", "").strip()

    if new_status not in VALID_STATUSES:
        return toast_response(f"Unknown status: {new_status}", "error")

    try:
        resp = requests.put(f"{DATABASE_SERVICE_URL}/applications/{application_id}",
                            json={"application_status": new_status}, timeout=TIMEOUT)
        if resp.status_code >= 400:
            return toast_response(resp.json().get("error", "Cannot update status."), "error")
    except requests.RequestException:
        return toast_response(_DB_UNAVAILABLE, "error")
    return toast_response(f"Status updated to {new_status}.")


# --------------------------------------------------------------------------- #
# Resumes (proxy download to student-1)                                        #
# --------------------------------------------------------------------------- #

@app.get("/api/resumes/<int:resume_id>/download")
def download_resume(resume_id):
    user = get_session_user()
    if not user:
        return "Unauthorized", 401
    try:
        upstream = download_resume_stream(
            resume_id,
            user.get("role", "applicant"),
            user.get("user_id"),
        )
    except requests.RequestException:
        return "Backend unavailable", 502
    if upstream is None:
        return "Forbidden", 403
    if upstream.status_code == 404:
        return "Resume not found", 404
    if upstream.status_code != 200:
        return "Backend error", 502

    headers = {"Content-Type": upstream.headers.get("Content-Type", "application/octet-stream")}
    disposition = upstream.headers.get("Content-Disposition")
    if disposition:
        headers["Content-Disposition"] = disposition
    return Response(
        stream_with_context(upstream.iter_content(chunk_size=8192)),
        status=200, headers=headers,
    )


# --------------------------------------------------------------------------- #
# AI-Mode: candidate screening                                                #
# --------------------------------------------------------------------------- #

@app.post("/api/applications/<int:application_id>/screen")
def screen_application(application_id):
    user = get_session_user()
    if not user:
        return render_message("Please log in first.", "error"), 200
    if user.get("role") != "staff":
        return render_message("Staff only.", "error"), 200

    try:
        app_resp = requests.get(f"{DATABASE_SERVICE_URL}/applications/{application_id}",
                                timeout=TIMEOUT)
        if app_resp.status_code == 404:
            return render_message("Application not found.", "error"), 200
        app_resp.raise_for_status()
    except requests.RequestException:
        return render_message("Database unavailable.", "error"), 200
    application = app_resp.json()

    posting = get_job_posting(application["job_posting_id"]) or {}
    candidate = get_user(application["user_id"]) or {}

    resume_text = "(No resume provided.)"
    if application.get("resume_id"):
        try:
            meta = get_resume_metadata(int(application["resume_id"]), "staff")
            dl_resp = download_resume_stream(int(application["resume_id"]), "staff")
            if meta and dl_resp.status_code == 200:
                extracted = extract_resume_text(dl_resp.content, meta.get("file_type", ""))
                if extracted:
                    resume_text = extracted
        except requests.RequestException:
            pass

    try:
        system_prompt = load_prompt("screening_system_prompt.txt")
        task_template = load_prompt("screening_task_prompt.txt")
    except OSError:
        return render_message("AI prompt templates are missing.", "error"), 200

    candidate_name = (
        f"{candidate.get('user_first_name', '')} "
        f"{candidate.get('user_last_name', '')}".strip() or "Unknown candidate"
    )
    user_prompt = task_template.format(
        job_title=posting.get("Job_Title", "(unknown)"),
        job_type=posting.get("Job_Type", "(unknown)"),
        job_description=posting.get("Job_Description", "(no description provided)"),
        job_requirements=posting.get("Requirements", "(none listed)"),
        candidate_name=candidate_name,
        resume_text=resume_text,
    )

    try:
        response = ollama_client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=400, temperature=0.2,
        )
        answer = (response.choices[0].message.content or "").strip()

        if len(answer) < 40:
            response = ollama_client.chat.completions.create(
                model=OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt +
                        "\n\nBe concrete. Follow the required output format exactly."},
                ],
                max_tokens=400, temperature=0.3,
            )
            answer = (response.choices[0].message.content or "").strip()

        if not answer:
            return render_message(
                "The AI did not return a screening result. Try again.", "error"), 200
    except Exception as exc:
        return render_message(
            "AI request failed. Check that Ollama is running and that "
            f"{OLLAMA_MODEL} is installed. Details: {exc}",
            "error"), 200

    parsed = parse_screening_response(answer)
    return render_ai_screening_panel(application_id, parsed), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)
