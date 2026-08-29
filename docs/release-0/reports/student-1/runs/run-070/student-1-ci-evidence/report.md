# Student 1 CI Workflow Report

- Workflow: student-1-ci
- Run ID: 32961642933
- Commit SHA: b34bbbbd1e9fda52036da1c799beb5bf326a0623
- Branch: main
- Repository: jackie-trng05/FIND

## CI Stages

1. Docker image build
2. Student 1 service smoke check
3. Automated tests (pytest)
4. Evidence generation

## Current Testing Status

Student 1 pytest suite result: **passed**
(82/82 passed,
0 failed, 0 errors,
0 skipped).
See student-1/tests/README.md for the full feature-coverage breakdown.


## Pytest Results

```
============================= test session starts ==============================
platform linux -- Python 3.11.16, pytest-9.1.1, pluggy-1.6.0 -- /opt/hostedtoolcache/Python/3.11.16/x64/bin/python
cachedir: .pytest_cache
rootdir: /home/runner/work/FIND/FIND/student-1
plugins: requests-mock-1.12.1
collecting ... collected 82 items

tests/test_backend_html_formatters.py::test_render_message_escapes_html PASSED [  1%]
tests/test_backend_html_formatters.py::test_render_message_success_and_info PASSED [  2%]
tests/test_backend_html_formatters.py::test_render_user_details_panel_prefills_values PASSED [  3%]
tests/test_backend_html_formatters.py::test_render_user_details_panel_shows_error PASSED [  4%]
tests/test_backend_html_formatters.py::test_render_profile_panel_no_profile_shows_create_prompt PASSED [  6%]
tests/test_backend_html_formatters.py::test_render_profile_panel_existing_profile_shows_update_form_and_delete PASSED [  7%]
tests/test_backend_html_formatters.py::test_render_profile_panel_nests_resume_panel_for_applicants PASSED [  8%]
tests/test_backend_html_formatters.py::test_render_profile_panel_hides_resume_panel_for_staff PASSED [  9%]
tests/test_backend_html_formatters.py::test_render_resume_panel_no_profile_prompts_to_create_one PASSED [ 10%]
tests/test_backend_html_formatters.py::test_render_resume_panel_empty_shows_upload_form PASSED [ 12%]
tests/test_backend_html_formatters.py::test_render_resume_panel_with_resume_hides_upload_form PASSED [ 13%]
tests/test_backend_html_formatters.py::test_render_resume_panel_shows_inline_error PASSED [ 14%]
tests/test_backend_html_formatters.py::test_render_profile_panel_message_renders_below_submit_button PASSED [ 15%]
tests/test_backend_html_formatters.py::test_render_resume_panel_message_renders_below_upload_button PASSED [ 17%]
tests/test_backend_html_formatters.py::test_render_resume_panel_message_renders_below_table_when_resume_exists PASSED [ 18%]
tests/test_backend_profile_pages.py::test_get_profile_requires_authentication PASSED [ 19%]
tests/test_backend_profile_pages.py::test_get_profile_shows_create_prompt_when_none_exists PASSED [ 20%]
tests/test_backend_profile_pages.py::test_get_profile_shows_update_form_when_exists PASSED [ 21%]
tests/test_backend_profile_pages.py::test_create_profile_injects_user_id_and_shows_inline_success PASSED [ 23%]
tests/test_backend_profile_pages.py::test_create_profile_requires_phone PASSED [ 24%]
tests/test_backend_profile_pages.py::test_create_profile_shows_db_error PASSED [ 25%]
tests/test_backend_profile_pages.py::test_update_profile_forbidden_for_non_owner PASSED [ 26%]
tests/test_backend_profile_pages.py::test_update_profile_allowed_for_owner PASSED [ 28%]
tests/test_backend_profile_pages.py::test_update_profile_not_found_propagates PASSED [ 29%]
tests/test_backend_profile_pages.py::test_delete_profile_forbidden_for_non_owner PASSED [ 30%]
tests/test_backend_profile_pages.py::test_delete_profile_allowed_for_owner PASSED [ 31%]
tests/test_backend_resume_pages.py::test_get_resume_panel_requires_authentication PASSED [ 32%]
tests/test_backend_resume_pages.py::test_get_resume_panel_forbidden_for_staff PASSED [ 34%]
tests/test_backend_resume_pages.py::test_get_resume_panel_prompts_to_create_profile_first PASSED [ 35%]
tests/test_backend_resume_pages.py::test_get_resume_panel_lists_existing_resume PASSED [ 36%]
tests/test_backend_resume_pages.py::test_upload_resume_rejects_when_no_profile PASSED [ 37%]
tests/test_backend_resume_pages.py::test_upload_resume_rejects_disallowed_type PASSED [ 39%]
tests/test_backend_resume_pages.py::test_upload_resume_success PASSED    [ 40%]
tests/test_backend_resume_pages.py::test_upload_resume_shows_duplicate_error PASSED [ 41%]
tests/test_backend_resume_pages.py::test_delete_resume_forbidden_for_non_owner PASSED [ 42%]
tests/test_backend_resume_pages.py::test_delete_resume_allowed_for_owner PASSED [ 43%]
tests/test_backend_resume_pages.py::test_download_resume_forbidden_for_non_owner PASSED [ 45%]
tests/test_backend_resume_pages.py::test_download_resume_allowed_for_owner PASSED [ 46%]
tests/test_backend_resume_pages.py::test_download_resume_allowed_for_staff PASSED [ 47%]
tests/test_backend_user_pages.py::test_get_user_details_requires_authentication PASSED [ 48%]
tests/test_backend_user_pages.py::test_get_user_details_renders_prefilled_form PASSED [ 50%]
tests/test_backend_user_pages.py::test_update_user_details_requires_authentication PASSED [ 51%]
tests/test_backend_user_pages.py::test_update_user_details_rejects_missing_first_name PASSED [ 52%]
tests/test_backend_user_pages.py::test_update_user_details_rejects_blank_names PASSED [ 53%]
tests/test_backend_user_pages.py::test_update_user_details_success_triggers_toast PASSED [ 54%]
tests/test_backend_user_pages.py::test_update_user_details_propagates_shared_api_failure PASSED [ 56%]
tests/test_database_profiles.py::test_create_profile_success PASSED      [ 57%]
tests/test_database_profiles.py::test_create_profile_missing_required_field PASSED [ 58%]
tests/test_database_profiles.py::test_create_profile_no_body PASSED      [ 59%]
tests/test_database_profiles.py::test_create_profile_duplicate_user_conflicts PASSED [ 60%]
tests/test_database_profiles.py::test_get_profile_by_id PASSED           [ 62%]
tests/test_database_profiles.py::test_get_profile_by_id_not_found PASSED [ 63%]
tests/test_database_profiles.py::test_get_profile_by_user PASSED         [ 64%]
tests/test_database_profiles.py::test_get_profile_by_user_not_found PASSED [ 65%]
tests/test_database_profiles.py::test_update_profile_success PASSED      [ 67%]
tests/test_database_profiles.py::test_update_profile_not_found PASSED    [ 68%]
tests/test_database_profiles.py::test_update_profile_blank_phone_rejected PASSED [ 69%]
tests/test_database_profiles.py::test_delete_profile_success PASSED      [ 70%]
tests/test_database_profiles.py::test_delete_profile_not_found PASSED    [ 71%]
tests/test_database_profiles.py::test_delete_profile_cascades_resumes PASSED [ 73%]
tests/test_database_resumes.py::test_upload_resume_success PASSED        [ 74%]
tests/test_database_resumes.py::test_upload_resume_missing_fields PASSED [ 75%]
tests/test_database_resumes.py::test_upload_resume_rejects_disallowed_file_type PASSED [ 76%]
tests/test_database_resumes.py::test_upload_resume_rejects_invalid_base64 PASSED [ 78%]
tests/test_database_resumes.py::test_upload_resume_rejects_oversized_file PASSED [ 79%]
tests/test_database_resumes.py::test_upload_resume_profile_not_found PASSED [ 80%]
tests/test_database_resumes.py::test_get_resumes_for_profile PASSED      [ 81%]
tests/test_database_resumes.py::test_get_resumes_for_profile_multiple PASSED [ 82%]
tests/test_database_resumes.py::test_upload_resume_rejects_second_upload_for_same_profile PASSED [ 84%]
tests/test_database_resumes.py::test_get_resume_meta PASSED              [ 85%]
tests/test_database_resumes.py::test_get_resume_meta_not_found PASSED    [ 86%]
tests/test_database_resumes.py::test_get_resume_file PASSED              [ 87%]
tests/test_database_resumes.py::test_get_resume_file_not_found PASSED    [ 89%]
tests/test_database_resumes.py::test_delete_resume_success PASSED        [ 90%]
tests/test_database_resumes.py::test_delete_resume_not_found PASSED      [ 91%]
tests/test_database_resumes.py::test_upload_unlinked_resume_success PASSED [ 92%]
tests/test_database_resumes.py::test_upload_unlinked_resume_missing_fields PASSED [ 93%]
tests/test_database_resumes.py::test_upload_unlinked_resume_rejects_disallowed_file_type PASSED [ 95%]
tests/test_database_resumes.py::test_upload_unlinked_resume_no_uniqueness_conflict PASSED [ 96%]
tests/test_frontend.py::test_health PASSED                               [ 97%]
tests/test_frontend.py::test_index_renders_profile_page PASSED           [ 98%]
tests/test_frontend.py::test_profile_page_renders PASSED                 [100%]

- generated xml file: /home/runner/work/FIND/FIND/student-1/pytest-results.xml -
============================== 82 passed in 1.11s ==============================
```
