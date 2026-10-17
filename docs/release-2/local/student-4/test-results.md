# Local Integration Test Report - student-4

**Status:** PENDING
**Captured:** 2026-10-17T01:29:02.676171+00:00
**Source commit:** d261e6649ac39c6308d0442c0c5df9f909e310d1

| Check | Result | Evidence detail |
| --- | --- | --- |
| frontend | PENDING | See execution record |
| create | PASS | See execution record |
| read | PASS | See execution record |
| update | PASS | See execution record |
| delete | PASS | See execution record |
| ai-mode | PASS | Expected populated AI fields and synthetic-input terms returned; not human quality approval |
| mcp | PASS | Backend MCP context returned explicit source citations |
| rag | PASS | Nonempty retrieved chunks returned through backend |
| multi-agent | PASS | Three agents and grounded evidence recorded; human decision remains pending |
| human-review | PENDING | See execution record |

See [evidence.json](evidence.json) for the original execution records, synthetic AI responses and provenance. These are authenticated backend checks, not full frontend CRUD or human approval. RAG validates retrieval, not generated-answer quality. Multi-Agent runs do not submit human decisions.

Pre-commit evidence: [canonical report](../../pre-commit/pre-commit-results-student4.md). Post-commit CI: [canonical results](../../post-commit/student-4/test-results.md) and [audit](../../post-commit/student-4/test-audit.jsonl).
