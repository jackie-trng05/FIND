"""Tests for the Student 1 database service — resumes table."""
import base64

VALID_FILE_DATA = base64.b64encode(b"resume contents").decode("utf-8")


def _create_profile(db_client, user_id=1):
    return db_client.post("/profiles", json={"user_id": user_id, "phone": "+61400000000"}).get_json()


def test_upload_resume_success(db_client):
    profile = _create_profile(db_client)
    resp = db_client.post(f"/profiles/{profile['profile_id']}/resumes", json={
        "file_name": "resume.pdf",
        "file_type": "application/pdf",
        "file_data": VALID_FILE_DATA,
    })
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["file_name"] == "resume.pdf"
    assert body["resume_id"] is not None


def test_upload_resume_missing_fields(db_client):
    profile = _create_profile(db_client)
    resp = db_client.post(f"/profiles/{profile['profile_id']}/resumes", json={"file_name": "resume.pdf"})
    assert resp.status_code == 400


def test_upload_resume_rejects_disallowed_file_type(db_client):
    profile = _create_profile(db_client)
    resp = db_client.post(f"/profiles/{profile['profile_id']}/resumes", json={
        "file_name": "resume.exe",
        "file_type": "application/x-msdownload",
        "file_data": VALID_FILE_DATA,
    })
    assert resp.status_code == 400


def test_upload_resume_rejects_invalid_base64(db_client):
    profile = _create_profile(db_client)
    resp = db_client.post(f"/profiles/{profile['profile_id']}/resumes", json={
        "file_name": "resume.pdf",
        "file_type": "application/pdf",
        "file_data": "not-valid-base64!!!",
    })
    assert resp.status_code == 400


def test_upload_resume_rejects_oversized_file(db_client):
    profile = _create_profile(db_client)
    oversized = base64.b64encode(b"x" * (5 * 1024 * 1024 + 1)).decode("utf-8")
    resp = db_client.post(f"/profiles/{profile['profile_id']}/resumes", json={
        "file_name": "resume.pdf",
        "file_type": "application/pdf",
        "file_data": oversized,
    })
    assert resp.status_code == 400


def test_upload_resume_profile_not_found(db_client):
    resp = db_client.post("/profiles/999/resumes", json={
        "file_name": "resume.pdf",
        "file_type": "application/pdf",
        "file_data": VALID_FILE_DATA,
    })
    assert resp.status_code == 404


def test_get_resumes_for_profile(db_client):
    profile = _create_profile(db_client)
    db_client.post(f"/profiles/{profile['profile_id']}/resumes", json={
        "file_name": "resume.pdf",
        "file_type": "application/pdf",
        "file_data": VALID_FILE_DATA,
    })
    resp = db_client.get(f"/profiles/{profile['profile_id']}/resumes")
    assert resp.status_code == 200
    resumes = resp.get_json()
    assert len(resumes) == 1
    assert resumes[0]["file_name"] == "resume.pdf"
    assert "file_data" not in resumes[0]


def test_get_resumes_for_profile_multiple(db_client):
    profile = _create_profile(db_client)
    db_client.post(f"/profiles/{profile['profile_id']}/resumes", json={
        "file_name": "resume_v1.pdf",
        "file_type": "application/pdf",
        "file_data": VALID_FILE_DATA,
    })
    db_client.post(f"/profiles/{profile['profile_id']}/resumes", json={
        "file_name": "resume_v2.docx",
        "file_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "file_data": VALID_FILE_DATA,
    })

    resp = db_client.get(f"/profiles/{profile['profile_id']}/resumes")

    assert resp.status_code == 200
    resumes = resp.get_json()
    assert len(resumes) == 2
    assert {r["file_name"] for r in resumes} == {"resume_v1.pdf", "resume_v2.docx"}


def test_get_resume_meta(db_client):
    profile = _create_profile(db_client)
    created = db_client.post(f"/profiles/{profile['profile_id']}/resumes", json={
        "file_name": "resume.pdf",
        "file_type": "application/pdf",
        "file_data": VALID_FILE_DATA,
    }).get_json()
    resp = db_client.get(f"/resumes/{created['resume_id']}")
    assert resp.status_code == 200
    assert resp.get_json()["file_name"] == "resume.pdf"


def test_get_resume_meta_not_found(db_client):
    resp = db_client.get("/resumes/999")
    assert resp.status_code == 404


def test_get_resume_file(db_client):
    profile = _create_profile(db_client)
    created = db_client.post(f"/profiles/{profile['profile_id']}/resumes", json={
        "file_name": "resume.pdf",
        "file_type": "application/pdf",
        "file_data": VALID_FILE_DATA,
    }).get_json()
    resp = db_client.get(f"/resumes/{created['resume_id']}/file")
    assert resp.status_code == 200
    assert resp.data == b"resume contents"
    assert resp.mimetype == "application/pdf"


def test_get_resume_file_not_found(db_client):
    resp = db_client.get("/resumes/999/file")
    assert resp.status_code == 404


def test_delete_resume_success(db_client):
    profile = _create_profile(db_client)
    created = db_client.post(f"/profiles/{profile['profile_id']}/resumes", json={
        "file_name": "resume.pdf",
        "file_type": "application/pdf",
        "file_data": VALID_FILE_DATA,
    }).get_json()
    resp = db_client.delete(f"/resumes/{created['resume_id']}")
    assert resp.status_code == 200
    assert db_client.get(f"/resumes/{created['resume_id']}").status_code == 404


def test_delete_resume_not_found(db_client):
    resp = db_client.delete("/resumes/999")
    assert resp.status_code == 404
