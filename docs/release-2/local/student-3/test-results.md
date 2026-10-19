# Local Integration Test Report - student-3

**Status:** COMPLETE
**Captured:** 2026-10-17T01:29:02.460904+00:00

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

Fixture: `release2-9f5798a139a7`. Backend: `http://localhost:16011`.

| Check | Captured operation or output | HTTP |
| --- | --- | --- |
| Create | `POST /api/applications/save`; new draft persisted | 200 |
| Read | `GET /api/context/applications/22/detail`; own fixture returned | 200 |
| Update | `PUT /api/applications/22/save`; declaration consent persisted | 200 |
| Delete | `DELETE /api/applications/22` | 200 |
| Verify deletion | `GET http://localhost:16012/applications/22`; record absent | 404 |
| AI-Mode | `/api/applications/22/screen`; populated feature-specific output and synthetic-input terms | 200 |
| MCP | `/mcp/applications-for-job`; explicit source citations | 200 |
| RAG | `/rag/retrieve`; nonempty retrieved chunks | 200 |
| Multi-Agent | `/multi-agent/workflow`; three agents, grounded evidence, no recorded fallback | 200 |

Captured workflow: `53662595-e711-45bd-b3dc-59e54c39b8fb`.