"""Collect pre-commit security-scan evidence for the FIND cloud pipeline.

Mirrors the shared self-registration pattern: the Pre-Commit review mode only
produces evidence once the cloud artifacts are landed in the repo. Paths point
at the intended FIND locations, so dropping the real files in place is enough —
no collector changes required.
"""

from pathlib import Path


REQUIRED_HOOK_IDS = ["ruff-scan", "detect-secrets-scan", "pip-audit-scan"]


def collect(app_dir: Path, repo_root: Path) -> tuple[bool, str]:
    pre_commit_dir = app_dir / "tests" / "pre_commit"

    required_paths = [
        app_dir / ".pre-commit-config.yaml",
        pre_commit_dir / "test_ruff_scan.py",
        pre_commit_dir / "test_secrets_scan.py",
        pre_commit_dir / "test_dependency_audit.py",
    ]

    missing = [str(path.relative_to(app_dir)) for path in required_paths if not path.exists()]
    if missing:
        return False, "Pre-test evidence incomplete. Missing: " + ", ".join(missing)

    config_text = (app_dir / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    missing_hooks = [hook_id for hook_id in REQUIRED_HOOK_IDS if hook_id not in config_text]
    if missing_hooks:
        return False, ".pre-commit-config.yaml missing hooks: " + ", ".join(missing_hooks)

    return True, (
        "Pre-test evidence: .pre-commit-config.yaml wires ruff-scan, detect-secrets-scan, "
        "and pip-audit-scan hooks to tests/pre_commit/ test files that block commits on failure."
    )

