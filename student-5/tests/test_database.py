"""Tests for the Student 5 database service — evaluations CRUD."""


def _create(db_client, **overrides):
    payload = {
        "Application_Id": 200,
        "User_Id": 1,
        "HR_Staff_Name": "Alex Morgan",
        "HR_Staff_Number": "HR-001",
    }
    payload.update(overrides)
    return db_client.post("/evaluations", json=payload)


# --- Create ---

def test_create_draft_with_no_scores(db_client):
    resp = _create(db_client)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["Application_Id"] == 200
    assert body["Evaluation_FinalRecommendation"] is None
    assert body["Evaluation_TechnicalScore"] is None
    assert body["Evaluation_OverallScore"] is None


def test_create_with_full_scores_and_decision(db_client):
    resp = _create(
        db_client,
        Evaluation_TechnicalScore=5,
        Evaluation_EducationScore=4,
        Evaluation_CommunicationScore=3,
        Evaluation_ProblemSolvingScore=4,
        Evaluation_ProfessionalismScore=5,
        Evaluation_FinalRecommendation="Hire",
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["Evaluation_FinalRecommendation"] == "Hire"
    assert body["Evaluation_OverallScore"] == 4.2


def test_create_missing_hr_name_rejected(db_client):
    resp = _create(db_client, HR_Staff_Name="")
    assert resp.status_code == 400


def test_create_missing_application_id_rejected(db_client):
    resp = db_client.post("/evaluations", json={
        "User_Id": 1, "HR_Staff_Name": "A", "HR_Staff_Number": "HR-001",
    })
    assert resp.status_code == 400


def test_create_duplicate_application_rejected(db_client):
    _create(db_client, Application_Id=300)
    resp = _create(db_client, Application_Id=300)
    assert resp.status_code == 409


def test_create_decision_without_scores_rejected(db_client):
    resp = _create(db_client, Evaluation_FinalRecommendation="Hire")
    assert resp.status_code == 400
    assert "scores" in resp.get_json()["error"].lower()


def test_create_partial_scores_with_decision_rejected(db_client):
    resp = _create(
        db_client,
        Evaluation_TechnicalScore=5,
        Evaluation_FinalRecommendation="Reject",
    )
    assert resp.status_code == 400


def test_create_invalid_score_range_rejected(db_client):
    resp = _create(db_client, Evaluation_TechnicalScore=6)
    assert resp.status_code == 400


def test_create_score_zero_rejected(db_client):
    resp = _create(db_client, Evaluation_TechnicalScore=0)
    assert resp.status_code == 400


def test_create_invalid_recommendation_rejected(db_client):
    resp = _create(
        db_client,
        Evaluation_TechnicalScore=3, Evaluation_EducationScore=3,
        Evaluation_CommunicationScore=3, Evaluation_ProblemSolvingScore=3,
        Evaluation_ProfessionalismScore=3,
        Evaluation_FinalRecommendation="Maybe",
    )
    assert resp.status_code == 400


def test_create_no_json_body(db_client):
    resp = db_client.post("/evaluations", data="", content_type="application/json")
    assert resp.status_code == 400


# --- Read ---

def test_get_evaluation_by_id(db_client):
    created = _create(db_client).get_json()
    resp = db_client.get(f"/evaluations/{created['Evaluation_Id']}")
    assert resp.status_code == 200
    assert resp.get_json()["Application_Id"] == 200


def test_get_evaluation_not_found(db_client):
    resp = db_client.get("/evaluations/999")
    assert resp.status_code == 404


def test_list_evaluations_empty(db_client):
    resp = db_client.get("/evaluations")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_list_evaluations_returns_all(db_client):
    _create(db_client, Application_Id=300)
    _create(db_client, Application_Id=301)
    resp = db_client.get("/evaluations")
    assert len(resp.get_json()) == 2


def test_list_filter_by_recommendation(db_client):
    _create(db_client, Application_Id=300, Evaluation_TechnicalScore=3,
            Evaluation_EducationScore=3, Evaluation_CommunicationScore=3,
            Evaluation_ProblemSolvingScore=3, Evaluation_ProfessionalismScore=3,
            Evaluation_FinalRecommendation="Hire")
    _create(db_client, Application_Id=301)
    resp = db_client.get("/evaluations?recommendation=Hire")
    results = resp.get_json()
    assert len(results) == 1
    assert results[0]["Evaluation_FinalRecommendation"] == "Hire"


def test_list_filter_in_progress(db_client):
    _create(db_client, Application_Id=300, Evaluation_TechnicalScore=3,
            Evaluation_EducationScore=3, Evaluation_CommunicationScore=3,
            Evaluation_ProblemSolvingScore=3, Evaluation_ProfessionalismScore=3,
            Evaluation_FinalRecommendation="Hire")
    _create(db_client, Application_Id=301)
    resp = db_client.get("/evaluations?status=in_progress")
    results = resp.get_json()
    assert len(results) == 1
    assert results[0]["Evaluation_FinalRecommendation"] is None


def test_list_filter_decided(db_client):
    _create(db_client, Application_Id=300, Evaluation_TechnicalScore=3,
            Evaluation_EducationScore=3, Evaluation_CommunicationScore=3,
            Evaluation_ProblemSolvingScore=3, Evaluation_ProfessionalismScore=3,
            Evaluation_FinalRecommendation="Reject")
    _create(db_client, Application_Id=301)
    resp = db_client.get("/evaluations?status=decided")
    results = resp.get_json()
    assert len(results) == 1
    assert results[0]["Evaluation_FinalRecommendation"] == "Reject"


# --- Update ---

def test_update_draft_add_scores(db_client):
    created = _create(db_client).get_json()
    eid = created["Evaluation_Id"]
    resp = db_client.put(f"/evaluations/{eid}", json={
        "Evaluation_TechnicalScore": 4,
        "Evaluation_EducationScore": 4,
        "Evaluation_CommunicationScore": 4,
        "Evaluation_ProblemSolvingScore": 4,
        "Evaluation_ProfessionalismScore": 4,
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["Evaluation_OverallScore"] == 4.0
    assert body["Evaluation_FinalRecommendation"] is None


def test_update_finalize_with_decision(db_client):
    created = _create(db_client).get_json()
    eid = created["Evaluation_Id"]
    resp = db_client.put(f"/evaluations/{eid}", json={
        "Evaluation_TechnicalScore": 5,
        "Evaluation_EducationScore": 4,
        "Evaluation_CommunicationScore": 3,
        "Evaluation_ProblemSolvingScore": 4,
        "Evaluation_ProfessionalismScore": 5,
        "Evaluation_FinalRecommendation": "Reject",
    })
    assert resp.status_code == 200
    assert resp.get_json()["Evaluation_FinalRecommendation"] == "Reject"


def test_update_decision_without_scores_rejected(db_client):
    created = _create(db_client).get_json()
    eid = created["Evaluation_Id"]
    resp = db_client.put(f"/evaluations/{eid}", json={
        "Evaluation_FinalRecommendation": "Hire",
    })
    assert resp.status_code == 400


def test_update_not_found(db_client):
    resp = db_client.put("/evaluations/999", json={"HR_Staff_Name": "X"})
    assert resp.status_code == 404


def test_update_invalid_score_rejected(db_client):
    created = _create(db_client).get_json()
    eid = created["Evaluation_Id"]
    resp = db_client.put(f"/evaluations/{eid}", json={"Evaluation_TechnicalScore": 10})
    assert resp.status_code == 400


# --- Delete ---

def test_delete_draft_evaluation(db_client):
    created = _create(db_client).get_json()
    eid = created["Evaluation_Id"]
    resp = db_client.delete(f"/evaluations/{eid}")
    assert resp.status_code == 200
    assert db_client.get(f"/evaluations/{eid}").status_code == 404


def test_delete_finalized_evaluation_rejected(db_client):
    created = _create(
        db_client,
        Evaluation_TechnicalScore=3, Evaluation_EducationScore=3,
        Evaluation_CommunicationScore=3, Evaluation_ProblemSolvingScore=3,
        Evaluation_ProfessionalismScore=3,
        Evaluation_FinalRecommendation="Hire",
    ).get_json()
    resp = db_client.delete(f"/evaluations/{created['Evaluation_Id']}")
    assert resp.status_code == 403


def test_delete_not_found(db_client):
    resp = db_client.delete("/evaluations/999")
    assert resp.status_code == 404


# --- Health ---

def test_health(db_client):
    resp = db_client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"
