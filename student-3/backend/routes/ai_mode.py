"""AI-Mode candidate screening route (Ollama-backed shortlist recommendation)."""

import requests
from flask import Blueprint

from services import database_api
from services.integration_api import (
    download_resume_stream,
    get_job_posting,
    get_resume_metadata,
    get_session_user,
    get_user,
)
from services.llm_client import (
    OLLAMA_MODEL,
    client as ollama_client,
    extract_resume_text,
    parse_screening_response,
)
from services.prompt_loader import load_prompt
from views.html_formatters import render_ai_screening_panel, render_message

ai_mode_bp = Blueprint("ai_mode", __name__)


@ai_mode_bp.post("/api/applications/<int:application_id>/screen")
def screen_application(application_id):
    user = get_session_user()
    if not user:
        return render_message("Please log in first.", "error"), 200
    if user.get("role") != "staff":
        return render_message("Staff only.", "error"), 200

    try:
        app_resp = database_api.get_application(application_id)
        if app_resp.status_code == 404:
            return render_message("Application not found.", "error"), 200
        app_resp.raise_for_status()
    except requests.RequestException:
        return render_message("Database unavailable.", "error"), 200
    application = app_resp.json()

    posting = get_job_posting(application["job_posting_id"]) or {}
    candidate = get_user(application["user_id"]) or {}

    resume_text = "(No resume provided.)"
    if application.get("resume_id"):
        try:
            meta = get_resume_metadata(int(application["resume_id"]), "staff")
            dl_resp = download_resume_stream(int(application["resume_id"]), "staff")
            if meta and dl_resp.status_code == 200:
                extracted = extract_resume_text(dl_resp.content, meta.get("file_type", ""))
                if extracted:
                    resume_text = extracted
        except requests.RequestException:
            pass

    try:
        system_prompt = load_prompt("system_prompt.txt")
        task_template = load_prompt("task_prompt.txt")
    except OSError:
        return render_message("AI prompt templates are missing.", "error"), 200

    candidate_name = (
        f"{candidate.get('user_first_name', '')} "
        f"{candidate.get('user_last_name', '')}".strip() or "Unknown candidate"
    )
    user_prompt = task_template.format(
        job_title=posting.get("Job_Title", "(unknown)"),
        job_type=posting.get("Job_Type", "(unknown)"),
        job_description=posting.get("Job_Description", "(no description provided)"),
        job_requirements=posting.get("Requirements", "(none listed)"),
        candidate_name=candidate_name,
        resume_text=resume_text,
    )

    try:
        response = ollama_client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=400, temperature=0.2,
        )
        answer = (response.choices[0].message.content or "").strip()

        if len(answer) < 40:
            response = ollama_client.chat.completions.create(
                model=OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt +
                        "\n\nBe concrete. Follow the required output format exactly."},
                ],
                max_tokens=400, temperature=0.3,
            )
            answer = (response.choices[0].message.content or "").strip()

        if not answer:
            return render_message(
                "The AI did not return a screening result. Try again.", "error"), 200
    except Exception as exc:
        return render_message(
            "AI request failed. Check that Ollama is running and that "
            f"{OLLAMA_MODEL} is installed. Details: {exc}",
            "error"), 200

    parsed = parse_screening_response(answer)
    return render_ai_screening_panel(application_id, parsed), 200
