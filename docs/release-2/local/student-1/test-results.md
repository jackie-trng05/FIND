# Local Integration Test Report - student-1

**Status:** COMPLETE
**Captured:** 2026-10-17T01:29:01.948872+00:00

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

Fixture: `release2-9f5798a139a7`. Backend: `http://localhost:16005`.

| Check | Captured operation or output | HTTP |
| --- | --- | --- |
| Create | `POST /profile`; synthetic profile persisted | 200 |
| Read | `GET /profile`; fixture profile returned | 200 |
| Update | `PUT /profile/12`; new location persisted | 200 |
| Delete | `DELETE /profile/12` | 200 |
| Verify deletion | `GET http://localhost:16006/profiles/12`; record absent | 404 |
| AI-Mode | `/profile/ai-suggestions`; populated feature-specific output and synthetic-input terms | 200 |
| MCP | `/mcp/applicant-profile`; explicit source citations | 200 |
| RAG | `/rag/retrieve`; nonempty retrieved chunks | 200 |
| Multi-Agent | `/multi-agent/workflow`; three agents, grounded evidence, no recorded fallback | 200 |

Captured workflow: `210f9c15-0455-472b-b505-fa223ac26b16`.