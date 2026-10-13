"""Worker Agent for the shared FIND multi-agent server.

Retrieves grounded evidence from a FIND database microservice over HTTP and then
asks the local Ollama worker model to produce an output that uses only that
evidence. Like the shared MCP / RAG servers, this agent runs as a host process
and reaches the containerised database through its host-mapped port (default the
student-3 application database on ``http://localhost:16012``).

The evidence domain is configurable with ``MULTI_AGENT_DB_URL`` so the same
shared server can ground workflows for any student's database service.
"""

import os
from typing import Any, Dict, List
from pathlib import Path
from io import BytesIO

import requests
from openai import OpenAI

try:
    from pypdf import PdfReader  # type: ignore
except Exception:  # pragma: no cover
    PdfReader = None  # type: ignore

BASE_DIR = Path(__file__).resolve().parents[1]
PROMPT_PATH = BASE_DIR / "prompts" / "worker_prompt.txt"

# The shared server is a host process, so it reaches the database service via its
# host-mapped port. Defaults to student-3's application database (host 16012).
MULTI_AGENT_DB_URL = os.getenv("MULTI_AGENT_DB_URL", "http://localhost:16012")
# Student-1's domain is profile + resume, not applications (mirrors mcp-server's
# STUDENT_1_DB_URL / applicant_profile tool, same host-mapped port 16006).
STUDENT_1_DB_URL = os.getenv("STUDENT_1_DB_URL", "http://localhost:16006")
DB_TIMEOUT_SECONDS = float(os.getenv("MULTI_AGENT_DB_TIMEOUT_SECONDS", "10"))

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
OLLAMA_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "45"))

FAST_MODE = os.getenv("FAST_MODE", "true").lower() == "true"
WORKER_MAX_TOKENS = int(os.getenv("WORKER_MAX_TOKENS", "180" if FAST_MODE else "400"))

_APPLICATION_FIELDS = (
    "application_id",
    "user_id",
    "job_posting_id",
    "resume_id",
    "application_status",
    "submitted_at",
)

# Resume text is truncated to keep the evidence (and LLM prompt) small.
_RESUME_TEXT_MAX_CHARS = 4000
_PROFILE_FIELDS = ("phone", "location", "professional_title", "summary", "interests")

client = OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama",
    timeout=OLLAMA_TIMEOUT_SECONDS,
)


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8").strip()


def extract_job_posting_id(user_request: str) -> str | None:
    """Pull the first integer token from the request (e.g. 'job posting 1' -> '1')."""
    for token in user_request.replace(".", " ").replace(",", " ").split():
        if token.isdigit():
            return token
    return None


def get_applications(
    job_posting_id: str | None, status: str | None = None, user_id: int | str | None = None
) -> List[Dict[str, Any]]:
    """Retrieve application records from the FIND database service over HTTP."""
    params: Dict[str, Any] = {}
    if job_posting_id:
        params["job_posting_id"] = job_posting_id
    if status:
        params["status"] = status
    if user_id:
        params["user_id"] = user_id

    url = f"{MULTI_AGENT_DB_URL.rstrip('/')}/applications"
    response = requests.get(url, params=params, timeout=DB_TIMEOUT_SECONDS)
    response.raise_for_status()
    records = response.json() or []
    return [
        {field: record.get(field) for field in _APPLICATION_FIELDS}
        for record in records
    ]


def format_evidence(applications: List[Dict[str, Any]], job_posting_id: str | None) -> str:
    if not applications:
        scope = f"job posting {job_posting_id}" if job_posting_id else "the platform"
        return f"No applications found for {scope}."

    lines = []
    for app in applications:
        lines.append(
            f"- application {app['application_id']} | "
            f"user {app['user_id']} | "
            f"job {app['job_posting_id']} | "
            f"status {app['application_status']}"
        )
    return "\n".join(lines)


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


def get_applicant_profile(user_id: int | str) -> Dict[str, Any] | None:
    """Retrieve one applicant's profile + resume text (student-1 domain).

    Mirrors mcp-server/tools.py's ``get_applicant_profile`` HTTP sequence:
    profiles/by-user/{id} -> profiles/{id}/resumes -> resumes/{id}/file. Every
    call is best-effort (a missing profile/resume is not an error), matching
    that tool's behaviour.
    """
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None

    base_url = STUDENT_1_DB_URL.rstrip("/")
    try:
        response = requests.get(f"{base_url}/profiles/by-user/{uid}", timeout=DB_TIMEOUT_SECONDS)
    except requests.RequestException:
        return None
    if response.status_code != 200:
        return None

    profile = response.json()
    profile_id = profile.get("profile_id")

    resume = None
    try:
        resumes_resp = requests.get(f"{base_url}/profiles/{profile_id}/resumes", timeout=DB_TIMEOUT_SECONDS)
        if resumes_resp.status_code == 200:
            records = resumes_resp.json()
            if records:
                resume = records[0]
    except requests.RequestException:
        resume = None

    resume_text = None
    if resume:
        try:
            file_resp = requests.get(
                f"{base_url}/resumes/{resume['resume_id']}/file", timeout=DB_TIMEOUT_SECONDS
            )
            if file_resp.status_code == 200:
                resume_text = _extract_resume_text(file_resp.content, resume.get("file_type", ""))
        except requests.RequestException:
            resume_text = None

    return {
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


def format_profile_evidence(profile_data: Dict[str, Any] | None, user_id: int | str | None) -> str:
    if not profile_data or not profile_data.get("profile"):
        scope = f"user {user_id}" if user_id else "this applicant"
        return f"No profile found for {scope}."

    fields = [f"{key} = {value}" for key, value in profile_data["profile"].items() if value]
    resume = profile_data.get("resume")
    if resume:
        fields.append(f"resume_file_name = {resume.get('file_name')}")
        if resume.get("text"):
            fields.append(f"resume_text = {resume['text']}")
    if not fields:
        return f"A profile exists for user {user_id} but has no fields set."
    return "; ".join(fields) + "."


def call_model(user_request: str, evidence_text: str, evidence_label: str = "Application Evidence") -> str:
    prompt = f"""
{load_prompt()}

Constraints:
- Use only the provided {evidence_label}.
- Do not invent facts, users, or fields.
- Return concise output under 180 words.

User Request:

{user_request}

{evidence_label}:

{evidence_text}
"""
    try:
        response = client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=WORKER_MAX_TOKENS,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:  # noqa: BLE001
        return (
            "Output:\n"
            "Model output could not be generated.\n\n"
            "Evidence Used:\n"
            f"{evidence_text}\n\n"
            "Limitations:\n"
            f"Model call failed. Human review required. Error: {exc}"
        )


def _worker_result(output: str, evidence: List[Any], evidence_count: int, **extra: Any) -> Dict[str, Any]:
    """Shape shared by every Worker outcome, regardless of evidence domain."""
    return {
        "status": "success",
        "agent": "worker_agent",
        "model": OLLAMA_MODEL,
        "evidence_count": evidence_count,
        "evidence": evidence,
        "output": output,
        "human_approval_required": True,
        **extra,
    }


def generate_output(
    user_request: str, user_id: int | str | None = None, evidence_domain: str = "applications"
) -> Dict[str, Any]:
    """Generate the Worker's output, grounded in the requested evidence domain.

    ``evidence_domain`` is an explicit, generic switch (e.g "applications" or
    "profile") supplied by the caller — the Worker has no built-in knowledge of
    which student feature wants which domain; that mapping lives in each
    feature's own backend (e.g. student-1's ``services/multi_agent_api.py``
    always requests "profile"). ``user_id`` deterministically scopes evidence
    to one caller's own records (both DB endpoints already support this) so
    personal ("my") requests ground correctly instead of blending in every
    other applicant's data; for profiles it's required outright (that lookup
    is single-user by design, so a missing id fails safe to "no evidence"
    rather than any risk of cross-applicant leakage).
    """
    if evidence_domain == "profile":
        if user_id is None:
            return _worker_result(
                "No applicant is identified for this request, so no profile evidence can be retrieved.",
                [], 0, user_id=None,
            )
        profile_data = get_applicant_profile(user_id)
        evidence_text = format_profile_evidence(profile_data, user_id)
        output = call_model(user_request, evidence_text, "Applicant Profile Evidence")
        has_profile = bool(profile_data and profile_data.get("profile"))
        return _worker_result(
            output, [profile_data] if profile_data else [], 1 if has_profile else 0, user_id=user_id,
        )

    if evidence_domain == "applications":
        job_posting_id = extract_job_posting_id(user_request)
        try:
            applications = get_applications(job_posting_id, user_id=user_id)
        except requests.RequestException as exc:
            return {
                "status": "error",
                "agent": "worker_agent",
                "job_posting_id": job_posting_id,
                "evidence_count": 0,
                "evidence": [],
                "output": "Database evidence could not be retrieved.",
                "error": str(exc),
                "human_approval_required": True,
            }
        evidence_text = format_evidence(applications, job_posting_id)
        output = call_model(user_request, evidence_text, "Application Evidence")
        return _worker_result(output, applications, len(applications), job_posting_id=job_posting_id)

    return _worker_result(
        f"Unknown evidence domain '{evidence_domain}'; no evidence could be retrieved.",
        [], 0, evidence_domain=evidence_domain,
    )


if __name__ == "__main__":
    import json

    result = generate_output("Summarise the applications submitted for job posting 1.")
    print(json.dumps(result, indent=2))
