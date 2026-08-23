"""Tests for the Student 2 backend HTML fragment builders."""

from views import html_formatters as fmt

_BACKEND = "http://localhost:16008"
_FRONTEND = "http://localhost:16007"

_POSTING = {
    "JobPosting_Id": 42,
    "Staff_Id": 1,
    "Job_Title": "Backend Engineer",
    "Job_Description": "Build and maintain the API.",
    "Job_Type": "Full time",
    "Location": "Sydney",
    "Salary_Range": "$120k",
    "Requirements": "Python",
    "Application_Deadline": "2025-12-31",
    "JobPosting_Status": "Published",
    "JobPosting_CreatedAt": "2025-01-01T00:00:00+00:00",
    "JobPosting_UpdatedAt": "2025-01-01T00:00:00+00:00",
    "JobPosting_PublishedAt": "2025-01-02T00:00:00+00:00",
}


def test_render_message_escapes_html():
    out = fmt.render_message("<script>alert(1)</script>", kind="error")
    assert "<script>" not in out
    assert "alert-error" in out


def test_postings_table_row_links_to_detail_page():
    out = fmt.render_postings_table([_POSTING], frontend_url=_FRONTEND)
    assert "Backend Engineer" in out
    assert f"{_FRONTEND}/postings/42" in out
    assert "badge-success" in out


def test_postings_table_empty_state():
    out = fmt.render_postings_table([], frontend_url=_FRONTEND)
    assert "empty-state" in out


def test_posting_panel_shows_management_actions():
    out = fmt.render_posting_panel(
        _POSTING, backend_url=_BACKEND, frontend_url=_FRONTEND
    )
    assert "Backend Engineer" in out
    assert "hx-delete" in out
    assert "/job-postings/42" in out
    # Published posting offers an Unpublish action.
    assert "unpublish" in out
    assert "Sydney" in out


def test_posting_form_omits_staff_id():
    create_form = fmt.render_posting_form(_BACKEND)
    assert "hx-post" in create_form
    assert 'name="Staff_Id"' not in create_form

    edit_form = fmt.render_posting_form(_BACKEND, posting=_POSTING)
    assert "hx-put" in edit_form
    assert "Backend Engineer" in edit_form
    assert 'name="Staff_Id"' not in edit_form


def test_create_form_embeds_ai_helper_and_validation():
    create_form = fmt.render_posting_form(_BACKEND)
    # AI helper lives inside the create form (not a separate box).
    assert "/ai/suggest-skills" in create_form
    assert 'id="ai-suggestions"' in create_form
    # Required-field validation is present.
    assert "required" in create_form
    # No Qualifications or Responsibilities fields.
    assert "Qualifications" not in create_form
    assert "Responsibilities" not in create_form


def test_edit_form_targets_panel_and_shows_error():
    edit_form = fmt.render_posting_form(_BACKEND, posting=_POSTING, error="Location is required.")
    # Inline edit replaces the panel (no separate editor slot).
    assert 'hx-target="#posting-panel"' in edit_form
    assert "Cancel" in edit_form
    assert "Location is required." in edit_form
    # The AI helper is also offered when editing.
    assert "/ai/suggest-skills" in edit_form


def test_skill_suggestions_deduplicate_repeated_items():
    text = "- Git\n- Git\n- git\n- Python"
    out = fmt.render_skill_suggestions(text)
    # Rendered as selectable checkboxes; each unique item appears once.
    assert out.count('value="Git"') == 1
    assert out.count('value="Python"') == 1
    assert "ai-check-input" in out


def test_skill_suggestions_render_headings_and_checkboxes():
    text = "Skills\n- Python\n- SQL"
    out = fmt.render_skill_suggestions(text)
    assert "ai-subhead" in out
    assert 'value="Python"' in out
    assert 'value="SQL"' in out
    assert "Update requirements" in out
