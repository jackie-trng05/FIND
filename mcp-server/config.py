"""Configuration for the shared, non-containerised FIND MCP server.

The MCP server runs as a local host process (NOT in docker-compose). It reaches
each student feature's database microservice through the service's host-mapped
port (the same canonical ports documented in the FIND README). Containerised
student backends reach this MCP server at ``http://host.docker.internal:16050``.

Every value can be overridden with an environment variable so the same module
works whether the server is started by a developer, by the agentic loop, or by
a student backend during local testing.
"""

import os
from pathlib import Path

# mcp-server/ lives at the FIND repository root.
BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent

# --- MCP server transport ------------------------------------------------
# Streamable-HTTP transport so containerised backends can reach the server at
# host.docker.internal:<MCP_PORT>. Bind to 0.0.0.0 so the Docker host gateway
# can route into the process.
MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_PORT", "16050"))

# --- Student database microservice locations -----------------------------
# The MCP server is a host process, so it talks to each database service via
# its host-mapped port (see README "Canonical Port Assignments").
DB_SERVICE_URLS: dict[str, str] = {
    "shared": os.getenv("SHARED_DB_URL", "http://localhost:16003"),
    "student-1": os.getenv("STUDENT_1_DB_URL", "http://localhost:16006"),
    "student-2": os.getenv("STUDENT_2_DB_URL", "http://localhost:16009"),
    "student-3": os.getenv("STUDENT_3_DB_URL", "http://localhost:16012"),
    "student-4": os.getenv("STUDENT_4_DB_URL", "http://localhost:16015"),
    "student-5": os.getenv("STUDENT_5_DB_URL", "http://localhost:16018"),
}

# --- Shared-tool paths ----------------------------------------------------
# ci_report reads a student's CI evidence JSON produced by the GitHub Actions
# "evidence-pack" job (reports/report.json at the repository root by default).
DEFAULT_CI_REPORT = os.getenv("CI_REPORT_PATH", str(REPO_ROOT / "reports" / "report.json"))

# HTTP timeout for outbound calls to database services (seconds).
REQUEST_TIMEOUT = int(os.getenv("MCP_REQUEST_TIMEOUT", "5"))


def db_url(feature: str) -> str:
    """Return the database service base URL for a feature key (e.g. 'student-2')."""
    return DB_SERVICE_URLS[feature]
