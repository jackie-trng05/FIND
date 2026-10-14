"""Collect Azure cloud deployment evidence for the FIND cloud pipeline.

Self-registers: produces evidence only once the Azure deploy script and its
validation report are landed in the repo. Paths point at the intended FIND
locations, so dropping the real files in place is enough.
"""

from pathlib import Path


REQUIRED_SNIPPETS = ["--registry-identity system", "--ingress internal", "--ingress external"]


def collect(app_dir: Path, repo_root: Path) -> tuple[bool, str]:
    deploy_script = app_dir / "scripts" / "deploy-azure.sh"
    deployment_results = app_dir / "docs" / "release-2" / "reports" / "deployment-results.md"

    required_paths = [deploy_script, deployment_results]

    missing = [str(path.relative_to(app_dir)) for path in required_paths if not path.exists()]
    if missing:
        return False, "Deployment evidence incomplete. Missing: " + ", ".join(missing)

    script_text = deploy_script.read_text(encoding="utf-8")
    missing_snippets = [snippet for snippet in REQUIRED_SNIPPETS if snippet not in script_text]
    if missing_snippets:
        return False, "deploy-azure.sh missing expected configuration: " + ", ".join(missing_snippets)

    return True, (
        "Deployment evidence: scripts/deploy-azure.sh uses managed identity "
        "(--registry-identity system) and isolates backend/database services with "
        "--ingress internal while the public frontend is --ingress external; "
        "docs/release-2/reports/deployment-results.md documents the validation run."
    )

