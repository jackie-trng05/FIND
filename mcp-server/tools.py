"""MCP tool implementations for the FIND platform.

Step 1 (this file) ships the two **shared** tools available to every student
feature:

    * project_files  -> inspect files in the repository (structure questions)
    * ci_report      -> read a student's CI evidence JSON (CI status questions)

Each per-student *retrieval* tool (applicant_profile, job_postings,
applications_for_job, interview_details, evaluation_scores) is added in Step 2
following the same contract: return a retrieval-context object built with
``retrieval.build_context`` so AI-Mode answers stay grounded with citations and
a confidence category.

All tools return plain Python data (dict / list). ``server.py`` registers them
as MCP tools; the tool functions here can also be called directly for unit
testing (mirrors the lab's ``if __name__ == '__main__'`` smoke test).
"""

import json
from pathlib import Path

import config
import retrieval

# Guard project_files against escaping the repository root.
_REPO_ROOT = config.REPO_ROOT.resolve()


def list_project_files(directory_path: str = ".") -> dict:
    """List files/folders under a repository-relative directory.

    Path is resolved relative to the FIND repository root and validated to stay
    inside it (no traversal outside the workspace).
    """
    target = (_REPO_ROOT / directory_path).resolve()

    if _REPO_ROOT not in target.parents and target != _REPO_ROOT:
        return retrieval.empty_context(
            f"Path is outside the repository workspace: {directory_path}"
        )
    if not target.exists() or not target.is_dir():
        return retrieval.empty_context(f"Directory not found: {directory_path}")

    names = sorted(item.name for item in target.iterdir())
    rel = target.relative_to(_REPO_ROOT).as_posix() or "."
    confidence = retrieval.derive_confidence(exact=bool(names), partial=False)
    return retrieval.build_context(
        {"directory": rel, "entries": names},
        [retrieval.source(table="filesystem", record_id=rel)],
        confidence,
    )


def read_ci_report(report_path: str | None = None) -> dict:
    """Read a CI evidence JSON file produced by the GitHub Actions workflow."""
    resolved = Path(report_path) if report_path else Path(config.DEFAULT_CI_REPORT)
    if not resolved.is_absolute():
        resolved = (_REPO_ROOT / resolved).resolve()

    if not resolved.exists():
        return retrieval.build_context(
            {
                "error": "Report not found",
                "path": str(resolved),
                "hint": "Run the student CI workflow_dispatch to generate report.json",
            },
            [retrieval.source(table="ci_evidence", record_id=str(resolved))],
            retrieval.LOW,
        )

    with resolved.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return retrieval.build_context(
        payload,
        [retrieval.source(table="ci_evidence", record_id=resolved.name)],
        retrieval.HIGH,
    )


if __name__ == "__main__":
    print(json.dumps(list_project_files("."), indent=2))
    print(json.dumps(read_ci_report(), indent=2))
