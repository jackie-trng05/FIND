# FIND RAG Server (shared, non-containerised)

ONE local RAG server is shared by all five FIND student features. It extends the
existing shared local AI-Mode with **grounded RAG answers**: retrieved context,
source citations, and a confidence category.

Like the shared MCP server, the RAG server is **NOT part of docker-compose**. The
Release 0 containerised feature microservices keep running unchanged; the RAG
server runs as a local host process and is reached from the containers via
`http://host.docker.internal:16070`.

## Files

| File | Responsibility |
| --- | --- |
| `rag_pipeline.py` | Corpus build, chunking, embeddings, vector + lexical retrieval, grounded answering, audit logging |
| `rag_server.py` | MCP (stdio) server exposing the three RAG tools |
| `rag_http_server.py` | HTTP server (port 16070) the containerised backends call |
| `rag_eval.py` | P@5 / R@5 retrieval metrics → `retrieval-metrics.md` |
| `mcp-config.json` | MCP client launch config |
| `tool-contracts.md` | Tool input/output contracts and authority tiers |
| `corpus/corpus.jsonl` | Generated corpus (git-ignored) |
| `chroma/` | Generated ChromaDB vector store (git-ignored) |
| `rag-audit.jsonl` | Generated per-call audit log (git-ignored) |

## Tools

- `refresh_corpus(caller)` — rebuild corpus + vector index from FIND evidence.
- `retrieve_context(query, k)` — top-k grounded chunks.
- `answer_question(query, k)` — grounded answer + citations + confidence.

Corpus authority tiers: **tier_1** live database services + platform facts,
**tier_2** CI evidence reports, **tier_3** repository file index.

## Setup

```bash
cd rag-server
python -m pip install -r requirements.txt
```

ChromaDB is optional — if it is not installed, retrieval transparently falls back
to a deterministic lexical retriever so the server still runs offline.

## Run

```bash
# MCP (stdio) transport — for MCP clients / the agentic loop
python rag_server.py

# HTTP transport — for the containerised student backends (port 16070)
python rag_http_server.py
curl http://localhost:16070/health
```

## Terminal smoke test

```bash
python -c "from rag_pipeline import refresh_corpus; import json; print(json.dumps(refresh_corpus(), indent=2))"
python -c "from rag_pipeline import retrieve_context; import json; print(json.dumps(retrieve_context('student feature microservices', 5), indent=2))"
python -c "from rag_pipeline import answer_question; import json; print(json.dumps(answer_question('Which repository files make up the FIND platform?', 5), indent=2))"
python rag_eval.py
```

## CI/CD

AI-Mode and RAG are **disabled during CI/CD** — each student workflow sets
`AI_MODE_ENABLED`, `MCP_ENABLED`, and `RAG_ENABLED` to `"false"`, so the pipeline
never needs Ollama, the MCP server, or this RAG server.

## Wiring (Steps 2 & 3)

- **Step 2** — each student backend adds `services/rag_api.py` + `routes/rag_mode.py`
  and a frontend RAG tab, gated by `RAG_ENABLED`. The frontend always reaches the
  RAG server *through* its own backend (`/rag/refresh`, `/rag/retrieve`, `/rag/answer`).
- **Step 3** — the shared local agentic loop gains a RAG validation mode alongside
  the existing modes (RAG collector + pipeline + prompts).
