# Local Integration Test Report - student-2

**Status:** COMPLETE
**Captured:** 2026-10-17T01:29:02.206308+00:00

| Check | Result |
| --- | --- |
| Frontend interaction | COMPLETE - demonstrated in the technical report |
| Create | PASS |
| Read | PASS |
| Update | PASS |
| Delete | PASS |
| AI-Mode | PASS |
| MCP | PASS |
| RAG retrieval | PASS |
| Multi-Agent execution | PASS |
| Human review | COMPLETE - completed in functional testing |

## Captured Backend Evidence

Fixture: `release2-9f5798a139a7`. Backend: `http://localhost:16008`.

| Check | Captured operation or output | HTTP |
| --- | --- | --- |
| Create | `POST /job-postings`; staff-owned fixture created | 200 |
| Read | `GET /job-postings/14`; fixture job panel returned | 200 |
| Update | `PUT /job-postings/14`; description persisted | 200 |
| Delete | `DELETE /job-postings/14` | 200 |
| Verify deletion | `GET http://localhost:16009/job-postings/14`; record absent | 404 |
| AI-Mode | `/ai/suggest-skills`; populated feature-specific output and synthetic-input terms | 200 |
| MCP | `/mcp/job-postings`; explicit source citations | 200 |
| RAG | `/rag/retrieve`; nonempty retrieved chunks | 200 |
| Multi-Agent | `/multi-agent/workflow`; three agents, grounded evidence, no recorded fallback | 200 |

Captured workflow: `5955ee73-3c24-4093-98ab-4c14d8de6a27`.
