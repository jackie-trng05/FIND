"""HTML fragment builders for the HTMX frontend.

The backend returns small HTML snippets that HTMX swaps into the page. Keeping
the markup here separates presentation from the route/handler logic.
"""

from datetime import date
from html import escape
import os

# Values allowed for the job-type select controls.
JOB_TYPES = ("Full time", "Part time", "Casual", "Contract")

# Browser-facing URL of Student 3's Application service (for apply/view links).
APPLICATIONS_PUBLIC_URL = os.getenv("APPLICATIONS_PUBLIC_URL", "http://localhost:16010")


def _e(value) -> str:
    return escape(str(value if value is not None else ""))


def _status_badge(status: str) -> str:
    css = "badge-success" if status == "Published" else "badge-warning"
    return f'<span class="badge {css}">{_e(status)}</span>'


def normalize_requirements(text: str) -> str:
    """Normalise requirements input into one bullet-prefixed item per line.

    Accepts existing bullet lists, newline-separated lists, or semicolon-
    separated lists. Deduplicates case-insensitively while preserving order.
    """
    if not text:
        return ""
    # Split on newlines then further split each part on semicolons.
    parts: list[str] = []
    for line in str(text).splitlines():
        for chunk in line.split(";"):
            parts.append(chunk)
    seen: set[str] = set()
    items: list[str] = []
    for raw in parts:
        item = raw.strip().lstrip("-•* ").strip()
        if not item:
            continue
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        items.append(item)
    return "\n".join(f"- {item}" for item in items)


def _requirements_html(text: str) -> str:
    """Render a stored requirements string as a bullet list."""
    items = []
    for line in str(text or "").splitlines():
        item = line.strip().lstrip("-•* ").strip()
        if item:
            items.append(item)
    if not items:
        return "—"
    lis = "".join(f"<li>{_e(item)}</li>" for item in items)
    return f'<ul class="requirements-list">{lis}</ul>'


def render_message(message: str, kind: str = "info") -> str:
    """Render an inline message. Errors use the shared alert styling."""
    if kind == "error":
        return f'<div class="alert alert-error">{_e(message)}</div>'
    if kind == "success":
        return f'<div class="alert alert-success">{_e(message)}</div>'
    return f'<p class="text-sm">{_e(message)}</p>'


# --------------------------------------------------------------------------- #
# List (admin table)                                                          #
# --------------------------------------------------------------------------- #

def render_postings_table(postings, *, frontend_url: str, role: str = "staff") -> str:
    """Table body rows for the main admin list. Each row links to its page."""
    is_applicant = role == "applicant"
    colspan = "4" if is_applicant else "5"
    if not postings:
        return (
            f'<tr><td colspan="{colspan}" class="empty-state">'
            "No job postings found.</td></tr>"
        )
    rows = []
    for p in postings:
        pid = p["JobPosting_Id"]
        link = f"{frontend_url}/postings/{pid}"
        status_cell = "" if is_applicant else f"<td>{_status_badge(p['JobPosting_Status'])}</td>"
        rows.append(
            f"""
        <tr class="posting-row" onclick="window.location='{link}'">
            <td class="cell-title">{_e(p['Job_Title'])}</td>
            <td>{_e(p['Job_Type'])}</td>
            <td>{_e(p['Location'])}</td>
            {status_cell}
            <td class="cell-action">
                <a class="btn btn-secondary btn-sm" href="{link}"
                   onclick="event.stopPropagation()">View</a>
            </td>
        </tr>"""
        )
    return "".join(rows)


# --------------------------------------------------------------------------- #
# Single posting page (detail + actions + inline editor)                      #
# --------------------------------------------------------------------------- #

def render_posting_panel(posting: dict, *, backend_url: str, frontend_url: str, role: str = "staff", existing_application: dict | None = None) -> str:
    """Full detail panel for a single posting page: info + management actions.

    ``existing_application`` is passed by the applicant view so that when the
    current candidate already has an active application for this posting,
    the panel shows a single "View Application" button that links directly to
    that draft/submitted application page.
    """
    pid = posting["JobPosting_Id"]
    base = f"{backend_url}/job-postings/{pid}"
    published = posting["JobPosting_Status"] == "Published"
    is_applicant = role == "applicant"

    if is_applicant:
        apply_url = f"{APPLICATIONS_PUBLIC_URL}/apply/{pid}"
        if existing_application and existing_application.get("application_id"):
            app_id = existing_application["application_id"]
            view_url = f"{APPLICATIONS_PUBLIC_URL}/applications/{app_id}"
            actions_html = (
                '<div class="panel-actions">'
                f'<a class="btn btn-primary" href="{view_url}" '
                'title="View your application">View Application</a>'
                '</div>'
            )
        else:
            actions_html = (
                '<div class="panel-actions">'
                f'<a class="btn btn-primary" href="{apply_url}" '
                'title="Apply for this job">Apply</a>'
                '</div>'
            )
        status_badge_html = ""
    else:
        if published:
            status_action = (
                f'<button class="btn btn-secondary" hx-put="{base}/unpublish" '
                f'hx-target="#posting-panel" hx-swap="innerHTML" '
                f'hx-confirm="Are you sure you want to unpublish this job posting?">Unpublish</button>'
            )
        else:
            status_action = (
                f'<button class="btn btn-primary" hx-put="{base}/publish" '
                f'hx-target="#posting-panel" hx-swap="innerHTML" '
                f'hx-confirm="Are you sure you want to publish this job posting?">Publish</button>'
            )
        actions_html = f"""
        <div class="panel-actions">
            <button class="btn btn-secondary" hx-get="{base}/edit"
                    hx-target="#posting-panel" hx-swap="innerHTML">Edit</button>
            {status_action}
            <button class="btn btn-danger" hx-delete="{base}"
                    hx-confirm="Delete this job posting permanently? This cannot be undone.">Delete</button>
        </div>"""
        status_badge_html = _status_badge(posting['JobPosting_Status'])

    # Requirements rendered as a bullet list; other fields as plain text.
    plain_fields = [
        ("Type", posting["Job_Type"]),
        ("Location", posting["Location"]),
        ("Salary range", posting["Salary_Range"]),
        ("Application deadline", posting["Application_Deadline"]),
    ]
    if not is_applicant:
        plain_fields.append(("Published", posting["JobPosting_PublishedAt"] or "—"))
    rows = "".join(
        f"<tr><th>{_e(label)}</th><td>{_e(value)}</td></tr>"
        for label, value in plain_fields
    )
    rows += (
        f"<tr><th>Requirements</th><td>{_requirements_html(posting['Requirements'])}</td></tr>"
    )

    return f"""
    <div class="panel-head">
        <div class="panel-heading">
            <h2>{_e(posting['Job_Title'])}</h2>
            {status_badge_html}
        </div>{actions_html}
    </div>
    <p class="posting-desc">{_e(posting['Job_Description'])}</p>
    <table class="detail-table">{rows}</table>
    """


# --------------------------------------------------------------------------- #
# Create / edit form                                                          #
# --------------------------------------------------------------------------- #

def _job_type_options(selected: str = "") -> str:
    opts = []
    for jt in JOB_TYPES:
        sel = " selected" if jt == selected else ""
        opts.append(f'<option value="{_e(jt)}"{sel}>{_e(jt)}</option>')
    return "".join(opts)


_REQ = '<span class="req" title="Required">*</span>'


def _ai_section(backend_url: str) -> str:
    """AI helper rendered inside the create form, next to Requirements."""
    return f"""
        <div class="ai-panel">
            <div class="ai-panel-head">
                <span class="ai-panel-title">AI suggestions</span>
                <div class="ai-actions">
                    <button type="button" id="ai-btn" class="btn btn-accent btn-sm"
                            hx-post="{backend_url}/ai/suggest-skills"
                            hx-include="[name='Job_Title'],[name='Job_Type'],[name='Job_Description']"
                            hx-target="#ai-suggestions" hx-swap="innerHTML"
                            hx-indicator="#ai-spinner" hx-disabled-elt="this">Generate</button>
                    <span id="ai-spinner" class="htmx-indicator ai-spinner">
                        <span class="spinner"></span> Thinking…
                    </span>
                </div>
            </div>
            <div id="ai-suggestions"></div>
        </div>"""





def render_posting_form(backend_url: str, posting: dict | None = None, *, error: str = "") -> str:
    """Create/Edit form. When ``posting`` is given the form edits it (PUT).

    Staff ID is assigned automatically by the backend and is not shown here.
    In create mode the form embeds an AI helper that suggests requirements.
    """
    editing = posting is not None
    p = posting or {}
    today = date.today().isoformat()

    if editing:
        pid = p["JobPosting_Id"]
        hx_attrs = (
            f'hx-put="{backend_url}/job-postings/{pid}" '
            f'hx-target="#posting-panel" hx-swap="innerHTML"'
        )
        submit_label = "Save changes"
        heading_html = "<h3>Edit posting</h3>"
        msg_area = f'<div class="form-alert">{render_message(error, "error") if error else ""}</div>'
        cancel_btn = (
            f'<button type="button" class="btn btn-secondary" '
            f'hx-get="{backend_url}/job-postings/{pid}" '
            f'hx-target="#posting-panel" hx-swap="innerHTML">Cancel</button>'
        )
        ai_section = _ai_section(backend_url)
    else:
        hx_attrs = (
            f'hx-post="{backend_url}/job-postings" hx-target="#form-msg" '
            f'hx-swap="innerHTML"'
        )
        submit_label = "Create posting"
        heading_html = ""
        msg_area = '<div id="form-msg"></div>'
        cancel_btn = '<a class="btn btn-secondary" href="/">Cancel</a>'
        ai_section = _ai_section(backend_url)

    return f"""
    <form class="posting-form" {hx_attrs}>
        {heading_html}
        {msg_area}
        <div class="form-group">
            <label class="form-label">Job title {_REQ}</label>
            <input class="form-input" name="Job_Title" required maxlength="120"
                   value="{_e(p.get('Job_Title', ''))}">
        </div>
        <div class="grid grid-2">
            <div class="form-group">
                <label class="form-label">Job type {_REQ}</label>
                <select class="form-select" name="Job_Type" required>{_job_type_options(p.get('Job_Type', 'Full time'))}</select>
            </div>
            <div class="form-group">
                <label class="form-label">Location {_REQ}</label>
                <input class="form-input" name="Location" required maxlength="120"
                       value="{_e(p.get('Location', ''))}">
            </div>
        </div>
        <div class="grid grid-2">
            <div class="form-group">
                <label class="form-label">Salary range</label>
                <input class="form-input" name="Salary_Range" maxlength="60"
                       value="{_e(p.get('Salary_Range', ''))}">
            </div>
            <div class="form-group">
                <label class="form-label">Application deadline</label>
                <input class="form-input" name="Application_Deadline" type="date" min="{today}"
                       value="{_e(p.get('Application_Deadline', ''))}">
            </div>
        </div>
        <div class="form-group">
            <label class="form-label">Description {_REQ}</label>
            <textarea class="form-textarea" name="Job_Description" rows="3" required maxlength="2000">{_e(p.get('Job_Description', ''))}</textarea>
        </div>
        <div class="form-group">
            <label class="form-label">Requirements {_REQ}</label>
            <textarea class="form-textarea" name="Requirements" rows="3" required maxlength="2000">{_e(p.get('Requirements', ''))}</textarea>
            {ai_section}
        </div>
        <div class="form-actions">
            <button class="btn btn-primary" type="submit">{_e(submit_label)}</button>
            {cancel_btn}
        </div>
    </form>
    """


# --------------------------------------------------------------------------- #
# AI suggestions                                                              #
# --------------------------------------------------------------------------- #

def dedupe_lines(text: str) -> list[str]:
    """Split model output into unique, non-empty, stripped lines.

    Duplicate bullet items (a common small-model failure) are removed
    case-insensitively while preserving order.
    """
    seen: set[str] = set()
    out: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        key = line.lower().lstrip("-•* ").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(line)
    return out


def render_skill_suggestions(text: str) -> str:
    """Render AI suggestions as selectable checkboxes.

    Bullet items become checkboxes the staff can tick and add to the
    Requirements field. Non-bullet lines render as small subheadings. Duplicate
    items (a common small-model failure) are removed case-insensitively.
    """
    lines = dedupe_lines(text)
    parts: list[str] = []
    has_items = False
    for line in lines:
        is_bullet = line[:1] in ("-", "•", "*")
        content = line.lstrip("-•* ").strip()
        if not content:
            continue
        if is_bullet:
            has_items = True
            parts.append(
                '<label class="ai-check">'
                f'<input type="checkbox" class="ai-check-input" value="{_e(content)}">'
                f"<span>{_e(content)}</span></label>"
            )
        else:
            parts.append(f'<h5 class="ai-subhead">{_e(content)}</h5>')

    if not has_items:
        body = "".join(parts) or f"<p>{_e(text)}</p>"
        return f'<div class="ai-result">{body}</div>'

    return (
        '<div class="ai-result">'
        '<div class="ai-result-head">'
        '<span class="ai-result-title">Select the requirements to add</span>'
        '<button type="button" class="btn btn-secondary btn-sm ai-add-btn" '
        'onclick="syncAiSelections(this)">Update requirements</button>'
        "</div>"
        '<div class="ai-checks">' + "".join(parts) + "</div>"
        "</div>"
    )
