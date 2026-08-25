"""Tests for the Student 1 backend service — /user fragment routes."""
import json

from conftest import SHARED_API_URL, mock_session

APPLICANT = {"user_id": 1, "role": "applicant", "first_name": "Jane", "last_name": "Doe"}


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
