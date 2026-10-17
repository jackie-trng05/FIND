# Release 2 Local Deployment Report

Generated from captured evidence. PENDING means not demonstrated. Do not edit generated reports: record evidence and refresh instead. Source inspection and health checks are not proof of integrated functionality.

| Student | Recorded validation | Evidence |
| --- | --- | --- |
| student-1 | PENDING | [evidence](../local/student-1/evidence.json); captured 2026-10-17T01:29:01.948872+00:00; tested commit d261e6649ac3 (capture dirty=True) |
| student-2 | PENDING | [evidence](../local/student-2/evidence.json); captured 2026-10-17T01:29:02.206308+00:00; tested commit d261e6649ac3 (capture dirty=True) |
| student-3 | PENDING | [evidence](../local/student-3/evidence.json); captured 2026-10-17T01:29:02.460904+00:00; tested commit d261e6649ac3 (capture dirty=True) |
| student-4 | PENDING | [evidence](../local/student-4/evidence.json); captured 2026-10-17T01:29:02.676171+00:00; tested commit d261e6649ac3 (capture dirty=True) |
| student-5 | PENDING | [evidence](../local/student-5/evidence.json); captured 2026-10-17T01:29:02.912997+00:00; tested commit d261e6649ac3 (capture dirty=True) |

Required checks: frontend, create, read, update, delete, ai-mode, mcp, rag, multi-agent, human-review.

## Authenticated Backend Checks

| Student | Create | Read | Update | Delete | AI-Mode | MCP | RAG | Multi-Agent |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| student-1 | [PASS](../local/student-1/evidence.json) | [PASS](../local/student-1/evidence.json) | [PASS](../local/student-1/evidence.json) | [PASS](../local/student-1/evidence.json) | [PASS](../local/student-1/evidence.json) | [PASS](../local/student-1/evidence.json) | [PASS](../local/student-1/evidence.json) | [PASS](../local/student-1/evidence.json) |
| student-2 | [PASS](../local/student-2/evidence.json) | [PASS](../local/student-2/evidence.json) | [PASS](../local/student-2/evidence.json) | [PASS](../local/student-2/evidence.json) | [PASS](../local/student-2/evidence.json) | [PASS](../local/student-2/evidence.json) | [PASS](../local/student-2/evidence.json) | [PASS](../local/student-2/evidence.json) |
| student-3 | [PASS](../local/student-3/evidence.json) | [PASS](../local/student-3/evidence.json) | [PASS](../local/student-3/evidence.json) | [PASS](../local/student-3/evidence.json) | [PASS](../local/student-3/evidence.json) | [PASS](../local/student-3/evidence.json) | [PASS](../local/student-3/evidence.json) | [PASS](../local/student-3/evidence.json) |
| student-4 | [PASS](../local/student-4/evidence.json) | [PASS](../local/student-4/evidence.json) | [PASS](../local/student-4/evidence.json) | [PASS](../local/student-4/evidence.json) | [PASS](../local/student-4/evidence.json) | [PASS](../local/student-4/evidence.json) | [PASS](../local/student-4/evidence.json) | [PASS](../local/student-4/evidence.json) |
| student-5 | [PASS](../local/student-5/evidence.json) | [PASS](../local/student-5/evidence.json) | [PASS](../local/student-5/evidence.json) | [PASS](../local/student-5/evidence.json) | [PASS](../local/student-5/evidence.json) | [PASS](../local/student-5/evidence.json) | [PASS](../local/student-5/evidence.json) | [PASS](../local/student-5/evidence.json) |

Synthetic fixtures only. These checks exercise authenticated backends, not full browser CRUD. AI PASS means populated feature-specific output; it is not factual-quality approval. RAG PASS is grounded retrieval, not generated-answer evaluation. Multi-Agent PASS requires three agents, nonempty evidence and no recorded model fallback; no human decisions are submitted.

Browser-shell evidence (not full frontend interaction): CAPTURED | [evidence](evidence/group-evidence.json); captured 2026-10-17T01:35:12.346629+00:00; tested commit d261e6649ac3 (capture dirty=True).

Local image build transcript: CAPTURED | [evidence](evidence/group-evidence.json); captured 2026-10-17T01:35:12.581606+00:00; tested commit d261e6649ac3 (capture dirty=True).

Retain multi-terminal logs, frontend workflow evidence and shared AI service integration evidence.

Latest automatic Docker service snapshot: CAPTURED | [evidence](evidence/group-evidence.json); captured 2026-10-17T01:23:29.345773+00:00; tested commit d261e6649ac3 (capture dirty=True).

