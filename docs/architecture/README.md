# Architecture documentation (Release 0)

The integrated Release 0 microservices architecture consists of the shared services plus one
frontend/backend/database set per student, all orchestrated locally by `docker-compose.yml`.

Shared microservices (team-owned)

- Main UI (host port 16001 → container port 3000) — shared navigation, login/register, and the
  unified dashboard that links out to every student's frontend
- Shared Access API (host port 16002 → container port 5000) — centralised authentication
  (`/api/auth/register`, `/login`, `/session`, `/user`, `/logout`) plus the shared AI-Mode `/ask`
  and `/ask-with-context` endpoints (mounted from `ai-services/ai-mode`)
- Shared Access Database (host port 16003 → container port 6000) — owns the `users` and
  `sessions` tables backing shared-api

Student microservices (all five implemented)

| Student | Feature | Frontend | Backend/API | Database |
| --- | --- | --- | --- | --- |
| 1 | Profile management | 16004 → 3000 | 16005 → 5001 | 16006 → 6001 |
| 2 | Job posting management | 16007 → 3002 | 16008 → 5002 | 16009 → 6002 |
| 3 | Application management | 16010 → 3003 | 16011 → 5003 | 16012 → 6003 |
| 4 | Interview scheduling | 16013 → 3004 | 16014 → 5004 | 16015 → 6004 |
| 5 | Candidate evaluation | 16016 → 3005 | 16017 → 5005 | 16018 → 6005 |

Each student's Database service owns a dedicated schema/table set for their own feature.

AI-Mode

- Every backend implements its
  own AI-Mode endpoint against a locally running Ollama instance
  (`http://host.docker.internal:11434`), using either `qwen2.5:0.5b` or `llama3.1:8b` depending on
  the feature. shared-api additionally hosts a generic `/ask` / `/ask-with-context` assistant used
  by the dashboard's AI Assistant panel.
- This satisfies the Release 0 requirement for a Frontend → Backend/API → Ollama → LLM workflow;
  MCP, RAG, and Multi-Agent integration are Release 1/2 scope.

Important note for browser access

- The browser must connect to the host-mapped ports shown above (for example, 16001 and 16004). The container-internal ports such as 3000 and 5001 are not the publicly reachable URLs from the host machine.
- If `localhost` resolves unexpectedly in Docker Desktop on Windows, use `127.0.0.1` instead for the same host ports.

Notes

- Cross-service data access must go through the exposed Database APIs.
- Docker Compose is expected to orchestrate all services for local integration testing.

## Cross-service calling convention and trust boundary

When one student's feature needs data owned by another student, the call goes
**frontend → own backend → other student's Database API**, calling the other
student's raw DB service directly rather than routing through that student's
authenticated backend. This is the pattern used consistently across the repo:

- student-2's backend → student-3-db (`APPLICATIONS_DB_URL`)
- student-3's backend → student-1-db (`STUDENT_1_DB_URL`)
- student-4's backend → student-3-db (`APPLICATIONS_DB_URL`)
- student-5's backend → student-3-db and student-4-db

Each Database API service performs **no authentication or authorization** —
it trusts its caller completely. This is a deliberate choice, not an oversight:
Database services are only reachable over the internal Docker network
(`find-network`) from other containers, never exposed directly to end users.
The host port mappings in `docker-compose.yml` are a local-dev convenience for
inspecting/debugging each DB in isolation, not a production access path.

The **actual trust boundary is each student's own backend**. Whichever
backend a request enters through is responsible for:
1. Validating the caller's session (via the shared-api `/api/auth/session`
   check), and
2. Enforcing ownership/role checks (e.g. "does this resume belong to this
   user's profile?", "is this caller staff?") **before** it reads/writes
   another student's DB.

Concretely, when student-3's backend fetches or uploads a resume that lives in
student-1's database, student-3 re-implements the ownership check locally
(see `_get_student1_profile*`/`get_resume_metadata` in
`student-3/backend/app.py`) rather than delegating that check to student-1's
backend. Student-1's own backend additionally exposes fully authenticated
resume endpoints for its own frontend/UI use; those are not currently called
by other students, but remain available if the team later decides to route
cross-service calls through authenticated backends instead of raw DBs.

This repository's Release 0 implementation covers all five students' frontend/backend/database
sets plus the shared services described above. Diagrams and per-release architecture updates
should continue to be added here as Release 1 (MCP, RAG) and Release 2 (Multi-Agent, cloud
deployment) extend this baseline.
