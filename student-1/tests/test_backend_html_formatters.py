"""Direct function tests for the Student 1 HTML fragment builders (no Flask client)."""
from views.html_formatters import (
    render_message,
    render_profile_panel,
    render_resume_panel,
    render_user_details_panel,
)

BACKEND_URL = "http://backend-service.test"


def test_render_message_escapes_html():
    out = render_message("<script>alert(1)</script>", kind="error")
    assert "<script>" not in out
    assert "alert-error" in out


def test_render_message_success_and_info():
    assert "alert-success" in render_message("Saved.", kind="success")
    assert "alert-success" not in render_message("Just fyi.", kind="info")


def test_render_user_details_panel_prefills_values():
    user = {"first_name": "Jane", "last_name": "Doe"}
    out = render_user_details_panel(user, backend_url=BACKEND_URL)
    assert 'value="Jane"' in out
    assert 'value="Doe"' in out
    assert f'hx-put="{BACKEND_URL}/user"' in out


def test_render_user_details_panel_shows_error():
    out = render_user_details_panel({}, backend_url=BACKEND_URL, error="First name and last name are required.")
    assert "alert-error" in out
    assert "required" in out


def test_render_profile_panel_no_profile_shows_create_prompt():
    out = render_profile_panel(None, backend_url=BACKEND_URL, role="applicant")
    assert "You do not have a profile yet" in out
    assert "Create Profile" in out
    assert f'hx-post="{BACKEND_URL}/profile"' in out
    assert "Delete Profile" not in out


def test_render_profile_panel_existing_profile_shows_update_form_and_delete():
    profile = {"profile_id": 10, "phone": "+61400000000", "location": "Sydney"}
    out = render_profile_panel(profile, backend_url=BACKEND_URL, role="applicant")
    assert "Update Profile" in out
    assert f'hx-put="{BACKEND_URL}/profile/10"' in out
    assert f'hx-delete="{BACKEND_URL}/profile/10"' in out
    assert 'value="+61400000000"' in out


def test_render_profile_panel_nests_resume_panel_for_applicants():
    out = render_profile_panel(None, backend_url=BACKEND_URL, role="applicant")
    assert 'id="resume-panel"' in out
    assert f'hx-get="{BACKEND_URL}/resume"' in out


def test_render_profile_panel_hides_resume_panel_for_staff():
    out = render_profile_panel(None, backend_url=BACKEND_URL, role="staff")
    assert 'id="resume-panel"' not in out


def test_render_resume_panel_no_profile_prompts_to_create_one():
    out = render_resume_panel(None, [], backend_url=BACKEND_URL)
    assert "Create your profile above" in out


def test_render_resume_panel_empty_shows_upload_form():
    out = render_resume_panel(10, [], backend_url=BACKEND_URL)
    assert "No resumes uploaded yet." in out
    assert f'hx-post="{BACKEND_URL}/resume"' in out
    assert 'accept=".pdf"' in out


def test_render_resume_panel_with_resume_hides_upload_form():
    resumes = [{"resume_id": 5, "file_name": "resume.pdf", "file_type": "application/pdf", "uploaded_at": "2026-01-01"}]
    out = render_resume_panel(10, resumes, backend_url=BACKEND_URL)
    assert "resume.pdf" in out
    assert f'hx-delete="{BACKEND_URL}/resume/5"' in out
    assert f'{BACKEND_URL}/resume/5/download' in out
    assert "Upload Resume" not in out
    assert "Delete the current resume to upload a replacement." in out


def test_render_resume_panel_shows_inline_error():
    out = render_resume_panel(10, [], backend_url=BACKEND_URL, message="Only PDF files are allowed.", kind="error")
    assert "alert-error" in out
    assert "Only PDF files are allowed." in out


def test_render_profile_panel_message_renders_below_submit_button():
    out = render_profile_panel(None, backend_url=BACKEND_URL, role="applicant", message="Profile created.", kind="success")
    assert out.index("Create Profile") < out.index("Profile created.")


def test_render_resume_panel_message_renders_below_upload_button():
    out = render_resume_panel(10, [], backend_url=BACKEND_URL, message="Only PDF files are allowed.", kind="error")
    assert out.index(">Upload<") < out.index("Only PDF files are allowed.")


def test_render_resume_panel_message_renders_below_table_when_resume_exists():
    resumes = [{"resume_id": 5, "file_name": "resume.pdf", "file_type": "application/pdf", "uploaded_at": "2026-01-01"}]
    out = render_resume_panel(10, resumes, backend_url=BACKEND_URL, message="Resume uploaded.", kind="success")
    assert out.index("</table>") < out.index("Resume uploaded.")
