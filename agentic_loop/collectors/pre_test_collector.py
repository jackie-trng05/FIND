"""Collect pre-commit security-scan evidence for the FIND cloud pipeline.

FIND is a five-student monorepo, so the pre-commit scans live per student:
each student owns Ruff / detect-secrets / pip-audit pytest files under
tests/lab11/pre_commit/ plus a captured evidence report under
docs/release-2/pre-commit/. The Pre-Commit review mode only produces evidence
once every student's scans and report are landed, so students self-register by
dropping their files in place.
"""

from pathlib import Path


REQUIRED_HOOK_IDS = ["ruff-scan", "detect-secrets-scan", "pip-audit-scan"]
SCAN_STEMS = ["test_ruff_scan", "test_secrets_scan", "test_dependency_audit"]


def collect(app_dir: Path, repo_root: Path) -> tuple[bool, str]:
    pre_commit_dir = app_dir / "tests" / "lab11" / "pre_commit"
    reports_dir = app_dir / "docs" / "release-2" / "pre-commit"
    config_path = app_dir / ".pre-commit-config.yaml"

    required_paths = [config_path]
    for n in range(1, 6):
        for stem in SCAN_STEMS:
            required_paths.append(pre_commit_dir / f"{stem}_student{n}.py")
        required_paths.append(reports_dir / f"pre-commit-results-student{n}.md")

    missing = [str(path.relative_to(app_dir)) for path in required_paths if not path.exists()]
    if missing:
        return False, "Pre-test evidence incomplete. Missing: " + ", ".join(missing)

    config_text = config_path.read_text(encoding="utf-8")
    missing_hooks = [hook_id for hook_id in REQUIRED_HOOK_IDS if hook_id not in config_text]
    if missing_hooks:
        return False, ".pre-commit-config.yaml missing hooks: " + ", ".join(missing_hooks)

    return True, (
        "Pre-test evidence: .pre-commit-config.yaml wires per-student ruff-scan, "
        "detect-secrets-scan, and pip-audit-scan hooks (scoped by files: ^student-N/) that "
        "block commits on failure. Each of student-1..5 has Ruff, detect-secrets, and "
        "pip-audit pytest files under tests/lab11/pre_commit/ and a captured evidence report under "
        "docs/release-2/pre-commit/pre-commit-results-studentN.md."
    )

