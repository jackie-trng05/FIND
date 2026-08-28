"""HTML-fragment renderers for the Student-5 (Evaluation) backend.

These functions return small HTML fragments that the HTMX front-end swaps
directly into the evaluations list page. Keeping the markup here mirrors the
``views/`` layer used by the other student services and keeps ``app.py`` focused
on request handling.
"""

from html import escape

from services.config import BACKEND_PUBLIC_URL, APPLICATIONS_PUBLIC_URL


def _e(value):
    """Escape a value for safe HTML output."""
    return escape("" if value is None else str(value))


def _score_class(score):
    try:
        s = float(score)
    except (TypeError, ValueError):
        return "score-low"
    if s >= 4:
        return "score-high"
    if s >= 3:
        return "score-mid"
    return "score-low"


def _rec_style(rec):
    if rec == "Hire":
        return "background:#d1fae5;color:#065f46;"
    if rec in ("Shortlist", "Hold"):
        return "background:#fef3c7;color:#92400e;"
    if rec == "Reject":
        return "background:#fde8e8;color:#991b1b;"
    return ""


def _short_date(value):
    if not value:
        return "\u2014"
    text = str(value)
    # Accept ISO ("2026-01-02T..." / "2026-01-02 ...") and return the date part.
    for sep in ("T", " "):
        if sep in text:
            return _e(text.split(sep, 1)[0])
    return _e(text[:10])


def render_evaluations_rows(evaluations):
    """Render the <tr> rows for the evaluations table body."""
    if not evaluations:
        return ('<tr><td colspan="9" style="text-align:center;color:var(--text-muted);">'
                "No evaluations found</td></tr>")

    rows = []
    for ev in evaluations:
        eval_id = ev.get("Evaluation_Id")
        applicant = ev.get("applicant_name") or ("App #" + _e(ev.get("Application_Id")))
        job = ev.get("job_title") or "\u2014"
        overall = ev.get("Evaluation_OverallScore")
        rec = ev.get("Evaluation_FinalRecommendation") or ""
        status = ev.get("Evaluation_Status") or ""

        if status != "Completed":
            actions = (
                '<div class="actions-cell">'
                f'<button class="btn btn-danger btn-sm" '
                f'hx-delete="{_e(BACKEND_PUBLIC_URL)}/api/evaluations/{_e(eval_id)}" '
                'hx-confirm="Delete this evaluation? This action cannot be undone." '
                'hx-target="closest tr" hx-swap="outerHTML swap:200ms">Delete</button>'
                f'<a href="/edit/{_e(eval_id)}" class="btn btn-ghost btn-sm">Edit</a>'
                "</div>"
            )
        else:
            actions = '<span style="color:var(--text-muted);font-size:0.8rem;">\u2014</span>'

        rows.append(
            "<tr>"
            f"<td>{_e(eval_id)}</td>"
            f"<td>{_e(applicant)}</td>"
            f"<td>{_e(job)}</td>"
            f'<td><span class="score-badge {_score_class(overall)}">{_e(overall)}</span></td>'
            f'<td><span class="status-badge" style="{_rec_style(rec)}">{_e(rec)}</span></td>'
            f'<td><span class="status-badge status-{_e(status.lower())}">{_e(status)}</span></td>'
            f"<td>{_e(ev.get('evaluator_name'))}</td>"
            f"<td>{_short_date(ev.get('updated_at'))}</td>"
            f"<td>{actions}</td>"
            "</tr>"
        )
    return "".join(rows)


def render_eligible_rows(apps):
    """Render the <tr> rows for the 'ready for evaluation' table body."""
    if not apps:
        return ('<tr><td colspan="5" style="text-align:center;color:var(--text-muted);">'
                "No applications ready for evaluation</td></tr>")

    rows = []
    for a in apps:
        app_id = a.get("application_id")
        applicant = a.get("applicant_name") or ("User #" + _e(a.get("user_id")))
        job = a.get("job_title") or "\u2014"
        status = a.get("application_status") or ""
        rows.append(
            "<tr>"
            f"<td>{_e(app_id)}</td>"
            f"<td>{_e(applicant)}</td>"
            f"<td>{_e(job)}</td>"
            f'<td><span class="status-badge" style="background:#dbeafe;color:#1e40af;">{_e(status)}</span></td>'
            f'<td><a href="/evaluate/{_e(app_id)}" class="btn btn-accent btn-sm" style="color:#fff;">Evaluate</a></td>'
            "</tr>"
        )
    return "".join(rows)
