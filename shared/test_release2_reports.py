import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


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

    def test_scan_timeout_is_saved_as_failure(self):
        with patch.object(reports.subprocess, "run", side_effect=reports.subprocess.TimeoutExpired("ruff", 180)):
            self.assertEqual(reports.security("student-1", "ruff"), 1)
        self.assertEqual(reports.read_events()[-1]["status"], "FAIL")

    def test_malformed_ruff_result_is_not_a_pass(self):
        result = type("Result", (), {"returncode": 0, "stdout": "{}", "stderr": ""})()
        with patch.object(reports.subprocess, "run", return_value=result):
            self.assertEqual(reports.security("student-1", "ruff"), 1)


if __name__ == "__main__":
    unittest.main()