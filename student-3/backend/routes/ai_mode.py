"""AI-Mode routes for Application Management.

Feature AI function: "AI-assisted candidate screening" — takes the job posting
and the candidate's resume, returns a suitability score, key matched skills,
and identified skill gaps.

The handler demonstrates the shared Agentic AI workflow:

    PLAN    -> assemble the prompt from job details + resume text
    ACT     -> call the approved open-source LLM through Ollama
    OBSERVE -> parse the model output; validate structure/length
    ADAPT   -> retry once with a stricter instruction if the output is too thin

The frontend calls this endpoint and HTMX swaps the returned HTML fragment.
"""

from __future__ import annotations

import requests
from flask import Blueprint, request

from services import database_api, postings_api, shared_api
from services.llm_client import OLLAMA_MODEL, create_chat_completion
from services.prompt_loader import load_prompt
from services.resume_text import extract_text
from views.html_formatters import (
    parse_screening_response,
    render_ai_screening_panel,
    render_message,
)

ai_mode_bp = Blueprint("ai_mode", __name__)

_MIN_USEFUL_LENGTH = 40


@ai_mode_bp.post("/api/applications/<int:application_id>/screen")
def screen_application(application_id: int):
    user = shared_api.get_session_user(request.headers.get("Cookie", ""))
    if not user:
        return render_message("Please log in first.", "error"), 200
    if user.get("role") != "staff":
        return render_message("Staff only.", "error"), 200

    # Load the application, posting and resume so we can build the prompt.
    try:
        app_resp = database_api.get_application(application_id)
        if app_resp.status_code == 404:
            return render_message("Application not found.", "error"), 200
        app_resp.raise_for_status()
    except requests.RequestException:
        return render_message("Database unavailable.", "error"), 200
    application = app_resp.json()

    posting = postings_api.get_job_posting(application["JobPosting_Id"]) or {}
    candidate = shared_api.get_user(application["User_Id"]) or {}

    resume_text = "(No resume provided.)"
    if application.get("Resume_Id"):
        try:
            meta_resp = database_api.get_resume(application["Resume_Id"])
            dl_resp = database_api.download_resume_stream(application["Resume_Id"])
            if meta_resp.status_code == 200 and dl_resp.status_code == 200:
                meta = meta_resp.json()
                data = dl_resp.content
                extracted = extract_text(data, meta.get("Resume_MimeType", ""))
                if extracted:
                    resume_text = extracted
        except requests.RequestException:
            pass

    try:
        system_prompt = load_prompt("screening_system_prompt.txt")
        task_template = load_prompt("screening_task_prompt.txt")
    except OSError:
        return render_message("AI prompt templates are missing.", "error"), 200

    candidate_name = (
        f"{candidate.get('user_first_name', '')} "
        f"{candidate.get('user_last_name', '')}".strip() or "Unknown candidate"
    )

    # PLAN --------------------------------------------------------------------
    user_prompt = task_template.format(
        job_title=posting.get("Job_Title", "(unknown)"),
        job_type=posting.get("Job_Type", "(unknown)"),
        job_description=posting.get("Job_Description", "(no description provided)"),
        job_requirements=posting.get("Requirements", "(none listed)"),
        candidate_name=candidate_name,
        resume_text=resume_text,
    )

    try:
        # ACT -----------------------------------------------------------------
        answer = create_chat_completion(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=400,
            temperature=0.2,
            model=OLLAMA_MODEL,
        )

        # OBSERVE -------------------------------------------------------------
        if len(answer) < _MIN_USEFUL_LENGTH:
            # ADAPT -----------------------------------------------------------
            answer = create_chat_completion(
                [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": user_prompt
                        + "\n\nBe concrete. Follow the required output format exactly.",
                    },
                ],
                max_tokens=400,
                temperature=0.3,
                model=OLLAMA_MODEL,
            )

        if not answer:
            return render_message(
                "The AI did not return a screening result. Try again.", "error"
            ), 200
    except Exception as exc:  # noqa: BLE001 - surface any Ollama/client failure to the UI
        return render_message(
            "AI request failed. Check that Ollama is running and that "
            f"{OLLAMA_MODEL} is installed. Details: {exc}",
            "error",
        ), 200

    parsed = parse_screening_response(answer)
    # Cache the screening so it survives page reloads.
    try:
        database_api.upsert_screening(application_id, parsed)
    except requests.RequestException:
        pass

    return render_ai_screening_panel(application_id=application_id, screening=parsed), 200
