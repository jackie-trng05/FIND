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


# --- Bug fix: "Submit Evaluation" must require EVERY field to be completed
#     (all five scores AND a hiring decision), otherwise an unfinished
#     evaluation was silently stored as a draft. The Submit button is guarded
#     client-side by validateSubmit(). ---

def test_submit_button_is_guarded_by_validation(frontend_client):
    html = frontend_client.get("/evaluate/42").data.decode()
    assert "function validateSubmit" in html
    # The Submit button only fires when validation passes.
    assert "click[validateSubmit()]" in html
    # Save as Draft stays unguarded (drafts may be incomplete).
    assert 'hx-vals=\'{"Evaluation_FinalRecommendation": ""}\'' in html


# --- NFR: "The evaluation form shall calculate and display the overall
#     candidate score within 2 seconds after all five criteria have been
#     entered." This proves the form ships the client-side calculator
#     (updateOverall) wired to all five criteria inputs and a display element,
#     so the score updates instantly on entry (no server round-trip). ---

def test_form_wires_all_five_criteria_to_overall_calculation(frontend_client):
    html = frontend_client.get("/evaluate/42").data.decode()
    # A display element for the overall score is present.
    assert 'id="overall-score"' in html
    # The client-side calculator exists.
    assert "function updateOverall" in html
    # All five criteria inputs trigger the calculation on entry.
    assert html.count("updateOverall()") >= 5
    for score_id in ("score-tech", "score-edu", "score-comm", "score-ps", "score-prof"):
        assert f'id="{score_id}"' in html
