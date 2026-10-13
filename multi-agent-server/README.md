# FIND Multi-Agent Server (shared, non-containerised)

A shared three-agent coordination service for the FIND platform, modelled on
Lab 10. It is the multi-agent analogue of the shared **MCP server** (port 16050)
and **RAG server** (port 16070): a local host process reachable from every
student backend container at `http://host.docker.internal:16080`.

## Agents

| Agent | Model (default) | Role |
|-------|-----------------|------|
| Planner  | `qwen2.5:0.5b` (`OLLAMA_MODEL`) | Create a short, structured workflow plan |
| Worker   | `qwen2.5:0.5b` (`OLLAMA_MODEL`) | Retrieve DB evidence and generate grounded output |
| Reviewer | `llama3.1:8b` (`OLLAMA_REVIEW_MODEL`) | Assess risk, correction, retest, recommendation |
| Human    | — | Final decision: Accept / Correction / Reject |

The Worker grounds its output in **real application records** fetched over HTTP
from a FIND database service (`MULTI_AGENT_DB_URL`, default the student-3
application DB on `http://localhost:16012`). No evidence is ever invented.

## Endpoints

```
GET  /health            -> {"status": "ok", "service": "multi-agent-server"}
POST /workflow          -> {"user_request": "...", "caller": "student-3"}
GET  /workflow/status   -> history/audit counts + latest workflow
```

Every run is appended to `workflow_history.jsonl` (full record) and
`coordination_audit.jsonl` (compact audit line).

## Configuration (environment variables)

| Variable | Default | Purpose |
|----------|---------|---------|
| `MULTI_AGENT_HOST` | `0.0.0.0` | Bind host |
| `MULTI_AGENT_PORT` / `PORT` | `16080` | Bind port |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Ollama endpoint (host process) |
| `OLLAMA_MODEL` | `qwen2.5:0.5b` | Planner + Worker model |
| `OLLAMA_REVIEW_MODEL` | `llama3.1:8b` | Reviewer model |
| `MULTI_AGENT_DB_URL` | `http://localhost:16012` | Evidence database service (host port) |
| `AGENT_STEP_TIMEOUT_SECONDS` | `120` | Per-agent step timeout |
| `FAST_MODE` | `true` | Smaller max-token budgets for faster local runs |

> Tip: the Planner/Worker default to the tiny, fast `qwen2.5:0.5b`; the Reviewer
> uses `llama3.1:8b` for quality. Run `ollama list` to confirm both are pulled
> (`ollama pull qwen2.5:0.5b` / `ollama pull llama3.1:8b` if not).

## Run it

```bash
cd multi-agent-server
python -m pip install -r requirements.txt
python app.py        # -> Multi-Agent HTTP server running on 0.0.0.0:16080
```

Keep it running in its own terminal, then `docker compose up --build -d` the FIND
platform. The student-3 staff candidate profile page shows the **Multi-Agent
Orchestrator** panel that drives this server.

### Terminal smoke test

```bash
python agents/planner_agent.py
python agents/worker_agent.py      # needs the student-3 DB reachable on 16012
python agents/reviewer_agent.py
python workflow_runner.py

curl -X POST http://localhost:16080/workflow \
  -H "Content-Type: application/json" \
  -d '{"user_request":"Summarise the applications submitted for job posting 1.","caller":"student-3"}'
```
