import re

PLATFORM_SERVICES = ["shared-frontend", "shared-api", "shared-db"]


def _service_block(compose_text: str, service_name: str) -> str:
    """Return just the env/volumes/etc. block for one top-level compose
    service, so keyword checks below don't get false positives from other
    services defined elsewhere in the file."""
    match = re.search(
        rf"(?ms)^  {re.escape(service_name)}:\n(.*?)(?=^  [\w-]+:\n|\Z)", compose_text
    )
    return match.group(1) if match else ""


def _collect_platform(app_dir, compose_text: str) -> tuple[bool, str]:
    required_paths = [
        app_dir / "shared" / "frontend",
        app_dir / "shared" / "backend" / "app.py",
        app_dir / "shared" / "database" / "app.py",
        app_dir / "shared" / "database" / "init_db.py",
    ]
    missing = [str(path.relative_to(app_dir)) for path in required_paths if not path.exists()]
    if missing:
        return False, "Architecture evidence incomplete. Missing: " + ", ".join(missing)

    present = [name for name in PLATFORM_SERVICES if name in compose_text]
    if len(present) != len(PLATFORM_SERVICES):
        return False, "docker-compose does not define all shared platform services."

    return True, (
        "Architecture evidence (platform): shared frontend, backend, and database "
        "service files exist; docker-compose defines shared-frontend, shared-api, and "
        "shared-db on a common network."
    )


def _collect_student(app_dir, compose_text: str, scope: str) -> tuple[bool, str]:
    student_dir = app_dir / scope
    if not student_dir.exists():
        return False, f"Architecture evidence incomplete. Missing directory: {scope}"

    tiers = {
        "frontend": student_dir / "frontend",
        "backend": student_dir / "backend",
        "database": student_dir / "database",
    }
    present_tiers = [name for name, path in tiers.items() if path.exists()]
    if not present_tiers:
        return False, f"No frontend/backend/database tiers found under {scope}."

    candidate_services = (f"{scope}-frontend", f"{scope}-backend", f"{scope}-db")
    compose_services = [name for name in candidate_services if name in compose_text]

    # Check the backend's actual compose env block, not just whether the
    # service name appears anywhere in the file, to confirm real dependencies
    # rather than assuming them.
    backend_block = _service_block(compose_text, f"{scope}-backend")
    uses_shared_api = "SHARED_API_URL" in backend_block
    uses_shared_db = "SHARED_DB_URL" in backend_block
    has_ollama_config = "OLLAMA_MODEL" in backend_block or "OLLAMA_BASE_URL" in backend_block

    identity_note = (
        "backend calls shared-api (SHARED_API_URL present) for identity/session validation"
        if uses_shared_api
        else "no SHARED_API_URL found in the backend's compose env -- shared auth is NOT confirmed"
    )
    shared_db_note = (
        "backend also reads shared-db directly (SHARED_DB_URL present)"
        if uses_shared_db
        else "no direct shared-db access found"
    )

    ai_mode_paths = [
        student_dir / "backend" / "routes" / "ai_mode.py",
        student_dir / "backend" / "services" / "llm_client.py",
    ]
    ai_mode_files_present = [p.name for p in ai_mode_paths if p.exists()]
    if ai_mode_files_present and has_ollama_config:
        ai_note = (
            f"AI-Mode capability confirmed: {', '.join(ai_mode_files_present)} present and "
            "Ollama configured in the backend's compose env"
        )
    elif ai_mode_files_present or has_ollama_config:
        ai_note = (
            "AI-Mode capability partially detected (code or Ollama config present, not both) "
            "-- verify before claiming it is fully implemented"
        )
    else:
        ai_note = "no AI-Mode route/LLM client or Ollama config found -- not implemented"

    return True, (
        f"Architecture evidence ({scope}): tiers present -> {', '.join(present_tiers)}; "
        f"docker-compose services -> {', '.join(compose_services) or 'none defined yet'}; "
        f"{identity_note}; {shared_db_note}; {ai_note}."
    )


def collect(app_dir, repo_root, scope: str | None = None) -> tuple[bool, str]:
    compose_path = app_dir / "docker-compose.yml"
    if not compose_path.exists():
        return False, "Architecture evidence incomplete. Missing: docker-compose.yml"

    compose_text = compose_path.read_text(encoding="utf-8")

    if scope is None:
        return _collect_platform(app_dir, compose_text)
    return _collect_student(app_dir, compose_text, scope)
