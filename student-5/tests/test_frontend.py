"""Tests for the Student 5 frontend service — page routes."""
from conftest import BACKEND_PUBLIC_URL


def test_health(frontend_client):
    resp = frontend_client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_index_renders_evaluations_page(frontend_client):
    resp = frontend_client.get("/")
    assert resp.status_code == 200
    assert b"Evaluations" in resp.data


def test_evaluate_renders_form_with_application_id(frontend_client):
    resp = frontend_client.get("/evaluate/42")
    assert resp.status_code == 200
    assert b"Evaluation Form" in resp.data or b"New Evaluation" in resp.data
    assert BACKEND_PUBLIC_URL.encode() in resp.data


def test_edit_renders_form_with_evaluation_id(frontend_client):
    resp = frontend_client.get("/edit/7")
    assert resp.status_code == 200
    assert BACKEND_PUBLIC_URL.encode() in resp.data


def test_submit_button_is_guarded_by_validation(frontend_client):
    html = frontend_client.get("/evaluate/42").data.decode()
    assert "function validateSubmit" in html
    assert "click[validateSubmit()]" in html
    assert 'hx-vals=\'{"Evaluation_FinalRecommendation": ""}\'' in html
