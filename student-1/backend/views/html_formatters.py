"""HTML fragment builders for the HTMX frontend.

The backend returns small HTML snippets that HTMX swaps into the page. Keeping
the markup here separates presentation from the route/handler logic.
"""

from html import escape


def _e(value) -> str:
    return escape(str(value if value is not None else ""))


def render_message(message: str, kind: str = "info") -> str:
    """Render an inline message. Errors/success use the shared alert styling."""
    if kind == "error":
        return f'<div class="alert alert-error">{_e(message)}</div>'
    if kind == "success":
        return f'<div class="alert alert-success">{_e(message)}</div>'
    return f'<p class="text-sm">{_e(message)}</p>'


# --------------------------------------------------------------------------- #
# User details (first/last name, shared users table)                          #
# --------------------------------------------------------------------------- #

def render_user_details_panel(user: dict, *, backend_url: str, error: str = "") -> str:
    error_html = render_message(error, "error") if error else ""
    return f"""
    <h2 style="margin-bottom:1rem;">User Details</h2>
    <div id="user-details-msg">{error_html}</div>
    <form hx-put="{backend_url}/user" hx-target="#user-details-panel" hx-swap="innerHTML">
        <div class="grid grid-2">
            <div class="form-group">
                <label class="form-label" for="ud_first_name">First Name <span class="required-marker">*</span></label>
                <input class="form-input" type="text" id="ud_first_name" name="first_name"
                       value="{_e(user.get('first_name', ''))}" required>
            </div>
            <div class="form-group">
                <label class="form-label" for="ud_last_name">Last Name <span class="required-marker">*</span></label>
                <input class="form-input" type="text" id="ud_last_name" name="last_name"
                       value="{_e(user.get('last_name', ''))}" required>
            </div>
        </div>
        <button type="submit" class="btn btn-primary">Save Details</button>
    </form>"""


# --------------------------------------------------------------------------- #
# Profile (create/view/edit + delete)                                         #
# --------------------------------------------------------------------------- #

def _ai_profile_section(backend_url: str) -> str:
    """AI helper rendered inside the profile form: suggests fields from the
    applicant's stored resume (professional title, summary, interests).
    Reuses the shared theme's .card/.htmx-indicator/.spinner styling rather
    than introducing new CSS classes."""
    return f"""
        <div class="card" style="margin-top:1rem;padding:1rem;">
            <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:0.5rem;">
                <span style="font-weight:600;font-size:0.9rem;">AI Assistant</span>
                <div style="display:flex;align-items:center;gap:0.5rem;">
                    <button type="button" id="ai-profile-btn" class="btn btn-accent btn-sm"
                            hx-post="{backend_url}/profile/ai-suggestions"
                            hx-target="#ai-profile-suggestions" hx-swap="innerHTML"
                            hx-indicator="#ai-profile-spinner" hx-disabled-elt="this">
                        Suggest from my resume
                    </button>
                    <span id="ai-profile-spinner" class="htmx-indicator" style="font-size:0.85rem;color:var(--text-muted);">
                        <span class="spinner" style="vertical-align:middle;margin-right:0.35rem;"></span>Thinking…
                    </span>
                </div>
            </div>
            <div id="ai-profile-suggestions" style="margin-top:0.75rem;"></div>
        </div>"""


def render_profile_panel(profile: dict | None, *, backend_url: str, role: str = "applicant", message: str = "", kind: str = "error") -> str:
    """Full profile card: create-prompt + form if no profile, else the
    pre-filled update form and delete button. Nests the resume panel
    (applicants only; staff never manage resumes)."""
    message_html = render_message(message, kind) if message else ""
    no_profile_html = (
        '<div class="alert alert-warning">You do not have a profile yet. Create one below.</div>'
        if not profile else ""
    )

    if profile:
        submit_label = "Update Profile"
        form_attrs = f'hx-put="{backend_url}/profile/{profile["profile_id"]}"'
        delete_btn = f"""
        <div style="margin-top:1.5rem;">
            <button type="button" class="btn btn-danger"
                    hx-delete="{backend_url}/profile/{profile['profile_id']}"
                    hx-target="#profile-panel" hx-swap="innerHTML"
                    hx-confirm="Are you sure you want to delete your profile? This will also delete your resume.">
                Delete Profile
            </button>
        </div>"""
    else:
        submit_label = "Create Profile"
        form_attrs = f'hx-post="{backend_url}/profile"'
        delete_btn = ""

    profile = profile or {}
    resume_section = ""
    ai_section = ""
    if role != "staff":
        resume_section = """
        <div style="margin-top:2rem;padding-top:1.5rem;border-top:1px solid var(--border);">
            <div id="resume-panel" hx-get="%s/resume" hx-trigger="load, profileChanged from:body" hx-swap="innerHTML"></div>
        </div>""" % backend_url
        ai_section = _ai_profile_section(backend_url)

    return f"""
    <h2 style="margin-bottom:1rem;">User Profile</h2>
    {no_profile_html}
    <form {form_attrs} hx-target="#profile-panel" hx-swap="innerHTML">
        <div class="grid grid-2">
            <div class="form-group">
                <label class="form-label" for="phone">Phone <span class="required-marker">*</span></label>
                <input class="form-input" type="tel" id="phone" name="phone"
                       value="{_e(profile.get('phone', ''))}" required>
            </div>
            <div class="form-group">
                <label class="form-label" for="location">Location</label>
                <input class="form-input" type="text" id="location" name="location"
                       value="{_e(profile.get('location', ''))}">
            </div>
        </div>
        <div class="form-group">
            <label class="form-label" for="professional_title">Professional Title</label>
            <input class="form-input" type="text" id="professional_title" name="professional_title"
                   value="{_e(profile.get('professional_title', ''))}">
        </div>
        <div class="form-group">
            <label class="form-label" for="summary">Summary</label>
            <textarea class="form-input" id="summary" name="summary" rows="3">{_e(profile.get('summary', ''))}</textarea>
        </div>
        <div class="form-group">
            <label class="form-label" for="interests">Interests</label>
            <input class="form-input" type="text" id="interests" name="interests"
                   placeholder="Comma-separated interests" value="{_e(profile.get('interests', ''))}">
        </div>
        {ai_section}
        <button type="submit" class="btn btn-primary">{submit_label}</button>
        <div id="profile-msg">{message_html}</div>
    </form>
    {delete_btn}
    {resume_section}"""


# --------------------------------------------------------------------------- #
# Resumes (single resume per profile)                                         #
# --------------------------------------------------------------------------- #

def _file_type_label(mime: str) -> str:
    return "PDF" if "pdf" in (mime or "") else (mime or "")


def render_resume_panel(profile_id: int | None, resumes: list, *, backend_url: str, message: str = "", kind: str = "error") -> str:
    """Resume table + upload form, or a "create your profile first" prompt."""
    message_html = render_message(message, kind) if message else ""

    if profile_id is None:
        return f"""
        <h3 style="margin-bottom:1rem;">My Resumes</h3>
        <div class="alert alert-warning">Create your profile above to upload a resume.</div>
        <div id="resume-msg">{message_html}</div>"""

    if resumes:
        r = resumes[0]
        rows = f"""
        <tr>
            <td>{_e(r['file_name'])}</td>
            <td><span class="badge">{_e(_file_type_label(r.get('file_type', '')))}</span></td>
            <td>{_e(r.get('uploaded_at', ''))}</td>
            <td>
                <a href="{backend_url}/resume/{r['resume_id']}/download" class="btn btn-secondary btn-sm">Download</a>
                <button type="button" class="btn btn-danger btn-sm"
                        hx-delete="{backend_url}/resume/{r['resume_id']}"
                        hx-target="#resume-panel" hx-swap="innerHTML"
                        hx-confirm="Delete this resume?">Delete</button>
            </td>
        </tr>"""
        upload_section = f"""
        <div id="resume-msg">{message_html}</div>
        <p class="form-help">Delete the current resume to upload a replacement.</p>"""
    else:
        rows = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted);">No resumes uploaded yet.</td></tr>'
        upload_section = f"""
        <h3 style="margin-bottom:0.75rem;">Upload Resume</h3>
        <form hx-post="{backend_url}/resume" hx-target="#resume-panel" hx-swap="innerHTML"
              hx-encoding="multipart/form-data">
            <div class="form-group">
                <label class="form-label" for="resume-file">Choose file (PDF only &mdash; max 5MB)</label>
                <input class="form-input" type="file" id="resume-file" name="file" accept=".pdf" required>
            </div>
            <button type="submit" class="btn btn-secondary">Upload</button>
            <div id="resume-msg">{message_html}</div>
        </form>"""

    return f"""
    <h3 style="margin-bottom:1rem;">My Resumes</h3>
    <div class="table-wrapper" style="margin-bottom:1.5rem;">
        <table>
            <thead>
                <tr><th>File Name</th><th>Type</th><th>Uploaded</th><th>Actions</th></tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
    {upload_section}"""


# --------------------------------------------------------------------------- #
# AI suggestions (profile autofill from resume)                               #
# --------------------------------------------------------------------------- #

def render_profile_suggestions(parsed: dict) -> str:
    """Render the AI's suggested profile fields, each with an Apply button.

    ``parsed`` is the dict returned by ``llm_client.parse_profile_suggestions``
    (professional_title, summary, interests, note). A non-empty ``note`` is
    shown as a caution banner (e.g. when the resume was unreadable and the
    suggestions are generic rather than tailored).
    """
    note = (parsed.get("note") or "").strip()
    note_html = f'<div class="alert alert-warning">{_e(note)}</div>' if note else ""

    field_targets = (
        ("professional_title", "Professional Title"),
        ("summary", "Summary"),
        ("interests", "Interests"),
    )
    rows = []
    for field_id, label in field_targets:
        value = (parsed.get(field_id) or "").strip()
        if not value:
            continue
        rows.append(f"""
        <div style="display:flex;align-items:center;justify-content:space-between;gap:0.75rem;padding:0.5rem 0;border-bottom:1px solid var(--border);font-size:0.9rem;">
            <div><strong>{_e(label)}:</strong> <span>{_e(value)}</span></div>
            <button type="button" class="btn btn-secondary btn-sm"
                    data-target="{field_id}" data-value="{_e(value)}"
                    onclick="applyProfileSuggestion(this)">Apply</button>
        </div>""")

    if not rows:
        return note_html + '<p class="text-sm">The AI did not return any suggestions. Try again.</p>'

    return f"""
    <div>
        {note_html}
        {''.join(rows)}
        <div style="margin-top:0.75rem;">
            <button type="button" class="btn btn-secondary btn-sm"
                    onclick="document.getElementById('ai-profile-suggestions').innerHTML=''">Dismiss</button>
        </div>
    </div>"""
