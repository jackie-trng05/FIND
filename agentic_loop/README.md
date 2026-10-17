# agentic_loop

This directory holds a dev-side review tool ([main.py](main.py) / [agentic_loop.py](agentic_loop.py))
that runs deterministic evidence collectors ([collectors/](collectors/)) against the running
Docker stack and asks a local Ollama model to critique the result
([core/orchestrator.py](core/orchestrator.py), [core/ai_runner.py](core/ai_runner.py)).

It is **not** the same thing as a product-facing AI feature. AI integrations are owned by their
feature backends; Student 1's profile suggestions are implemented in
[student-1/backend/routes/ai_mode.py](../student-1/backend/routes/ai_mode.py) and use Ollama
through [student-1/backend/services/llm_client.py](../student-1/backend/services/llm_client.py).

## Requirement coverage vs. the project spec (section 4)

Y = implemented in this repo today. N = not implemented. Partial = some code exists but does
not fully satisfy the requirement.

| Release | Requirement | Implemented | Where / Notes |
|---|---|---|---|
| Release 0 | Student 1 profile AI-mode (Frontend → Backend/API → Ollama → LLM) | Y | [ai_mode.py](../student-1/backend/routes/ai_mode.py) calls Ollama through the Student 1 backend; [shared/backend/app.py](../shared/backend/app.py) remains authentication-only |
| Release 0 | Ollama runtime | Y | Student feature backends configure `OLLAMA_BASE_URL` and `OLLAMA_MODEL` in [docker-compose.yml](../docker-compose.yml) |
| Release 0 | Approved open-source LLM(s) (Qwen/Llama/DeepSeek) | Y | All students are using `llama3.1:8b` or `qwen2.5:0.5b`|
| All releases (spec's "Shared Team Agentic Loop" requirement, not tied to one release) | Plan → Act → Observe → Adapt "shall be implemented by the integrated team application" | Y (Release 1 baseline) | Release 1 adds retrieval; Release 2 adds dedicated planner, worker, and reviewer agents. |
| Release 1 | MCP server | Y | Shared local MCP server validated by the MCP review mode |
| Release 1 | RAG server | Y | Shared local RAG server validated by the RAG review mode |
| Release 1 | Grounded AI responses using retrieved context | Y | RAG review validates retrieval, citations, confidence, and unsupported-answer controls |
| Release 2 (local) | Multi-Agent Server | Y | Shared [multi-agent-server/](../multi-agent-server/) validated by the new **Multi-Agent** review mode |
| Release 2 (local) | Planner Agent | Y | [planner_agent.py](../multi-agent-server/agents/planner_agent.py) (`plan_workflow`); wiring checked by the Multi-Agent review mode |
| Release 2 (local) | Worker Agent | Y | [worker_agent.py](../multi-agent-server/agents/worker_agent.py) (`generate_output`) grounds output in real FIND DB records |
| Release 2 (local) | Reviewer Agent | Y | [reviewer_agent.py](../multi-agent-server/agents/reviewer_agent.py) (`review_output`) is an independent reviewer sequenced after planner + worker |
| Release 2 (local) | Human review | Y | A human reads the printed output and decides the next action; the multi-agent workflow adds an explicit Accept / Correction / Reject gate |
| Release 2 | Testing and deployment evidence reviews | Partial | Multi-Agent, pre-test, CI/CD and deployment menu modes consume captured report evidence and save real model transcripts. Missing evidence remains pending; see the [Release 2 runbook](../docs/release-2/reports/README.md). |
| Release 2 (cloud) | AI-Mode/MCP/RAG/Multi-Agent disabled by default | Pending deployment evidence | The required baseline disables all four services. Cloud AI hosting is optional bonus work, not a baseline requirement. |

## Release 2 Reports

Follow the [report runbook](../docs/release-2/reports/README.md) to capture scans,
import each student's CI artifact, record deployment validation, snapshot workflow
history and make a human release decision. The Release 2 menu uses the same shared
report implementation as `python shared/release2_reports.py review --mode ...`.
It reviews actual artifact content and persists OBSERVE/IMPLEMENTATION/REVIEW logs.
Legacy structural collectors remain available in source but are not sufficient
evidence of runtime success. A completed model call is not a passing assessment.

## Running the review tool

Install the tool's own dependencies first (separate from any per-service
`requirements.txt` — this is a repo-root dev tool, not a container):

```bash
pip install -r requirements.txt   # openai, python-dotenv, requests (repo root)
```

Then start the stack and run the loop:

```bash
docker compose up --build   # start the stack first
python agentic_loop/agentic_loop.py
```

If you see `ModuleNotFoundError: No module named 'openai'`, the root
`requirements.txt` above hasn't been installed for whichever Python interpreter
you're running the script with.

