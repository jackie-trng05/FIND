"""AI-Mode route: suggest profile fields from the applicant's stored resume.

Feature AI function (registration form): "Analyse a user's stored resume to
suggest profile autocomplete, such as summary, professional title, and
interests." Demonstrates the shared Agentic AI workflow:

    PLAN    -> load the caller's profile and resume text
    ACT     -> call the approved open-source LLM through Ollama
    OBSERVE -> parse the labeled response and check it's usable and consistent
    ADAPT   -> retry once with a stricter instruction if the output is empty
               or inconsistent (e.g. summary populated but title is not)

The frontend calls this endpoint and HTMX swaps the returned HTML fragment.
"""

from flask import Blueprint

from services import database_api, integration_api
from services.llm_client import (
    OLLAMA_MODEL,
    classify_resume_quality,
    client as ollama_client,
    extract_resume_text,
    parse_profile_suggestions,
)
from services.prompt_loader import load_prompt
from views.html_formatters import render_message, render_profile_suggestions

ai_mode_bp = Blueprint("ai_mode", __name__)

_GENERIC_TITLE_PLACEHOLDER = "Add your current or most recent job title here"


def _get_my_profile(user_id: int) -> dict | None:
    resp = database_api.get_profile_by_user(user_id)
    return resp.json() if resp.status_code == 200 else None


def _looks_like_person_name(value: str, user: dict) -> bool:
    """Catch the model echoing the candidate's own name back as the title --
    a known failure mode for small local models, even with prompt guardrails."""
    full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip().lower()
    return bool(full_name) and value.strip().lower() == full_name


def _ask(system_prompt, user_prompt, extra_instruction=""):
    response = ollama_client.chat.completions.create(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt + extra_instruction},
        ],
        max_tokens=350,
        temperature=0.2,
    )
    return (response.choices[0].message.content or "").strip()


@ai_mode_bp.post("/profile/ai-suggestions")
def suggest_profile_fields():
    user = integration_api.get_session_user()
    if not user:
        return {"error": "Not authenticated"}, 401
    if user["role"] == "staff":
        return render_message("Staff accounts do not have profiles to suggest.", "error"), 200

    # PLAN: locate the caller's profile and resume text.
    profile = _get_my_profile(user["user_id"])
    if not profile:
        return render_message("Create your profile above before using AI suggestions.", "error"), 200

    resumes_resp = database_api.list_resumes(profile["profile_id"])
    resumes = resumes_resp.json() if resumes_resp.status_code == 200 else []
    if not resumes:
        return render_message(
            "Upload a resume below to get AI suggestions for your profile.", "info"
        ), 200

    file_resp = database_api.get_resume_file(resumes[0]["resume_id"])
    if file_resp.status_code != 200:
        return render_message("Could not read your resume file. Try re-uploading it.", "error"), 200

    resume_text = extract_resume_text(file_resp.content, file_resp.headers.get("Content-Type", ""))

    # OBSERVE (resume quality): decide this in code, not by asking the model
    # to self-report -- a small local model isn't reliable at accurately
    # distinguishing "the file couldn't be read" from "there just isn't much text".
    quality = classify_resume_quality(resume_text)
    if quality == "unreadable":
        return render_message(
            "We couldn't extract readable text from your resume file. It may be a "
            "scanned image or an unsupported format — try re-uploading a text-based PDF.",
            "error",
        ), 200

    try:
        system_prompt = load_prompt("system_prompt.txt")
        task_template = load_prompt("task_prompt.txt")
    except OSError:
        return render_message("AI prompt templates are missing.", "error"), 200

    user_prompt = task_template.format(resume_text=resume_text)

    # ACT: call the approved LLM. OBSERVE: check the parsed reply has content.
    try:
        answer = _ask(system_prompt, user_prompt)
        parsed = parse_profile_suggestions(answer)

        has_content = any(
            parsed[field].strip() for field in ("professional_title", "summary", "interests")
        )
        # Also retry if the model filled in a real Summary but left the title as
        # its own placeholder -- that inconsistency means it had usable content
        # (e.g. a synthetic/example resume) and shouldn't have fallen back at all.
        inconsistent = (
            parsed["professional_title"].strip() == _GENERIC_TITLE_PLACEHOLDER
            and len(parsed["summary"].strip()) > 20
        )
        if not has_content or inconsistent:
            # ADAPT: retry once with a stricter instruction.
            answer = _ask(
                system_prompt,
                user_prompt,
                "\n\nFollow the required four-line format exactly, using the labels "
                "Professional_Title, Summary, Interests, and Note. The resume text you were "
                "given has real content (it may look like a test/example resume, but treat it "
                "the same as a real one) -- do not fall back to a placeholder Professional_Title.",
            )
            parsed = parse_profile_suggestions(answer)
    except Exception as exc:
        return render_message(
            "Local AI agent request failed. Check that Ollama is running and that "
            f"{OLLAMA_MODEL} is installed. Details: {exc}",
            "error",
        ), 200

    if quality == "short":
        # Deterministic, code-authored caveat -- overrides whatever the model
        # put in Note, so the wording is accurate and consistent rather than
        # depending on a small model to describe its own limitation correctly.
        parsed["note"] = (
            "Your resume is quite short, so these are general suggestions -- "
            "add more detail to your resume for more tailored results."
        )

    if _looks_like_person_name(parsed["professional_title"], user):
        parsed["professional_title"] = _GENERIC_TITLE_PLACEHOLDER

    return render_profile_suggestions(parsed), 200
