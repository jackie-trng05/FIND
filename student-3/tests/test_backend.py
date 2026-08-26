"""Tests for the Student 3 backend helper rendering and AI parsing logic.

The backend is composed from the ``config``, ``services`` and ``views``
packages (see ``backend/app.py``); this suite exercises the presentation and
AI-parsing helpers directly from those modules.
"""

import os
import types

# config.py reads these service URLs at import time.
os.environ.setdefault("DATABASE_SERVICE_URL", "http://student-3-db:6003")
os.environ.setdefault("SHARED_API_URL", "http://find-shared-api:5000")
os.environ.setdefault("SHARED_DB_URL", "http://find-shared-db:6000")
os.environ.setdefault("POSTINGS_DB_URL", "http://student-2-db:6002")
os.environ.setdefault("STUDENT_1_DB_URL", "http://find-student-1-db:6001")

# backend/ is placed on sys.path by conftest.py.
import config
from services import llm_client
from views import html_formatters


def _load_backend_module():
    """Expose the formatter/parsing helpers under a single namespace."""
    module = types.SimpleNamespace()
    module.render_message = html_formatters.render_message
    module.render_my_applications_table = html_formatters.render_my_applications_table
    module.render_ai_screening_panel = html_formatters.render_ai_screening_panel
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
