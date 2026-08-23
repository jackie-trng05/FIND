from flask import Blueprint, request
import requests

from services.database_api import get_interviews
from services.llm_client import OLLAMA_MODEL, create_chat_completion
from services.prompt_loader import load_prompt


ai_mode_bp = Blueprint("ai_mode", __name__)


@ai_mode_bp.post("/ask")
def ask_local_agent():
    question = request.form.get("question", "").strip()

    if not question:
        return "<p>Question is required.</p>", 400

    try:
        answer = create_chat_completion(
            [
                {
                    "role": "system",
                    "content": (
                        "You are a concise recruitment assistant for the Interview "
                        "microservice. Answer in one short paragraph unless asked otherwise."
                    ),
                },
                {"role": "user", "content": question},
            ],
            max_tokens=200,
            temperature=0.2,
            model=OLLAMA_MODEL,
        )
        return f"<p>{answer}</p>", 200
    except Exception as exc:
        return (
            "<p>Local AI agent request failed. "
            "Check that Ollama is running and that the model is installed.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@ai_mode_bp.post("/suggest-times")
def suggest_interview_times():
    preferences = request.form.get("preferences", "").strip()

    if not preferences:
        return "<p>Please describe the staff availability or applicant preferences.</p>", 400

    try:
        scheduled = _existing_schedule_context()
    except requests.RequestException:
        scheduled = "No existing interview data could be retrieved."

    try:
        system_prompt = load_prompt("interview/system_prompt.txt")
        task_prompt = load_prompt("interview/task_prompt.txt")

        final_prompt = f"""{task_prompt}

Currently scheduled interviews (avoid clashing with these):
{scheduled}

Staff availability and applicant preferences:
{preferences}
"""

        answer = create_chat_completion(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": final_prompt},
            ],
            max_tokens=300,
            temperature=0.3,
            model=OLLAMA_MODEL,
        )
        return f"<p>{answer}</p>", 200
    except Exception as exc:
        return (
            "<p>Interview time suggestion failed.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


def _existing_schedule_context():
    interviews = get_interviews()
    if not interviews:
        return "None."

    lines = [
        f"- {item.get('interview_datetime')} "
        f"(staff {item.get('staff_id')}, status {item.get('interview_status')})"
        for item in interviews
    ]
    return "\n".join(lines)
