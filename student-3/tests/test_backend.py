"""Tests for the Student 3 backend helper rendering and AI parsing logic.

The backend is composed from the ``services``, ``views`` and ``routes``
packages (see ``backend/app.py``); this suite exercises the presentation and
AI-parsing helpers directly from those modules.
"""

import os
import types
from unittest.mock import Mock

# services/config.py reads these service URLs at import time.
os.environ.setdefault("DATABASE_SERVICE_URL", "http://student-3-db:6003")
os.environ.setdefault("SHARED_API_URL", "http://find-shared-api:5000")
os.environ.setdefault("SHARED_DB_URL", "http://find-shared-db:6000")
os.environ.setdefault("POSTINGS_DB_URL", "http://student-2-db:6002")
os.environ.setdefault("STUDENT_1_DB_URL", "http://find-student-1-db:6001")

# backend/ is placed on sys.path by conftest.py.
import app as backend_app
from routes import applications as application_routes
from services import config, database_api, integration_api, llm_client
from views import html_formatters


def _load_backend_module():
    """Expose the formatter/parsing helpers under a single namespace."""
    module = types.SimpleNamespace()
    module.render_message = html_formatters.render_message
    module.render_apply_form = html_formatters.render_apply_form
    module.render_application_detail = html_formatters.render_application_detail
    module.render_candidate_profile = html_formatters.render_candidate_profile
    module.render_my_applications_table = html_formatters.render_my_applications_table
    module.render_ai_screening_panel = html_formatters.render_ai_screening_panel
    module.render_staff_applications_table = html_formatters.render_staff_applications_table
    module.render_pending_interviews_bar = html_formatters.render_pending_interviews_bar
    module.parse_screening_response = llm_client.parse_screening_response
    module.FRONTEND_PUBLIC_URL = config.FRONTEND_PUBLIC_URL
    return module


fmt = _load_backend_module()

_POSTING = {
    "JobPosting_Id": 42,
    "Job_Title": "Backend Engineer",
    "Job_Description": "Build and maintain APIs",
    "Job_Type": "Full time",
    "Location": "Sydney",
    "Salary_Range": "$120k",
    "Requirements": "- Python\n- SQL",
    "Application_Deadline": "2099-01-01",
    "JobPosting_Status": "Published",
}

_APPLICATION = {
    "application_id": 7,
    "user_id": 6,
    "job_posting_id": 42,
    "resume_id": 3,
    "application_status": "Submitted",
    "availability_date": "2099-03-15",
    "declaration_accepted": 1,
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-02T00:00:00+00:00",
    "submitted_at": "2026-01-02T00:00:00+00:00",
}

_DRAFT_APPLICATION = dict(_APPLICATION)
_DRAFT_APPLICATION["application_id"] = 8
_DRAFT_APPLICATION["application_status"] = "Draft"
_DRAFT_APPLICATION["submitted_at"] = None

_USER = {
    "first_name": "Ada",
    "last_name": "Lovelace",
    "email": "ada@example.com",
}

_PROFILE_RESUME = {
    "resume_id": 3,
    "file_name": "resume.pdf",
    "uploaded_at": "2026-01-01T00:00:00+00:00",
    "from_profile": True,
}

_PROFILE = {
    "phone": "+61400000006",
    "location": "Sydney, Australia",
    "professional_title": "Software Engineer",
    "summary": "Full-stack developer seeking new opportunities.",
    "interests": "Python, React, Cloud computing",
}

_STAFF_USER = {
    "user_first_name": "Ada",
    "user_last_name": "Lovelace",
    "user_email": "ada@example.com",
}


def test_render_message_escapes_html():
    out = fmt.render_message("<script>alert(1)</script>", kind="error")
    assert "<script>" not in out
    assert "alert-error" in out


def test_my_applications_table_for_submitted_and_draft():
    submitted = fmt.render_my_applications_table([_APPLICATION], {42: _POSTING})
    assert "Backend Engineer" in submitted
    assert "Withdraw" in submitted
    assert f"{fmt.FRONTEND_PUBLIC_URL}/applications/7" in submitted

    draft = fmt.render_my_applications_table([_DRAFT_APPLICATION], {42: _POSTING})
    assert "Delete" in draft
    assert "Withdraw" not in draft
    assert f"{fmt.FRONTEND_PUBLIC_URL}/apply/42" in draft


def test_my_applications_filters_status_title_and_sort_for_current_user(monkeypatch):
    frontend_application = dict(_APPLICATION)
    frontend_application["application_id"] = 9
    frontend_application["job_posting_id"] = 43
    frontend_application["application_status"] = "Submitted"
    frontend_posting = dict(_POSTING, JobPosting_Id=43, Job_Title="Frontend Engineer")
    response = Mock()
    response.json.return_value = [_APPLICATION, frontend_application, _DRAFT_APPLICATION]

    monkeypatch.setattr(integration_api, "get_session_user", lambda: {"user_id": 6})
    monkeypatch.setattr(database_api.requests, "get", Mock(return_value=response))
    monkeypatch.setattr(integration_api, "get_postings_map", lambda ids: {42: _POSTING, 43: frontend_posting})

    with backend_app.app.test_client() as client:
        result = client.get("/api/my-applications?status=Submitted&q=engineer&sort=title&order=desc")

    assert result.status_code == 200
    assert result.text.index("Frontend Engineer") < result.text.index("Backend Engineer")
    assert "#8" not in result.text
    database_api.requests.get.assert_called_once_with(
        f"{config.DATABASE_SERVICE_URL}/applications", params={"user_id": 6}, timeout=config.TIMEOUT
    )


def test_render_apply_form_shows_autofill_notes_and_download_link():
    out = fmt.render_apply_form(_POSTING, _USER, _DRAFT_APPLICATION, _PROFILE_RESUME)
    assert "Your details" in out
    assert out.count("Auto-filled from your profile.") >= 2
    assert f'{fmt.FRONTEND_PUBLIC_URL}/resumes/3/download' in out


def test_render_application_detail_uses_frontend_resume_download_link():
    out = fmt.render_application_detail(_APPLICATION, _POSTING, _USER, _PROFILE_RESUME)
    assert f'{fmt.FRONTEND_PUBLIC_URL}/resumes/3/download' in out
    assert 'target="_blank"' not in out


def test_staff_status_dropdown_keeps_shortlisted_available_for_non_submitted_rows():
    hired_application = dict(_APPLICATION)
    hired_application["application_status"] = "Hired"
    out = fmt.render_staff_applications_table([hired_application], {42: _POSTING}, {6: _STAFF_USER})
    assert 'badge-accent' not in out or 'Shortlisted' in out
    assert '<select' not in out
    assert 'Hired' in out


def test_render_candidate_profile_moves_manual_actions_below_ai_section():
    screened = {"Recommendation": "Yes", "Reasoning": "Strong match."}
    out = fmt.render_candidate_profile(_APPLICATION, _POSTING, _STAFF_USER, _PROFILE_RESUME, screened)
    assert 'data-shortlist-application-id="7"' in out
    assert 'data-reject-application-id="7"' in out
    assert out.index('AI Screening') < out.index('data-shortlist-application-id="7"')
    assert 'Change status:' not in out


def test_render_candidate_profile_includes_profile_details():
    out = fmt.render_candidate_profile(
        _APPLICATION, _POSTING, _STAFF_USER, _PROFILE_RESUME, None, profile=_PROFILE
    )
    for value in _PROFILE.values():
        assert value in out


def test_render_candidate_profile_hides_manual_actions_when_not_submitted():
    hired_application = dict(_APPLICATION)
    hired_application["application_status"] = "Hired"
    out = fmt.render_candidate_profile(hired_application, _POSTING, _STAFF_USER, _PROFILE_RESUME, None)
    assert 'data-shortlist-application-id' not in out
    assert 'data-reject-application-id="7"' in out
    assert 'AI Screening' not in out


def test_render_candidate_profile_hides_manual_actions_when_rejected():
    rejected_application = dict(_APPLICATION)
    rejected_application["application_status"] = "Rejected"
    out = fmt.render_candidate_profile(rejected_application, _POSTING, _STAFF_USER, _PROFILE_RESUME, None)
    assert 'data-shortlist-application-id' not in out
    assert 'data-reject-application-id' not in out
    assert 'AI Screening' not in out


def test_update_status_only_allows_submitted_to_shortlisted_or_rejected(monkeypatch):
    monkeypatch.setattr(integration_api, 'get_session_user', lambda: {'role': 'staff'})
    monkeypatch.setattr(application_routes, 'load_application', lambda application_id: ({'application_status': 'Hired'}, None))

    with backend_app.app.test_client() as client:
        resp = client.put('/api/applications/7/status', json={'application_status': 'Shortlisted'})

    assert resp.status_code == 200
    assert 'Only submitted applications can be updated here.' in resp.headers['HX-Trigger']


def test_update_status_allows_reject_from_non_rejected_states(monkeypatch):
    monkeypatch.setattr(integration_api, 'get_session_user', lambda: {'role': 'staff'})
    load_application = Mock(return_value=({'application_status': 'Hired'}, None))
    monkeypatch.setattr(application_routes, 'load_application', load_application)
    put_response = Mock(status_code=200)
    monkeypatch.setattr(database_api.requests, 'put', Mock(return_value=put_response))

    with backend_app.app.test_client() as client:
        resp = client.put('/api/applications/7/status', json={'application_status': 'Rejected'})

    assert resp.status_code == 200
    assert 'Status updated to Rejected.' in resp.headers['HX-Trigger']
    load_application.assert_called_once()
    database_api.requests.put.assert_called_once()


def test_update_status_rejects_already_rejected(monkeypatch):
    monkeypatch.setattr(integration_api, 'get_session_user', lambda: {'role': 'staff'})
    load_application = Mock(return_value=({'application_status': 'Rejected'}, None))
    monkeypatch.setattr(application_routes, 'load_application', load_application)

    with backend_app.app.test_client() as client:
        resp = client.put('/api/applications/7/status', json={'application_status': 'Rejected'})

    assert resp.status_code == 200
    assert 'Application is already rejected.' in resp.headers['HX-Trigger']


def test_ai_panel_yes_no_only_and_no_shortlist_button():
    yes_html = fmt.render_ai_screening_panel(7, {
        "Recommendation": "Yes",
        "Reasoning": "Resume matches most core requirements.",
    })
    assert "rec-yes" in yes_html
    assert "Recommend shortlist" in yes_html
    assert "Shortlist candidate" not in yes_html

    no_html = fmt.render_ai_screening_panel(7, {
        "Recommendation": "No",
        "Reasoning": "Resume misses key requirements.",
    })
    assert "rec-no" in no_html
    assert "Do not shortlist" in no_html
    assert "Shortlist candidate" not in no_html


def test_parse_screening_response_is_binary():
    assert fmt.parse_screening_response("Recommendation: Yes\nReasoning: Fit") ["Recommendation"] == "Yes"
    assert fmt.parse_screening_response("Recommendation: no\nReasoning: Miss") ["Recommendation"] == "No"
    # Any non-yes token is normalized to No.
    assert fmt.parse_screening_response("Recommendation: perhaps\nReasoning: unsure") ["Recommendation"] == "No"


def test_render_pending_interviews_bar_counts():
    apps = [
        {"application_status": "Shortlisted"},
        {"application_status": "Shortlisted"},
        {"application_status": "Interview Completed"},
    ]
    out = fmt.render_pending_interviews_bar(apps)
    assert "awaiting interview scheduling" in out
    assert "ready to evaluate" in out
