"""HTML fragment builders for the HTMX frontend.

The backend returns small HTML snippets that HTMX swaps into the page. Keeping
the markup here separates presentation from the route/handler logic.
"""

from datetime import date, datetime
from html import escape

from services.config import (
    BACKEND_PUBLIC_URL,
    DELETABLE_STATUSES,
    EVALUATIONS_URL,
    FRONTEND_PUBLIC_URL,
    INTERVIEWS_URL,
    INTERVIEW_ACTION_STATUSES,
    VALID_STATUSES,
    WITHDRAWABLE_STATUSES,
)


def _e(value):
    return escape(str(value if value is not None else ""))


def _status_badge(status):
    css_map = {
        "Draft": "badge-warning", "Submitted": "badge-info",
        "Shortlisted": "badge-accent", "Interview Requested": "badge-warning",
        "Interview Scheduled": "badge-info", "Interview Completed": "badge-accent",
        "Evaluation In Progress": "badge-warning", "Hired": "badge-success",
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
            <a class="resume-current-name"
               href="{FRONTEND_PUBLIC_URL}/resumes/{resume['resume_id']}/download">{_e(resume.get('file_name', 'resume.pdf'))}</a>
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
                    <legend>
                        <span class="legend-title">Your details</span>
                        <span class="legend-note">Auto-filled from your profile.</span>
                    </legend>
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
                    <legend>
                        <span class="legend-title">Resume</span>
                        {f'<span class="legend-note">Auto-filled from your profile.</span>' if editing and resume and resume.get('from_profile') else ''}
                    </legend>
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
            f' href="{INTERVIEWS_URL}/schedule?application_id={aid}">Schedule Interview</a>'
        )
    actions_html = f'<div class="panel-actions">{"".join(actions)}</div>' if actions else ""

    if resume is not None:
        resume_block = f"""
        <div class="resume-current">
            <span class="resume-current-label">Uploaded file:</span>
            <a class="resume-current-name"
               href="{FRONTEND_PUBLIC_URL}/resumes/{resume['resume_id']}/download">
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
    opts = []
    for status in VALID_STATUSES:
        if status in ("Draft", "Withdrawn"):
            continue
        attrs = []
        if status == current:
            attrs.append("selected")
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
        status_badge = _status_badge(a["application_status"])

        interview_btn = ""
        if a["application_status"] == "Shortlisted":
            interview_btn = (
                f'<a class="btn btn-accent btn-sm" target="_blank" rel="noopener"'
                f' href="{INTERVIEWS_URL}/schedule?application_id={aid}">Interview</a>'
            )
        evaluate_btn = ""
        if a["application_status"] == "Interview Completed":
            evaluate_btn = (
                f'<a class="btn btn-primary btn-sm" target="_blank" rel="noopener"'
                f' href="{EVALUATIONS_URL}/evaluate/{aid}">Evaluate</a>'
            )
        elif a["application_status"] == "Evaluation In Progress":
            evaluate_btn = (
                f'<a class="btn btn-accent btn-sm" target="_blank" rel="noopener"'
                f' href="{EVALUATIONS_URL}/evaluate/{aid}">Continue Evaluation</a>'
            )
        actions_html = interview_btn + evaluate_btn
        rows.append(f"""
        <tr class="application-row" data-href="{detail_link}">
            <td class="cell-id">#{aid}</td>
            <td class="cell-title">{_e(title)}</td>
            <td>{_e(candidate_name)}</td>
            <td>{status_badge}</td>
            <td class="cell-action-center cell-interactive">{actions_html}</td>
        </tr>""")
    return "".join(rows)


def render_pending_interviews_bar(applications):
    to_schedule = [a for a in applications if a["application_status"] == "Shortlisted"]
    to_evaluate = [a for a in applications if a["application_status"] == "Interview Completed"]
    in_progress = [a for a in applications if a["application_status"] == "Evaluation In Progress"]
    if not to_schedule and not to_evaluate and not in_progress:
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
    if in_progress:
        parts.append(
            f'<span class="pending-item"><strong>{len(in_progress)}</strong> '
            "evaluations in progress</span>"
        )
    return f'<div class="pending-bar">{"".join(parts)}</div>'


def _render_resume_row(resume):
    if resume is None:
        return "<p>No resume uploaded.</p>"
    return f"""
    <table class="detail-table">
        <tr><th>File</th>
            <td>
                <a class="btn btn-secondary btn-sm"
                   href="{FRONTEND_PUBLIC_URL}/resumes/{resume['resume_id']}/download">
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


def render_candidate_profile(application, posting, user, resume, screening, profile=None):
    aid = application["application_id"]
    status = application["application_status"]
    profile = profile or {}
    resume_html = _render_resume_row(resume)
    ai_section_html = ""
    if status == "Submitted":
        ai_html = render_ai_screening_panel(aid, screening)
        ai_section_html = f"""
    <section class="ai-section">
        <h3>AI Screening</h3>
        <div id="ai-screening-panel">{ai_html}</div>
    </section>"""

    manual_actions_html = ""
    if status != "Rejected":
        shortlist_button = ""
        if status == "Submitted":
            shortlist_button = f"""
            <button type="button" class="btn btn-primary btn-sm"
                    data-shortlist-application-id="{aid}">
                Shortlist candidate
            </button>"""
        manual_actions_html = f"""
        <div class="ai-manual-actions">
            {shortlist_button}
            <button type="button" class="btn btn-danger btn-sm"
                    data-reject-application-id="{aid}">
                Reject candidate
            </button>
        </div>"""

    return f"""
    <div id="profile-msg"></div>
    <div class="panel-head">
        <div class="panel-heading">
            <h2>{_e(user.get('user_first_name', ''))} {_e(user.get('user_last_name', ''))}</h2>
            {_status_badge(status)}
        </div>
    </div>

    <div class="detail-grid detail-grid-single">
        <section>
            <h3>Candidate Information</h3>
            <table class="detail-table">
                <tr><th>First name</th><td>{_e(user.get('user_first_name', '—'))}</td></tr>
                <tr><th>Last name</th><td>{_e(user.get('user_last_name', '—'))}</td></tr>
                <tr><th>Email</th><td>{_e(user.get('user_email', '—'))}</td></tr>
                <tr><th>Phone</th><td>{_e(profile.get('phone', '—'))}</td></tr>
                <tr><th>Location</th><td>{_e(profile.get('location', '—'))}</td></tr>
                <tr><th>Professional title</th><td>{_e(profile.get('professional_title', '—'))}</td></tr>
                <tr><th>Summary</th><td>{_e(profile.get('summary', '—'))}</td></tr>
                <tr><th>Interests</th><td>{_e(profile.get('interests', '—'))}</td></tr>
                <tr><th>Applied position</th><td>{_e(posting.get('Job_Title', '—'))}</td></tr>
                <tr><th>Date submitted</th><td>{_format_date(application.get('submitted_at') or '')}</td></tr>
            </table>
            <h4 class="section-subhead">Uploaded Resume</h4>
            {resume_html}
        </section>
    </div>

    {ai_section_html}
    {manual_actions_html}
    """
