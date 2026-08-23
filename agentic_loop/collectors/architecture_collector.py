PLATFORM_SERVICES = ["shared-frontend", "shared-api", "shared-db"]


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

    return True, (
        f"Architecture evidence ({scope}): tiers present -> {', '.join(present_tiers)}; "
        f"docker-compose services -> {', '.join(compose_services) or 'none defined yet'}; "
        "identity is expected to come from the shared auth service."
    )


def collect(app_dir, repo_root, scope: str | None = None) -> tuple[bool, str]:
    compose_path = app_dir / "docker-compose.yml"
    if not compose_path.exists():
        return False, "Architecture evidence incomplete. Missing: docker-compose.yml"

    compose_text = compose_path.read_text(encoding="utf-8")

    if scope is None:
        return _collect_platform(app_dir, compose_text)
    return _collect_student(app_dir, compose_text, scope)
