import json
from pathlib import Path


REQUIRED_WORKFLOW_JOBS = ["build-images", "smoke-check", "unit-tests", "evidence-pack"]
REQUIRED_REPORT_KEYS = ["workflow_name", "run_id", "commit_sha", "branch", "repository", "tests"]


def collect(app_dir: Path, repo_root: Path, scope: str | None = None) -> tuple[bool, str]:
    """Collect CI/CD evidence for one student's pipeline.

    Each student owns a GitHub Actions workflow at .github/workflows/<student>-ci.yml
    and a downloaded evidence pack under docs/release-0/reports/<student>/ containing
    report.json, report.md, run-view.md, and the raw pytest artifacts.
    """
    if not scope:
        return False, "DevOps evidence requires a student scope (e.g. student-1)."

    workflow_path = repo_root / ".github" / "workflows" / f"{scope}-ci.yml"
    reports_dir = repo_root / "docs" / "release-0" / "reports" / scope

    required_paths = [
        workflow_path,
        reports_dir / "report.json",
        reports_dir / "report.md",
        reports_dir / "run-view.md",
    ]

    missing = [str(path.relative_to(repo_root)) for path in required_paths if not path.exists()]
    if missing:
        return False, "DevOps evidence incomplete. Missing: " + ", ".join(missing)

    workflow_text = workflow_path.read_text(encoding="utf-8")
    report_json_text = (reports_dir / "report.json").read_text(encoding="utf-8")

    missing_jobs = [job for job in REQUIRED_WORKFLOW_JOBS if job not in workflow_text]
    if missing_jobs:
        return False, "Workflow missing required jobs: " + ", ".join(missing_jobs)

    try:
        report_json = json.loads(report_json_text)
    except json.JSONDecodeError:
        return False, "report.json is not valid JSON."

    missing_keys = [key for key in REQUIRED_REPORT_KEYS if key not in report_json]
    if missing_keys:
        return False, "report.json missing required keys: " + ", ".join(missing_keys)

    teardown_ok = "docker compose down -v" in workflow_text
    teardown_text = "includes" if teardown_ok else "does not include"

    tests = report_json.get("tests", {})
    tests_summary = (
        f"{tests.get('status', 'unknown')} "
        f"({tests.get('passed', 0)}/{tests.get('total', 0)} passed, "
        f"{tests.get('failed', 0)} failed, {tests.get('errors', 0)} errors, "
        f"{tests.get('skipped', 0)} skipped)"
    )

    run_view_text = (reports_dir / "run-view.md").read_text(encoding="utf-8")
    run_url = next((line.strip() for line in run_view_text.splitlines() if line.strip().startswith("https://")), "")

    return True, (
        f"DevOps evidence ({scope}): workflow defines build-images, smoke-check, unit-tests, "
        f"and evidence-pack; teardown {teardown_text} 'docker compose down -v'; "
        f"report.json contains run metadata for run {report_json.get('run_id')} on branch "
        f"{report_json.get('branch')} (commit {report_json.get('commit_sha')}); "
        f"pytest result: {tests_summary}. Run URL: {run_url or 'not found'}."
    )
