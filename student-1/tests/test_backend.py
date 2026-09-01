"""Tests for the Student 1 backend service.

Covers the HTML fragment builders (``views.html_formatters``) plus the
normal-mode ``/user``, ``/profile`` and ``/resume`` routes.
"""
import io
import json

from conftest import BACKEND_PUBLIC_URL, DATABASE_SERVICE_URL, SHARED_API_URL, mock_session
from views.html_formatters import (
    render_message,
    render_profile_panel,
    render_resume_panel,
    render_user_details_panel,
)

BACKEND_URL = BACKEND_PUBLIC_URL

APPLICANT = {"user_id": 1, "role": "applicant", "first_name": "Jane", "last_name": "Doe"}
OTHER_APPLICANT = {"user_id": 2, "role": "applicant", "first_name": "John", "last_name": "Smith"}
STAFF = {"user_id": 9, "role": "staff", "first_name": "Sam", "last_name": "Staff"}


# --------------------------------------------------------------------------- #
# HTML fragment builders (no Flask client)                                     #
# --------------------------------------------------------------------------- #

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


# --------------------------------------------------------------------------- #
# /user fragment routes                                                        #
# --------------------------------------------------------------------------- #

def test_get_user_details_requires_authentication(backend_client):
    resp = backend_client.get("/user")
    assert resp.status_code == 401


def test_get_user_details_renders_prefilled_form(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)

    resp = backend_client.get("/user", headers=auth_headers)

    assert resp.status_code == 200
    assert b"Jane" in resp.data
    assert b"Doe" in resp.data


def test_update_user_details_requires_authentication(backend_client):
    resp = backend_client.put("/user", data={"first_name": "Jane", "last_name": "Doe"})
    assert resp.status_code == 401


def test_update_user_details_rejects_missing_first_name(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)

    resp = backend_client.put("/user", data={"first_name": "", "last_name": "Doe"}, headers=auth_headers)

    assert resp.status_code == 200
    assert b"required" in resp.data


def test_update_user_details_rejects_blank_names(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)

    resp = backend_client.put("/user", data={"first_name": "   ", "last_name": "Doe"}, headers=auth_headers)

    assert resp.status_code == 200
    assert b"required" in resp.data


def test_update_user_details_success_triggers_toast(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.put(f"{SHARED_API_URL}/api/auth/user", json={"first_name": "Janet", "last_name": "Doe"})

    resp = backend_client.put("/user", data={"first_name": "Janet", "last_name": "Doe"}, headers=auth_headers)

    assert resp.status_code == 200
    assert b"Janet" in resp.data
    triggers = json.loads(resp.headers.get("HX-Trigger", "{}"))
    assert triggers["showToast"] == "Details updated."
    assert triggers["userUpdated"] == {"first_name": "Janet", "last_name": "Doe"}


def test_update_user_details_propagates_shared_api_failure(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.put(f"{SHARED_API_URL}/api/auth/user", json={"error": "Invalid session"}, status_code=401)

    resp = backend_client.put("/user", data={"first_name": "Jane", "last_name": "Doe"}, headers=auth_headers)

    assert resp.status_code == 200
    assert b"Failed to update details" in resp.data


# --------------------------------------------------------------------------- #
# /profile fragment routes                                                     #
# --------------------------------------------------------------------------- #

def test_get_profile_requires_authentication(backend_client):
    resp = backend_client.get("/profile")
    assert resp.status_code == 401


def test_get_profile_shows_create_prompt_when_none_exists(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DATABASE_SERVICE_URL}/profiles/by-user/1", status_code=404, json={"error": "Profile not found"})

    resp = backend_client.get("/profile", headers=auth_headers)

    assert resp.status_code == 200
    assert b"You do not have a profile yet" in resp.data


def test_get_profile_shows_update_form_when_exists(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DATABASE_SERVICE_URL}/profiles/by-user/1", json={"profile_id": 10, "user_id": 1, "phone": "+61400000000"})

    resp = backend_client.get("/profile", headers=auth_headers)

    assert resp.status_code == 200
    assert b"Update Profile" in resp.data


def test_create_profile_injects_user_id_and_shows_inline_success(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.post(f"{DATABASE_SERVICE_URL}/profiles", json={"profile_id": 10, "user_id": 1, "phone": "+61400000000"}, status_code=201)

    resp = backend_client.post("/profile", data={"phone": "+61400000000"}, headers=auth_headers)

    assert resp.status_code == 200
    sent_body = requests_mock.request_history[-1].json()
    assert sent_body["user_id"] == 1
    assert b"Profile created." in resp.data
    assert "profileChanged" in resp.headers.get("HX-Trigger", "")


def test_create_profile_requires_phone(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)

    resp = backend_client.post("/profile", data={"phone": ""}, headers=auth_headers)

    assert resp.status_code == 200
    assert b"Phone is required" in resp.data


def test_create_profile_shows_db_error(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.post(f"{DATABASE_SERVICE_URL}/profiles", json={"error": "Profile already exists for this user"}, status_code=409)

    resp = backend_client.post("/profile", data={"phone": "+61400000000"}, headers=auth_headers)

    assert resp.status_code == 200
    assert b"Profile already exists" in resp.data


def test_update_profile_forbidden_for_non_owner(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DATABASE_SERVICE_URL}/profiles/10", json={"profile_id": 10, "user_id": 2})

    resp = backend_client.put("/profile/10", data={"phone": "+61499999999"}, headers=auth_headers)

    assert resp.status_code == 403


def test_update_profile_allowed_for_owner(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DATABASE_SERVICE_URL}/profiles/10", json={"profile_id": 10, "user_id": 1, "phone": "+61400000000"})
    requests_mock.put(f"{DATABASE_SERVICE_URL}/profiles/10", json={"profile_id": 10, "user_id": 1, "phone": "+61499999999"})

    resp = backend_client.put("/profile/10", data={"phone": "+61499999999"}, headers=auth_headers)

    assert resp.status_code == 200
    assert b"+61499999999" in resp.data
    assert b"Profile updated." in resp.data
    # Rendered inline below the submit button, not as a toast.
    assert resp.data.index(b"Update Profile") < resp.data.index(b"Profile updated.")


def test_update_profile_not_found_propagates(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DATABASE_SERVICE_URL}/profiles/10", status_code=404, json={"error": "Profile not found"})

    resp = backend_client.put("/profile/10", data={"phone": "+61499999999"}, headers=auth_headers)

    assert resp.status_code == 200
    assert b"Profile not found" in resp.data


def test_delete_profile_forbidden_for_non_owner(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DATABASE_SERVICE_URL}/profiles/10", json={"profile_id": 10, "user_id": 2})

    resp = backend_client.delete("/profile/10", headers=auth_headers)

    assert resp.status_code == 403


def test_delete_profile_allowed_for_owner(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DATABASE_SERVICE_URL}/profiles/10", json={"profile_id": 10, "user_id": 1})
    requests_mock.delete(f"{DATABASE_SERVICE_URL}/profiles/10", json={"message": "Profile deleted"})

    resp = backend_client.delete("/profile/10", headers=auth_headers)

    assert resp.status_code == 200
    assert b"You do not have a profile yet" in resp.data
    assert "profileChanged" in resp.headers.get("HX-Trigger", "")


# --------------------------------------------------------------------------- #
# /resume fragment routes                                                      #
# --------------------------------------------------------------------------- #

def test_get_resume_panel_requires_authentication(backend_client):
    resp = backend_client.get("/resume")
    assert resp.status_code == 401


def test_get_resume_panel_forbidden_for_staff(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, STAFF)

    resp = backend_client.get("/resume", headers=auth_headers)

    assert resp.status_code == 200
    assert b"Staff cannot manage resumes" in resp.data


def test_get_resume_panel_prompts_to_create_profile_first(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DATABASE_SERVICE_URL}/profiles/by-user/1", status_code=404, json={"error": "Profile not found"})

    resp = backend_client.get("/resume", headers=auth_headers)

    assert resp.status_code == 200
    assert b"Create your profile above" in resp.data


def test_get_resume_panel_lists_existing_resume(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DATABASE_SERVICE_URL}/profiles/by-user/1", json={"profile_id": 10, "user_id": 1})
    requests_mock.get(f"{DATABASE_SERVICE_URL}/profiles/10/resumes", json=[{"resume_id": 5, "file_name": "resume.pdf", "file_type": "application/pdf"}])

    resp = backend_client.get("/resume", headers=auth_headers)

    assert resp.status_code == 200
    assert b"resume.pdf" in resp.data


def test_upload_resume_rejects_when_no_profile(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DATABASE_SERVICE_URL}/profiles/by-user/1", status_code=404, json={"error": "Profile not found"})

    data = {"file": (io.BytesIO(b"%PDF-1.4 fake"), "resume.pdf", "application/pdf")}
    resp = backend_client.post("/resume", data=data, content_type="multipart/form-data", headers=auth_headers)

    assert resp.status_code == 200
    assert b"Create your profile" in resp.data


def test_upload_resume_rejects_disallowed_type(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DATABASE_SERVICE_URL}/profiles/by-user/1", json={"profile_id": 10, "user_id": 1})
    requests_mock.get(f"{DATABASE_SERVICE_URL}/profiles/10/resumes", json=[])

    data = {"file": (io.BytesIO(b"malicious"), "resume.exe", "application/x-msdownload")}
    resp = backend_client.post("/resume", data=data, content_type="multipart/form-data", headers=auth_headers)

    assert resp.status_code == 200
    assert b"Only PDF files are allowed" in resp.data


def test_upload_resume_success(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DATABASE_SERVICE_URL}/profiles/by-user/1", json={"profile_id": 10, "user_id": 1})
    requests_mock.post(f"{DATABASE_SERVICE_URL}/profiles/10/resumes", json={"resume_id": 5, "file_name": "resume.pdf"}, status_code=201)
    requests_mock.get(f"{DATABASE_SERVICE_URL}/profiles/10/resumes", json=[{"resume_id": 5, "file_name": "resume.pdf", "file_type": "application/pdf"}])

    data = {"file": (io.BytesIO(b"%PDF-1.4 fake"), "resume.pdf", "application/pdf")}
    resp = backend_client.post("/resume", data=data, content_type="multipart/form-data", headers=auth_headers)

    assert resp.status_code == 200
    assert b"resume.pdf" in resp.data
    assert b"Resume uploaded." in resp.data
    # Rendered below the table (the upload form/button is gone once a resume exists).
    assert resp.data.index(b"</table>") < resp.data.index(b"Resume uploaded.")


def test_upload_resume_shows_duplicate_error(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DATABASE_SERVICE_URL}/profiles/by-user/1", json={"profile_id": 10, "user_id": 1})
    requests_mock.post(
        f"{DATABASE_SERVICE_URL}/profiles/10/resumes",
        json={"error": "This profile already has a resume. Delete the existing resume before uploading a new one."},
        status_code=409,
    )
    requests_mock.get(f"{DATABASE_SERVICE_URL}/profiles/10/resumes", json=[])

    data = {"file": (io.BytesIO(b"%PDF-1.4 fake"), "resume.pdf", "application/pdf")}
    resp = backend_client.post("/resume", data=data, content_type="multipart/form-data", headers=auth_headers)

    assert resp.status_code == 200
    assert b"already has a resume" in resp.data


def test_delete_resume_forbidden_for_non_owner(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DATABASE_SERVICE_URL}/resumes/5", json={"resume_id": 5, "profile_id": 10})
    requests_mock.get(f"{DATABASE_SERVICE_URL}/profiles/by-user/1", json={"profile_id": 11, "user_id": 1})

    resp = backend_client.delete("/resume/5", headers=auth_headers)

    assert resp.status_code == 403


def test_delete_resume_allowed_for_owner(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DATABASE_SERVICE_URL}/resumes/5", json={"resume_id": 5, "profile_id": 10})
    requests_mock.get(f"{DATABASE_SERVICE_URL}/profiles/by-user/1", json={"profile_id": 10, "user_id": 1})
    requests_mock.delete(f"{DATABASE_SERVICE_URL}/resumes/5", json={"message": "Resume deleted"})
    requests_mock.get(f"{DATABASE_SERVICE_URL}/profiles/10/resumes", json=[])

    resp = backend_client.delete("/resume/5", headers=auth_headers)

    assert resp.status_code == 200
    assert b"No resumes uploaded yet" in resp.data


def test_download_resume_forbidden_for_non_owner(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DATABASE_SERVICE_URL}/resumes/5", json={"resume_id": 5, "profile_id": 10})
    requests_mock.get(f"{DATABASE_SERVICE_URL}/profiles/by-user/1", json={"profile_id": 11, "user_id": 1})

    resp = backend_client.get("/resume/5/download", headers=auth_headers)

    assert resp.status_code == 403


def test_download_resume_allowed_for_owner(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DATABASE_SERVICE_URL}/resumes/5", json={"resume_id": 5, "profile_id": 10})
    requests_mock.get(f"{DATABASE_SERVICE_URL}/profiles/by-user/1", json={"profile_id": 10, "user_id": 1})
    requests_mock.get(
        f"{DATABASE_SERVICE_URL}/resumes/5/file",
        content=b"resume bytes",
        headers={"Content-Type": "application/pdf", "Content-Disposition": 'attachment; filename="resume.pdf"'},
    )

    resp = backend_client.get("/resume/5/download", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.data == b"resume bytes"


def test_download_resume_allowed_for_staff(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, STAFF)
    requests_mock.get(f"{DATABASE_SERVICE_URL}/resumes/5", json={"resume_id": 5, "profile_id": 10})
    requests_mock.get(
        f"{DATABASE_SERVICE_URL}/resumes/5/file",
        content=b"resume bytes",
        headers={"Content-Type": "application/pdf", "Content-Disposition": 'attachment; filename="resume.pdf"'},
    )

    resp = backend_client.get("/resume/5/download", headers=auth_headers)

    assert resp.status_code == 200
