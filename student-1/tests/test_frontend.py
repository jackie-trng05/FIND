"""Tests for the Student 1 frontend service — page routes and reverse-proxy behaviour."""
import io

from conftest import STUDENT1_BACKEND_URL

# requests_mock leaves headers empty unless told otherwise; real backend responses are
# jsonify()'d Flask responses, so mocks must set this for the proxied Response to be JSON.
JSON_HEADERS = {"Content-Type": "application/json"}


def test_health(frontend_client):
    resp = frontend_client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_index_redirects_to_profile(frontend_client):
    resp = frontend_client.get("/")
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/profile"


def test_profile_page_renders(frontend_client):
    resp = frontend_client.get("/profile")
    assert resp.status_code == 200
    assert b"User Details" in resp.data


def test_proxy_profiles_post_forwards_json_and_cookie(frontend_client, requests_mock):
    requests_mock.post(
        f"{STUDENT1_BACKEND_URL}/api/profiles", json={"profile_id": 10}, status_code=201, headers=JSON_HEADERS
    )

    frontend_client.set_cookie("session_token", "test-session")
    resp = frontend_client.post("/api/profiles", json={"phone": "+61400000000"})

    assert resp.status_code == 201
    assert resp.get_json()["profile_id"] == 10
    sent = requests_mock.request_history[-1]
    assert sent.json() == {"phone": "+61400000000"}
    assert "session_token=test-session" in sent.headers.get("Cookie", "")


def test_proxy_profiles_sub_forwards_get(frontend_client, requests_mock):
    requests_mock.get(
        f"{STUDENT1_BACKEND_URL}/api/profiles/10", json={"profile_id": 10, "user_id": 1}, headers=JSON_HEADERS
    )

    resp = frontend_client.get("/api/profiles/10")

    assert resp.status_code == 200
    assert resp.get_json()["profile_id"] == 10


def test_proxy_resumes_forwards_delete(frontend_client, requests_mock):
    requests_mock.delete(
        f"{STUDENT1_BACKEND_URL}/api/resumes/5", json={"message": "Resume deleted"}, headers=JSON_HEADERS
    )

    resp = frontend_client.delete("/api/resumes/5")

    assert resp.status_code == 200
    assert resp.get_json()["message"] == "Resume deleted"


def test_proxy_user_forwards_put(frontend_client, requests_mock):
    requests_mock.put(f"{STUDENT1_BACKEND_URL}/api/user", json={"first_name": "Jane"}, headers=JSON_HEADERS)

    resp = frontend_client.put("/api/user", json={"first_name": "Jane", "last_name": "Doe"})

    assert resp.status_code == 200
    assert resp.get_json()["first_name"] == "Jane"


def test_proxy_multipart_upload_forwards_file(frontend_client, requests_mock):
    requests_mock.post(
        f"{STUDENT1_BACKEND_URL}/api/profiles/10/resumes",
        json={"resume_id": 7}, status_code=201, headers=JSON_HEADERS,
    )

    data = {"file": (io.BytesIO(b"%PDF-1.4 fake"), "resume.pdf", "application/pdf")}
    resp = frontend_client.post("/api/profiles/10/resumes", data=data, content_type="multipart/form-data")

    assert resp.status_code == 201
    assert resp.get_json()["resume_id"] == 7
    sent = requests_mock.request_history[-1]
    assert sent.headers["Content-Type"].startswith("multipart/form-data")


def test_proxy_logout_clears_session_cookie(frontend_client, requests_mock):
    requests_mock.post(
        f"{STUDENT1_BACKEND_URL}/api/auth/logout", json={"message": "Logged out"}, headers=JSON_HEADERS
    )

    frontend_client.set_cookie("session_token", "test-session")
    resp = frontend_client.post("/api/auth/logout")

    assert resp.status_code == 200
    assert resp.get_json()["message"] == "Logged out"
    set_cookie_headers = resp.headers.getlist("Set-Cookie")
    assert any(h.startswith("session_token=") and "Max-Age=0" in h for h in set_cookie_headers)
