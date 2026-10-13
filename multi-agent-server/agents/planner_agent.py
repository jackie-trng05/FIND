"""Planner Agent for the shared FIND multi-agent server.

Uses the local Ollama planner model (default ``llama3.1:8b``) to turn a free-form
user request into a short, structured workflow plan. The plan is advisory: the
Worker and Reviewer agents and the human reviewer do the grounded work. If the
model is unavailable the agent returns a safe deterministic fallback plan so the
coordinator can still complete the workflow.
"""

import os
from pathlib import Path
from typing import Any, Dict, List

from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parents[1]
PROMPT_PATH = BASE_DIR / "prompts" / "planner_prompt.txt"

# The server runs as a local host process (like mcp-server / rag-server), so the
# default Ollama endpoint is localhost rather than host.docker.internal.
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
OLLAMA_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "45"))

FAST_MODE = os.getenv("FAST_MODE", "true").lower() == "true"
PLANNER_MAX_TOKENS = int(os.getenv("PLANNER_MAX_TOKENS", "120" if FAST_MODE else "300"))

client = OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama",
    timeout=OLLAMA_TIMEOUT_SECONDS,
)


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8").strip()


def default_steps() -> List[Dict[str, Any]]:
    return [
        {"step": 1, "agent": "planner_agent", "action": "Create workflow plan"},
        {"step": 2, "agent": "worker_agent", "action": "Retrieve database evidence and generate output"},
        {"step": 3, "agent": "reviewer_agent", "action": "Review output for risk, correction, retest, and recommendation"},
        {"step": 4, "agent": "human_reviewer", "action": "Accept, partially accept, or reject"},
    ]


def call_model(user_request: str) -> str:
    prompt = f"""
{load_prompt()}

Constraints:
- Keep output concise.
- Provide exactly 3 milestones.
- Keep response under 140 words.

User Request:

{user_request}
"""
    try:
        response = client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=PLANNER_MAX_TOKENS,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:  # noqa: BLE001 - fall back to a safe deterministic plan
        return (
            "Objective: Process the user request.\n"
            "Steps: Plan, work, review, human decision.\n"
            "Evidence Required: FIND application evidence from the database service.\n"
            "Human Approval: Required.\n"
            f"Fallback Reason: {exc}"
        )


def plan_workflow(user_request: str) -> Dict[str, Any]:
    return {
        "status": "success",
        "agent": "planner_agent",
        "model": OLLAMA_MODEL,
        "objective": user_request,
        "plan": call_model(user_request),
        "steps": default_steps(),
        "human_approval_required": True,
    }


if __name__ == "__main__":
    import json

    result = plan_workflow("Summarise the applications submitted for job posting 1.")
    print(json.dumps(result, indent=2))
