"""Tests for the Student 1 backend service — resume endpoints (role + ownership)."""
import io

from conftest import DB_SERVICE_URL, mock_session

APPLICANT = {"user_id": 1, "role": "applicant", "first_name": "Jane", "last_name": "Doe"}
STAFF = {"user_id": 9, "role": "staff", "first_name": "Sam", "last_name": "Staff"}


def test_upload_resume_forbidden_for_staff(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, STAFF)

    resp = backend_client.post("/api/profiles/10/resumes", json={
        "file_name": "resume.pdf", "file_type": "application/pdf", "file_data": "aGVsbG8=",
    }, headers=auth_headers)

    assert resp.status_code == 403


def test_upload_resume_forbidden_for_non_owner(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/10", json={"profile_id": 10, "user_id": 2})

    resp = backend_client.post("/api/profiles/10/resumes", json={
        "file_name": "resume.pdf", "file_type": "application/pdf", "file_data": "aGVsbG8=",
    }, headers=auth_headers)

    assert resp.status_code == 403


def test_upload_resume_success_for_owner(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/10", json={"profile_id": 10, "user_id": 1})
    requests_mock.post(f"{DB_SERVICE_URL}/profiles/10/resumes", json={"resume_id": 5, "file_name": "resume.pdf"}, status_code=201)

    resp = backend_client.post("/api/profiles/10/resumes", json={
        "file_name": "resume.pdf", "file_type": "application/pdf", "file_data": "aGVsbG8=",
    }, headers=auth_headers)

    assert resp.status_code == 201
    assert resp.get_json()["resume_id"] == 5


def test_list_resumes_forbidden_for_staff(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, STAFF)

    resp = backend_client.get("/api/profiles/10/resumes", headers=auth_headers)

    assert resp.status_code == 403


def test_list_resumes_forbidden_for_non_owner(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/10", json={"profile_id": 10, "user_id": 2})

    resp = backend_client.get("/api/profiles/10/resumes", headers=auth_headers)

    assert resp.status_code == 403


def test_list_resumes_success_for_owner(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/10", json={"profile_id": 10, "user_id": 1})
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/10/resumes", json=[{"resume_id": 5, "file_name": "resume.pdf"}])

    resp = backend_client.get("/api/profiles/10/resumes", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.get_json()[0]["resume_id"] == 5


def test_download_resume_allowed_for_staff(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, STAFF)
    requests_mock.get(f"{DB_SERVICE_URL}/resumes/5", json={"resume_id": 5, "profile_id": 10})
    requests_mock.get(
        f"{DB_SERVICE_URL}/resumes/5/file",
        content=b"resume bytes",
        headers={"Content-Type": "application/pdf", "Content-Disposition": 'attachment; filename="resume.pdf"'},
    )

    resp = backend_client.get("/api/resumes/5/download", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.data == b"resume bytes"


def test_download_resume_forbidden_for_non_owner(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/resumes/5", json={"resume_id": 5, "profile_id": 10})
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/10", json={"profile_id": 10, "user_id": 2})

    resp = backend_client.get("/api/resumes/5/download", headers=auth_headers)

    assert resp.status_code == 403


def test_download_resume_success_for_owner(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/resumes/5", json={"resume_id": 5, "profile_id": 10})
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/10", json={"profile_id": 10, "user_id": 1})
    requests_mock.get(
        f"{DB_SERVICE_URL}/resumes/5/file",
        content=b"resume bytes",
        headers={"Content-Type": "application/pdf", "Content-Disposition": 'attachment; filename="resume.pdf"'},
    )

    resp = backend_client.get("/api/resumes/5/download", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.data == b"resume bytes"


def test_delete_resume_forbidden_for_staff(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, STAFF)

    resp = backend_client.delete("/api/resumes/5", headers=auth_headers)

    assert resp.status_code == 403


def test_delete_resume_forbidden_for_non_owner(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/resumes/5", json={"resume_id": 5, "profile_id": 10})
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/10", json={"profile_id": 10, "user_id": 2})

    resp = backend_client.delete("/api/resumes/5", headers=auth_headers)

    assert resp.status_code == 403


def test_delete_resume_success_for_owner(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/resumes/5", json={"resume_id": 5, "profile_id": 10})
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/10", json={"profile_id": 10, "user_id": 1})
    requests_mock.delete(f"{DB_SERVICE_URL}/resumes/5", json={"message": "Resume deleted"})

    resp = backend_client.delete("/api/resumes/5", headers=auth_headers)

    assert resp.status_code == 200


def test_upload_resume_multipart_success_for_owner(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/10", json={"profile_id": 10, "user_id": 1})
    requests_mock.post(f"{DB_SERVICE_URL}/profiles/10/resumes", json={"resume_id": 7, "file_name": "resume.pdf"}, status_code=201)

    data = {"file": (io.BytesIO(b"%PDF-1.4 fake"), "resume.pdf", "application/pdf")}
    resp = backend_client.post(
        "/api/profiles/10/resumes", data=data, content_type="multipart/form-data", headers=auth_headers
    )

    assert resp.status_code == 201
    assert resp.get_json()["resume_id"] == 7
    sent_body = requests_mock.request_history[-1].json()
    assert sent_body["file_name"] == "resume.pdf"
    assert sent_body["file_type"] == "application/pdf"


def test_upload_resume_multipart_rejects_no_file_selected(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/10", json={"profile_id": 10, "user_id": 1})

    data = {"file": (io.BytesIO(b""), "")}
    resp = backend_client.post(
        "/api/profiles/10/resumes", data=data, content_type="multipart/form-data", headers=auth_headers
    )

    assert resp.status_code == 400
    assert resp.get_json()["error"] == "No file selected"


def test_upload_resume_multipart_rejects_disallowed_type(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/10", json={"profile_id": 10, "user_id": 1})

    data = {"file": (io.BytesIO(b"malicious"), "resume.exe", "application/x-msdownload")}
    resp = backend_client.post(
        "/api/profiles/10/resumes", data=data, content_type="multipart/form-data", headers=auth_headers
    )

    assert resp.status_code == 400
    assert "Only PDF files are allowed" in resp.get_json()["error"]


def test_upload_resume_multipart_rejects_oversized_file(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/10", json={"profile_id": 10, "user_id": 1})

    # Flask's app.config["MAX_CONTENT_LENGTH"] (5MB) rejects the oversized body at the
    # request-parsing layer with 413, before the handler's own size check ever runs.
    oversized = io.BytesIO(b"x" * (5 * 1024 * 1024 + 1))
    data = {"file": (oversized, "resume.pdf", "application/pdf")}
    resp = backend_client.post(
        "/api/profiles/10/resumes", data=data, content_type="multipart/form-data", headers=auth_headers
    )

    assert resp.status_code == 413


def test_download_resume_not_found_propagates(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/resumes/5", status_code=404, json={"error": "Resume not found"})

    resp = backend_client.get("/api/resumes/5/download", headers=auth_headers)

    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Resume not found"


def test_download_resume_file_missing_after_ownership_check(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/resumes/5", json={"resume_id": 5, "profile_id": 10})
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/10", json={"profile_id": 10, "user_id": 1})
    requests_mock.get(f"{DB_SERVICE_URL}/resumes/5/file", status_code=404, json={"error": "Resume not found"})

    resp = backend_client.get("/api/resumes/5/download", headers=auth_headers)

    assert resp.status_code == 404
    assert resp.get_json()["error"] == "File not found"


def test_delete_resume_not_found_propagates(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/resumes/5", status_code=404, json={"error": "Resume not found"})

    resp = backend_client.delete("/api/resumes/5", headers=auth_headers)

    assert resp.status_code == 404


def test_get_resume_meta_forbidden_for_non_owner(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/resumes/5", json={"resume_id": 5, "profile_id": 10})
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/10", json={"profile_id": 10, "user_id": 2})

    resp = backend_client.get("/api/resumes/5", headers=auth_headers)

    assert resp.status_code == 403


def test_get_resume_meta_success_for_owner(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/resumes/5", json={"resume_id": 5, "profile_id": 10, "file_name": "resume.pdf"})
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/10", json={"profile_id": 10, "user_id": 1})

    resp = backend_client.get("/api/resumes/5", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.get_json()["file_name"] == "resume.pdf"


def test_get_resume_meta_success_for_staff(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, STAFF)
    requests_mock.get(f"{DB_SERVICE_URL}/resumes/5", json={"resume_id": 5, "profile_id": 10, "file_name": "resume.pdf"})

    resp = backend_client.get("/api/resumes/5", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.get_json()["file_name"] == "resume.pdf"


def test_get_resume_meta_not_found(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/resumes/5", status_code=404, json={"error": "Resume not found"})

    resp = backend_client.get("/api/resumes/5", headers=auth_headers)

    assert resp.status_code == 404


def test_get_resume_meta_no_ownership_check_when_unlinked(backend_client, requests_mock, auth_headers):
    # profile_id is None for an application-only resume; any authenticated caller
    # is trusted (student-3 already validated ownership via applications.user_id).
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/resumes/5", json={"resume_id": 5, "profile_id": None, "file_name": "cover.pdf"})

    resp = backend_client.get("/api/resumes/5", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.get_json()["file_name"] == "cover.pdf"


def test_download_resume_no_ownership_check_when_unlinked(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/resumes/5", json={"resume_id": 5, "profile_id": None})
    requests_mock.get(
        f"{DB_SERVICE_URL}/resumes/5/file",
        content=b"resume bytes",
        headers={"Content-Type": "application/pdf", "Content-Disposition": 'attachment; filename="resume.pdf"'},
    )

    resp = backend_client.get("/api/resumes/5/download", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.data == b"resume bytes"


def test_delete_resume_forbidden_when_unlinked(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/resumes/5", json={"resume_id": 5, "profile_id": None})

    resp = backend_client.delete("/api/resumes/5", headers=auth_headers)

    assert resp.status_code == 403


def test_upload_unlinked_resume_forbidden_for_staff(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, STAFF)

    resp = backend_client.post("/api/resumes", json={
        "file_name": "cover.pdf", "file_type": "application/pdf", "file_data": "aGVsbG8=",
    }, headers=auth_headers)

    assert resp.status_code == 403


def test_upload_unlinked_resume_success(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.post(f"{DB_SERVICE_URL}/resumes", json={"resume_id": 11, "file_name": "cover.pdf"}, status_code=201)

    resp = backend_client.post("/api/resumes", json={
        "file_name": "cover.pdf", "file_type": "application/pdf", "file_data": "aGVsbG8=",
    }, headers=auth_headers)

    assert resp.status_code == 201
    assert resp.get_json()["resume_id"] == 11
