# student-2 CI Evidence

Run: https://github.com/jackie-trng05/FIND/actions/runs/38985346182

Tested commit: cae018c09a9cb7702730dbbbb3977523168f4fc0

============================= test session starts ==============================
platform linux -- Python 3.11.17, pytest-9.1.1, pluggy-1.7.0 -- /opt/hostedtoolcache/Python/3.11.17/x64/bin/python
cachedir: .pytest_cache
rootdir: /home/runner/work/FIND/FIND
configfile: pyproject.toml
collecting ... collected 7 items

tests/post_commit/test_api_job_postings.py::test_service_health PASSED   [ 14%]
tests/post_commit/test_api_job_postings.py::test_job_postings_exist PASSED [ 28%]
tests/post_commit/test_api_job_postings.py::test_job_posting_by_id PASSED [ 42%]
tests/post_commit/test_api_job_postings.py::test_job_postings_by_status PASSED [ 57%]
tests/post_commit/test_token_auth.py::test_valid_token_decodes PASSED    [ 71%]
tests/post_commit/test_token_auth.py::test_expired_token_rejected PASSED [ 85%]
tests/post_commit/test_token_auth.py::test_invalid_signature_rejected PASSED [100%]

=============================== warnings summary ===============================
student-2/tests/post_commit/test_token_auth.py::test_invalid_signature_rejected
  /opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/jwt/api_jwt.py:370: InsecureKeyLengthWarning: The HMAC key is 12 bytes long, which is below the minimum recommended length of 32 bytes for SHA256. See RFC 7518 Section 3.2.
    decoded = self.decode_complete(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
========================= 7 passed, 1 warning in 0.23s =========================


## Audit

```json
{"status": "PASS", "commit_sha": "cae018c09a9cb7702730dbbbb3977523168f4fc0", "timestamp": "2026-10-17T00:15:11Z"}

```

## Downloaded CI Unit Report

```json
{
  "workflow_name": "student-2-ci",
  "run_id": "38985346182",
  "commit_sha": "cae018c09a9cb7702730dbbbb3977523168f4fc0",
  "branch": "main",
  "repository": "jackie-trng05/FIND",
  "tests": {
    "status": "passed",
    "total": 32,
    "passed": 32,
    "failed": 0,
    "errors": 0,
    "skipped": 0
  }
}
```

## pytest-output.txt

```text
============================= test session starts ==============================
platform linux -- Python 3.11.17, pytest-8.3.3, pluggy-1.7.0 -- /opt/hostedtoolcache/Python/3.11.17/x64/bin/python
cachedir: .pytest_cache
rootdir: /home/runner/work/FIND/FIND
configfile: pyproject.toml
plugins: anyio-4.15.1
collecting ... collected 32 items

tests/test_backend.py::test_render_message_escapes_html PASSED           [  3%]
tests/test_backend.py::test_postings_table_row_links_to_detail_page PASSED [  6%]
tests/test_backend.py::test_postings_table_empty_state PASSED            [  9%]
tests/test_backend.py::test_posting_panel_shows_management_actions PASSED [ 12%]
tests/test_backend.py::test_posting_form_omits_user_id PASSED            [ 15%]
tests/test_backend.py::test_create_form_embeds_ai_helper_and_validation PASSED [ 18%]
tests/test_backend.py::test_edit_form_targets_panel_and_shows_error PASSED [ 21%]
tests/test_backend.py::test_skill_suggestions_deduplicate_repeated_items PASSED [ 25%]
tests/test_backend.py::test_skill_suggestions_render_headings_and_checkboxes PASSED [ 28%]
tests/test_database.py::test_health PASSED                               [ 31%]
tests/test_database.py::test_seed_has_at_least_ten_records PASSED        [ 34%]
tests/test_database.py::test_applicant_filter_returns_only_published PASSED [ 37%]
tests/test_database.py::test_create_defaults_to_draft PASSED             [ 40%]
tests/test_database.py::test_publish_and_unpublish_roundtrip PASSED      [ 43%]
tests/test_database.py::test_update_and_delete PASSED                    [ 46%]
tests/test_job_postings_tool.py::test_targeted_query_is_high_confidence_with_citations PASSED [ 50%]
tests/test_job_postings_tool.py::test_broad_status_listing_is_medium PASSED [ 53%]
tests/test_job_postings_tool.py::test_no_matches_is_low PASSED           [ 56%]
tests/test_job_postings_tool.py::test_service_unreachable_is_low PASSED  [ 59%]
tests/test_mcp_mode.py::test_mcp_status_reports_disabled_flags PASSED    [ 62%]
tests/test_mcp_mode.py::test_project_files_disabled_when_mcp_off PASSED  [ 65%]
tests/test_mcp_mode.py::test_ci_report_disabled_when_mcp_off PASSED      [ 68%]
tests/test_mcp_mode.py::test_job_postings_disabled_when_mcp_off PASSED   [ 71%]
tests/test_mcp_mode.py::test_role_recommendation_disabled_when_mcp_off PASSED [ 75%]
tests/test_mcp_mode.py::test_role_recommendation_requires_query PASSED   [ 78%]
tests/test_rag_mode.py::test_rag_status_reports_disabled_flags PASSED    [ 81%]
tests/test_rag_mode.py::test_answer_disabled_when_rag_off PASSED         [ 84%]
tests/test_rag_mode.py::test_retrieve_disabled_when_rag_off PASSED       [ 87%]
tests/test_rag_mode.py::test_refresh_disabled_when_rag_off PASSED        [ 90%]
tests/test_rag_mode.py::test_answer_rejects_empty_query PASSED           [ 93%]
tests/test_rag_mode.py::test_retrieve_rejects_empty_query PASSED         [ 96%]
tests/test_rag_mode.py::test_answer_maps_service_error_to_503 PASSED     [100%]

- generated xml file: /home/runner/work/FIND/FIND/student-2/pytest-results.xml -
============================== 32 passed in 0.57s ==============================

```

## pytest-results.xml

```text
<?xml version="1.0" encoding="utf-8"?><testsuites><testsuite name="pytest" errors="0" failures="0" skipped="0" tests="32" time="0.575" timestamp="2026-10-17T00:14:50.814203+00:00" hostname="runnervm8k3b6"><testcase classname="student-2.tests.test_backend" name="test_render_message_escapes_html" time="0.000" /><testcase classname="student-2.tests.test_backend" name="test_postings_table_row_links_to_detail_page" time="0.000" /><testcase classname="student-2.tests.test_backend" name="test_postings_table_empty_state" time="0.000" /><testcase classname="student-2.tests.test_backend" name="test_posting_panel_shows_management_actions" time="0.000" /><testcase classname="student-2.tests.test_backend" name="test_posting_form_omits_user_id" time="0.000" /><testcase classname="student-2.tests.test_backend" name="test_create_form_embeds_ai_helper_and_validation" time="0.000" /><testcase classname="student-2.tests.test_backend" name="test_edit_form_targets_panel_and_shows_error" time="0.000" /><testcase classname="student-2.tests.test_backend" name="test_skill_suggestions_deduplicate_repeated_items" time="0.000" /><testcase classname="student-2.tests.test_backend" name="test_skill_suggestions_render_headings_and_checkboxes" time="0.000" /><testcase classname="student-2.tests.test_database" name="test_health" time="0.012" /><testcase classname="student-2.tests.test_database" name="test_seed_has_at_least_ten_records" time="0.007" /><testcase classname="student-2.tests.test_database" name="test_applicant_filter_returns_only_published" time="0.006" /><testcase classname="student-2.tests.test_database" name="test_create_defaults_to_draft" time="0.007" /><testcase classname="student-2.tests.test_database" name="test_publish_and_unpublish_roundtrip" time="0.010" /><testcase classname="student-2.tests.test_database" name="test_update_and_delete" time="0.010" /><testcase classname="student-2.tests.test_job_postings_tool" name="test_targeted_query_is_high_confidence_with_citations" time="0.001" /><testcase classname="student-2.tests.test_job_postings_tool" name="test_broad_status_listing_is_medium" time="0.001" /><testcase classname="student-2.tests.test_job_postings_tool" name="test_no_matches_is_low" time="0.001" /><testcase classname="student-2.tests.test_job_postings_tool" name="test_service_unreachable_is_low" time="0.001" /><testcase classname="student-2.tests.test_mcp_mode" name="test_mcp_status_reports_disabled_flags" time="0.003" /><testcase classname="student-2.tests.test_mcp_mode" name="test_project_files_disabled_when_mcp_off" time="0.003" /><testcase classname="student-2.tests.test_mcp_mode" name="test_ci_report_disabled_when_mcp_off" time="0.003" /><testcase classname="student-2.tests.test_mcp_mode" name="test_job_postings_disabled_when_mcp_off" time="0.003" /><testcase classname="student-2.tests.test_mcp_mode" name="test_role_recommendation_disabled_when_mcp_off" time="0.003" /><testcase classname="student-2.tests.test_mcp_mode" name="test_role_recommendation_requires_query" time="0.003" /><testcase classname="student-2.tests.test_rag_mode" name="test_rag_status_reports_disabled_flags" time="0.002" /><testcase classname="student-2.tests.test_rag_mode" name="test_answer_disabled_when_rag_off" time="0.002" /><testcase classname="student-2.tests.test_rag_mode" name="test_retrieve_disabled_when_rag_off" time="0.002" /><testcase classname="student-2.tests.test_rag_mode" name="test_refresh_disabled_when_rag_off" time="0.002" /><testcase classname="student-2.tests.test_rag_mode" name="test_answer_rejects_empty_query" time="0.002" /><testcase classname="student-2.tests.test_rag_mode" name="test_retrieve_rejects_empty_query" time="0.002" /><testcase classname="student-2.tests.test_rag_mode" name="test_answer_maps_service_error_to_503" time="0.002" /></testsuite></testsuites>
```
