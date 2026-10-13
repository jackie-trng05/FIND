"""Reviewer Agent for the shared FIND multi-agent server.

Uses the local Ollama review model (default ``llama3.1:8b``) to assess the Worker
agent's output against the retrieved evidence: risk, correction, retest, and a
recommendation. This is the governance step before the human makes the final
decision. On model failure it returns a conservative "do not approve" review.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict

from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parents[1]
PROMPT_PATH = BASE_DIR / "prompts" / "reviewer_prompt.txt"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_REVIEW_MODEL = os.getenv("OLLAMA_REVIEW_MODEL", "llama3.1:8b")
OLLAMA_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "45"))

FAST_MODE = os.getenv("FAST_MODE", "true").lower() == "true"
REVIEWER_MAX_TOKENS = int(os.getenv("REVIEWER_MAX_TOKENS", "160" if FAST_MODE else "400"))

client = OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama",
    timeout=OLLAMA_TIMEOUT_SECONDS,
)


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8").strip()


def call_model(user_request: str, worker_result: Dict[str, Any]) -> str:
    prompt = f"""
{load_prompt()}

Constraints:
- Keep each section brief and actionable.
- Return only: Risk, Correction, Retest, Recommendation.
- Keep response under 160 words.

User Request:

{user_request}

Worker Result:

{json.dumps(worker_result, indent=2)}
"""
    try:
        response = client.chat.completions.create(
            model=OLLAMA_REVIEW_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=REVIEWER_MAX_TOKENS,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:  # noqa: BLE001
        return (
            "Risk: Review model unavailable.\n"
            "Correction: Verify Ollama and reviewer model.\n"
            "Retest: Run the workflow again.\n"
            f"Recommendation: Do not approve until reviewed. Error: {exc}"
        )


def review_output(user_request: str, worker_result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "status": "success",
        "agent": "reviewer_agent",
        "model": OLLAMA_REVIEW_MODEL,
        "review": call_model(user_request, worker_result),
        "human_approval_required": True,
    }


if __name__ == "__main__":
    sample_worker_result = {
        "status": "success",
        "job_posting_id": "1",
        "evidence_count": 2,
        "output": "Two applications are submitted for job posting 1.",
    }
    result = review_output("Summarise the applications for job posting 1.", sample_worker_result)
    print(json.dumps(result, indent=2))
