"""Tests for the Student 5 backend service — evaluation CRUD endpoints."""
from conftest import (
    APPLICATIONS_DB_URL,
    DB_SERVICE_URL,
    DRAFT_EVALUATION,
    FULL_EVALUATION,
    POSTINGS_DB_URL,
    SHARED_DB_URL,
    STAFF_USER,
    APPLICANT_USER,
    mock_session,
)

SAVED_EVAL = {
    "Evaluation_Id": 1,
    "Application_Id": 200,
    "User_Id": 1,
    "Evaluation_TechnicalScore": 4,
    "Evaluation_EducationScore": 3,
    "Evaluation_CommunicationScore": 5,
    "Evaluation_ProblemSolvingScore": 4,
    "Evaluation_ProfessionalismScore": 4,
    "Evaluation_OverallScore": 4.0,
    "Evaluation_FinalRecommendation": "Hire",
}

SAVED_DRAFT = {
    "Evaluation_Id": 2,
    "Application_Id": 201,
    "User_Id": 1,
    "Evaluation_TechnicalScore": None,
    "Evaluation_EducationScore": None,
    "Evaluation_CommunicationScore": None,
    "Evaluation_ProblemSolvingScore": None,
    "Evaluation_ProfessionalismScore": None,
    "Evaluation_OverallScore": None,
    "Evaluation_FinalRecommendation": None,
}


def _mock_app_enrichment(requests_mock, application_id=200):
    requests_mock.get(f"{APPLICATIONS_DB_URL}/applications/{application_id}", json={
        "application_id": application_id, "user_id": 10, "job_posting_id": 50,
        "application_status": "Interview Completed",
    })
    requests_mock.get(f"{SHARED_DB_URL}/users/10", json={
        "user_first_name": "Jane", "user_last_name": "Doe", "user_email": "jane@test.com",
    })
    requests_mock.get(f"{POSTINGS_DB_URL}/job-postings/50", json={"Job_Title": "Software Engineer"})


# --- Authentication ---

def test_list_evaluations_requires_auth(backend_client):
    resp = backend_client.get("/api/evaluations")
    assert resp.status_code == 401


def test_list_evaluations_requires_staff(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, APPLICANT_USER)
    resp = backend_client.get("/api/evaluations", headers=auth_headers)
    assert resp.status_code == 403


# --- Create ---

def test_create_evaluation_success(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, STAFF_USER)
    requests_mock.post(f"{DB_SERVICE_URL}/evaluations", json=SAVED_EVAL, status_code=201)

    resp = backend_client.post("/api/evaluations", json=FULL_EVALUATION, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.get_json()["Evaluation_Id"] == 1


def test_create_evaluation_injects_user_id(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, STAFF_USER)
    requests_mock.post(f"{DB_SERVICE_URL}/evaluations", json=SAVED_EVAL, status_code=201)

    backend_client.post("/api/evaluations", json=FULL_EVALUATION, headers=auth_headers)
    sent = requests_mock.request_history[-1].json()
    assert sent["User_Id"] == STAFF_USER["user_id"]


def test_create_draft_evaluation(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, STAFF_USER)
    requests_mock.post(f"{DB_SERVICE_URL}/evaluations", json=SAVED_DRAFT, status_code=201)
    requests_mock.put(f"{APPLICATIONS_DB_URL}/applications/201", json={}, status_code=200)

    resp = backend_client.post("/api/evaluations", json=DRAFT_EVALUATION, headers=auth_headers)
    assert resp.status_code == 201


# --- HTMX create with application status update ---

def test_htmx_create_draft_sets_evaluation_in_progress(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, STAFF_USER)
    requests_mock.post(f"{DB_SERVICE_URL}/evaluations", json=SAVED_DRAFT, status_code=201)
    requests_mock.put(f"{APPLICATIONS_DB_URL}/applications/201", json={}, status_code=200)

    resp = backend_client.post(
        "/api/evaluations",
        data={"Application_Id": "201", "Evaluation_FinalRecommendation": ""},
        headers={**auth_headers, "HX-Request": "true"},
    )
    assert resp.status_code == 200
    assert "HX-Redirect" in resp.headers
    put_calls = [h for h in requests_mock.request_history
                 if h.method == "PUT" and "/applications/201" in h.url]
    assert len(put_calls) == 1
    assert put_calls[0].json()["application_status"] == "Evaluation In Progress"


def test_htmx_submit_hire_sets_hired(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, STAFF_USER)
    requests_mock.post(f"{DB_SERVICE_URL}/evaluations", json=SAVED_EVAL, status_code=201)
    _mock_app_enrichment(requests_mock)
    requests_mock.put(f"{APPLICATIONS_DB_URL}/applications/200", json={}, status_code=200)

    resp = backend_client.post(
        "/api/evaluations",
        data={"Application_Id": "200", "Evaluation_TechnicalScore": "4",
              "Evaluation_EducationScore": "3", "Evaluation_CommunicationScore": "5",
              "Evaluation_ProblemSolvingScore": "4", "Evaluation_ProfessionalismScore": "4",
              "Evaluation_FinalRecommendation": "Hire"},
        headers={**auth_headers, "HX-Request": "true"},
    )
    assert resp.status_code == 200
    assert "Hired" in resp.headers.get("HX-Redirect", "")


def test_htmx_submit_reject_sets_rejected(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, STAFF_USER)
    requests_mock.post(f"{DB_SERVICE_URL}/evaluations", json={**SAVED_EVAL, "Evaluation_FinalRecommendation": "Reject"}, status_code=201)
    _mock_app_enrichment(requests_mock)
    requests_mock.put(f"{APPLICATIONS_DB_URL}/applications/200", json={}, status_code=200)

    resp = backend_client.post(
        "/api/evaluations",
        data={"Application_Id": "200", "Evaluation_TechnicalScore": "4",
              "Evaluation_EducationScore": "3", "Evaluation_CommunicationScore": "5",
              "Evaluation_ProblemSolvingScore": "4", "Evaluation_ProfessionalismScore": "4",
              "Evaluation_FinalRecommendation": "Reject"},
        headers={**auth_headers, "HX-Request": "true"},
    )
    assert resp.status_code == 200
    assert "Rejected" in resp.headers.get("HX-Redirect", "")


# --- Read ---

def test_get_evaluation_enriches_with_applicant_info(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, STAFF_USER)
    requests_mock.get(f"{DB_SERVICE_URL}/evaluations/1", json=SAVED_EVAL)
    _mock_app_enrichment(requests_mock)

    resp = backend_client.get("/api/evaluations/1", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["applicant_name"] == "Jane Doe"
    assert body["job_title"] == "Software Engineer"


def test_get_evaluation_not_found(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, STAFF_USER)
    requests_mock.get(f"{DB_SERVICE_URL}/evaluations/999", json={"error": "not found"}, status_code=404)

    resp = backend_client.get("/api/evaluations/999", headers=auth_headers)
    assert resp.status_code == 404


# --- Update ---

def test_update_evaluation_success(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, STAFF_USER)
    requests_mock.put(f"{DB_SERVICE_URL}/evaluations/1", json=SAVED_EVAL)

    resp = backend_client.put("/api/evaluations/1", json={"Evaluation_TechnicalScore": 5}, headers=auth_headers)
    assert resp.status_code == 200


# --- Delete ---

def test_delete_evaluation_success(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, STAFF_USER)
    requests_mock.get(f"{DB_SERVICE_URL}/evaluations/1", json=SAVED_DRAFT)
    requests_mock.delete(f"{DB_SERVICE_URL}/evaluations/1", json={"message": "deleted"})
    requests_mock.put(f"{APPLICATIONS_DB_URL}/applications/201", json={}, status_code=200)

    resp = backend_client.delete("/api/evaluations/1", headers=auth_headers)
    assert resp.status_code == 200


def test_delete_evaluation_reverts_application_status(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, STAFF_USER)
    requests_mock.get(f"{DB_SERVICE_URL}/evaluations/1", json=SAVED_DRAFT)
    requests_mock.delete(f"{DB_SERVICE_URL}/evaluations/1", json={"message": "deleted"})
    requests_mock.put(f"{APPLICATIONS_DB_URL}/applications/201", json={}, status_code=200)

    resp = backend_client.delete("/api/evaluations/1", headers=auth_headers)
    assert resp.status_code == 200

    put_calls = [r for r in requests_mock.request_history
                 if r.method == "PUT" and r.url.endswith("/applications/201")]
    assert len(put_calls) == 1
    assert put_calls[0].json()["application_status"] == "Interview Completed"


def test_delete_evaluation_htmx_triggers(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, STAFF_USER)
    requests_mock.get(f"{DB_SERVICE_URL}/evaluations/1", json=SAVED_DRAFT)
    requests_mock.delete(f"{DB_SERVICE_URL}/evaluations/1", json={"message": "deleted"})
    requests_mock.put(f"{APPLICATIONS_DB_URL}/applications/201", json={}, status_code=200)

    resp = backend_client.delete("/api/evaluations/1",
                                 headers={**auth_headers, "HX-Request": "true"})
    assert resp.status_code == 200
    assert "showToast" in resp.headers.get("HX-Trigger", "")


# --- Eligible applications ---

def test_eligible_applications_filters_evaluated(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, STAFF_USER)
    requests_mock.get(f"{APPLICATIONS_DB_URL}/applications", json=[
        {"application_id": 1, "user_id": 10, "job_posting_id": 50, "application_status": "Interview Completed"},
        {"application_id": 2, "user_id": 11, "job_posting_id": 51, "application_status": "Interview Completed"},
        {"application_id": 3, "user_id": 12, "job_posting_id": 52, "application_status": "Submitted"},
    ])
    requests_mock.get(f"{DB_SERVICE_URL}/evaluations", json=[{"Application_Id": 2}])
    requests_mock.get(f"{SHARED_DB_URL}/users/10", json={"user_first_name": "Jane", "user_last_name": "Doe"})
    requests_mock.get(f"{POSTINGS_DB_URL}/job-postings/50", json={"Job_Title": "Developer"})

    resp = backend_client.get("/api/eligible-applications", headers=auth_headers)
    assert resp.status_code == 200
    apps = resp.get_json()
    assert len(apps) == 1
    assert apps[0]["application_id"] == 1


# --- Notification ---

def test_notify_requires_valid_action(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, STAFF_USER)
    resp = backend_client.post("/api/evaluations/1/notify", json={"action": "Maybe"}, headers=auth_headers)
    assert resp.status_code == 400


def test_notify_hired_updates_application(backend_client, requests_mock, auth_headers):
    mock_session(requests_mock, STAFF_USER)
    requests_mock.get(f"{DB_SERVICE_URL}/evaluations/1", json=SAVED_EVAL)
    _mock_app_enrichment(requests_mock)
    requests_mock.put(f"{APPLICATIONS_DB_URL}/applications/200", json={}, status_code=200)

    resp = backend_client.post("/api/evaluations/1/notify", json={"action": "Hired"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "Hired"
