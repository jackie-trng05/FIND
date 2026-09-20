# FIND — Shared MCP Server (non-containerised)

**One** shared MCP server used by **all five** student features. It runs as a
**local host process** over the **streamable-HTTP** transport on a fixed port
(default **16050**) and exposes controlled retrieval tools that ground AI-Mode
answers with source citations and a confidence category.

> This server is **not** part of `docker-compose.yml`. The Release 0
> containerised feature microservices keep running unchanged; AI-Mode, this MCP
> server, and the agentic loop stay local host processes.

## Address

| Consumer | URL |
| --- | --- |
| Host / agentic loop | `http://localhost:16050/mcp` |
| Containerised student backend | `http://host.docker.internal:16050/mcp` |

Override with `MCP_HOST` / `MCP_PORT` if needed.

## Tools

### Shared (Step 1 — available to every feature)

| Tool | Purpose | Input | Output |
| --- | --- | --- | --- |
| `project_files` | List repository files/folders | `directory_path` (repo-relative) | retrieval context (`entries`) |
| `ci_report` | Read a student's CI evidence JSON | `report_path` (optional) | retrieval context (report JSON) |

### Per-student retrieval tools (Step 2)

Registered via `register_student_tools()` in `server.py`. One tool per domain:
`applicant_profile`, `job_postings`, `applications_for_job`,
`interview_details`, `evaluation_scores`.

## Retrieval context contract (RAG)

Every tool returns the shared shape built by `retrieval.build_context`:

```json
{
  "answer_data": { "...": "tool result" },
  "sources": [ { "table": "...", "record_id": "...", "field": "..." } ],
  "confidence": "High | Medium | Low"
}
```

Confidence rule: **High** = exact record match · **Medium** = partial/filtered
match · **Low** = empty result / fallback.

## Run

```powershell
cd mcp-server
pip install -r requirements.txt   # installs mcp<2 (FastMCP) + requests
python server.py
```

Expected:

```
Starting FIND MCP Server (shared, non-containerised)...
Transport: streamable-http  Address: 0.0.0.0:16050
Server status: RUNNING
Available tools:
- project_files
- ci_report
```

## Test the tools directly

```powershell
cd mcp-server
python tools.py
```

Prints the `project_files` and `ci_report` retrieval-context objects.
