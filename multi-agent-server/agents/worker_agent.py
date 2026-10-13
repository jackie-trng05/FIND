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

import requests
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parents[1]
PROMPT_PATH = BASE_DIR / "prompts" / "worker_prompt.txt"

# The shared server is a host process, so it reaches the database service via its
# host-mapped port. Defaults to student-3's application database (host 16012).
MULTI_AGENT_DB_URL = os.getenv("MULTI_AGENT_DB_URL", "http://localhost:16012")
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


def get_applications(job_posting_id: str | None, status: str | None = None) -> List[Dict[str, Any]]:
    """Retrieve application records from the FIND database service over HTTP."""
    params: Dict[str, Any] = {}
    if job_posting_id:
        params["job_posting_id"] = job_posting_id
    if status:
        params["status"] = status

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


def call_model(user_request: str, evidence_text: str) -> str:
    prompt = f"""
{load_prompt()}

Constraints:
- Use only the provided Application Evidence.
- Do not invent applications, users, or fields.
- Return concise output under 180 words.

User Request:

{user_request}

Application Evidence:

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


def generate_output(user_request: str) -> Dict[str, Any]:
    job_posting_id = extract_job_posting_id(user_request)

    try:
        applications = get_applications(job_posting_id)
        evidence_text = format_evidence(applications, job_posting_id)
        output = call_model(user_request, evidence_text)
        return {
            "status": "success",
            "agent": "worker_agent",
            "model": OLLAMA_MODEL,
            "job_posting_id": job_posting_id,
            "evidence_count": len(applications),
            "evidence": applications,
            "output": output,
            "human_approval_required": True,
        }
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


if __name__ == "__main__":
    import json

    result = generate_output("Summarise the applications submitted for job posting 1.")
    print(json.dumps(result, indent=2))
