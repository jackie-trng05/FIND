"""Collect structural evidence for the shared FIND multi-agent server."""

from pathlib import Path


# Each agent module must expose its required entry function.
REQUIRED_AGENT_FUNCTIONS = {
    "planner_agent.py": "plan_workflow",
    "worker_agent.py": "generate_output",
    "reviewer_agent.py": "review_output",
}


def _student_routes(app_dir: Path) -> list[str]:
    """Student backends that wire a Multi-Agent-Mode route to the shared server."""
    students: list[str] = []
    for child in sorted(app_dir.glob("student-*")):
        if (child / "backend" / "routes" / "multi_agent_mode.py").exists():
            students.append(child.name)
    return students


def collect(app_dir: Path, repo_root: Path) -> tuple[bool, str]:
    server_dir = app_dir / "multi-agent-server"
    agents_dir = server_dir / "agents"
    prompts_dir = app_dir / "agentic_loop" / "prompts" / "multi_agent"

    required_paths = [
        agents_dir / "planner_agent.py",
        agents_dir / "worker_agent.py",
        agents_dir / "reviewer_agent.py",
        server_dir / "coordinator.py",
        server_dir / "app.py",
        server_dir / "requirements.txt",
        prompts_dir / "implementation" / "multi_agent_implementation_prompt.txt",
        prompts_dir / "review" / "multi_agent_review_prompt.txt",
    ]

    missing = [str(path.relative_to(app_dir)) for path in required_paths if not path.exists()]
    if missing:
        return False, "Multi-agent evidence incomplete. Missing: " + ", ".join(missing)

    coordinator_text = (server_dir / "coordinator.py").read_text(encoding="utf-8")
    missing_calls = [
        func for func in REQUIRED_AGENT_FUNCTIONS.values() if func not in coordinator_text
    ]
    if missing_calls:
        return False, "coordinator.py missing calls to: " + ", ".join(missing_calls)

    student_routes = _student_routes(app_dir)
    if not student_routes:
        return False, (
            "No student backend wires a Multi-Agent-Mode route "
            "(expected at least one student-*/backend/routes/multi_agent_mode.py)."
        )

    return True, (
        "Multi-agent evidence: multi-agent-server/ contains planner_agent.py, worker_agent.py, "
        "reviewer_agent.py, coordinator.py, and app.py; coordinator wires plan_workflow, "
        "generate_output, and review_output into a single governed workflow "
        "(planner + worker, then reviewer, then human decision). "
        "UI integration present in: " + ", ".join(student_routes) + "."
    )
