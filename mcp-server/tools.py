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

import requests

import config
import retrieval

# Guard project_files against escaping the repository root.
_REPO_ROOT = config.REPO_ROOT.resolve()

# Database column -> friendly score key for the evaluation_scores tool.
_EVALUATION_SCORE_FIELDS = {
    "Evaluation_TechnicalScore": "technical",
    "Evaluation_EducationScore": "education",
    "Evaluation_CommunicationScore": "communication",
    "Evaluation_ProblemSolvingScore": "problem_solving",
    "Evaluation_ProfessionalismScore": "professionalism",
}


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


# --- Student 5: Candidate Evaluation -------------------------------------
def get_evaluation_scores(application_id: int | str) -> dict:
    """Retrieve a candidate's evaluation scorecard for one application.

    Grounds the student-5 AI-Mode question "Should we hire candidate X?": given
    an ``application_id`` it returns the five 1-5 criteria scores, the overall
    score and the final Hire/Reject recommendation, each backed by a citation to
    the ``evaluations`` record/field so the answer stays grounded.

    Confidence (per the shared rule, driven by whether an evaluation exists):
        High   = an evaluation exists and is finalized (Hire/Reject decided)
        Medium = an evaluation exists but is still in progress (draft, no decision)
        Low    = no evaluation on record for the application (or the service is
                 unreachable / the id is invalid)
    """
    try:
        app_id = int(application_id)
    except (TypeError, ValueError):
        return retrieval.empty_context(
            f"application_id must be an integer, got: {application_id!r}",
            [retrieval.source(table="evaluations")],
        )

    url = f"{config.db_url('student-5')}/evaluations"
    try:
        response = requests.get(
            url, params={"application_id": app_id}, timeout=config.REQUEST_TIMEOUT
        )
        response.raise_for_status()
        records = response.json()
    except Exception as exc:  # noqa: BLE001 - surface any transport/parse failure as Low
        return retrieval.empty_context(
            f"Evaluation service unreachable for application {app_id}: {exc}",
            [retrieval.source(table="evaluations")],
        )

    if not records:
        return retrieval.build_context(
            {
                "application_id": app_id,
                "evaluation": None,
                "message": "No evaluation has been recorded for this application yet.",
            },
            [retrieval.source(table="evaluations", field="Application_Id")],
            retrieval.LOW,
        )

    record = records[0]
    evaluation_id = record.get("Evaluation_Id")
    recommendation = record.get("Evaluation_FinalRecommendation")
    finalized = recommendation is not None

    scores = {
        key: record.get(column) for column, key in _EVALUATION_SCORE_FIELDS.items()
    }

    answer_data = {
        "application_id": app_id,
        "evaluation_id": evaluation_id,
        "scores": scores,
        "overall_score": record.get("Evaluation_OverallScore"),
        "recommendation": recommendation,
        "status": "finalized" if finalized else "in_progress",
    }

    # Cite each score field, the overall score and the recommendation.
    sources = [
        retrieval.source(table="evaluations", record_id=evaluation_id, field=column)
        for column in _EVALUATION_SCORE_FIELDS
    ]
    sources.append(
        retrieval.source(
            table="evaluations", record_id=evaluation_id, field="Evaluation_OverallScore"
        )
    )
    sources.append(
        retrieval.source(
            table="evaluations",
            record_id=evaluation_id,
            field="Evaluation_FinalRecommendation",
        )
    )

    confidence = retrieval.derive_confidence(exact=finalized, partial=not finalized)
    return retrieval.build_context(answer_data, sources, confidence)


if __name__ == "__main__":
    print(json.dumps(list_project_files("."), indent=2))
    print(json.dumps(read_ci_report(), indent=2))
    print(json.dumps(get_evaluation_scores(13), indent=2))
