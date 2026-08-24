"""HTML fragment builders for the HTMX frontend.

The backend returns small HTML snippets that HTMX swaps into the page.
Keeping the markup here separates presentation from the route/handler logic.
"""

from __future__ import annotations

import os
from datetime import date, datetime
from html import escape

# HTMX-swapped fragments run on the frontend origin (port 16010), so bare
# relative URLs like ``/api/applications/1/withdraw`` would be sent to the
# frontend and 404. Every ``hx-*`` attribute in these fragments therefore uses
# the absolute backend URL below.
BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:16011")

VALID_STATUSES = (
    "Draft",
    "Submitted",
    "Shortlisted",
    "Interview Requested",
    "Interview Scheduled",
    "Interview Completed",
    "Evaluation Completed",
    "Hired",
    "Rejected",
    "Withdrawn",
)

# Statuses at which "Withdraw Application" is offered to the applicant.
# Draft applications are not withdrawn — they're deleted (see the Draft-only
# Delete button on the My Applications table).
WITHDRAWABLE_STATUSES = (
    "Submitted",
    "Shortlisted",
    "Interview Requested",
    "Interview Scheduled",
    "Interview Completed",
    "Evaluation Completed",
)

# Statuses at which the applicant is allowed to hard-delete the row entirely.
DELETABLE_STATUSES = ("Draft",)

# Statuses at which staff should see an "Interview" action on the row.
INTERVIEW_ACTION_STATUSES = ("Shortlisted",)

# Interview / Evaluations feature URLs (owned by student-4 & student-5).
INTERVIEWS_URL = "http://localhost:16013"
EVALUATIONS_URL = "http://localhost:16016"

MAX_RESUME_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_RESUME_MIME = {
    "application/pdf": "PDF",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "DOCX",
    "application/msword": "DOC",  # some older browsers/uploaders still send this
}
ALLOWED_RESUME_EXTS = (".pdf", ".docx", ".doc")


# --------------------------------------------------------------------------- #
# Small helpers                                                               #
# --------------------------------------------------------------------------- #

def _e(value) -> str:
    return escape(str(value if value is not None else ""))


def _status_badge(status: str) -> str:
    css_map = {
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
    css = css_map.get(status, "badge-muted")
    return f'<span class="badge {css}">{_e(status)}</span>'


def _format_date(value: str, fallback: str = "—") -> str:
    if not value:
        return fallback
    # Handle both ISO date and full ISO datetime.
    try:
        if len(value) == 10:
            return date.fromisoformat(value).strftime("%d %b %Y")
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%d %b %Y")
    except ValueError:
        return _e(value)


def render_message(message: str, kind: str = "info") -> str:
    """Render an inline message. Errors use the shared alert styling."""
    if kind == "error":
        return f'<div class="alert alert-error">{_e(message)}</div>'
    if kind == "success":
        return f'<div class="alert alert-success">{_e(message)}</div>'
    return f'<p class="text-sm">{_e(message)}</p>'


# --------------------------------------------------------------------------- #
# Applicant "My Applications" list                                            #
# --------------------------------------------------------------------------- #

def render_my_applications_table(
    applications: list[dict], postings: dict[int, dict], *, frontend_url: str
) -> str:
    """Rows for the applicant's My Applications table.

    Business rules:
      * The entire row is clickable (via ``data-href``); Drafts jump to the
        apply page for the posting, everything else to the read-only detail.
      * ``Draft`` rows offer only **Delete**.
      * Rows in any withdrawable status (Submitted / Shortlisted / etc.) offer
        only **Withdraw**.
    """
    if not applications:
        return (
            '<tr><td colspan="4" class="empty-state">'
            "No applications found.</td></tr>"
        )
    rows = []
    for a in applications:
        aid = a["Application_Id"]
        posting = postings.get(a["JobPosting_Id"]) or {}
        title = posting.get("Job_Title", f"Posting #{a['JobPosting_Id']}")
        submitted = _format_date(a.get("Application_SubmittedAt") or "", fallback="—")
        # Drafts open the apply form (so the candidate can continue editing);
        # every other status opens the read-only detail page.
        if a["Application_Status"] == "Draft":
            row_link = f"{frontend_url}/apply/{a['JobPosting_Id']}"
        else:
            row_link = f"{frontend_url}/applications/{aid}"

        action_btn = ""
        if a["Application_Status"] in DELETABLE_STATUSES:
            action_btn = (
                f'<button class="btn btn-danger btn-sm delete-btn"'
                f' hx-delete="{BACKEND_PUBLIC_URL}/api/applications/{aid}"'
                f' hx-target="#toast-area" hx-swap="none"'
                f' hx-confirm="Are you sure you want to delete this draft application? This cannot be undone.">'
                f'Delete</button>'
            )
        elif a["Application_Status"] in WITHDRAWABLE_STATUSES:
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
            <td>{_status_badge(a['Application_Status'])}</td>
            <td class="cell-action-center cell-interactive">{action_btn}</td>
        </tr>""")
    return "".join(rows)


# --------------------------------------------------------------------------- #
# Applicant apply form                                                        #
# --------------------------------------------------------------------------- #

_REQ = '<span class="req" title="Required">*</span>'


def render_apply_form(
    *, backend_url: str, posting: dict, user: dict,
    application: dict | None = None,
    resume: dict | None = None,
    error: str = "",
) -> str:
    """Applicant apply / edit-draft form.

    Displays the target job posting details, pre-fills candidate info from
    the shared session, and requires availability + resume + declaration
    before enabling Submit.
    """
    editing = application is not None
    a = application or {}

    declaration_checked = " checked" if a.get("Declaration_Accepted") else ""

    if editing:
        aid = a["Application_Id"]
        save_url = f"/api/applications/{aid}/save"
        submit_url = f"/api/applications/{aid}/submit"
        delete_url = f"{BACKEND_PUBLIC_URL}/api/applications/{aid}"
        heading = "Edit draft application"
    else:
        aid = None
        save_url = "/api/applications/save"
        submit_url = "/api/applications/submit"
        delete_url = None
        heading = "Apply for this position"

    resume_summary_html = ""
    if resume:
        size_bytes = int(resume.get("Resume_SizeBytes") or 0)
        size_label = f"{max(1, size_bytes // 1024)} KB" if size_bytes else ""
        source_note = ""
        if resume.get("from_profile"):
            source_note = (
                '<span class="resume-current-source">'
                "&mdash; auto-filled from your profile</span>"
            )
        meta_html = f'<span class="resume-current-meta">({size_label})</span>' if size_label else ""
        resume_summary_html = f"""
        <div class="resume-current">
            <span class="resume-current-label">Current file:</span>
            <span class="resume-current-name">{_e(resume['Resume_Filename'])}</span>
            {meta_html}
            {source_note}
        </div>"""

    error_html = render_message(error, "error") if error else ""
    delete_btn = ""
    if editing and a.get("Application_Status") == "Draft":
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
                <input type="hidden" name="JobPosting_Id" value="{_e(posting['JobPosting_Id'])}">

                <!-- Candidate details (read-only, from session) -->
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

                <!-- Resume -->
                <fieldset class="form-section">
                    <legend>Resume</legend>
                    {resume_summary_html}
                    <div class="form-group">
                        <label class="form-label">
                            {"Replace resume" if resume else f"Upload resume {_REQ}"}
                        </label>
                        <input class="form-input" type="file" name="Resume_File"
                               accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document">
                        <p class="form-help">PDF or DOCX, maximum 5 MB.</p>
                    </div>
                </fieldset>

                <!-- Declaration -->
                <fieldset class="form-section">
                    <legend>Declaration</legend>
                    <label class="form-checkbox">
                        <input type="checkbox" name="Declaration_Accepted" value="1"{declaration_checked}>
                        <span>I confirm that the information provided in this application is accurate to the best of my knowledge. {_REQ}</span>
                    </label>
                </fieldset>

                <div class="form-actions">
                    <button type="button" class="btn btn-secondary"
                            data-action="save"
                            data-endpoint="{save_url}">
                        Save Draft
                    </button>
                    <button type="button" class="btn btn-primary" id="apply-submit-btn"
                            data-action="submit"
                            data-endpoint="{submit_url}">
                        Submit Application
                    </button>
                    {delete_btn}
                    <a class="btn btn-ghost" href="/">Cancel</a>
                </div>
            </form>
        </div>
    </div>
    """


def _render_posting_summary(posting: dict) -> str:
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


def _render_requirements_bullets(text: str) -> str:
    items = []
    for line in str(text or "").splitlines():
        item = line.strip().lstrip("-•* ").strip()
        if item:
            items.append(item)
    if not items:
        return "<p>—</p>"
    lis = "".join(f"<li>{_e(item)}</li>" for item in items)
    return f'<ul class="requirements-list">{lis}</ul>'


# --------------------------------------------------------------------------- #
# Applicant application detail page                                           #
# --------------------------------------------------------------------------- #

def render_application_detail(
    *, application: dict, posting: dict, user: dict,
    resume: dict | None, backend_url: str, frontend_url: str,
) -> str:
    """Read-only view of a submitted (or otherwise non-Draft) application.

    Layout mirrors the applicant apply form so the candidate sees the same
    structure they submitted, plus a status + date-submitted header at the top
    and (when appropriate) a Withdraw / Interview action.
    """
    aid = application["Application_Id"]
    status = application["Application_Status"]

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
    actions_html = (
        f'<div class="panel-actions">{"".join(actions)}</div>' if actions else ""
    )

    # Resume block matches the apply-form style so applicants recognise it.
    resume_block = ""
    if resume is not None:
        size_bytes = int(resume.get("Resume_SizeBytes") or 0)
        size_label = f" ({max(1, size_bytes // 1024)} KB)" if size_bytes else ""
        resume_block = f"""
        <div class="resume-current">
            <span class="resume-current-label">Uploaded file:</span>
            <a class="resume-current-name" target="_blank"
               href="{BACKEND_PUBLIC_URL}/api/resumes/{resume['Resume_Id']}/download">
                {_e(resume['Resume_Filename'])}
            </a>
            <span class="resume-current-meta">{size_label}</span>
        </div>"""
    else:
        resume_block = '<p class="form-help">No resume uploaded.</p>'

    submitted_display = _format_date(application.get("Application_SubmittedAt") or "")
    posting_summary = _render_posting_summary(posting)

    declaration_check = "checked" if application.get("Declaration_Accepted") else ""

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


def _render_resume_row(resume: dict | None, application: dict) -> str:
    if resume is None:
        return "<p>No resume uploaded.</p>"
    size_kb = max(1, int(resume["Resume_SizeBytes"]) // 1024)
    return f"""
    <table class="detail-table">
        <tr><th>File</th>
            <td>
                <a class="btn btn-secondary btn-sm" target="_blank"
                   href="{BACKEND_PUBLIC_URL}/api/resumes/{resume['Resume_Id']}/download">
                   Download {_e(resume['Resume_Filename'])}
                </a>
                <span class="resume-meta">({size_kb} KB)</span>
            </td>
        </tr>
        <tr><th>Uploaded</th><td>{_format_date(resume.get('Resume_UploadedAt') or '')}</td></tr>
    </table>
    """


# --------------------------------------------------------------------------- #
# Staff "All Applications" table                                              #
# --------------------------------------------------------------------------- #

def render_staff_applications_table(
    applications: list[dict],
    postings: dict[int, dict],
    users: dict[int, dict],
    *, frontend_url: str,
) -> str:
    """Rows for the staff All Applications table."""
    if not applications:
        return (
            '<tr><td colspan="5" class="empty-state">'
            "No applications found.</td></tr>"
        )
    rows = []
    for a in applications:
        aid = a["Application_Id"]
        posting = postings.get(a["JobPosting_Id"]) or {}
        candidate = users.get(a["User_Id"]) or {}
        title = posting.get("Job_Title", f"Posting #{a['JobPosting_Id']}")
        candidate_name = (
            f"{candidate.get('user_first_name', '')} "
            f"{candidate.get('user_last_name', '')}".strip()
            or "Unknown candidate"
        )
        detail_link = f"{frontend_url}/staff/applications/{aid}"

        status_select = _render_status_select(aid, a["Application_Status"])

        interview_btn = ""
        # Staff can only kick off scheduling for a shortlisted candidate; they
        # do not reschedule a booked interview (applicants request that).
        if a["Application_Status"] == "Shortlisted":
            interview_btn = (
                f'<a class="btn btn-accent btn-sm" target="_blank" rel="noopener"'
                f' href="{INTERVIEWS_URL}/?application={aid}">Interview</a>'
            )
        evaluate_btn = ""
        if a["Application_Status"] == "Interview Completed":
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


def _render_status_select(application_id: int, current: str) -> str:
    """Render the staff status dropdown.

    Business rules (per feature spec):
      * "Draft" is never shown as a status option to staff.
      * Staff can only actively change the status to "Shortlisted" or
        "Rejected" from this control. Every other option is displayed
        (so staff can see the full pipeline and the current stage) but
        rendered ``disabled`` so it cannot be picked.
      * The current status is always shown pre-selected, even if it is one
        of the disabled values (e.g. Interview Completed).
    """
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
            # Current status stays visible-selected but not re-selectable.
            attrs.append("disabled")
        attr_str = (" " + " ".join(attrs)) if attrs else ""
        opts.append(f'<option value="{_e(status)}"{attr_str}>{_e(status)}</option>')
    return f"""
    <select class="form-select form-select-sm status-select"
            data-application-id="{application_id}"
            data-current="{_e(current)}"
            hx-put="{BACKEND_PUBLIC_URL}/api/applications/{application_id}/status"
            hx-vals='js:{{"Application_Status": event.target.value}}'
            hx-target="#toast-area" hx-swap="none"
            hx-trigger="change">
        {"".join(opts)}
    </select>
    """


def render_pending_interviews_bar(applications: list[dict]) -> str:
    """Small banner at the top of the staff table."""
    to_schedule = [a for a in applications if a["Application_Status"] == "Shortlisted"]
    to_evaluate = [
        a for a in applications if a["Application_Status"] == "Interview Completed"
    ]
    if not to_schedule and not to_evaluate:
        return (
            '<div class="pending-bar">'
            '<span class="pending-empty">No pending interviews to schedule or evaluate.</span>'
            "</div>"
        )
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


# --------------------------------------------------------------------------- #
# Staff candidate profile page                                                #
# --------------------------------------------------------------------------- #

def render_candidate_profile(
    *, application: dict, posting: dict, user: dict, resume: dict | None,
    screening: dict | None, backend_url: str,
) -> str:
    aid = application["Application_Id"]
    status = application["Application_Status"]

    ai_html = render_ai_screening_panel(application_id=aid, screening=screening)
    resume_html = _render_resume_row(resume, application)
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
                <tr><th>Date submitted</th><td>{_format_date(application.get('Application_SubmittedAt') or '')}</td></tr>
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


def _render_header_status_select(application_id: int, current: str) -> str:
    """Compact status control shown next to the candidate's name.

    Business rule: staff can only change the candidate's status to
    ``Shortlisted`` or ``Rejected`` from the profile page. The current
    status is shown as a pre-selected disabled option so it's still visible.
    """
    selectable = ("Shortlisted", "Rejected")
    opts = []
    if current not in selectable:
        opts.append(
            f'<option value="{_e(current)}" selected disabled>{_e(current)}</option>'
        )
    for status in selectable:
        selected = " selected" if status == current else ""
        opts.append(f'<option value="{_e(status)}"{selected}>{_e(status)}</option>')
    return f"""
    <select class="form-select form-select-sm status-select header-status-select"
            data-application-id="{application_id}"
            data-current="{_e(current)}"
            hx-put="{BACKEND_PUBLIC_URL}/api/applications/{application_id}/status"
            hx-vals='js:{{"Application_Status": event.target.value}}'
            hx-target="#toast-area" hx-swap="none"
            hx-trigger="change">
        {"".join(opts)}
    </select>
    """


def render_ai_screening_panel(*, application_id: int, screening: dict | None) -> str:
    """Render the AI Screening panel.

    The AI produces a shortlist recommendation (Yes / No / Maybe) plus a
    short reasoning paragraph. The panel exposes:
      * A "Generate AI recommendation" button that (re-)runs the model.
      * When a recommendation is available, a "Shortlist candidate" button
        that promotes the application's status to Shortlisted.
    """
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
            <p>No AI recommendation yet. Ask the AI whether this candidate should be shortlisted.</p>
            <div class="ai-actions-row">{generate_button}</div>
        </div>"""

    recommendation = str(screening.get("Recommendation", "Maybe")).strip() or "Maybe"
    if recommendation not in ("Yes", "No", "Maybe"):
        recommendation = "Maybe"
    reasoning = str(screening.get("Reasoning", "")).strip() or "No reasoning provided."
    rec_class = {"Yes": "rec-yes", "No": "rec-no", "Maybe": "rec-maybe"}[recommendation]
    rec_label = {
        "Yes": "Shortlist this candidate",
        "No": "Do not shortlist",
        "Maybe": "Borderline — consider",
    }[recommendation]

    # The Shortlist button is only offered when the AI actually recommends it
    # (Yes / Maybe). It calls the status endpoint and fires ``statusChanged``
    # so the profile page reloads with the updated header badge + dropdown.
    shortlist_btn = ""
    if recommendation in ("Yes", "Maybe"):
        shortlist_btn = (
            f'<button class="btn btn-primary" onclick="shortlistCandidate({application_id})">'
            f'Shortlist candidate</button>'
        )

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
            {shortlist_btn}
            {generate_button}
        </div>
    </div>
    """


def _render_bullets(text: str) -> str:
    items = []
    for line in str(text or "").splitlines():
        item = line.strip().lstrip("-•* ").strip()
        if item:
            items.append(item)
    if not items:
        return "<p>—</p>"
    lis = "".join(f"<li>{_e(item)}</li>" for item in items)
    return f'<ul class="ai-bullets">{lis}</ul>'


# --------------------------------------------------------------------------- #
# LLM response parser                                                         #
# --------------------------------------------------------------------------- #

def parse_screening_response(text: str) -> dict:
    """Parse the LLM screening response into structured fields.

    Expected format (see prompts/screening_system_prompt.txt):
        Recommendation: <Yes | No | Maybe>
        Reasoning: <2-3 sentences>

    Any deviation is handled gracefully — a missing recommendation falls
    back to ``Maybe`` and any free-form text is captured as the reasoning.
    """
    recommendation = "Maybe"
    reasoning_lines: list[str] = []
    current: str | None = None

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
            elif token_lc.startswith("no"):
                recommendation = "No"
            elif token_lc.startswith("maybe") or token_lc.startswith("perhaps"):
                recommendation = "Maybe"
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
    return {
        "Recommendation": recommendation,
        "Reasoning": reasoning,
    }


# --------------------------------------------------------------------------- #
# Utilities                                                                   #
# --------------------------------------------------------------------------- #

