"""Shared structural checks for per-student MCP and RAG integration."""

import re
from pathlib import Path


STUDENTS = tuple(f"student-{number}" for number in range(1, 6))


def _read_tree(paths: tuple[Path, ...]) -> str:
    parts = []
    for root in paths:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in {".html", ".js", ".py"}:
                parts.append(path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(parts)


def collect_feature_matrix(app_dir: Path, repo_root: Path, mode: str) -> str:
    """Return a requirement matrix for frontend wiring, route/client files, and disabled CI mode."""
    variable = "MCP" if mode == "mcp" else "RAG"
    client_name = "mcp_client.py" if mode == "mcp" else "rag_api.py"

    lines = [f"Per-student {variable} Release 1 requirement matrix:"]
    for student in STUDENTS:
        student_root = app_dir / student
        backend = student_root / "backend"
        route = backend / "routes" / f"{mode}_mode.py"
        client = backend / "services" / client_name
        frontend_text = _read_tree((student_root / "frontend", backend / "views"))
        workflow = app_dir / ".github" / "workflows" / f"{student}-ci.yml"
        workflow_text = workflow.read_text(encoding="utf-8") if workflow.exists() else ""

        checks = {
            "frontend_request_wiring": (
                f"/{mode}/" in frontend_text
                and ("fetch(" in frontend_text or "hx-post=" in frontend_text)
            ),
            "backend_route": route.exists() and client.exists(),
            "ci_mode_disabled": bool(
                re.search(rf"{variable}_ENABLED:\s*[\"']?false[\"']?", workflow_text, re.IGNORECASE)
            ),
        }
        missing = [name for name, present in checks.items() if not present]
        status = ", ".join(
            f"{name}={'PASS' if present else 'MISSING'}" for name, present in checks.items()
        )
        lines.append(f"- {student}: {status}.")

    lines.append(
        "A MISSING item means the source tree does not demonstrate that Release 1 integration requirement. "
        "Run the lab's browser and curl workflow separately to prove live interactions."
    )
    return "\n".join(lines)