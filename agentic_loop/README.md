# agentic_loop

This directory holds a dev-side review tool ([main.py](main.py) / [agentic_loop.py](agentic_loop.py))
that runs deterministic evidence collectors ([collectors/](collectors/)) against the running
Docker stack and asks a local Ollama model to critique the result
([core/orchestrator.py](core/orchestrator.py), [core/ai_runner.py](core/ai_runner.py)).

It is **not** the same thing as the product-facing AI feature — that's
[`ai-services/ai-mode`](../ai-services/ai-mode/), which powers the "Ask AI" buttons wired into
the shared dashboard (`/ask`, `/ask-with-context`).

## Requirement coverage vs. the project spec (section 4)

Y = implemented in this repo today. N = not implemented. Partial = some code exists but does
not fully satisfy the requirement.

| Release | Requirement | Implemented | Where / Notes |
|---|---|---|---|
| Release 0 | AI-mode (Frontend → Backend/API → Ollama → LLM) | Y | [ai-services/ai-mode/routes.py](../ai-services/ai-mode/routes.py) registered on shared-api ([shared/backend/app.py](../shared/backend/app.py)); called from the dashboard's "Ask AI" buttons ([shared/frontend/templates/dashboard.html](../shared/frontend/templates/dashboard.html)) |
| Release 0 | Ollama runtime | Y | `OLLAMA_BASE_URL` configured per service in [docker-compose.yml](../docker-compose.yml) (`host.docker.internal:11434`) |
| Release 0 | Approved open-source LLM(s) (Qwen/Llama/DeepSeek) | Y | `qwen2.5:0.5b` (shared-api, student-1 agentic_loop) and `llama3.1:8b` (student-3) configured in docker-compose |
| All releases (spec's "Shared Team Agentic Loop" requirement, not tied to one release) | Plan → Act → Observe → Adapt "shall be implemented by the integrated team application" | Y (Release 0 baseline) | What "meeting the loop" requires at each stage, in plain English:<br>• **Release 0** — a user asks a question, the app sends it to a local LLM via Ollama, and displays the answer back. That single round trip counts as Plan → Act → Observe → Adapt; no dedicated planning or self-correcting code is required yet.<br>• **Release 1** — the same loop, but Act/Observe must be grounded in real retrieved information: an MCP server exposes tools/data and a RAG server retrieves relevant context, so answers are backed by that retrieved evidence instead of a fixed block of prompt text.<br>• **Release 2** — Plan, Act, and Adapt move from the human to dedicated agents: a Planner Agent decides what to do, a Worker Agent carries it out, and a Reviewer Agent checks/adjusts the result, with a human review step layered on top — all coordinated by a Multi-Agent Server running locally. In the cloud deployment only the baseline AI-mode/Ollama/LLM pieces need to keep running; MCP, RAG, and the Multi-Agent System stay disabled there.<br><br>**Current status:** `/ask` and `/ask-with-context` satisfy the Release 0 version described above (Plan = user's question, Act = LLM call, Observe = rendered answer, Adapt = user's follow-up question). The app does not yet *autonomously* Plan or Adapt without a human — that's the Release 2 Planner/Reviewer work, not a Release 0 gap. |
| Release 1 | MCP server | N | [ai-services/mcp-server/README.md](../ai-services/mcp-server/README.md) is a placeholder only |
| Release 1 | RAG server | N | [ai-services/rag-server/README.md](../ai-services/rag-server/README.md) is a placeholder only |
| Release 1 | Grounded AI responses using retrieved context | N | `/ask-with-context` injects a static, hand-written [context_prompt.txt](../ai-services/ai-mode/prompts/implementation/context_prompt.txt) — no retrieval pipeline exists yet |
| Release 2 (local) | Multi-Agent Server | N | [ai-services/multi-agent-server/README.md](../ai-services/multi-agent-server/README.md) is a placeholder only |
| Release 2 (local) | Planner Agent | N | No planning step exists; mode selection in `main.py` is manual |
| Release 2 (local) | Worker Agent | Partial | `agentic_loop`'s "implementation" LLM call performs an Act-like step, but only within this dev tool, not as a product-level Worker Agent |
| Release 2 (local) | Reviewer Agent | Partial | The architecture pipeline's second LLM call self-critiques the first call's output using the same evidence — not an independent reviewer agent |
| Release 2 (local) | Human review | Y | Currently the *only* review/adapt mechanism — a human reads the printed output and decides the next action |
| Release 2 (cloud) | AI-Mode / Ollama / approved LLM(s) deployed to cloud | N | No cloud deployment configuration exists yet |
| Release 2 (cloud) | MCP/RAG/Multi-Agent explicitly disabled in cloud | N/A | Not applicable until cloud deployment exists |

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

