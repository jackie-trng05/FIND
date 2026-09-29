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


def summarize_feature_matrix(evidence: str, mode: str) -> str:
    """Return the source-tree verdict, independent of model-generated summaries."""
    variable = "MCP" if mode == "mcp" else "RAG"
    rows = {
        student: line
        for line in evidence.splitlines()
        for student in STUDENTS
        if line.startswith(f"- {student}:")
    }
    missing_rows = [student for student in STUDENTS if student not in rows]
    incomplete = {
        student: re.findall(r"([a-z_]+)=MISSING", rows[student])
        for student in STUDENTS
        if student in rows and "=MISSING" in rows[student]
    }

    if missing_rows:
        incomplete.update({student: ["student row missing"] for student in missing_rows})
    if incomplete:
        details = "; ".join(
            f"{student}: {', '.join(requirements)}"
            for student, requirements in incomplete.items()
        )
        return f"{variable} source-tree validation INCOMPLETE. {details}."
    return (
        f"{variable} source-tree validation PASS: all five students meet the "
        "frontend wiring, backend route/client, and CI-disablement checks."
    )