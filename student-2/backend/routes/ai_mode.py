"""AI-Mode routes for Job Posting Management.

Feature AI function (registration form): "Suggest suitable skills/qualifications
based on the position." The handler demonstrates the shared Agentic AI workflow:

    PLAN    -> assemble the prompt from the job title/type/description
    ACT     -> call the approved open-source LLM through Ollama
    OBSERVE -> inspect the model output for usable content
    ADAPT   -> retry once with a stricter instruction if the output is too thin

The frontend calls this endpoint and HTMX swaps the returned HTML fragment.
"""

from flask import Blueprint, request

from services.llm_client import OLLAMA_MODEL, create_chat_completion
from services.prompt_loader import load_prompt
from views.html_formatters import render_message, render_skill_suggestions

ai_mode_bp = Blueprint("ai_mode", __name__)

_MIN_USEFUL_LENGTH = 40


@ai_mode_bp.post("/ai/suggest-skills")
def suggest_skills():
    job_title = request.form.get("Job_Title", "").strip()
    job_description = request.form.get("Job_Description", "").strip()
    job_type = request.form.get("Job_Type", "").strip() or "Full time"

    if not job_title:
        return render_message("Enter a job title first, then ask the AI.", "error"), 200

    try:
        system_prompt = load_prompt("skills_system_prompt.txt")
        task_template = load_prompt("skills_task_prompt.txt")
    except OSError:
        return render_message("AI prompt templates are missing.", "error"), 200

    # PLAN: build the user prompt from the job details.
    user_prompt = task_template.format(
        job_title=job_title,
        job_type=job_type,
        job_description=job_description or "(no description provided)",
    )

    try:
        # ACT: call the approved LLM.
        answer = create_chat_completion(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=300,
            temperature=0.2,
            model=OLLAMA_MODEL,
        )

        # OBSERVE: is the response usable?
        if len(answer) < _MIN_USEFUL_LENGTH:
            # ADAPT: retry once, nudging the model to be concrete.
            answer = create_chat_completion(
                [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": user_prompt
                        + "\n\nBe specific and list concrete skills and qualifications.",
                    },
                ],
                max_tokens=300,
                temperature=0.3,
                model=OLLAMA_MODEL,
            )

        if not answer:
            return render_message("The AI did not return any suggestions. Try again.", "error"), 200

        return render_skill_suggestions(answer), 200
    except Exception as exc:  # noqa: BLE001 - surface any Ollama/client failure to the UI
        return (
            render_message(
                "AI request failed. Check that Ollama is running and that "
                f"{OLLAMA_MODEL} is installed. Details: {exc}",
                "error",
            ),
            200,
        )
