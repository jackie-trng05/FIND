"""Tests for the Student 1 backend service — /resume fragment routes."""
import io

from conftest import DATABASE_SERVICE_URL, mock_session

APPLICANT = {"user_id": 1, "role": "applicant", "first_name": "Jane", "last_name": "Doe"}
STAFF = {"user_id": 9, "role": "staff", "first_name": "Sam", "last_name": "Staff"}


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
