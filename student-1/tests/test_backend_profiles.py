"""Tests for the Student 1 backend service — profile endpoints (session + ownership)."""
from conftest import DB_SERVICE_URL, SHARED_API_URL, mock_session

APPLICANT = {"user_id": 1, "role": "applicant", "first_name": "Jane", "last_name": "Doe"}
OTHER_APPLICANT = {"user_id": 2, "role": "applicant", "first_name": "John", "last_name": "Smith"}


def test_requires_authentication(backend_client):
    resp = backend_client.get("/api/profiles/1")
    assert resp.status_code == 401


def test_invalid_session_rejected(backend_client, requests_mock, auth_headers):
    requests_mock.get(f"{SHARED_API_URL}/api/auth/session", status_code=401)
    resp = backend_client.get("/api/profiles/1", headers=auth_headers)
    assert resp.status_code == 401


def test_create_profile_injects_user_id(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.post(f"{DB_SERVICE_URL}/profiles", json={"profile_id": 10, "user_id": 1}, status_code=201)

    resp = backend_client.post("/api/profiles", json={"phone": "+61400000000"}, headers=auth_headers)

    assert resp.status_code == 201
    assert resp.get_json()["profile_id"] == 10
    sent_body = requests_mock.request_history[-1].json()
    assert sent_body["user_id"] == 1


def test_get_my_profile_when_none_exists(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/by-user/1", status_code=404, json={"error": "Profile not found"})

    resp = backend_client.get("/api/profiles/me", headers=auth_headers)

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["profile"] is None
    assert body["role"] == "applicant"


def test_get_my_profile_when_exists(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/by-user/1", json={"profile_id": 10, "user_id": 1})

    resp = backend_client.get("/api/profiles/me", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.get_json()["profile"]["profile_id"] == 10


def test_get_profile_forbidden_for_non_owner(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/10", json={"profile_id": 10, "user_id": 2})

    resp = backend_client.get("/api/profiles/10", headers=auth_headers)

    assert resp.status_code == 403


def test_get_profile_allowed_for_owner(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/10", json={"profile_id": 10, "user_id": 1})

    resp = backend_client.get("/api/profiles/10", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.get_json()["user_id"] == 1


def test_update_profile_forbidden_for_non_owner(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/10", json={"profile_id": 10, "user_id": 2})

    resp = backend_client.put("/api/profiles/10", json={"phone": "+61499999999"}, headers=auth_headers)

    assert resp.status_code == 403


def test_update_profile_allowed_for_owner(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/10", json={"profile_id": 10, "user_id": 1})
    requests_mock.put(f"{DB_SERVICE_URL}/profiles/10", json={"profile_id": 10, "user_id": 1, "phone": "+61499999999"})

    resp = backend_client.put("/api/profiles/10", json={"phone": "+61499999999"}, headers=auth_headers)

    assert resp.status_code == 200
    assert resp.get_json()["phone"] == "+61499999999"


def test_delete_profile_forbidden_for_non_owner(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/10", json={"profile_id": 10, "user_id": 2})

    resp = backend_client.delete("/api/profiles/10", headers=auth_headers)

    assert resp.status_code == 403


def test_delete_profile_allowed_for_owner(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/10", json={"profile_id": 10, "user_id": 1})
    requests_mock.delete(f"{DB_SERVICE_URL}/profiles/10", json={"message": "Profile deleted"})

    resp = backend_client.delete("/api/profiles/10", headers=auth_headers)

    assert resp.status_code == 200


def test_update_user_identity_proxies_to_shared_api(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.put(f"{SHARED_API_URL}/api/auth/user", json={"first_name": "Jane", "last_name": "Doe"})

    resp = backend_client.put("/api/user", json={"first_name": "Jane", "last_name": "Doe"}, headers=auth_headers)

    assert resp.status_code == 200
    assert resp.get_json()["first_name"] == "Jane"


def test_update_user_identity_rejects_missing_first_name(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)

    resp = backend_client.put("/api/user", json={"first_name": "", "last_name": "Doe"}, headers=auth_headers)

    assert resp.status_code == 400
    assert "required" in resp.get_json()["error"]


def test_update_user_identity_rejects_missing_last_name(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)

    resp = backend_client.put("/api/user", json={"first_name": "Jane", "last_name": ""}, headers=auth_headers)

    assert resp.status_code == 400
    assert "required" in resp.get_json()["error"]


def test_update_user_identity_rejects_blank_names(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)

    resp = backend_client.put("/api/user", json={"first_name": "   ", "last_name": "Doe"}, headers=auth_headers)

    assert resp.status_code == 400


def test_update_user_identity_propagates_shared_api_failure(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.put(f"{SHARED_API_URL}/api/auth/user", json={"error": "Invalid session"}, status_code=401)

    resp = backend_client.put("/api/user", json={"first_name": "Jane", "last_name": "Doe"}, headers=auth_headers)

    assert resp.status_code == 401
    assert resp.get_json()["error"] == "Invalid session"


def test_get_profile_not_found_propagates(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/10", status_code=404, json={"error": "Profile not found"})

    resp = backend_client.get("/api/profiles/10", headers=auth_headers)

    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Profile not found"


def test_update_profile_not_found_propagates(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/10", status_code=404, json={"error": "Profile not found"})

    resp = backend_client.put("/api/profiles/10", json={"phone": "+61499999999"}, headers=auth_headers)

    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Profile not found"


def test_delete_profile_not_found_propagates(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT)
    requests_mock.get(f"{DB_SERVICE_URL}/profiles/10", status_code=404, json={"error": "Profile not found"})

    resp = backend_client.delete("/api/profiles/10", headers=auth_headers)

    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Profile not found"


def test_logout_proxies_to_shared_api(backend_client, requests_mock, auth_headers):
    requests_mock.post(f"{SHARED_API_URL}/api/auth/logout", json={"message": "Logged out"})

    resp = backend_client.post("/api/auth/logout", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.get_json()["message"] == "Logged out"
