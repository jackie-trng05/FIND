# Release 2 Local Deployment Report

The integrated FIND application operates locally with the Release 2
**non-containerised Multi-Agent Server**. The server runs as a local host
process (`multi-agent-server/app.py`, port `16080`); the containerised FIND
platform reaches it at `host.docker.internal:16080`. Evidence below is the real
captured output of multi-server system testing across multiple terminals, for
**all five student features**.

- Captured: 2026-10-17 (AEST)
- Commit: `0d18bb3`
- Models: Planner/Worker `qwen2.5:0.5b`, Reviewer `llama3.1:8b` (Ollama host process)
- Evidence domains (shared server): `profile`→student-1 db, `applications`→student-3 db, `interview`→student-4 db

## Terminal A — non-containerised Multi-Agent Server (port 16080)

Started with `cd multi-agent-server; python app.py`. It is **not** a container —
it listens directly on the host (PID 8224 on `0.0.0.0:16080`).

```text
# health check
{"status": "ok", "service": "multi-agent-server"}

# process listening on 16080
LocalAddress   LocalPort   State    OwningProcess
0.0.0.0        16080       Listen   8224
```

Full log: [`logs/terminal-a-multi-agent-server.log`](logs/terminal-a-multi-agent-server.log)

## Terminal B — integrated FIND platform (containers)

`docker compose ps` — all shared + per-student services up (frontend/backend/db
for students 1–5 plus shared-api/db/frontend).

```text
NAME                     SERVICE             PORTS                     STATUS
find-shared-api          shared-api          0.0.0.0:16002->5000/tcp   Up
find-student-1-backend   student-1-backend   0.0.0.0:16005->5001/tcp   Up
find-student-2-backend   student-2-backend   0.0.0.0:16008->5002/tcp   Up
find-student-3-backend   student-3-backend   0.0.0.0:16011->5003/tcp   Up
find-student-4-backend   student-4-backend   0.0.0.0:16014->5004/tcp   Up
find-student-5-backend   student-5-backend   0.0.0.0:16017->5005/tcp   Up
(all frontends/dbs + shared-db/frontend Up — see full log)
```

Full log: [`logs/terminal-b-docker-compose.log`](logs/terminal-b-docker-compose.log)

## Terminal C — multi-server system test (all students)

Each containerised student backend drives the non-containerised Multi-Agent
Server, which runs a grounded Planner → Worker → Reviewer workflow over real DB
records (nothing invented), leaving the human decision pending.

| Caller | Backend | Multi-Agent | Domain | Agents | Grounded evidence | Reviewer | Human decision | Duration |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| student-1 | :16005 | enabled | profile | 3 | 1 record | llama3.1:8b | pending | 4.8s |
| student-2 | :16008 | enabled | applications | 3 | 2 records | llama3.1:8b | pending | 4.3s |
| student-3 | :16011 | enabled | applications | 3 | 2 records | llama3.1:8b | pending | 2.5s |
| student-4 | :16014 | enabled | interview | 3 | 1 record | llama3.1:8b | pending | 3.3s |
| student-5 | :16017 | enabled | applications | 3 | 2 records | llama3.1:8b | pending | 2.9s |

Per-student full logs (backend `/multi-agent/status` + full workflow JSON):

- [`logs/terminal-c-student-1-workflow.log`](logs/terminal-c-student-1-workflow.log)
- [`logs/terminal-c-student-2-workflow.log`](logs/terminal-c-student-2-workflow.log)
- [`logs/terminal-c-student-3-workflow.log`](logs/terminal-c-student-3-workflow.log)
- [`logs/terminal-c-student-4-workflow.log`](logs/terminal-c-student-4-workflow.log)
- [`logs/terminal-c-student-5-workflow.log`](logs/terminal-c-student-5-workflow.log)

## Result

The integrated application runs locally end-to-end for every feature: each
containerised student backend (Terminal B) calls the non-containerised
Multi-Agent Server (Terminal A), which returns a three-agent, evidence-grounded,
human-review-pending result (Terminal C). Every run is persisted to
`workflow_history.jsonl` / `coordination_audit.jsonl`.
