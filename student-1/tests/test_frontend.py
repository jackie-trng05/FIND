"""Tests for the Student 1 frontend service — page routes (thin template server, no proxying)."""
from conftest import BACKEND_PUBLIC_URL


def test_health(frontend_client):
    resp = frontend_client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_index_renders_profile_page(frontend_client):
    resp = frontend_client.get("/")
    assert resp.status_code == 200
    assert b"User Details" not in resp.data  # rendered by the backend fragment, not this shell
    assert f'{BACKEND_PUBLIC_URL}/user'.encode() in resp.data
    assert f'{BACKEND_PUBLIC_URL}/profile'.encode() in resp.data


def test_profile_page_renders(frontend_client):
    resp = frontend_client.get("/profile")
    assert resp.status_code == 200
    assert b"My Profile" in resp.data

