"""Tests for the Student 1 database service — profiles and resumes tables."""
import base64

VALID_FILE_DATA = base64.b64encode(b"resume contents").decode("utf-8")


def _create_profile(db_client, user_id=1):
    return db_client.post("/profiles", json={"user_id": user_id, "phone": "+61400000000"}).get_json()


# --------------------------------------------------------------------------- #
# Profiles                                                                     #
# --------------------------------------------------------------------------- #

def test_create_profile_success(db_client):
    resp = db_client.post("/profiles", json={"user_id": 1, "phone": "+61400000000"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["user_id"] == 1
    assert body["phone"] == "+61400000000"
    assert body["profile_id"] is not None


def test_create_profile_missing_required_field(db_client):
    resp = db_client.post("/profiles", json={"user_id": 1})
    assert resp.status_code == 400
    assert "phone" in resp.get_json()["error"]


def test_create_profile_no_body(db_client):
    resp = db_client.post("/profiles", data="", content_type="application/json")
    assert resp.status_code == 400


def test_create_profile_duplicate_user_conflicts(db_client):
    db_client.post("/profiles", json={"user_id": 1, "phone": "+61400000000"})
    resp = db_client.post("/profiles", json={"user_id": 1, "phone": "+61400000001"})
    assert resp.status_code == 409


def test_get_profile_by_id(db_client):
    created = db_client.post("/profiles", json={"user_id": 1, "phone": "+61400000000"}).get_json()
    resp = db_client.get(f"/profiles/{created['profile_id']}")
    assert resp.status_code == 200
    assert resp.get_json()["user_id"] == 1


def test_get_profile_by_id_not_found(db_client):
    resp = db_client.get("/profiles/999")
    assert resp.status_code == 404


def test_get_profile_by_user(db_client):
    db_client.post("/profiles", json={"user_id": 5, "phone": "+61400000005"})
    resp = db_client.get("/profiles/by-user/5")
    assert resp.status_code == 200
    assert resp.get_json()["user_id"] == 5


def test_get_profile_by_user_not_found(db_client):
    resp = db_client.get("/profiles/by-user/999")
    assert resp.status_code == 404


def test_update_profile_success(db_client):
    created = db_client.post("/profiles", json={"user_id": 1, "phone": "+61400000000"}).get_json()
    resp = db_client.put(f"/profiles/{created['profile_id']}", json={
        "phone": "+61499999999",
        "professional_title": "Software Engineer",
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["phone"] == "+61499999999"
    assert body["professional_title"] == "Software Engineer"


def test_update_profile_not_found(db_client):
    resp = db_client.put("/profiles/999", json={"phone": "+61499999999"})
    assert resp.status_code == 404


def test_update_profile_blank_phone_rejected(db_client):
    created = db_client.post("/profiles", json={"user_id": 1, "phone": "+61400000000"}).get_json()
    resp = db_client.put(f"/profiles/{created['profile_id']}", json={"phone": ""})
    assert resp.status_code == 400


def test_delete_profile_success(db_client):
    created = db_client.post("/profiles", json={"user_id": 1, "phone": "+61400000000"}).get_json()
    resp = db_client.delete(f"/profiles/{created['profile_id']}")
    assert resp.status_code == 200
    assert db_client.get(f"/profiles/{created['profile_id']}").status_code == 404


def test_delete_profile_not_found(db_client):
    resp = db_client.delete("/profiles/999")
    assert resp.status_code == 404


def test_delete_profile_cascades_resumes(db_client):
    created = db_client.post("/profiles", json={"user_id": 1, "phone": "+61400000000"}).get_json()
    profile_id = created["profile_id"]
    db_client.post(f"/profiles/{profile_id}/resumes", json={
        "file_name": "resume.pdf",
        "file_type": "application/pdf",
        "file_data": "aGVsbG8=",
    })
    db_client.delete(f"/profiles/{profile_id}")
    resp = db_client.get(f"/profiles/{profile_id}/resumes")
    assert resp.status_code == 200
    assert resp.get_json() == []


# --------------------------------------------------------------------------- #
# Resumes                                                                      #
# --------------------------------------------------------------------------- #

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
    # A profile is only ever allowed one resume (see test_upload_resume_rejects_second_upload
    # below); two different profiles each with their own resume should both list correctly.
    profile_1 = _create_profile(db_client, user_id=1)
    profile_2 = _create_profile(db_client, user_id=2)
    db_client.post(f"/profiles/{profile_1['profile_id']}/resumes", json={
        "file_name": "resume_v1.pdf",
        "file_type": "application/pdf",
        "file_data": VALID_FILE_DATA,
    })
    db_client.post(f"/profiles/{profile_2['profile_id']}/resumes", json={
        "file_name": "resume_v2.pdf",
        "file_type": "application/pdf",
        "file_data": VALID_FILE_DATA,
    })

    resp_1 = db_client.get(f"/profiles/{profile_1['profile_id']}/resumes")
    resp_2 = db_client.get(f"/profiles/{profile_2['profile_id']}/resumes")

    assert resp_1.get_json()[0]["file_name"] == "resume_v1.pdf"
    assert resp_2.get_json()[0]["file_name"] == "resume_v2.pdf"


def test_upload_resume_rejects_second_upload_for_same_profile(db_client):
    profile = _create_profile(db_client)
    first = db_client.post(f"/profiles/{profile['profile_id']}/resumes", json={
        "file_name": "resume_v1.pdf",
        "file_type": "application/pdf",
        "file_data": VALID_FILE_DATA,
    })
    assert first.status_code == 201

    second = db_client.post(f"/profiles/{profile['profile_id']}/resumes", json={
        "file_name": "resume_v2.pdf",
        "file_type": "application/pdf",
        "file_data": VALID_FILE_DATA,
    })
    assert second.status_code == 409

    resp = db_client.get(f"/profiles/{profile['profile_id']}/resumes")
    resumes = resp.get_json()
    assert len(resumes) == 1
    assert resumes[0]["file_name"] == "resume_v1.pdf"


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


def test_upload_unlinked_resume_success(db_client):
    resp = db_client.post("/resumes", json={
        "file_name": "cover.pdf",
        "file_type": "application/pdf",
        "file_data": VALID_FILE_DATA,
    })
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["resume_id"] is not None

    meta = db_client.get(f"/resumes/{body['resume_id']}").get_json()
    assert meta["profile_id"] is None


def test_upload_unlinked_resume_missing_fields(db_client):
    resp = db_client.post("/resumes", json={"file_name": "cover.pdf"})
    assert resp.status_code == 400


def test_upload_unlinked_resume_rejects_disallowed_file_type(db_client):
    resp = db_client.post("/resumes", json={
        "file_name": "cover.exe",
        "file_type": "application/x-msdownload",
        "file_data": VALID_FILE_DATA,
    })
    assert resp.status_code == 400


def test_upload_unlinked_resume_no_uniqueness_conflict(db_client):
    # Multiple unlinked (profile_id NULL) resumes must not collide with the
    # UNIQUE(profile_id) constraint used for the one-resume-per-profile rule.
    first = db_client.post("/resumes", json={
        "file_name": "cover1.pdf", "file_type": "application/pdf", "file_data": VALID_FILE_DATA,
    })
    second = db_client.post("/resumes", json={
        "file_name": "cover2.pdf", "file_type": "application/pdf", "file_data": VALID_FILE_DATA,
    })
    assert first.status_code == 201
    assert second.status_code == 201
