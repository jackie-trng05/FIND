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
from io import BytesIO
from pathlib import Path

import requests

import config
import retrieval

try:
    from pypdf import PdfReader  # type: ignore
except Exception:  # pragma: no cover
    PdfReader = None  # type: ignore

# Guard project_files against escaping the repository root.
_REPO_ROOT = config.REPO_ROOT.resolve()

# Resume text is truncated to keep retrieval contexts (and LLM prompts) small.
_RESUME_TEXT_MAX_CHARS = 4000

# Database column -> friendly score key for the evaluation_scores tool.
_EVALUATION_SCORE_FIELDS = {
    "Evaluation_TechnicalScore": "technical",
    "Evaluation_EducationScore": "education",
    "Evaluation_CommunicationScore": "communication",
    "Evaluation_ProblemSolvingScore": "problem_solving",
    "Evaluation_ProfessionalismScore": "professionalism",
}

# Fields surfaced for each application by the applications_for_job tool.
_APPLICATION_FIELDS = (
    "application_id",
    "user_id",
    "resume_id",
    "application_status",
    "submitted_at",
)


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


# --- Student 1: Applicant Profile -----------------------------------------
_PROFILE_FIELDS = ("phone", "location", "professional_title", "summary", "interests")


def _extract_resume_text(data: bytes, mimetype: str) -> str:
    """Best-effort PDF text extraction (only PDF resumes are accepted). Returns
    "" when the file can't be parsed. Truncated to ``_RESUME_TEXT_MAX_CHARS``."""
    text = ""
    if "pdf" in (mimetype or "").lower() and PdfReader is not None:
        try:
            reader = PdfReader(BytesIO(data))
            pages = []
            for page in reader.pages[:10]:
                try:
                    pages.append(page.extract_text() or "")
                except Exception:
                    continue
            text = "\n".join(p.strip() for p in pages if p.strip())
        except Exception:
            text = ""
    text = text.strip()
    if len(text) > _RESUME_TEXT_MAX_CHARS:
        text = text[:_RESUME_TEXT_MAX_CHARS] + "\n[...truncated...]"
    return text


def get_applicant_profile(user_id: int | str) -> dict:
    """Retrieve an applicant's profile fields plus their resume text/metadata.

    Grounds the student-1 AI-Mode question "Summarise this applicant's
    strengths": given a ``user_id`` it returns the profile fields (phone,
    location, professional_title, summary, interests) and the linked resume's
    metadata (file_name, file_type, uploaded_at) plus its extracted text
    (best-effort PDF extraction, truncated), each backed by a citation to the
    ``profiles``/``resumes`` record/field so the answer stays grounded.

    Confidence (per the shared rule, driven by field completeness):
        High   = a profile exists with title/summary/interests all filled AND
                 a resume is on file with its text successfully extracted
        Medium = a profile exists but some of those fields are missing, no
                 resume has been uploaded yet, or its text couldn't be read
        Low    = no profile on record for the user (or the service is
                 unreachable / the id is invalid)
    """
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return retrieval.empty_context(
            f"user_id must be an integer, got: {user_id!r}",
            [retrieval.source(table="profiles")],
        )

    base_url = config.db_url("student-1")
    try:
        response = requests.get(
            f"{base_url}/profiles/by-user/{uid}", timeout=config.REQUEST_TIMEOUT
        )
    except Exception as exc:  # noqa: BLE001 - surface any transport failure as Low
        return retrieval.empty_context(
            f"Profile service unreachable for user {uid}: {exc}",
            [retrieval.source(table="profiles")],
        )

    if response.status_code != 200:
        return retrieval.build_context(
            {
                "user_id": uid,
                "profile": None,
                "resume": None,
                "message": "No profile has been created for this user yet.",
            },
            [retrieval.source(table="profiles", field="user_id")],
            retrieval.LOW,
        )

    profile = response.json()
    profile_id = profile.get("profile_id")

    resume = None
    try:
        resumes_resp = requests.get(
            f"{base_url}/profiles/{profile_id}/resumes", timeout=config.REQUEST_TIMEOUT
        )
        if resumes_resp.status_code == 200:
            records = resumes_resp.json()
            if records:
                resume = records[0]
    except Exception:  # noqa: BLE001 - resume lookup is best-effort
        resume = None

    resume_text = None
    if resume:
        try:
            file_resp = requests.get(
                f"{base_url}/resumes/{resume['resume_id']}/file", timeout=config.REQUEST_TIMEOUT
            )
            if file_resp.status_code == 200:
                resume_text = _extract_resume_text(file_resp.content, resume.get("file_type", ""))
        except Exception:  # noqa: BLE001 - resume text extraction is best-effort
            resume_text = None

    answer_data = {
        "user_id": uid,
        "profile": {field: profile.get(field) for field in _PROFILE_FIELDS},
        "resume": (
            {
                "file_name": resume.get("file_name"),
                "file_type": resume.get("file_type"),
                "uploaded_at": resume.get("uploaded_at"),
                "text": resume_text,
            }
            if resume
            else None
        ),
    }

    # Cite each populated profile field plus the resume file, when present.
    sources = [
        retrieval.source(table="profiles", record_id=profile_id, field=field)
        for field in _PROFILE_FIELDS
        if profile.get(field)
    ]
    if resume:
        sources.append(
            retrieval.source(table="resumes", record_id=resume.get("resume_id"), field="file_name")
        )
        if resume_text:
            sources.append(
                retrieval.source(table="resumes", record_id=resume.get("resume_id"), field="file_data")
            )

    fields_complete = all(profile.get(field) for field in ("professional_title", "summary", "interests"))
    resume_ok = resume is not None and bool(resume_text)
    confidence = retrieval.derive_confidence(
        exact=fields_complete and resume_ok,
        partial=not (fields_complete and resume_ok),
    )
    return retrieval.build_context(answer_data, sources, confidence)


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


# --- Student 3: Applications / Screening ---------------------------------
def get_applications_for_job(job_posting_id: int | str, status: str | None = None) -> dict:
    """Retrieve the applications submitted for a job posting.

    Grounds the student-3 AI-Mode question "Who should be shortlisted for job X?":
    given a ``job_posting_id`` (and an optional ``status`` filter) it returns the
    matching application records — including the soft ``resume_id`` link to
    student-1's resume — each backed by a citation to the ``applications`` record
    so the shortlist answer stays grounded.

    Confidence (per the shared rule):
        High   = a status filter was supplied and matching records were returned
                 (a precise, filtered query)
        Medium = no status filter, but the job has applications (a broader set
                 that still needs a human shortlisting decision)
        Low    = no applications for the job (or the service is unreachable /
                 the id is invalid)
    """
    try:
        job_id = int(job_posting_id)
    except (TypeError, ValueError):
        return retrieval.empty_context(
            f"job_posting_id must be an integer, got: {job_posting_id!r}",
            [retrieval.source(table="applications")],
        )

    status_filter = (status or "").strip()
    params: dict = {"job_posting_id": job_id}
    if status_filter:
        params["status"] = status_filter

    url = f"{config.db_url('student-3')}/applications"
    try:
        response = requests.get(url, params=params, timeout=config.REQUEST_TIMEOUT)
        response.raise_for_status()
        records = response.json()
    except Exception as exc:  # noqa: BLE001 - surface any transport/parse failure as Low
        return retrieval.empty_context(
            f"Application service unreachable for job {job_id}: {exc}",
            [retrieval.source(table="applications")],
        )

    if not records:
        return retrieval.build_context(
            {
                "job_posting_id": job_id,
                "status_filter": status_filter or None,
                "count": 0,
                "applications": [],
                "message": "No applications match this job posting yet.",
            },
            [retrieval.source(table="applications", field="job_posting_id")],
            retrieval.LOW,
        )

    applications = [
        {field: record.get(field) for field in _APPLICATION_FIELDS}
        for record in records
    ]

    answer_data = {
        "job_posting_id": job_id,
        "status_filter": status_filter or None,
        "count": len(applications),
        "applications": applications,
    }

    # Cite each application's status and its soft resume link.
    sources = []
    for app in applications:
        app_id = app["application_id"]
        sources.append(
            retrieval.source(table="applications", record_id=app_id, field="application_status")
        )
        if app.get("resume_id") is not None:
            sources.append(
                retrieval.source(table="applications", record_id=app_id, field="resume_id")
            )

    confidence = retrieval.derive_confidence(
        exact=bool(status_filter), partial=not status_filter
    )
    return retrieval.build_context(answer_data, sources, confidence)


# --- Student 2: Job Posting Management -----------------------------------
# Cap the postings echoed back so answer_data / citations stay bounded.
_POSTING_LIMIT = 10


def _description_snippet(text: str | None, limit: int = 240) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit].rstrip() + "…"


def get_job_postings(
    query: str = "", job_type: str = "", location: str = "", status: str = "Published"
) -> dict:
    """Retrieve job postings matching an optional filter (student-2 domain).

    Grounds the student-2 AI-Mode question "Which roles fit a Python backend
    engineer?": the ``query`` runs a free-text match over the postings' title,
    description and requirements; ``job_type`` / ``location`` / ``status`` narrow
    the result set. Each returned posting is cited to its ``job_postings`` record
    (Requirements + Job_Description) so the answer stays grounded, and posting
    IDs are surfaced in ``answer_data``.

    Confidence (per the shared rule):
        High   = a targeted filter (query/type/location) was supplied and matched
        Medium = only a broad status listing was requested but postings exist
        Low    = no postings match (or the service is unreachable)
    """
    filters = {}
    if status:
        filters["status"] = status
    if job_type:
        filters["job_type"] = job_type
    if location:
        filters["location"] = location
    if query:
        filters["q"] = query

    url = f"{config.db_url('student-2')}/job-postings"
    try:
        response = requests.get(url, params=filters, timeout=config.REQUEST_TIMEOUT)
        response.raise_for_status()
        records = response.json()
    except Exception as exc:  # noqa: BLE001 - surface any transport/parse failure as Low
        return retrieval.empty_context(
            f"Job posting service unreachable: {exc}",
            [retrieval.source(table="job_postings")],
        )

    if not records:
        return retrieval.build_context(
            {
                "filters": filters,
                "count": 0,
                "postings": [],
                "message": "No job postings match the requested filter.",
            },
            [retrieval.source(table="job_postings", field="JobPosting_Status")],
            retrieval.LOW,
        )

    limited = records[:_POSTING_LIMIT]
    postings = [
        {
            "job_posting_id": record.get("JobPosting_Id"),
            "title": record.get("Job_Title"),
            "job_type": record.get("Job_Type"),
            "location": record.get("Location"),
            "status": record.get("JobPosting_Status"),
            "requirements": record.get("Requirements"),
            "description": _description_snippet(record.get("Job_Description")),
        }
        for record in limited
    ]

    sources = []
    for record in limited:
        posting_id = record.get("JobPosting_Id")
        sources.append(
            retrieval.source(table="job_postings", record_id=posting_id, field="Requirements")
        )
        sources.append(
            retrieval.source(table="job_postings", record_id=posting_id, field="Job_Description")
        )

    answer_data = {
        "filters": filters,
        "count": len(records),
        "returned": len(postings),
        "postings": postings,
    }

    targeted = bool(query or job_type or location)
    confidence = retrieval.derive_confidence(exact=targeted, partial=not targeted)
    return retrieval.build_context(answer_data, sources, confidence)

# --- Student 4: Interview Scheduling -------------------------------------
def _parse_interview_notes(raw) -> dict:
    """Parse the ``interview_notes`` JSON column into a dict of feedback areas.

    Notes are stored as a JSON object keyed by skill area (Technical,
    Education, Communication, Problem Solving, Professionalism). Blank areas are
    dropped so a scheduled-but-unwritten interview yields an empty dict. Returns
    an empty dict when notes have not been written yet or cannot be parsed.
    """
    if not raw or not str(raw).strip():
        return {}
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {"Notes": str(raw)}
    if isinstance(parsed, dict):
        return {key: value for key, value in parsed.items() if str(value).strip()}
    return {"Notes": parsed}


def get_interview_details(application_id: int | str) -> dict:
    """Retrieve the interview scheduled for one application.

    Grounds the student-4 AI-Mode question "Summarise interview feedback for
    candidate X": given an ``application_id`` it returns the interview's
    datetime, meeting link and the structured ``interview_notes`` feedback, each
    backed by a citation to the ``interviews`` record/field so the answer stays
    grounded.

    Confidence (per the shared rule, driven by whether an interview exists and
    has written-up feedback):
        High   = an interview exists and its feedback notes are written up
        Medium = an interview exists but its notes are still empty (scheduled,
                 no feedback yet)
        Low    = no interview on record for the application (or the service is
                 unreachable / the id is invalid)
    """
    try:
        app_id = int(application_id)
    except (TypeError, ValueError):
        return retrieval.empty_context(
            f"application_id must be an integer, got: {application_id!r}",
            [retrieval.source(table="interviews")],
        )

    url = f"{config.db_url('student-4')}/interviews"
    try:
        response = requests.get(url, timeout=config.REQUEST_TIMEOUT)
        response.raise_for_status()
        records = response.json()
    except Exception as exc:  # noqa: BLE001 - surface any transport/parse failure as Low
        return retrieval.empty_context(
            f"Interview service unreachable for application {app_id}: {exc}",
            [retrieval.source(table="interviews")],
        )

    matches = [record for record in records if record.get("application_id") == app_id]
    if not matches:
        return retrieval.build_context(
            {
                "application_id": app_id,
                "interview": None,
                "message": "No interview has been scheduled for this application yet.",
            },
            [retrieval.source(table="interviews", field="application_id")],
            retrieval.LOW,
        )

    # Most recent interview for the application if several exist.
    record = sorted(
        matches, key=lambda item: item.get("interview_datetime") or "", reverse=True
    )[0]
    interview_id = record.get("interview_id")
    notes = _parse_interview_notes(record.get("interview_notes"))
    has_feedback = bool(notes)

    answer_data = {
        "application_id": app_id,
        "interview_id": interview_id,
        "interview_datetime": record.get("interview_datetime"),
        "interview_link": record.get("interview_link"),
        "notes": notes,
        "status": "completed" if has_feedback else "scheduled",
    }

    # Cite the schedule fields and each written-up feedback area.
    sources = [
        retrieval.source(
            table="interviews", record_id=interview_id, field="interview_datetime"
        ),
        retrieval.source(
            table="interviews", record_id=interview_id, field="interview_link"
        ),
    ]
    for area in notes:
        sources.append(
            retrieval.source(
                table="interviews",
                record_id=interview_id,
                field=f"interview_notes.{area}",
            )
        )

    confidence = retrieval.derive_confidence(
        exact=has_feedback, partial=not has_feedback
    )
    return retrieval.build_context(answer_data, sources, confidence)


if __name__ == "__main__":
    print(json.dumps(list_project_files("."), indent=2))
    print(json.dumps(read_ci_report(), indent=2))
    print(json.dumps(get_applicant_profile(1), indent=2))
    print(json.dumps(get_applications_for_job(1), indent=2))
    print(json.dumps(get_evaluation_scores(13), indent=2))
    print(json.dumps(get_job_postings(query="python"), indent=2))
    print(json.dumps(get_interview_details(4), indent=2))
