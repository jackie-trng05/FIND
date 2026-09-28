"""Collect structural evidence for the shared FIND MCP server."""

from pathlib import Path

from collectors.feature_integration_collector import collect_feature_matrix


REQUIRED_TOOLS = (
    "project_files",
    "ci_report",
    "applicant_profile",
    "job_postings",
    "applications_for_job",
    "interview_details",
    "evaluation_scores",
)


def collect(app_dir: Path, repo_root: Path) -> tuple[bool, str]:
    server_dir = app_dir / "mcp-server"
    required_paths = (server_dir / "server.py", server_dir / "tools.py", server_dir / "requirements.txt")
    missing = [str(path.relative_to(app_dir)) for path in required_paths if not path.exists()]
    if missing:
        return False, "MCP evidence incomplete. Missing: " + ", ".join(missing)

    server_text = (server_dir / "server.py").read_text(encoding="utf-8")
    tools_text = (server_dir / "tools.py").read_text(encoding="utf-8")
    missing_tools = [
        tool for tool in REQUIRED_TOOLS if tool not in server_text and tool not in tools_text
    ]
    if missing_tools:
        return False, "MCP implementation is missing tools: " + ", ".join(missing_tools)

    shared_evidence = (
        "MCP evidence: mcp-server contains server.py, tools.py, and requirements.txt; "
        f"{len(REQUIRED_TOOLS)} required shared and student retrieval tools are declared."
    )
    return True, f"{shared_evidence}\n\n{collect_feature_matrix(app_dir, repo_root, 'mcp')}"