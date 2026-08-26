# Architecture documentation (setup / boilerplate)

The sample integrated microservices architecture (Release 0) defines the following minimal services for the setup/boilerplate validation:

Shared microservices (team-owned)
- Main UI (host port 16001 → container port 3000) — shared navigation and entry point for the integrated app
- Shared Access API (host port 16002 → container port 5000) — centralized access and authentication APIs (minimal placeholder during setup)
- Shared Access Database API (host port 16003 → container port 6000) — shared DB access API placeholder

Student microservices (example: Student 1)
- Frontend (host port 16004 → container port 3000)
- Backend/API (host port 16005 → container port 5001)
- Database API (host port 16006 → container port 6001) — owns a dedicated schema for Student 1 (placeholder)

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

This repository contains minimal placeholders for the shared microservices and Student 1 to validate the architecture and setup. Update this document with diagrams and exact service contracts as the setup progresses.
