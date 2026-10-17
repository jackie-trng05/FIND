"""Collect post-commit (CI/CD) test evidence for the FIND cloud pipeline.

FIND is a five-student monorepo, so the post-commit tests and their CI
evidence live per student: each student owns API and token-auth tests under
student-N/tests/post_commit/ plus captured CI results under
docs/release-2/post-commit/student-N/ (test-results.md + test-audit.jsonl).
The CI/CD review mode only produces evidence once every student's tests and
result artifacts are landed, so students self-register by dropping their files
in place.
"""

import json
from pathlib import Path


def _latest_status(audit_path: Path) -> str:
    lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
    if not lines:
        return "EMPTY"
    last = lines[-1]
    try:
        return str(json.loads(last).get("status", "UNKNOWN")).upper()
    except json.JSONDecodeError:
        return "PASS" if "PASS" in last else "FAIL"


def collect(app_dir: Path, repo_root: Path) -> tuple[bool, str]:
    reports_root = app_dir / "docs" / "release-2" / "post-commit"

    missing: list[str] = []
    statuses: dict[str, str] = {}

    for n in range(1, 6):
        student = f"student-{n}"
        post_commit_dir = app_dir / student / "tests" / "post_commit"
        token_test = post_commit_dir / "test_token_auth.py"
        api_tests = list(post_commit_dir.glob("test_api_*.py")) if post_commit_dir.exists() else []
        results_md = reports_root / student / "test-results.md"
        audit_jsonl = reports_root / student / "test-audit.jsonl"

        if not api_tests:
            missing.append(f"{student}/tests/post_commit/test_api_*.py")
        if not token_test.exists():
            missing.append(str(token_test.relative_to(app_dir)))
        if not results_md.exists():
            missing.append(str(results_md.relative_to(app_dir)))
        if not audit_jsonl.exists():
            missing.append(str(audit_jsonl.relative_to(app_dir)))
        else:
            statuses[student] = _latest_status(audit_jsonl)

    if missing:
        return False, "CI/CD test evidence incomplete. Missing: " + ", ".join(missing)

    empty = [s for s, v in statuses.items() if v == "EMPTY"]
    if empty:
        return False, (
            "Post-commit audit log empty for: " + ", ".join(empty) + ". Run the post-commit tests first."
        )

    status_line = ", ".join(f"{s}={v}" for s, v in sorted(statuses.items()))
    all_pass = all(v == "PASS" for v in statuses.values())

    return True, (
        "CI/CD test evidence: each of student-1..5 has API and token-auth tests under "
        "student-N/tests/post_commit/ with captured CI results under "
        "docs/release-2/post-commit/student-N/ (test-results.md + test-audit.jsonl). "
        f"Latest audit status per student: {status_line}. "
        f"Overall: {'all PASS' if all_pass else 'one or more FAIL'}."
    )
