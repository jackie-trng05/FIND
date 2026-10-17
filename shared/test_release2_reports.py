import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from shared import release2_delivery as delivery


SPEC = importlib.util.spec_from_file_location("release2_reports", Path(__file__).with_name("release2_reports.py"))
reports = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reports)


class Release2ReportsTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        report_patch = patch.object(reports, "REPORTS", self.root / "reports")
        report_patch.start()
        self.addCleanup(report_patch.stop)
        git_patch = patch.object(reports, "git", return_value="a" * 40)
        git_patch.start()
        self.addCleanup(git_patch.stop)

    def test_refresh_never_invents_passes(self):
        reports.render()
        output = (reports.REPORTS / "test-results.md").read_text()
        self.assertIn("student-5 | PENDING", output)
        self.assertNotIn("| PASS |", output)
        self.assertEqual(len(list(reports.REPORTS.glob("*.md"))), 9)
        self.assertIn("<!-- TODO: Cloud deployment has not been performed", (reports.REPORTS / "deployment-results.md").read_text())

    def test_ci_evidence_displays_tested_commit_not_import_checkout(self):
        event = {"status": "PASS", "timestamp": "2026-10-17", "commit": "a" * 40,
                 "tested_commit": "b" * 40, "dirty": True}
        self.assertIn("tested commit " + "b" * 12, reports.event_line(event))

    def test_consolidation_keeps_latest_capture_and_rewrites_nested_links(self):
        old = reports.artifact("old.txt", "Superseded failed attempt")
        reports.save_event("integration", "student-1", "FAIL", feature="ai-mode", artifact=old)
        current = reports.artifact("ai.json", json.dumps({"response": "Actual successful model output"}))
        reports.save_event("integration", "student-1", "PASS", feature="ai-mode", artifact=current)
        local = reports.artifact("local.json", json.dumps({"checks": {"ai-mode": {"status": "PASS", "evidence": current}}}))
        reports.save_event("local", "student-1", "PENDING", artifact=local,
                           summary={"checks": {"ai-mode": {"status": "PASS", "evidence": current}}})
        events = reports.read_events()
        reports.consolidate_evidence()
        retained = reports.read_events()
        self.assertEqual(len(retained), 2)
        self.assertEqual(retained[0]["id"], events[1]["id"])
        self.assertEqual(retained[0]["timestamp"], events[1]["timestamp"])
        self.assertFalse((reports.REPORTS / old).exists())
        self.assertFalse((reports.REPORTS / current).exists())
        pack = reports.REPORTS / "evidence/student-1-evidence.json"
        text = pack.read_text()
        self.assertIn("Actual successful model output", text)
        self.assertNotIn("Superseded failed attempt", text)
        self.assertEqual(retained[1]["summary"]["checks"]["ai-mode"]["evidence"], "evidence/student-1-evidence.json")
        reports.consolidate_evidence()
        self.assertEqual(pack.read_text(), text)

    def test_consolidation_discloses_unresolved_failure_and_preserves_unmanaged_files(self):
        failed = reports.artifact("scan.txt", "Large failed scanner transcript")
        reports.save_event("security", "group", "FAIL", artifact=failed, scanner="ruff", summary={"finding_count": 2})
        custom = reports.REPORTS / "evidence/human-note.txt"
        custom.write_text("Human-owned file")
        reports.consolidate_evidence()
        event = reports.read_events()[0]
        self.assertEqual(event["status"], "FAIL")
        self.assertEqual(event["summary"]["finding_count"], 2)
        pack = json.loads((reports.REPORTS / event["artifact"]).read_text())
        self.assertIn("no passing replacement", pack["records"][0]["omitted"])
        self.assertEqual(custom.read_text(), "Human-owned file")

    def test_consolidation_trims_windows_workflow_logs_but_keeps_assertions(self):
        path = reports.artifact("workflow.txt", "Run: https://github.com/team/find/actions/runs/123\r\nassert response.status_code == 200\r\n\r\nWORKFLOW LOGS:\r\nVERBOSE WORKFLOW LOG")
        reports.save_event("ci-supporting", "student-1", "CAPTURED", artifact=path)
        reports.consolidate_evidence()
        text = (reports.REPORTS / "evidence/student-1-evidence.json").read_text()
        self.assertIn("assert response.status_code == 200", text)
        self.assertNotIn("VERBOSE WORKFLOW LOG", text)

    def test_ci_import_includes_matching_downloaded_unit_report(self):
        source = self.root / "student-1-post-commit-evidence"
        source.mkdir()
        (source / "test-results.md").write_text("tests/post_commit/test_api_profiles.py::test_profile_by_id PASSED")
        (source / "test-audit.jsonl").write_text(json.dumps({"status": "PASS", "commit_sha": "a" * 40}))
        unit_source = self.root / "student-1-ci-evidence"
        unit_source.mkdir()
        unit_report = {"workflow_name": "student-1-ci", "commit_sha": "a" * 40,
                       "tests": {"status": "passed", "total": 108, "passed": 108}}
        (unit_source / "report.json").write_text(json.dumps(unit_report))
        self.assertEqual(reports.import_ci("student-1", source, "https://github.com/team/find/actions/runs/123", "a" * 40), 0)
        event = reports.read_events()[-1]
        self.assertEqual(event["summary"]["unit_tests"]["passed"], 108)
        self.assertEqual(len(event["summary"]["post_commit_tests"]), 1)

    def test_ci_import_requires_matching_tested_commit(self):
        (self.root / "test-results.md").write_text("test_profile_by_id PASSED")
        (self.root / "test-audit.jsonl").write_text(json.dumps({"status": "PASS", "commit_sha": "b" * 40}))
        with self.assertRaisesRegex(ValueError, "matching"):
            reports.import_ci("student-1", self.root, "https://github.com/team/find/actions/runs/123", "a" * 40)
        self.assertEqual(reports.read_events(), [])

    def test_ci_import_preserves_real_failure_and_provenance(self):
        (self.root / "test-results.md").write_text("test_profile_by_id FAILED")
        (self.root / "test-audit.jsonl").write_text(json.dumps({"status": "FAIL", "commit_sha": "a" * 40}))
        self.assertEqual(reports.import_ci("student-1", self.root, "https://github.com/team/find/actions/runs/123", "a" * 40), 1)
        self.assertEqual(reports.read_events()[-1]["status"], "FAIL")
        self.assertIn("student-1 | FAIL", (reports.REPORTS / "test-results.md").read_text())

    def test_deployment_report_rejects_health_only_evidence(self):
        source = self.root / "local.json"
        source.write_text(json.dumps({"reviewer": "Student 1", "timestamp": "2026-10-17", "checks": {"frontend": {"status": "PASS", "evidence": "HTTP 200"}}}))
        with self.assertRaisesRegex(ValueError, "Required local checks"):
            reports.record("local", "student-1", source)

    def test_pending_deployment_checks_remain_pending(self):
        source = self.root / "local.json"
        source.write_text(json.dumps({"reviewer": "Student 1", "timestamp": "2026-10-17", "frontend_url": "http://localhost:16004", "execution_logs": ["terminal transcript"],
                                      "checks": {name: {"status": "PENDING", "evidence": "Not executed"} for name in reports.CHECKS["local"]}}))
        reports.record("local", "student-1", source)
        self.assertEqual(reports.read_events()[-1]["status"], "PENDING")

    def test_review_uses_latest_actual_evidence_not_only_file_presence(self):
        first = reports.artifact("old.txt", "old failure")
        reports.save_event("security", "student-1", "FAIL", scanner="ruff", artifact=first)
        second = reports.artifact("new.txt", "real scan output")
        reports.save_event("security", "student-1", "PASS", scanner="ruff", artifact=second)
        evidence = reports.review_evidence("pre_test")
        self.assertIn("real scan output", evidence)
        self.assertNotIn("old failure", evidence)
        self.assertIn("student-5", evidence)

    def test_manual_security_runs_do_not_satisfy_commit_hook_requirement(self):
        reports.save_event("security", "student-1", "PASS", scanner="ruff", invocation="manual")
        self.assertIn("student-1: passing ruff commit-hook evidence", reports.completion_gaps(reports.read_events()))

    def test_local_report_links_checks_without_inventing_human_approval(self):
        reports.save_event("local", "student-1", "PENDING", artifact="evidence/local.json",
                           summary={"checks": {"create": {"status": "PASS"}, "ai-mode": {"status": "PASS", "evidence": "evidence/ai.json"}}})
        text = (reports.REPORTS / "local-deployment-report.md").read_text()
        self.assertIn("[PASS](evidence/ai.json)", text)
        self.assertIn("student-1 | PENDING", text)
        self.assertIn("not full browser CRUD", text)

    def test_hook_preflight_and_contribution_drafts_do_not_count_as_participation(self):
        reports.save_event("hook-preflight", "group", "PASS", artifact="evidence/preflight.txt", summary={"expected_count": 15})
        reports.save_event("contribution-draft", "student-1", "CAPTURED", artifact="evidence/draft.json")
        gaps = reports.completion_gaps(reports.read_events())
        self.assertIn("student-1: passing ruff commit-hook evidence", gaps)
        self.assertIn("student-1: contribution evidence (RECORDED)", gaps)

    def test_preflight_matches_the_actual_active_hook_ids(self):
        output = "\n".join(f"- hook id: {tool}-scan-student-{number}" for number in range(1, 6)
                           for tool in ("ruff", "detect-secrets", "pip-audit"))
        result = type("Result", (), {"returncode": 0, "stdout": output, "stderr": ""})()
        with patch.object(delivery, "reports", reports), patch.object(delivery.subprocess, "run", return_value=result):
            delivery.collect_hook_preflight()
        event = reports.read_events()[-1]
        self.assertEqual(event["status"], "PASS")
        self.assertEqual(len(event["summary"]["hooks_seen"]), 15)

    def test_release_cannot_be_ready_with_missing_evidence(self):
        source = self.root / "release.json"
        source.write_text(json.dumps({"reviewer": "Human", "timestamp": "2026-10-17", "decision": "READY", "justification": "Looks good"}))
        with self.assertRaisesRegex(ValueError, "Cannot mark READY"):
            reports.record("release", "group", source)

    def test_template_never_overwrites_human_input(self):
        reports.template("local", "student-1")
        with self.assertRaises(FileExistsError):
            reports.template("local", "student-1")

    def test_review_becomes_stale_when_input_changes(self):
        reports.save_event("security", "student-1", "PASS", scanner="ruff", invocation="commit-hook")
        reports.save_event("review", "group", "COMPLETE", mode="pre_test", input_ids=reports.review_input_ids(reports.read_events(), "pre_test"))
        self.assertNotIn("pre_test: review is stale; rerun after latest evidence", reports.completion_gaps(reports.read_events()))
        reports.save_event("security", "student-1", "FAIL", scanner="ruff", invocation="commit-hook")
        self.assertIn("pre_test: review is stale; rerun after latest evidence", reports.completion_gaps(reports.read_events()))

    def test_secret_scan_invalid_output_fails_without_publishing_content(self):
        result = type("Result", (), {"returncode": 0, "stdout": "private malformed output", "stderr": ""})()
        with patch.object(reports.subprocess, "run", return_value=result):
            self.assertEqual(reports.security("student-1", "detect-secrets"), 1)
        event = reports.read_events()[-1]
        self.assertNotIn("private malformed output", (reports.REPORTS / event["artifact"]).read_text())

    def test_import_hooks_is_idempotent_and_preserves_capture_metadata(self):
        source = self.root / ".release2-hook-evidence" / "evidence"
        source.mkdir(parents=True)
        (source / "scan.txt").write_text("real hook output")
        (source / "report-audit.jsonl").write_text(json.dumps({"id": "original", "timestamp": "2026-10-17", "commit": "b" * 40,
            "dirty": True, "kind": "security", "student": "student-1", "status": "FAIL", "scanner": "ruff",
            "invocation": "commit-hook", "artifact": "evidence/scan.txt"}) + "\n")
        with patch.object(reports, "ROOT", self.root):
            reports.import_hooks()
            reports.import_hooks()
        self.assertEqual(len(reports.read_events()), 1)
        self.assertEqual(reports.read_events()[0]["tested_head"], "b" * 40)

    def test_commit_transcript_import_requires_actual_matching_commit(self):
        path = self.root / "commit.txt"
        path.write_text("pre-commit run --all-files\nRuff Scan (student-1)....Passed")
        with self.assertRaisesRegex(ValueError, "actual git commit"):
            reports.import_commit_transcript("student-1", path, "a" * 40, "Human", "2026-10-17T01:00:00+00:00")
        self.assertEqual(reports.read_events(), [])

    def test_commit_transcript_import_is_private_and_idempotent(self):
        path = self.root / "commit.txt"
        path.write_text("git commit -m test\nRuff Scan (student-1)....Passed\ndetect-secrets Scan (student-1)....Passed\npip-audit Scan (student-1)....Passed\n[feat/reports aaaaaaa] test\nPRIVATE TERMINAL TEXT")
        for _ in range(2):
            self.assertEqual(reports.import_commit_transcript("student-1", path, "a" * 40, "Human", "2026-10-17T01:00:00+00:00"), 0)
        events = reports.read_events()
        self.assertEqual(len(events), 3)
        self.assertTrue(all(event["invocation"] == "commit-hook" for event in events))
        self.assertNotIn("PRIVATE TERMINAL TEXT", (reports.REPORTS / events[0]["artifact"]).read_text())

    def test_skipped_student_hook_does_not_pass_participation(self):
        path = self.root / "commit.txt"
        path.write_text("git commit -m test\nRuff Scan (student-1)....Skipped\ndetect-secrets Scan (student-1)....Passed\npip-audit Scan (student-1)....Passed\n[feat/reports aaaaaaa] test")
        self.assertEqual(reports.import_commit_transcript("student-1", path, "a" * 40, "Human", "2026-10-17T01:00:00+00:00"), 1)
        self.assertIn("student-1: passing ruff commit-hook evidence", reports.completion_gaps(reports.read_events()))

    def test_human_approval_becomes_stale_after_new_evidence(self):
        reports.save_event("release", "group", "READY", approved_ids=[])
        reports.save_event("snapshot", "group", "CAPTURED")
        self.assertIn("Final named human release approval is stale; approve the latest evidence", reports.completion_gaps(reports.read_events()))

    def test_off_topic_model_response_is_not_a_valid_review(self):
        self.assertFalse(reports.valid_review("Here is Python code that summarizes your workflows.", ("Strengths", "Weaknesses", "Recommendations")))
        self.assertTrue(reports.valid_review("Strengths: audit present. Weaknesses: student-1 missing. Recommendations: retest.", ("Strengths", "Weaknesses", "Recommendations")))

    def test_review_cannot_ignore_required_failure_labels(self):
        text = "Strengths: detailed coverage. Weaknesses: limited AI coverage. Recommendations: add details."
        self.assertFalse(reports.valid_review(text, ("Strengths", "Weaknesses", "Recommendations"), ("student-1", "PENDING")))
        self.assertFalse(reports.valid_review(text, ("Strengths", "Weaknesses", "Recommendations"), ("pip-audit", "FAIL")))

    def test_missing_execution_evidence_can_only_produce_a_gap_review(self):
        reports.render()
        evidence = reports.review_evidence("deployment")
        self.assertIn("gap review only", evidence)
        self.assertIn("student-5 | PENDING", evidence)
        self.assertIn("Cloud execution is intentionally deferred", evidence)

    def test_ci_review_shows_tested_sha_instead_of_only_import_checkout(self):
        path = reports.artifact("ci.txt", "Actual CI evidence")
        reports.save_event("ci", "student-1", "PASS", artifact=path, tested_commit="b" * 40)
        evidence = reports.review_evidence("cicd_test")
        self.assertIn("tested_commit: " + "b" * 40, evidence)
        self.assertIn("not authenticated backend routes", evidence)

    def test_scan_timeout_is_saved_as_failure(self):
        with patch.object(reports.subprocess, "run", side_effect=reports.subprocess.TimeoutExpired("ruff", 180)):
            self.assertEqual(reports.security("student-1", "ruff"), 1)
        self.assertEqual(reports.read_events()[-1]["status"], "FAIL")

    def test_malformed_ruff_result_is_not_a_pass(self):
        result = type("Result", (), {"returncode": 0, "stdout": "{}", "stderr": ""})()
        with patch.object(reports.subprocess, "run", return_value=result):
            self.assertEqual(reports.security("student-1", "ruff"), 1)

    def test_ai_http_success_without_inspected_content_is_pending(self):
        response = type("Response", (), {"status_code": 200, "text": "<p>Some output</p>"})()
        self.assertEqual(delivery.integration_result("ai-mode", response)[0], "PENDING")

    def test_local_ai_command_dispatches_to_live_collector(self):
        with patch("sys.argv", ["release2_delivery", "local-ai"]), patch.object(delivery, "collect_local") as collect:
            delivery.main()
        collect.assert_called_once_with(include_ai=True)

    def test_ai_profile_missing_resume_is_not_a_pass(self):
        response = type("Response", (), {"status_code": 200, "text": "<p>Upload a resume first.</p>"})()
        self.assertEqual(delivery.integration_result("ai-mode", response, student="student-1")[0], "FAIL")

    def test_ai_default_scores_without_rationale_are_not_a_pass(self):
        scores = {name: 3 for name in ("technical", "education", "communication", "problem_solving", "professionalism")}
        response = type("Response", (), {"status_code": 200, "text": json.dumps(scores)})()
        self.assertEqual(delivery.integration_result("ai-mode", response, student="student-5")[0], "FAIL")
        scores["rationale"] = "Synthetic candidate explained Python testing clearly."
        response.text = json.dumps(scores)
        self.assertEqual(delivery.integration_result("ai-mode", response, student="student-5")[0], "PASS")

    def test_rag_requires_nonempty_grounded_chunks(self):
        response = type("Response", (), {"status_code": 200, "text": '<pre>{&quot;status&quot;: &quot;success&quot;, &quot;results&quot;: []}</pre>'})()
        self.assertEqual(delivery.integration_result("rag", response)[0], "FAIL")
        response.text = '<pre>{&quot;status&quot;: &quot;success&quot;, &quot;results&quot;: [{&quot;text&quot;: &quot;QA testing evidence&quot;, &quot;source_id&quot;: &quot;qa-1&quot;}]}</pre>'
        self.assertEqual(delivery.integration_result("rag", response)[0], "PASS")

    def test_multi_agent_success_does_not_invent_human_decision(self):
        response = type("Response", (), {"status_code": 200, "text": "<h3>Multi-Agent Workflow</h3>"})()
        workflow = {f"{role}_result": {"status": "success"} for role in ("planner", "worker", "reviewer")}
        workflow["worker_result"]["evidence_count"] = 2
        result = delivery.integration_result("multi-agent", response, workflow)
        self.assertEqual(result[0], "PASS")
        self.assertIn("pending", result[1])
        workflow["reviewer_result"]["review"] = "Review model unavailable"
        self.assertEqual(delivery.integration_result("multi-agent", response, workflow)[0], "FAIL")


if __name__ == "__main__":
    unittest.main()