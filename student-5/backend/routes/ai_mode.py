"""AI-Mode routes for Candidate Evaluation.

Feature AI function: "AI-assisted evaluation scoring" — takes a candidate's
completed interview notes (primary source) plus the job posting, applicant
profile and application details, and returns suggested 1-5 scores across the
five evaluation criteria together with a short rationale. HR staff can accept
or override the suggestion.

The handler demonstrates the shared Agentic AI workflow:

    PLAN    -> gather interview notes + application context, build the prompt
    ACT     -> call the approved open-source LLM through Ollama (AI-Mode)
    OBSERVE -> parse the model output as JSON; validate structure
    ADAPT   -> retry once with a stricter instruction if parsing fails
"""

import json

import requests as http_requests
from flask import Blueprint, jsonify, request

from services.integration_api import require_session
from services.config import (
    APPLICATIONS_DB_URL,
    INTERVIEWS_DB_URL,
    POSTINGS_DB_URL,
    SHARED_DB_URL,
)
from services.llm_client import OLLAMA_MODEL, create_chat_completion
from services.prompt_loader import load_prompt

ai_mode_bp = Blueprint("ai_mode", __name__)

_DEFAULT_SCORE = 3


def _clamp(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return _DEFAULT_SCORE
    return max(1, min(5, value))


def _parse_scores(raw):
    """OBSERVE: turn the model's text into a scores dict, tolerating stray text."""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(raw[start:end])
            except json.JSONDecodeError:
                return None
    return None


@ai_mode_bp.post("/api/ai/evaluation-recommendation")
def ai_recommendation():
    user, err = require_session()
    if err:
        return err
    if user["role"] != "staff":
        return jsonify({"error": "Staff access only"}), 403

    data = request.get_json() or {}
    application_id = data.get("application_id")
    if not application_id:
        return jsonify({"error": "application_id is required"}), 400

    # PLAN --------------------------------------------------------------------
    application_info = ""
    job_info = ""
    applicant_info = ""
    interview_notes = ""

    try:
        app_resp = http_requests.get(f"{APPLICATIONS_DB_URL}/applications/{application_id}", timeout=5)
        if app_resp.status_code == 200:
            app_data = app_resp.json()
            application_info = json.dumps(app_data, indent=2)

            posting_resp = http_requests.get(f"{POSTINGS_DB_URL}/job-postings/{app_data.get('job_posting_id')}", timeout=5)
            if posting_resp.status_code == 200:
                job_info = json.dumps(posting_resp.json(), indent=2)

            user_resp = http_requests.get(f"{SHARED_DB_URL}/users/{app_data.get('user_id')}", timeout=5)
            if user_resp.status_code == 200:
                applicant_info = json.dumps(user_resp.json(), indent=2)
    except Exception:
        pass

    try:
        interviews_resp = http_requests.get(f"{INTERVIEWS_DB_URL}/interviews", timeout=5)
        if interviews_resp.status_code == 200:
            notes = [
                iv.get("interview_notes", "").strip()
                for iv in interviews_resp.json()
                if iv.get("application_id") == application_id
                and iv.get("interview_notes", "").strip()
            ]
            interview_notes = "\n\n".join(notes)
    except Exception:
        pass

    system_prompt = load_prompt("system_prompt.txt")
    user_prompt = load_prompt("task_prompt.txt").format(
        interview_notes=interview_notes or "Not available",
        job_info=job_info or "Not available",
        applicant_info=applicant_info or "Not available",
        application_info=application_info or "Not available",
    )

    try:
        # ACT -----------------------------------------------------------------
        raw = create_chat_completion(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=300,
            temperature=0.3,
        )

        # OBSERVE -------------------------------------------------------------
        result = _parse_scores(raw)

        # ADAPT ---------------------------------------------------------------
        if result is None:
            raw = create_chat_completion(
                [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": user_prompt
                        + "\n\nRespond with ONLY a valid JSON object using the exact keys requested.",
                    },
                ],
                max_tokens=300,
                temperature=0.2,
            )
            result = _parse_scores(raw) or {}

        return jsonify({
            "technical": _clamp(result.get("technical")),
            "education": _clamp(result.get("education")),
            "communication": _clamp(result.get("communication")),
            "problem_solving": _clamp(result.get("problem_solving")),
            "professionalism": _clamp(result.get("professionalism")),
            "rationale": result.get("rationale", ""),
        })
    except Exception as exc:
        return jsonify({
            "error": f"AI service unavailable: {str(exc)}. "
                     f"Check that Ollama is running and that {OLLAMA_MODEL} is installed.",
            "technical": _DEFAULT_SCORE, "education": _DEFAULT_SCORE,
            "communication": _DEFAULT_SCORE, "problem_solving": _DEFAULT_SCORE,
            "professionalism": _DEFAULT_SCORE, "rationale": "",
        }), 200
