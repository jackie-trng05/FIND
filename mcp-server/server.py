"""Shared FIND MCP server.

ONE MCP server is shared by all five student features. It runs over the
**streamable-HTTP** transport on a fixed port (default 16050).

It is deployed as a container (docker-compose service ``mcp-server``), where
student backends reach it at ``http://find-mcp-server:16050/mcp`` (and in the
cloud at the app's internal FQDN). When run instead as a local host process,
containerised backends reach it via ``http://host.docker.internal:16050/mcp``.

Step 1 registers the two shared tools (project_files, ci_report). Per-student
retrieval tools are registered in Step 2 via ``register_student_tools``.
"""

import config
import tools
from mcp.server.fastmcp import FastMCP

AVAILABLE_TOOLS = [
    "project_files",
    "ci_report",
    "applicant_profile",
    "applications_for_job",
    "job_postings",
    "interview_details",
    "evaluation_scores",
]

mcp = FastMCP("FIND MCP", host=config.MCP_HOST, port=config.MCP_PORT)


# --- Shared tools --------------------------------------------------------
@mcp.tool()
def project_files(directory_path: str = ".") -> dict:
    """List repository files/folders under a repo-relative directory."""
    return tools.list_project_files(directory_path)


@mcp.tool()
def ci_report(report_path: str = "") -> dict:
    """Read a student's CI evidence JSON (defaults to reports/report.json)."""
    return tools.read_ci_report(report_path or None)


# --- Per-student retrieval tools (Step 2) --------------------------------
def register_student_tools(server: FastMCP) -> None:
    """Register each student feature's retrieval tool.

    One tool per student domain. Kept as an explicit extension point so students
    self-register their tool (under ``students/``) without touching the shared
    server wiring above.
    """
    from students import student_1, student_2, student_3, student_4, student_5

    student_1.register(server)
    student_2.register(server)
    student_3.register(server)
    student_4.register(server)
    student_5.register(server)


register_student_tools(mcp)


if __name__ == "__main__":
    print("Starting FIND MCP Server (shared)...")
    print(f"Transport: streamable-http  Address: {config.MCP_HOST}:{config.MCP_PORT}")
    print("Server status: RUNNING")
    print("Available tools:")
    for tool_name in AVAILABLE_TOOLS:
        print(f"- {tool_name}")
    mcp.run(transport="streamable-http")
