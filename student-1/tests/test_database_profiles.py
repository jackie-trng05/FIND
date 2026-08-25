"""Tests for the Student 1 database service — profiles table."""


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
