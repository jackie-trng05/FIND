# RAG Validation Report (shared)

Shared across all five FIND student features. The agentic loop (RAG mode) prints
its result to the console but does not write any file — paste the exact
OBSERVE / IMPLEMENTATION / REVIEW text from your run below.

Command:

```bash
cd agentic_loop
python main.py     # choose the RAG option
```

Run context: Ollama up with `qwen2.5:0.5b` (implementation) and `llama3.1:8b`
(review); RAG corpus freshly rebuilt (178 chunks, see rag-report.md). The loop
prints to the console only — the exact output is pasted below.

## Evidence collected (OBSERVE)

Deterministic evidence from `rag_collector.collect()` (no LLM) — this is the
ground truth the agents reason over:

```text
OBSERVE: RAG evidence: rag-server contains the pipeline, MCP server, HTTP server, and requirements; 3 required tools are defined (refresh_corpus, retrieve_context, answer_question).

Per-student RAG Release 1 requirement matrix:
- student-1: frontend_request_wiring=PASS, backend_route=PASS, ci_mode_disabled=PASS.
- student-2: frontend_request_wiring=PASS, backend_route=PASS, ci_mode_disabled=PASS.
- student-3: frontend_request_wiring=PASS, backend_route=PASS, ci_mode_disabled=PASS.
- student-4: frontend_request_wiring=PASS, backend_route=PASS, ci_mode_disabled=PASS.
- student-5: frontend_request_wiring=PASS, backend_route=PASS, ci_mode_disabled=PASS.
A MISSING item means the source tree does not demonstrate that Release 1 integration requirement. Run the lab's browser and curl workflow separately to prove live interactions.
```

**All five students PASS on all three checks** (frontend request wiring, backend
route/client, CI mode-disabled flag) and the three required RAG tools
(`refresh_corpus`, `retrieve_context`, `answer_question`) are present.

## Implementation agent assessment (qwen2.5:0.5b)

```text
IMPLEMENTATION: Strengths: The FIND RAG integration meets all the specified requirements. Risks: The missing evidence includes a missing item in the student's row. Retest: The missing item should be filled with the actual evidence from the student's row.
```

## Review agent assessment (llama3.1:8b, review + reasoning prompts)

```text
REVIEW: Based on the provided evidence, the RAG validation quality is as follows: **Missing Evidence:** * Student-1: frontend_request_wiring=PASS, backend_route=PASS, ci_mode_disabled=PASS (no missing items) * Student-2: frontend_request_wiring=PASS, backend_route=PASS, ci_mode_disabled=PASS (no missing items) * Student-3: frontend_request_wiring=PASS, backend_route=PASS, ci_mode_disabled=PASS (no missing items) * Student-4: frontend_request_wiring=PASS, backend_route=PASS, ci_mode_disabled=PASS (no missing items) * Student-5: frontend_request_wiring=PASS, backend_route=PASS, ci_mode_disabled=MISSING (missing item: ci_mode_disabled) **RAG Validation Quality:** * Risk: The RAG is not complete due to missing evidence in Student-5's row.
```

## Interpretation

The agents run on small local models, so their prose must be read against the
deterministic OBSERVE evidence, which is the authoritative signal:

- **Implementation agent (qwen2.5:0.5b)** correctly concludes the integration
  *"meets all the specified requirements"*; its vague "missing item" caveat is
  generic boilerplate not supported by any MISSING entry in the evidence.
- **Review agent (llama3.1:8b)** confirms students 1–4 have no missing items but
  then **hallucinates** `ci_mode_disabled=MISSING` for student-5. This directly
  contradicts the OBSERVE matrix, which records student-5 as
  `ci_mode_disabled=PASS`. It is a known small-model artifact (the review output
  is also truncated mid-sentence), **not** a real gap.

**Conclusion:** the ground-truth collector shows **all five students PASS all
three RAG integration checks** with the three required tools present. The RAG
integration is complete; the only "risk" raised was a model misread of
authoritative evidence, not an actual defect. Live browser/curl interaction is
still proven separately in [rag-report.md](rag-report.md).
