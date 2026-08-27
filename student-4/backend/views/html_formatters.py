from html import escape

STATUS_CLASSES = {
    "scheduled": "status-scheduled",
    "accepted": "status-accepted",
    "declined": "status-declined",
    "rescheduled": "status-rescheduled",
    "completed": "status-completed",
    "cancelled": "status-cancelled",
}

def _status_badge(status):
    status = (status or "").strip()
    css_class = STATUS_CLASSES.get(status.lower(), "status-scheduled")
    return f'<span class="badge {css_class}">{escape(status)}</span>'


def _field(interview, key, default=""):
    return escape(str(interview.get(key, default) or default))


def format_interviews_html(interviews):
    if not interviews:
        return "<p>No interviews found.</p>"

    rows = ""
    for interview in interviews:
        rows += f"""
        <tr>
            <td>{_field(interview, 'interview_id')}</td>
            <td>{_field(interview, 'application_id')}</td>
            <td>{_field(interview, 'staff_id')}</td>
            <td>{_field(interview, 'interview_datetime')}</td>
            <td>{_status_badge(interview.get('interview_status'))}</td>
            <td>{_field(interview, 'interview_notes')}</td>
        </tr>"""

    return f"""
    <table class="data-table">
        <thead>
            <tr>
                <th>ID</th>
                <th>Application</th>
                <th>Staff</th>
                <th>Date &amp; Time</th>
                <th>Status</th>
                <th>Notes</th>
            </tr>
        </thead>
        <tbody>{rows}
        </tbody>
    </table>"""


def format_interview_html(interview):
    link = interview.get("interview_link") or ""
    link_html = (
        f'<a href="{escape(link)}" target="_blank">{escape(link)}</a>'
        if link
        else "No link provided"
    )

    return f"""
    <div class="interview-detail">
        <p><strong>Interview ID:</strong> {_field(interview, 'interview_id')}</p>
        <p><strong>Application ID:</strong> {_field(interview, 'application_id')}</p>
        <p><strong>Staff ID:</strong> {_field(interview, 'staff_id')}</p>
        <p><strong>Date &amp; Time:</strong> {_field(interview, 'interview_datetime')}</p>
        <p><strong>Status:</strong> {_status_badge(interview.get('interview_status'))}</p>
        <p><strong>Meeting Link:</strong> {link_html}</p>
        <p><strong>Notes:</strong> {_field(interview, 'interview_notes')}</p>
    </div>"""


# --------------------------------------------------------------------------- #
# HTMX fragment builders (used by the /ui/* endpoints)                        #
# --------------------------------------------------------------------------- #

import json
from datetime import datetime

# Skill areas assessed before an interview can be completed.
NOTE_SECTIONS = (
    "Technical",
    "Education",
    "Communication",
    "Problem Solving",
    "Professionalism",
)

# Interview status -> themed badge class (matches the shared design system).
_INTERVIEW_BADGE = {
    "shortlisted": "badge-warning",
    "interview requested": "badge-warning",
    "interview scheduled": "badge-info",
    "interview completed": "badge-success",
    "withdrawn": "badge-danger",
}


def _interview_badge(status):
    status = (status or "").strip()
    cls = _INTERVIEW_BADGE.get(status.lower(), "badge-muted")
    return f'<span class="badge {cls}">{escape(status)}</span>'


def _parse_dt(value):
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(str(value).strip(), fmt)
        except (TypeError, ValueError):
            continue
    return None


def _fmt_dt(value):
    dt = _parse_dt(value)
    if not dt:
        return escape(str(value or "—"))
    return dt.strftime("%a %d %b %Y, %H:%M")


def _parse_notes(raw):
    if not raw:
        return None
    if isinstance(raw, dict):
        return raw
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else None
    except (ValueError, TypeError):
        return None


# ---- List page ------------------------------------------------------------ #

def render_interview_rows(interviews, role="staff", sort="datetime", direction="asc", backend_url=""):
    """Full sortable interviews table for the list page (HTMX target)."""
    is_staff = role == "staff"
    person_head = "Applicant" if is_staff else "Interviewer"

    def _sort_key(item):
        if sort == "person":
            return (item.get("applicant_name") if is_staff else item.get("staff_name")) or ""
        if sort == "posting":
            return item.get("job_posting_title") or ""
        if sort == "status":
            return item.get("interview_status") or ""
        dt = _parse_dt(item.get("interview_datetime"))
        return dt.timestamp() if dt else 0

    rows = sorted(interviews, key=_sort_key, reverse=(direction == "desc"))

    def _th(key, label):
        arrow = ""
        if sort == key:
            arrow = " ▲" if direction == "asc" else " ▼"
        nxt = "desc" if (sort == key and direction == "asc") else "asc"
        return (
            f'<th class="sortable" '
            f'hx-get="{backend_url}/ui/interviews/rows" '
            f'hx-target="#list-body" hx-include="#list-filters" '
            f'hx-vals=\'{{"sort":"{key}","dir":"{nxt}"}}\'>'
            f'{label}{arrow}</th>'
        )

    head = (
        "<thead><tr>"
        + _th("person", person_head)
        + _th("posting", "Job Posting")
        + _th("datetime", "Date &amp; Time")
        + _th("status", "Status")
        + "<th></th></tr></thead>"
    )

    if not rows:
        return (
            f'<table class="data-table">{head}<tbody>'
            '<tr><td colspan="5" class="empty-state">No interviews match your filters.</td></tr>'
            "</tbody></table>"
        )

    body = ""
    for it in rows:
        person = (it.get("applicant_name") if is_staff else it.get("staff_name")) or "—"
        link = f"/interview/{escape(str(it.get('interview_id')))}?from=list"
        body += f"""
        <tr class="clickable application-row" data-href="{link}">
            <td>{escape(str(person))}<div class="meta">Application #{escape(str(it.get('application_id')))}</div></td>
            <td>{escape(str(it.get('job_posting_title') or '—'))}</td>
            <td>{_fmt_dt(it.get('interview_datetime'))}</td>
            <td>{_interview_badge(it.get('interview_status'))}</td>
            <td class="cell-action"><a class="btn btn-secondary btn-sm" href="{link}">View</a></td>
        </tr>"""
    return f'<table class="data-table">{head}<tbody>{body}</tbody></table>'


# ---- Calendar ------------------------------------------------------------- #

_DOW = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
_CAL_STATUS = {
    "shortlisted": "cal-shortlisted",
    "interview requested": "cal-requested",
    "interview scheduled": "cal-scheduled",
    "interview completed": "cal-completed",
    "withdrawn": "cal-withdrawn",
}


def render_calendar(interviews, year, month, backend_url=""):
    """Month grid fragment with prev/next navigation via HTMX."""
    import calendar as _cal

    first_weekday = datetime(year, month, 1).weekday()  # Mon=0
    start_day = (first_weekday + 1) % 7  # convert to Sun=0
    days_in_month = _cal.monthrange(year, month)[1]
    today = datetime.now()
    today_key = (today.year, today.month, today.day)

    events = {}
    for it in interviews:
        dt = _parse_dt(it.get("interview_datetime"))
        if not dt or dt.year != year or dt.month != month:
            continue
        events.setdefault(dt.day, []).append((dt, it))

    title = datetime(year, month, 1).strftime("%B %Y")
    prev_y, prev_m = (year - 1, 12) if month == 1 else (year, month - 1)
    next_y, next_m = (year + 1, 1) if month == 12 else (year, month + 1)

    def _nav(label, y, m):
        return (
            f'<button class="btn btn-secondary btn-sm" type="button" '
            f'hx-get="{backend_url}/ui/calendar" hx-target="#cal-wrap" '
            f'hx-vals=\'{{"year":{y},"month":{m}}}\'>{label}</button>'
        )

    cells = ""
    for _ in range(start_day):
        cells += '<div class="cal-cell empty"></div>'
    for day in range(1, days_in_month + 1):
        is_today = (year, month, day) == today_key
        day_events = sorted(events.get(day, []), key=lambda e: e[0])
        ev_html = ""
        for dt, it in day_events:
            time = dt.strftime("%H:%M")
            label = f"{time} · {escape(str(it.get('applicant_name') or '—'))}"
            cls = _CAL_STATUS.get(str(it.get("interview_status") or "").lower(), "cal-scheduled")
            href = f"/interview/{escape(str(it.get('interview_id')))}?from=calendar"
            ev_html += f'<a class="cal-event {cls}" href="{href}" title="{label}">{label}</a>'
        cells += (
            f'<div class="cal-cell {"today" if is_today else ""}">'
            f'<span class="cal-daynum">{day}</span>{ev_html}</div>'
        )

    dow = "".join(f'<div class="cal-dow">{d}</div>' for d in _DOW)
    return f"""
    <div class="calendar-bar">
        {_nav("&larr; Prev", prev_y, prev_m)}
        <h2>{title}</h2>
        {_nav("Next &rarr;", next_y, next_m)}
    </div>
    <div class="cal-grid">{dow}{cells}</div>"""


# ---- To-schedule / applications ------------------------------------------ #

def render_schedulable_rows(applications):
    if not applications:
        return '<div class="empty-state">No shortlisted applications are waiting to be scheduled.</div>'
    rows = ""
    for app in applications:
        rows += f"""
        <div class="interview-row">
            <div>
                <div class="who">{escape(str(app.get('applicant_name') or '—'))} · Application #{escape(str(app.get('application_id')))}</div>
                <div class="meta">{escape(str(app.get('job_posting_title') or '—'))} (#{escape(str(app.get('job_posting_id')))})</div>
            </div>
            <div class="btn-row">
                {_interview_badge(app.get('application_status'))}
                <a class="btn btn-primary btn-sm" href="/schedule?application_id={escape(str(app.get('application_id')))}">Schedule interview</a>
            </div>
        </div>"""
    return f'<div class="interview-list">{rows}</div>'


def render_schedule_options(applications):
    opts = '<option value="">Select an application…</option>'
    for app in applications:
        opts += (
            f'<option value="{escape(str(app.get("application_id")))}" '
            f'data-applicant-id="{escape(str(app.get("applicant_id") or ""))}" '
            f'data-applicant-name="{escape(str(app.get("applicant_name") or ""))}" '
            f'data-posting-id="{escape(str(app.get("job_posting_id") or ""))}" '
            f'data-posting-title="{escape(str(app.get("job_posting_title") or ""))}">'
            f'#{escape(str(app.get("application_id")))} — {escape(str(app.get("applicant_name") or ""))}'
            f' · {escape(str(app.get("job_posting_title") or ""))}</option>'
        )
    return opts


def render_time_suggestions(slots, note=""):
    """Selectable AI-suggested interview time chips (all in the future).

    Each ``slot`` is a "YYYY-MM-DD HH:MM" string. The schedule page wires a
    click on a chip to fill the date & time field via ``data-datetime``.
    """
    if not slots:
        return (
            '<div class="empty-state">No suitable future times could be suggested. '
            'Try describing your availability above.</div>'
        )
    chips = ""
    for dt in slots:
        chips += (
            f'<button type="button" class="suggest-chip" data-datetime="{escape(str(dt))}">'
            f'{escape(_fmt_dt(dt))}</button>'
        )
    hint = f'<p class="form-hint">{escape(note)}</p>' if note else ""
    return (
        '<div class="ai-result">'
        '<div class="ai-result-head"><span class="ai-result-title">Suggested times</span></div>'
        f'<div class="suggest-chips">{chips}</div>'
        f'{hint}'
        '</div>'
    )



# ---- To-complete ---------------------------------------------------------- #

def render_to_complete_rows(interviews):
    if not interviews:
        return '<div class="empty-state">No interviews are waiting to be completed.</div>'
    rows = ""
    for it in interviews:
        posting = it.get("job_posting_title")
        prefix = f"{escape(str(posting))} · " if posting else ""
        rows += f"""
        <div class="interview-row">
            <div>
                <div class="who">{escape(str(it.get('applicant_name') or '—'))} · Application #{escape(str(it.get('application_id')))}</div>
                <div class="meta">{prefix}Interviewed {_fmt_dt(it.get('interview_datetime'))}</div>
            </div>
            <div class="btn-row">
                {_interview_badge(it.get('interview_status'))}
                <a class="btn btn-primary btn-sm" href="/interview/{escape(str(it.get('interview_id')))}?from=to-complete">Complete Interview</a>
            </div>
        </div>"""
    return f'<div class="interview-list">{rows}</div>'


# ---- Applicant requests --------------------------------------------------- #

def render_requests(interviews, backend_url=""):
    pending = [it for it in interviews if it.get("interview_status") == "Interview Requested"]
    if not pending:
        return '<div class="card"><div class="empty-state">You have no interview requests right now.</div></div>'
    cards = ""
    for it in pending:
        iid = escape(str(it.get("interview_id")))
        notes = it.get("interview_notes")
        notes_html = f'<div class="meta">{escape(str(notes))}</div>' if notes else ""
        posting = it.get("job_posting_title")
        posting_html = f'<div class="meta">{escape(str(posting))}</div>' if posting else ""
        cards += f"""
        <section class="card" style="margin-bottom:1rem;">
            <div class="interview-row" style="border:0;padding:0;">
                <div>
                    <div class="who">{escape(str(it.get('staff_name') or '—'))} · Application #{escape(str(it.get('application_id')))}</div>
                    <div class="meta">{_fmt_dt(it.get('interview_datetime'))}</div>
                    {posting_html}
                    {notes_html}
                </div>
                <div class="btn-row">
                    {_interview_badge(it.get('interview_status'))}
                    <a class="btn btn-secondary btn-sm" href="/interview/{iid}?from=requests">View</a>
                </div>
            </div>
            <div class="btn-row" style="margin-top:1rem;">
                <button class="btn btn-primary btn-sm" type="button"
                        hx-post="{backend_url}/interviews/{iid}/accept"
                        hx-confirm="Accept this interview? Your application will move to Interview Scheduled."
                        hx-swap="none">Accept</button>
                <button class="btn btn-danger btn-sm" type="button"
                        onclick="this.closest('section').querySelector('.decline-box').style.display='block'">Decline</button>
            </div>
            <div class="decline-box" style="display:none;margin-top:0.75rem;">
                <label>Reason for declining (optional)</label>
                <textarea name="reason" rows="2" placeholder="Let the recruiter know why"></textarea>
                <div class="btn-row" style="margin-top:0.5rem;">
                    <button class="btn btn-danger btn-sm" type="button"
                            hx-post="{backend_url}/interviews/{iid}/decline"
                            hx-include="closest .decline-box"
                            hx-confirm="Decline this interview? Declining withdraws your application."
                            hx-swap="none">Decline Interview</button>
                </div>
            </div>
        </section>"""
    return cards


# ---- Detail --------------------------------------------------------------- #

def _detail_rows(interview):
    applicant = escape(str(interview.get("applicant_name") or "—"))
    applicant_id = interview.get("applicant_id")
    if applicant_id:
        applicant += f" (#{escape(str(applicant_id))})"
    posting = interview.get("job_posting_title")
    posting_cell = "—"
    if posting:
        posting_cell = escape(str(posting))
        if interview.get("job_posting_id"):
            posting_cell += f" (#{escape(str(interview.get('job_posting_id')))})"
    link = interview.get("interview_link")
    link_cell = (
        f'<a href="{escape(str(link))}" target="_blank" rel="noopener">{escape(str(link))}</a>'
        if link else "No link provided"
    )
    pairs = [
        ("Applicant", applicant),
        ("Application", f"#{escape(str(interview.get('application_id')))}"),
        ("Job Posting", posting_cell),
        ("Interviewer", f"{escape(str(interview.get('staff_name') or '—'))} (#{escape(str(interview.get('staff_id')))})"),
        ("Date &amp; Time", _fmt_dt(interview.get("interview_datetime"))),
        ("Meeting Link", link_cell),
    ]
    return "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in pairs)


def _notes_view(raw):
    notes = _parse_notes(raw)
    if not notes:
        text = str(raw or "").strip()
        return (
            f'<p class="meta">{escape(text)}</p>' if text
            else '<p class="form-hint">No interview notes yet.</p>'
        )
    items = "".join(
        f"<dt>{escape(s)}</dt><dd>{escape(str(notes.get(s, '')) or '—')}</dd>"
        for s in NOTE_SECTIONS
    )
    return f'<dl class="detail-grid notes-grid">{items}</dl>'


def _notes_form(raw):
    notes = _parse_notes(raw) or {}
    fields = ""
    for s in NOTE_SECTIONS:
        fields += f"""
        <div class="full">
            <label>{escape(s)}</label>
            <textarea name="note-{escape(s)}" rows="2" required placeholder="Notes on {escape(s)}">{escape(str(notes.get(s, '')))}</textarea>
        </div>"""
    return f'<div class="notes-form">{fields}</div>'


def render_interview_detail(interview, role, backend_url="", is_past=False):
    """Detail card with role/status-appropriate HTMX actions."""
    is_staff = role == "staff"
    status = interview.get("interview_status")
    iid = escape(str(interview.get("interview_id")))

    actions = ""
    extra = ""
    if is_staff:
        if status not in ("Interview Completed", "Withdrawn"):
            actions = f"""
            <div class="btn-row" style="margin-top:1.25rem;">
                <button class="btn btn-danger" type="button"
                        hx-delete="{backend_url}/interviews/{iid}"
                        hx-confirm="Cancel this interview? This removes the interview request."
                        hx-swap="none">Cancel Interview</button>
            </div>"""
        if status == "Interview Completed":
            extra = f'<div style="margin-top:1.5rem;"><h2>Interview notes</h2>{_notes_view(interview.get("interview_notes"))}</div>'
        elif status == "Interview Scheduled" and is_past:
            extra = f"""
            <div style="margin-top:1.5rem;">
                <h2>Complete Interview</h2>
                <p class="form-hint">Write up all five skill areas to mark this interview complete.</p>
                <form hx-post="{backend_url}/interviews/{iid}/complete" hx-swap="none">
                    {_notes_form(interview.get("interview_notes"))}
                    <div class="btn-row" style="margin-top:0.75rem;">
                        <button class="btn btn-primary" type="submit"
                                hx-confirm="Complete this interview? The notes will be saved and the interview marked Interview Completed.">Complete Interview</button>
                    </div>
                </form>
            </div>"""
        elif status == "Interview Scheduled":
            extra = (
                '<div style="margin-top:1.5rem;"><h2>Interview notes</h2>'
                '<p class="form-hint">You can write up and complete this interview once its scheduled time has passed.</p></div>'
            )
    elif status == "Interview Requested":
        actions = f"""
        <div class="btn-row" style="margin-top:1.25rem;">
            <button class="btn btn-primary" type="button"
                    hx-post="{backend_url}/interviews/{iid}/accept"
                    hx-confirm="Accept this interview? Your application will move to Interview Scheduled."
                    hx-swap="none">Accept Interview</button>
            <button class="btn btn-danger" type="button"
                    onclick="document.getElementById('decline-area').style.display='block'">Decline Interview</button>
        </div>
        <div id="decline-area" style="display:none;margin-top:1.25rem;">
            <label for="decline_reason">Reason for declining (optional)</label>
            <textarea id="decline_reason" name="reason" rows="2" placeholder="Let the recruiter know why"></textarea>
            <div class="btn-row" style="margin-top:0.75rem;">
                <button class="btn btn-danger" type="button"
                        hx-post="{backend_url}/interviews/{iid}/decline"
                        hx-include="#decline_reason"
                        hx-confirm="Decline this interview? Declining withdraws your application."
                        hx-swap="none">Decline Interview</button>
            </div>
        </div>"""

    return f"""
    <div class="status-header">{_interview_badge(status)}</div>
    <dl class="detail-grid">{_detail_rows(interview)}</dl>
    {actions}
    {extra}"""
