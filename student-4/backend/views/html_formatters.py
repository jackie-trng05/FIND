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
