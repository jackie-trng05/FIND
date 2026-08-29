# Student 1 CI Workflow Report

- Workflow: student-1-ci
- Run ID: 32876815704
- Commit SHA: 142da490175ca9ea1a5646026ff974380ca45df3
- Branch: 17/merge
- Repository: jackie-trng05/FIND

## CI Stages

1. Docker image build
2. Student 1 service smoke check
3. Automated tests (pytest)
4. Evidence generation

## Current Testing Status

Student 1 pytest suite result: **passed**
(90/90 passed,
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
collecting ... collected 90 items

tests/test_backend_profiles.py::test_requires_authentication PASSED      [  1%]
tests/test_backend_profiles.py::test_invalid_session_rejected PASSED     [  2%]
tests/test_backend_profiles.py::test_create_profile_injects_user_id PASSED [  3%]
tests/test_backend_profiles.py::test_get_my_profile_when_none_exists PASSED [  4%]
tests/test_backend_profiles.py::test_get_my_profile_when_exists PASSED   [  5%]
tests/test_backend_profiles.py::test_get_profile_forbidden_for_non_owner PASSED [  6%]
tests/test_backend_profiles.py::test_get_profile_allowed_for_owner PASSED [  7%]
tests/test_backend_profiles.py::test_update_profile_forbidden_for_non_owner PASSED [  8%]
tests/test_backend_profiles.py::test_update_profile_allowed_for_owner PASSED [ 10%]
tests/test_backend_profiles.py::test_delete_profile_forbidden_for_non_owner PASSED [ 11%]
tests/test_backend_profiles.py::test_delete_profile_allowed_for_owner PASSED [ 12%]
tests/test_backend_profiles.py::test_update_user_identity_proxies_to_shared_api PASSED [ 13%]
tests/test_backend_profiles.py::test_update_user_identity_rejects_missing_first_name PASSED [ 14%]
tests/test_backend_profiles.py::test_update_user_identity_rejects_missing_last_name PASSED [ 15%]
tests/test_backend_profiles.py::test_update_user_identity_rejects_blank_names PASSED [ 16%]
tests/test_backend_profiles.py::test_update_user_identity_propagates_shared_api_failure PASSED [ 17%]
tests/test_backend_profiles.py::test_get_profile_not_found_propagates PASSED [ 18%]
tests/test_backend_profiles.py::test_update_profile_not_found_propagates PASSED [ 20%]
tests/test_backend_profiles.py::test_delete_profile_not_found_propagates PASSED [ 21%]
tests/test_backend_profiles.py::test_logout_proxies_to_shared_api PASSED [ 22%]
tests/test_backend_resumes.py::test_upload_resume_forbidden_for_staff PASSED [ 23%]
tests/test_backend_resumes.py::test_upload_resume_forbidden_for_non_owner PASSED [ 24%]
tests/test_backend_resumes.py::test_upload_resume_success_for_owner PASSED [ 25%]
tests/test_backend_resumes.py::test_list_resumes_forbidden_for_staff PASSED [ 26%]
tests/test_backend_resumes.py::test_list_resumes_forbidden_for_non_owner PASSED [ 27%]
tests/test_backend_resumes.py::test_list_resumes_success_for_owner PASSED [ 28%]
tests/test_backend_resumes.py::test_download_resume_allowed_for_staff PASSED [ 30%]
tests/test_backend_resumes.py::test_download_resume_forbidden_for_non_owner PASSED [ 31%]
tests/test_backend_resumes.py::test_download_resume_success_for_owner PASSED [ 32%]
tests/test_backend_resumes.py::test_delete_resume_forbidden_for_staff PASSED [ 33%]
tests/test_backend_resumes.py::test_delete_resume_forbidden_for_non_owner PASSED [ 34%]
tests/test_backend_resumes.py::test_delete_resume_success_for_owner PASSED [ 35%]
tests/test_backend_resumes.py::test_upload_resume_multipart_success_for_owner PASSED [ 36%]
tests/test_backend_resumes.py::test_upload_resume_multipart_rejects_no_file_selected PASSED [ 37%]
tests/test_backend_resumes.py::test_upload_resume_multipart_rejects_disallowed_type PASSED [ 38%]
tests/test_backend_resumes.py::test_upload_resume_multipart_rejects_oversized_file PASSED [ 40%]
tests/test_backend_resumes.py::test_download_resume_not_found_propagates PASSED [ 41%]
tests/test_backend_resumes.py::test_download_resume_file_missing_after_ownership_check PASSED [ 42%]
tests/test_backend_resumes.py::test_delete_resume_not_found_propagates PASSED [ 43%]
tests/test_backend_resumes.py::test_get_resume_meta_forbidden_for_non_owner PASSED [ 44%]
tests/test_backend_resumes.py::test_get_resume_meta_success_for_owner PASSED [ 45%]
tests/test_backend_resumes.py::test_get_resume_meta_success_for_staff PASSED [ 46%]
tests/test_backend_resumes.py::test_get_resume_meta_not_found PASSED     [ 47%]
tests/test_backend_resumes.py::test_get_resume_meta_no_ownership_check_when_unlinked PASSED [ 48%]
tests/test_backend_resumes.py::test_download_resume_no_ownership_check_when_unlinked PASSED [ 50%]
tests/test_backend_resumes.py::test_delete_resume_allowed_when_unlinked PASSED [ 51%]
tests/test_backend_resumes.py::test_upload_unlinked_resume_forbidden_for_staff PASSED [ 52%]
tests/test_backend_resumes.py::test_upload_unlinked_resume_success PASSED [ 53%]
tests/test_database_profiles.py::test_create_profile_success PASSED      [ 54%]
tests/test_database_profiles.py::test_create_profile_missing_required_field PASSED [ 55%]
tests/test_database_profiles.py::test_create_profile_no_body PASSED      [ 56%]
tests/test_database_profiles.py::test_create_profile_duplicate_user_conflicts PASSED [ 57%]
tests/test_database_profiles.py::test_get_profile_by_id PASSED           [ 58%]
tests/test_database_profiles.py::test_get_profile_by_id_not_found PASSED [ 60%]
tests/test_database_profiles.py::test_get_profile_by_user PASSED         [ 61%]
tests/test_database_profiles.py::test_get_profile_by_user_not_found PASSED [ 62%]
tests/test_database_profiles.py::test_update_profile_success PASSED      [ 63%]
tests/test_database_profiles.py::test_update_profile_not_found PASSED    [ 64%]
tests/test_database_profiles.py::test_update_profile_blank_phone_rejected PASSED [ 65%]
tests/test_database_profiles.py::test_delete_profile_success PASSED      [ 66%]
tests/test_database_profiles.py::test_delete_profile_not_found PASSED    [ 67%]
tests/test_database_profiles.py::test_delete_profile_cascades_resumes PASSED [ 68%]
tests/test_database_resumes.py::test_upload_resume_success PASSED        [ 70%]
tests/test_database_resumes.py::test_upload_resume_missing_fields PASSED [ 71%]
tests/test_database_resumes.py::test_upload_resume_rejects_disallowed_file_type PASSED [ 72%]
tests/test_database_resumes.py::test_upload_resume_rejects_invalid_base64 PASSED [ 73%]
tests/test_database_resumes.py::test_upload_resume_rejects_oversized_file PASSED [ 74%]
tests/test_database_resumes.py::test_upload_resume_profile_not_found PASSED [ 75%]
tests/test_database_resumes.py::test_get_resumes_for_profile PASSED      [ 76%]
tests/test_database_resumes.py::test_get_resumes_for_profile_multiple PASSED [ 77%]
tests/test_database_resumes.py::test_upload_resume_rejects_second_upload_for_same_profile PASSED [ 78%]
tests/test_database_resumes.py::test_get_resume_meta PASSED              [ 80%]
tests/test_database_resumes.py::test_get_resume_meta_not_found PASSED    [ 81%]
tests/test_database_resumes.py::test_get_resume_file PASSED              [ 82%]
tests/test_database_resumes.py::test_get_resume_file_not_found PASSED    [ 83%]
tests/test_database_resumes.py::test_delete_resume_success PASSED        [ 84%]
tests/test_database_resumes.py::test_delete_resume_not_found PASSED      [ 85%]
tests/test_database_resumes.py::test_upload_unlinked_resume_success PASSED [ 86%]
tests/test_database_resumes.py::test_upload_unlinked_resume_missing_fields PASSED [ 87%]
tests/test_database_resumes.py::test_upload_unlinked_resume_rejects_disallowed_file_type PASSED [ 88%]
tests/test_database_resumes.py::test_upload_unlinked_resume_no_uniqueness_conflict PASSED [ 90%]
tests/test_frontend.py::test_health PASSED                               [ 91%]
tests/test_frontend.py::test_index_redirects_to_profile PASSED           [ 92%]
tests/test_frontend.py::test_profile_page_renders PASSED                 [ 93%]
tests/test_frontend.py::test_proxy_profiles_post_forwards_json_and_cookie PASSED [ 94%]
tests/test_frontend.py::test_proxy_profiles_sub_forwards_get PASSED      [ 95%]
tests/test_frontend.py::test_proxy_resumes_forwards_delete PASSED        [ 96%]
tests/test_frontend.py::test_proxy_user_forwards_put PASSED              [ 97%]
tests/test_frontend.py::test_proxy_multipart_upload_forwards_file PASSED [ 98%]
tests/test_frontend.py::test_proxy_logout_clears_session_cookie PASSED   [100%]

- generated xml file: /home/runner/work/FIND/FIND/student-1/pytest-results.xml -
============================== 90 passed in 3.63s ==============================
```
