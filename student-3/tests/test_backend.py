"""Tests for the Student 3 backend HTML fragment builders and screening parser."""

from views import html_formatters as fmt


_POSTING = {
    "JobPosting_Id": 42,
    "Job_Title": "Backend Engineer",
    "Job_Description": "Build and maintain the API.",
    "Job_Type": "Full time",
    "Location": "Sydney",
    "Salary_Range": "$120k",
    "Requirements": "- Python\n- SQL",
    "Application_Deadline": "2099-01-01",
    "JobPosting_Status": "Published",
}

_APPLICATION = {
    "Application_Id": 7,
    "User_Id": 6,
    "JobPosting_Id": 42,
    "Resume_Id": 3,
    "Application_Status": "Submitted",
    "Availability_Date": "2099-03-15",
    "Declaration_Accepted": 1,
    "Application_CreatedAt": "2026-01-01T00:00:00+00:00",
    "Application_UpdatedAt": "2026-01-02T00:00:00+00:00",
    "Application_SubmittedAt": "2026-01-02T00:00:00+00:00",
}

_DRAFT_APPLICATION = dict(_APPLICATION)
_DRAFT_APPLICATION["Application_Id"] = 8
_DRAFT_APPLICATION["Application_Status"] = "Draft"
_DRAFT_APPLICATION["Application_SubmittedAt"] = None

_USER_APPLICANT = {
    "first_name": "Emily", "last_name": "Johnson", "email": "e@example.com",
    "role": "applicant", "user_id": 6,
}
_USER_STAFF_DB = {
    "user_id": 6, "user_first_name": "Emily", "user_last_name": "Johnson",
    "user_email": "e@example.com", "user_role": "applicant",
}

_RESUME = {
    "Resume_Id": 3, "User_Id": 6, "Resume_Filename": "emily.pdf",
    "Resume_MimeType": "application/pdf", "Resume_SizeBytes": 2048,
    "Resume_UploadedAt": "2026-01-01T00:00:00+00:00",
}

_FRONTEND = "http://localhost:16010"
_BACKEND = "http://localhost:16011"


# --------------------------------------------------------------------------- #
# Message rendering                                                           #
# --------------------------------------------------------------------------- #

def test_render_message_escapes_html():
    out = fmt.render_message("<script>alert(1)</script>", kind="error")
    assert "<script>" not in out
    assert "alert-error" in out


# --------------------------------------------------------------------------- #
# Applicant My Applications table                                             #
# --------------------------------------------------------------------------- #

def test_my_applications_empty_state():
    out = fmt.render_my_applications_table([], {}, frontend_url=_FRONTEND)
    assert "empty-state" in out
    assert "No applications found" in out
    # 4 columns after removing the Date submitted + View/Continue column.
    assert 'colspan="4"' in out


def test_my_applications_submitted_shows_only_withdraw_button():
    out = fmt.render_my_applications_table(
        [_APPLICATION], {42: _POSTING}, frontend_url=_FRONTEND
    )
    assert "Backend Engineer" in out
    assert "Submitted" in out
    assert "Withdraw" in out
    # No standalone View / Continue links any more.
    assert "View" not in out
    assert "Continue" not in out
    # Draft-only Delete button is not present for Submitted rows.
    assert 'class="btn btn-danger btn-sm delete-btn"' not in out


def test_my_applications_draft_shows_delete_only():
    out = fmt.render_my_applications_table(
        [_DRAFT_APPLICATION], {42: _POSTING}, frontend_url=_FRONTEND
    )
    # Draft rows expose Delete, NOT Withdraw.
    assert "Delete" in out
    assert "Withdraw" not in out


def test_hired_row_hides_action_button():
    hired = dict(_APPLICATION)
    hired["Application_Status"] = "Hired"
    out = fmt.render_my_applications_table(
        [hired], {42: _POSTING}, frontend_url=_FRONTEND
    )
    assert "Withdraw" not in out
    assert "Delete" not in out


def test_draft_row_routes_to_apply_page():
    out = fmt.render_my_applications_table(
        [_DRAFT_APPLICATION], {42: _POSTING}, frontend_url=_FRONTEND
    )
    assert f"{_FRONTEND}/apply/42" in out
    # And other rows go to the detail page.
    out2 = fmt.render_my_applications_table(
        [_APPLICATION], {42: _POSTING}, frontend_url=_FRONTEND
    )
    assert f"{_FRONTEND}/applications/7" in out2


# --------------------------------------------------------------------------- #
# Applicant apply form                                                        #
# --------------------------------------------------------------------------- #

def test_apply_form_pre_fills_candidate_details():
    out = fmt.render_apply_form(
        backend_url=_BACKEND, posting=_POSTING, user=_USER_APPLICANT,
    )
    assert "Emily" in out
    assert "Johnson" in out
    assert "e@example.com" in out
    assert 'type="file"' in out
    assert 'name="Declaration_Accepted"' in out
    # Availability was removed from the applicant flow.
    assert 'name="Availability_Date"' not in out


def test_apply_form_requires_declaration_and_resume():
    out = fmt.render_apply_form(
        backend_url=_BACKEND, posting=_POSTING, user=_USER_APPLICANT,
    )
    assert "declaration" in out.lower()
    assert 'type="file"' in out


def test_apply_form_shows_resume_when_present():
    out = fmt.render_apply_form(
        backend_url=_BACKEND, posting=_POSTING, user=_USER_APPLICANT,
        application=_DRAFT_APPLICATION, resume=_RESUME,
    )
    assert "emily.pdf" in out


# --------------------------------------------------------------------------- #
# Applicant application detail                                                #
# --------------------------------------------------------------------------- #

def test_application_detail_shows_withdraw_for_submitted():
    out = fmt.render_application_detail(
        application=_APPLICATION, posting=_POSTING, user=_USER_APPLICANT,
        resume=_RESUME, backend_url=_BACKEND, frontend_url=_FRONTEND,
    )
    assert "Withdraw Application" in out
    # The new read-only detail layout uses the apply-form look.
    assert "Your details" in out
    assert "Resume" in out
    assert "Declaration" in out
    # Header status bar shows Status, Date submitted, and Application ID.
    assert "detail-status-bar" in out
    assert "Date submitted" in out


def test_application_detail_hides_withdraw_for_hired():
    hired = dict(_APPLICATION)
    hired["Application_Status"] = "Hired"
    out = fmt.render_application_detail(
        application=hired, posting=_POSTING, user=_USER_APPLICANT,
        resume=_RESUME, backend_url=_BACKEND, frontend_url=_FRONTEND,
    )
    assert "Withdraw Application" not in out


def test_application_detail_shows_schedule_interview_for_shortlisted():
    shortlisted = dict(_APPLICATION)
    shortlisted["Application_Status"] = "Shortlisted"
    out = fmt.render_application_detail(
        application=shortlisted, posting=_POSTING, user=_USER_APPLICANT,
        resume=_RESUME, backend_url=_BACKEND, frontend_url=_FRONTEND,
    )
    assert "Schedule Interview" in out


# --------------------------------------------------------------------------- #
# Staff All Applications table                                                #
# --------------------------------------------------------------------------- #

def test_staff_table_row_shows_status_select_and_candidate_name():
    postings = {42: _POSTING}
    users = {6: _USER_STAFF_DB}
    out = fmt.render_staff_applications_table(
        [_APPLICATION], postings, users, frontend_url=_FRONTEND,
    )
    assert "Emily Johnson" in out
    assert "status-select" in out
    # Row click goes to the candidate profile page.
    assert f"{_FRONTEND}/staff/applications/7" in out
    # Draft option must never appear in the staff status dropdown.
    assert 'value="Draft"' not in out
    # Only Shortlisted and Rejected are selectable; the current status
    # (Submitted) is also disabled so staff can't re-pick it.
    assert '<option value="Submitted" selected disabled>' in out
    assert '<option value="Shortlisted"' in out
    # Interview Scheduled etc. render but are disabled.
    assert 'value="Interview Scheduled" disabled' in out


def test_staff_table_actions_are_center_aligned():
    postings = {42: _POSTING}
    users = {6: _USER_STAFF_DB}
    app = dict(_APPLICATION); app["Application_Status"] = "Shortlisted"
    out = fmt.render_staff_applications_table(
        [app], postings, users, frontend_url=_FRONTEND,
    )
    assert 'cell-action-center' in out
    assert 'Interview' in out


def test_staff_table_shows_evaluate_button_when_interview_completed():
    app = dict(_APPLICATION); app["Application_Status"] = "Interview Completed"
    out = fmt.render_staff_applications_table(
        [app], {42: _POSTING}, {6: _USER_STAFF_DB}, frontend_url=_FRONTEND,
    )
    assert "Evaluate" in out


def test_staff_table_empty_state():
    out = fmt.render_staff_applications_table([], {}, {}, frontend_url=_FRONTEND)
    assert "empty-state" in out
    # Table now has 5 columns after Date submitted was removed.
    assert 'colspan="5"' in out


def test_pending_interviews_bar_counts_correctly():
    apps = [
        {"Application_Status": "Shortlisted"},
        {"Application_Status": "Shortlisted"},
        {"Application_Status": "Interview Completed"},
        {"Application_Status": "Submitted"},
    ]
    out = fmt.render_pending_interviews_bar(apps)
    assert ">2<" in out or "2</strong>" in out
    assert ">1<" in out or "1</strong>" in out


# --------------------------------------------------------------------------- #
# Candidate profile / AI screening panel                                      #
# --------------------------------------------------------------------------- #

def test_candidate_profile_shows_ai_empty_when_no_screening():
    out = fmt.render_candidate_profile(
        application=_APPLICATION, posting=_POSTING, user=_USER_STAFF_DB,
        resume=_RESUME, screening=None, backend_url=_BACKEND,
    )
    assert "Generate AI recommendation" in out
    assert "AI Screening" in out
    # The old "Application Status" section was removed; the status control now
    # lives next to the candidate's name.
    assert "Application Status" not in out
    assert "header-status-select" in out
    # Header dropdown only offers Shortlisted / Rejected as picker choices.
    assert '<option value="Shortlisted"' in out
    assert '<option value="Rejected"' in out
    # Current non-selectable status remains shown as disabled option.
    assert '<option value="Submitted" selected disabled>Submitted</option>' in out
    # Application Details is nested inside the Candidate Information section.
    assert "Application Details" not in out
    assert "Uploaded Resume" in out


def test_ai_panel_renders_recommendation_and_reasoning():
    screening = {
        "Recommendation": "Yes",
        "Reasoning": "Strong Python and API design experience aligns with the role.",
    }
    out = fmt.render_ai_screening_panel(application_id=7, screening=screening)
    assert "Recommendation" in out
    assert ">Yes<" in out
    assert "rec-yes" in out
    assert "Strong Python" in out
    # "Yes" recommendations expose the Shortlist button.
    assert "Shortlist candidate" in out


def test_ai_panel_no_shortlist_button_when_recommendation_is_no():
    out = fmt.render_ai_screening_panel(application_id=7, screening={
        "Recommendation": "No",
        "Reasoning": "Missing required experience.",
    })
    assert "Shortlist candidate" not in out
    assert "rec-no" in out


# --------------------------------------------------------------------------- #
# LLM response parsing                                                        #
# --------------------------------------------------------------------------- #

def test_parse_screening_response_extracts_recommendation_and_reasoning():
    text = (
        "Recommendation: Yes\n"
        "Reasoning: The candidate has 4 years of Python experience and has shipped\n"
        "comparable microservices. Strong overall fit."
    )
    parsed = fmt.parse_screening_response(text)
    assert parsed["Recommendation"] == "Yes"
    assert "Python experience" in parsed["Reasoning"]


def test_parse_screening_response_normalises_variants():
    assert fmt.parse_screening_response("Recommendation: no\nReasoning: X")["Recommendation"] == "No"
    assert fmt.parse_screening_response("Recommendation: perhaps\nReasoning: X")["Recommendation"] == "Maybe"


def test_parse_screening_response_handles_junk_gracefully():
    parsed = fmt.parse_screening_response("nonsense")
    assert parsed["Recommendation"] == "Maybe"
    assert parsed["Reasoning"] == "nonsense"
