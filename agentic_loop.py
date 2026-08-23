"""Shared Team Agentic Loop for the FIND recruitment platform.

Implements the required PLAN -> ACT -> OBSERVE -> ADAPT workflow (spec 4.3) for
the integrated FIND application. It runs deterministic validation against the
running Docker services and then asks a local Ollama LLM (spec 4.2, Release 0:
Frontend -> Backend/API -> Ollama -> LLM) for one small improvement.

Run the stack first (docker-compose up --build), then:

    python agentic_loop.py
"""

import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from openai import OpenAI

ENV_PATH = Path(__file__).with_name(".env")
load_dotenv(dotenv_path=ENV_PATH)

# --- Configuration -----------------------------------------------------------

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")

# Docker-published service ports (see docker-compose.yml).
SHARED_API_URL = os.getenv("SHARED_API_URL", "http://localhost:16002")
SHARED_DB_URL = os.getenv("SHARED_DB_URL", "http://localhost:16003")
STUDENT_1_API_URL = os.getenv("STUDENT_1_API_URL", "http://localhost:16005")
STUDENT_1_DB_URL = os.getenv("STUDENT_1_DB_URL", "http://localhost:16006")

REQUEST_TIMEOUT = 5  # seconds

# --- PLAN --------------------------------------------------------------------

PLAN = {
    "goal": "Validate the integrated FIND recruitment platform using a local open-source AI agent",
    "pass_condition": "Core service health checks and shared data-quality checks pass locally",
    "nfr": "Health endpoints respond within 500 ms",
    "ai_condition": "The local model responds through the Ollama runtime",
    "features": {
        "shared-auth": "User accounts, roles, and sessions",
        "student-1": "User profile customisation (profiles, resumes)",
        "student-2": "Job posting management",
        "student-3": "Job application management",
        "student-4": "Interview scheduling and coordination",
        "student-5": "Candidate evaluation",
    },
    "checks": [
        "GET /health (shared-api)",
        "GET /health (shared-db)",
        "GET /users (shared-db)",
        "GET /health (student-1-backend)",
        "GET /health (student-1-db)",
    ],
}


# --- ACT / validation helpers ------------------------------------------------

def _get(url):
    """Return (json_or_none, error_or_none) for a GET request."""
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return None, f"{url} returned HTTP {resp.status_code}"
        try:
            return resp.json(), None
        except ValueError:
            return resp.text, None
    except requests.RequestException as exc:
        return None, f"{url} unreachable ({exc})"


def validate_user(user):
    """Deterministic checks for a single shared user record."""
    if not isinstance(user.get("user_id"), int):
        return False, "user_id must be an integer"
    if not user.get("user_email"):
        return False, "user_email is required"
    if user.get("user_role") not in ("applicant", "staff"):
        return False, "user_role must be 'applicant' or 'staff'"
    return True, "ok"


# --- OBSERVE -----------------------------------------------------------------

def observe_service_health():
    """Ping the health endpoints of the core running services."""
    services = {
        "shared-api": f"{SHARED_API_URL}/health",
        "shared-db": f"{SHARED_DB_URL}/health",
        "student-1-backend": f"{STUDENT_1_API_URL}/health",
        "student-1-db": f"{STUDENT_1_DB_URL}/health",
    }

    healthy, down = [], []
    for name, url in services.items():
        _, err = _get(url)
        (down if err else healthy).append(name)

    if not healthy:
        return False, "No FIND services are reachable. Is docker-compose running?"

    msg = f"Healthy: {', '.join(healthy)}"
    if down:
        msg += f" | Not reachable: {', '.join(down)}"
    return True, msg


def observe_data_quality():
    """Validate the shared user seed data used across every FIND feature."""
    users, err = _get(f"{SHARED_DB_URL}/users")
    if err:
        return False, f"Could not read shared users ({err})"

    if len(users) != 10:
        return False, f"Expected 10 seed users, found {len(users)}"

    staff = [u for u in users if u.get("user_role") == "staff"]
    applicants = [u for u in users if u.get("user_role") == "applicant"]
    if len(staff) != 5 or len(applicants) != 5:
        return False, f"Expected 5 staff and 5 applicants, found {len(staff)} staff and {len(applicants)} applicants"

    for user in users:
        ok, reason = validate_user(user)
        if not ok:
            return False, reason

    return True, "Shared user data validation passed (10 users: 5 staff, 5 applicants)"


# --- ADAPT (local AI advice) -------------------------------------------------

def get_local_agent_advice(health_message, data_message):
    prompt = (
        "You are reviewing the integrated FIND recruitment platform.\n"
        "It is a Flask microservices application (shared auth + five student features):\n"
        "- Shared: users (user_id, user_email, user_role, first/last name), sessions.\n"
        "- Student 1: user profile customisation (profiles, resumes).\n"
        "- Student 2: job posting management.\n"
        "- Student 3: job application management.\n"
        "- Student 4: interview scheduling and coordination.\n"
        "- Student 5: candidate evaluation.\n\n"
        f"OBSERVE service health: {health_message}\n"
        f"OBSERVE data quality: {data_message}\n\n"
        "Rules:\n"
        "- Do not invent new database tables or fields.\n"
        "- Do not invent new services or endpoints.\n"
        "- Do not recommend functionality that already exists.\n"
        "- Recommend one small improvement to validation, error handling, "
        "response formatting, or testing.\n"
        "- Return exactly two bullet points."
    )

    try:
        client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
        response = client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a concise software engineering reviewer.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=220,
            temperature=0.2,
        )
        return response.choices[0].message.content.strip(), None
    except Exception as exc:  # noqa: BLE001 - loop must survive a missing runtime
        return None, f"Local AI agent unavailable ({exc})."


# --- Loop --------------------------------------------------------------------

def main():
    print("PLAN:", PLAN)

    print("ACT: Check FIND service health and shared data records")

    health_ok, health_msg = observe_service_health()
    print("OBSERVE (health):", health_msg)

    if health_ok:
        data_ok, data_msg = observe_data_quality()
    else:
        data_ok, data_msg = False, "Skipped: services not reachable"
    print("OBSERVE (data):", data_msg)

    if not (health_ok and data_ok):
        print("ADAPT: Start the stack (docker-compose up --build) and rerun validation")
    else:
        print("ADAPT: Proceed to feature-level endpoint checks")

    advice, advice_err = get_local_agent_advice(health_msg, data_msg)
    if advice:
        print("ADAPT (Local AI suggestion):")
        print(advice)
    else:
        print("ADAPT (Local AI suggestion):", advice_err)


if __name__ == "__main__":
    main()
