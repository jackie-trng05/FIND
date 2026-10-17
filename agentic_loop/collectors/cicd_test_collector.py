"""Collect post-commit (CI/CD) test evidence for the FIND cloud pipeline.

Self-registers: produces evidence only once the post-commit tests and their
result artifacts are landed in the repo. Paths point at the intended FIND
locations, so dropping the real files in place is enough.
"""

from pathlib import Path


def collect(app_dir: Path, repo_root: Path) -> tuple[bool, str]:
    post_commit_dir = app_dir / "tests" / "post_commit"
    reports_dir = app_dir / "docs" / "release-2" / "reports"

    required_paths = [
        post_commit_dir / "test_api_students.py",
        post_commit_dir / "test_token_auth.py",
        reports_dir / "test-results.md",
        reports_dir / "test-audit.jsonl",
    ]

    missing = [str(path.relative_to(app_dir)) for path in required_paths if not path.exists()]
    if missing:
        return False, "CI/CD test evidence incomplete. Missing: " + ", ".join(missing)

    audit_lines = (reports_dir / "test-audit.jsonl").read_text(encoding="utf-8").strip().splitlines()
    if not audit_lines:
        return False, "docs/release-2/reports/test-audit.jsonl is empty. Run the post-commit tests first."

    last_status = "PASS" in audit_lines[-1]

    return True, (
        "CI/CD test evidence: tests/post_commit/ contains API and token-auth tests; "
        "docs/release-2/reports/test-results.md and test-audit.jsonl exist "
        f"(latest audit entry status: {'PASS' if last_status else 'FAIL'})."
    )

