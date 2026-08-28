import re
from datetime import datetime, timedelta

from flask import Blueprint, request
import requests

from services.database_api import get_interviews
from services.llm_client import OLLAMA_MODEL, create_chat_completion
from services.prompt_loader import load_prompt
from views import html_formatters as fmt


ai_mode_bp = Blueprint("ai_mode", __name__)

# Number of time suggestions surfaced as clickable chips.
_MAX_SUGGESTIONS = 6

# Matches a strict "YYYY-MM-DD HH:MM" timestamp anywhere in a line of LLM output.
_DT_RE = re.compile(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}")



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
    """Suggest clickable, future-only interview time slots.

    Uses the local model when it is available (guided by any staff/applicant
    preferences) and always tops up with deterministic future business-hour
    slots so the feature stays usable even when Ollama is offline. Every
    suggestion is guaranteed to be in the future and to avoid clashing with
    already-scheduled interviews.
    """
    preferences = request.form.get("preferences", "").strip()
    existing = _scheduled_datetimes()

    slots = _llm_slots(preferences, existing)
    if len(slots) < _MAX_SUGGESTIONS:
        for slot in _deterministic_slots(existing, _MAX_SUGGESTIONS):
            if slot not in slots:
                slots.append(slot)
            if len(slots) >= _MAX_SUGGESTIONS:
                break

    slots = slots[:_MAX_SUGGESTIONS]
    return fmt.render_time_suggestions(
        slots, note="Click a time to fill in the date & time field."
    ), 200


def _parse_dt(value):
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return None


def _scheduled_datetimes():
    """Datetimes of existing interviews, normalised to 'YYYY-MM-DD HH:MM'."""
    try:
        interviews = get_interviews()
    except requests.RequestException:
        return set()
    result = set()
    for item in interviews:
        dt = _parse_dt(item.get("interview_datetime"))
        if dt:
            result.add(dt.strftime("%Y-%m-%d %H:%M"))
    return result


def _deterministic_slots(existing, limit):
    """Future weekday business-hour slots, skipping clashes and the past."""
    now = datetime.now()
    day = now.date()
    slots = []
    for _ in range(21):  # look ahead ~3 working weeks
        day = day + timedelta(days=1)
        if day.weekday() >= 5:  # skip Sat/Sun
            continue
        for hour in (9, 11, 14, 16):
            candidate = datetime(day.year, day.month, day.day, hour, 0)
            if candidate <= now:
                continue
            stamp = candidate.strftime("%Y-%m-%d %H:%M")
            if stamp in existing:
                continue
            slots.append(stamp)
            if len(slots) >= limit:
                return slots
    return slots


def _llm_slots(preferences, existing):
    """Ask the local model for future slots; return only valid future ones."""
    try:
        scheduled = _existing_schedule_context()
    except requests.RequestException:
        scheduled = "No existing interview data could be retrieved."

    try:
        system_prompt = load_prompt("interview/system_prompt.txt")
        task_prompt = load_prompt("interview/task_prompt.txt")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        final_prompt = f"""{task_prompt}

The current date and time is {now_str}. Only suggest times AFTER this moment.

Currently scheduled interviews (avoid clashing with these):
{scheduled}

Staff availability and applicant preferences:
{preferences or "No specific preferences provided; suggest sensible business-hour slots."}
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
    except Exception:
        return []

    now = datetime.now()
    slots = []
    for match in _DT_RE.findall(answer or ""):
        stamp = " ".join(match.split())
        dt = _parse_dt(stamp)
        if not dt or dt <= now:
            continue
        stamp = dt.strftime("%Y-%m-%d %H:%M")
        if stamp in existing or stamp in slots:
            continue
        slots.append(stamp)
        if len(slots) >= _MAX_SUGGESTIONS:
            break
    return slots


def _existing_schedule_context():
    interviews = get_interviews()
    if not interviews:
        return "None."

    lines = [
        f"- {item.get('interview_datetime')} (staff {item.get('user_id')})"
        for item in interviews
    ]
    return "\n".join(lines)
