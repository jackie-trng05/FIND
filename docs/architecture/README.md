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

This repository contains minimal placeholders for the shared microservices and Student 1 to validate the architecture and setup. Update this document with diagrams and exact service contracts as the setup progresses.
