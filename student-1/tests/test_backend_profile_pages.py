"""Tests for the Student 1 backend service — /profile fragment routes."""
from conftest import DB_SERVICE_URL, mock_session

APPLICANT = {"user_id": 1, "role": "applicant", "first_name": "Jane", "last_name": "Doe"}
OTHER_APPLICANT = {"user_id": 2, "role": "applicant", "first_name": "John", "last_name": "Smith"}


def test_get_profile_requires_authentication(backend_client):
    resp = backend_client.get("/profile")
    assert resp.status_code == 401


def test_get_profile_shows_create_prompt_when_none_exists(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/by-user/1", status_code=404, json={"error": "Profile not found"})

    resp = backend_client.get("/profile", headers=auth_headers)

    assert resp.status_code == 200
    assert b"You do not have a profile yet" in resp.data


def test_get_profile_shows_update_form_when_exists(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/by-user/1", json={"profile_id": 10, "user_id": 1, "phone": "+61400000000"})

    resp = backend_client.get("/profile", headers=auth_headers)

    assert resp.status_code == 200
    assert b"Update Profile" in resp.data


def test_create_profile_injects_user_id_and_shows_inline_success(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.post(f"{DB_SERVICE_URL}/profiles", json={"profile_id": 10, "user_id": 1, "phone": "+61400000000"}, status_code=201)

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
    requests_mock.post(f"{DB_SERVICE_URL}/profiles", json={"error": "Profile already exists for this user"}, status_code=409)

    resp = backend_client.post("/profile", data={"phone": "+61400000000"}, headers=auth_headers)

    assert resp.status_code == 200
    assert b"Profile already exists" in resp.data


def test_update_profile_forbidden_for_non_owner(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/10", json={"profile_id": 10, "user_id": 2})

    resp = backend_client.put("/profile/10", data={"phone": "+61499999999"}, headers=auth_headers)

    assert resp.status_code == 403


def test_update_profile_allowed_for_owner(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/10", json={"profile_id": 10, "user_id": 1, "phone": "+61400000000"})
    requests_mock.put(f"{DB_SERVICE_URL}/profiles/10", json={"profile_id": 10, "user_id": 1, "phone": "+61499999999"})

    resp = backend_client.put("/profile/10", data={"phone": "+61499999999"}, headers=auth_headers)

    assert resp.status_code == 200
    assert b"+61499999999" in resp.data
    assert b"Profile updated." in resp.data
    # Rendered inline below the submit button, not as a toast.
    assert resp.data.index(b"Update Profile") < resp.data.index(b"Profile updated.")


def test_update_profile_not_found_propagates(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/10", status_code=404, json={"error": "Profile not found"})

    resp = backend_client.put("/profile/10", data={"phone": "+61499999999"}, headers=auth_headers)

    assert resp.status_code == 200
    assert b"Profile not found" in resp.data


def test_delete_profile_forbidden_for_non_owner(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/10", json={"profile_id": 10, "user_id": 2})

    resp = backend_client.delete("/profile/10", headers=auth_headers)

    assert resp.status_code == 403


def test_delete_profile_allowed_for_owner(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/10", json={"profile_id": 10, "user_id": 1})
    requests_mock.delete(f"{DB_SERVICE_URL}/profiles/10", json={"message": "Profile deleted"})

    resp = backend_client.delete("/profile/10", headers=auth_headers)

    assert resp.status_code == 200
    assert b"You do not have a profile yet" in resp.data
    assert "profileChanged" in resp.headers.get("HX-Trigger", "")
