# FIND shared MCP server (streamable-HTTP transport, default port 16050).
#
# Built from the repository root context so the two shared tools can read repo
# evidence they expose: project_files (repo file index) and ci_report
# (docs/release-0/reports/**). config.REPO_ROOT resolves to /app (the parent of
# /app/mcp-server), so the repo evidence is copied alongside the server package.
FROM python:3.11-slim

WORKDIR /app/mcp-server

COPY mcp-server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mcp-server/ .

# Repo evidence read by the shared tools (resolved relative to REPO_ROOT=/app).
COPY docs/ /app/docs/
COPY README.md /app/README.md

EXPOSE 16050

CMD ["python", "server.py"]
