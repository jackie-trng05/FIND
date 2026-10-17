"""Collect Azure deployment configuration and validation evidence for FIND."""

import re
from pathlib import Path


REQUIRED_SNIPPETS = [
    '--registry-identity "$ACR_PULL_IDENTITY_ID"',
    '--ingress "$ingress"',
    'ingress="$4"',
]


def collect(app_dir: Path, repo_root: Path) -> tuple[bool, str]:
    deploy_script = app_dir / "scripts" / "deploy-azure.sh"
    deployment_results = app_dir / "docs" / "release-2" / "deploy" / "deployment-results.md"

    required_paths = [deploy_script, deployment_results]
    missing = [str(path.relative_to(app_dir)) for path in required_paths if not path.exists()]
    if missing:
        return False, "Deployment evidence incomplete. Missing: " + ", ".join(missing)

    script_text = deploy_script.read_text(encoding="utf-8")
    missing_snippets = [snippet for snippet in REQUIRED_SNIPPETS if snippet not in script_text]
    for ingress in ("internal", "external"):
        if not re.search(rf"(?m)^deploy_app\s+\S+\s+\S+\s+\d+\s+{ingress}\b", script_text):
            missing_snippets.append(f"deploy_app with {ingress} ingress")
    if missing_snippets:
        return False, "deploy-azure.sh missing expected configuration: " + ", ".join(missing_snippets)

    return True, (
        "Deployment evidence: scripts/deploy-azure.sh uses a shared user-assigned "
        'managed identity (--registry-identity "$ACR_PULL_IDENTITY_ID") and passes '
        'ingress through deploy_app (--ingress "$ingress"), with internal database '
        "and external frontend/API deployment calls; "
        "docs/release-2/deploy/deployment-results.md exists as validation evidence."
    )
