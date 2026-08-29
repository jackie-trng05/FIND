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
| All releases (spec's "Shared Team Agentic Loop" requirement, not tied to one release) | Plan → Act → Observe → Adapt "shall be implemented by the integrated team application" | Y (Release 0 baseline) | Student 1's profile flow locates the profile and resume, calls Ollama, validates the parsed result, and retries when needed. Release 1 adds retrieval; Release 2 adds dedicated planner, worker, and reviewer agents. |
| Release 1 | MCP server | N | No MCP service is present in this repository |
| Release 1 | RAG server | N | No RAG service is present in this repository |
| Release 1 | Grounded AI responses using retrieved context | N | No MCP/RAG retrieval pipeline is present in this repository |
| Release 2 (local) | Multi-Agent Server | N | No multi-agent service is present in this repository |
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

