# FIND

## Project overview
At this stage, this repository contains the team-integrated FIND project boilerplate. It provides the shared frontend and student microservice scaffolding used for local development and integration testing.

## Setup instructions
- Install Docker Desktop (Windows/Mac) and ensure it is running before attempting to start the compose stack. Docker Desktop must be running so the Docker daemon is available for docker compose commands.
- Recommended: use Docker Desktop stable release that supports the Compose V2 command `docker compose`.

## Running the application locally
1. From the repository root run:
   - docker compose up --build
   This builds and starts the defined containers. Ensure Docker Desktop is running first.
2. To stop and remove containers, networks, and named volumes created by compose run:
   - docker compose down

## Quick links to running containers
Use the host ports below in the browser. Do not use the internal container ports such as 3000, 5000, or 5001 directly when browsing from the host machine.

- Shared frontend: http://localhost:16001/
- Shared API health: http://localhost:16002/health
- Shared DB placeholder: http://localhost:16003/
- Student 1 frontend: http://localhost:16004/
- Student 1 backend health: http://localhost:16005/health
- Student 1 DB placeholder: http://localhost:16006/

If `localhost` does not resolve correctly in your Docker/Windows setup, use `127.0.0.1` instead of `localhost` for the same URLs.

## Canonical local ports (host -> container)
This repository uses the high-number port scheme to avoid common low-port restrictions and browser unsafe-port issues. The canonical mapping is:
- 16001 — shared frontend (landing page) → container port 3000
- 16002 — shared API (health endpoint) → container port 5000
- 16003 — shared DB (placeholder) → container port 6000
- 16004 — student-1 frontend → container port 3000
- 16005 — student-1 backend/API → container port 5001
- 16006 — student-1 database → container port 6001

Adjust these mappings only with team agreement.

## Containers to be added by other students
When other student services are implemented, add their host port mappings using consecutive high numbers (e.g., 16007, 16008...). Keep host ports non-overlapping.

Student 2

student-2-frontend: host 16007 -> container 3002
student-2-backend: host 16008 -> container 5002
student-2-database: host 16009 -> container 6002

Student 3

student-3-frontend: host 16010 -> container 3003
student-3-backend: host 16011 -> container 5003
student-3-database: host 16012 -> container 6003

Student 4

student-4-frontend: host 16013 -> container 3004
student-4-backend: host 16014 -> container 5004
student-4-database: host 16015 -> container 6004

Student 5

student-5-frontend: host 16016 -> container 3005
student-5-backend: host 16017 -> container 5005
student-5-database: host 16018 -> container 6005

## Notes and troubleshooting
- The browser should always use the mapped host ports in this repo (for example, 16001, 16002, 16004). The container-internal ports such as 3000 are not the public URLs for the local browser.
- If you see a warning about `version` in docker-compose.yml being obsolete, remove the top-level `version:` attribute from compose files and rely on Compose V2 features.
- If a container fails to build due to missing paths (e.g., shared/ui not found), ensure the referenced build contexts exist in the repository and are correct.
- If a host URL (e.g., http://localhost:16002) or other ports return "Cannot GET /", that usually means the container is running but the service has no route at root — check the container logs for details.
- If your browser reports `ECONNREFUSED` or `connection refused` for localhost while `127.0.0.1` works, this is usually a local host resolution issue rather than a broken app. The canonical repo URLs remain the host-mapped ports above.

## Documentation and code style
- Avoid using internal phase labels in committed files; instead use wording such as "set up", "boilerplate/student 1 set up", or similar team-facing terms.

## Contact
For repo-level infra changes, coordinate with the team owner before committing large-scale compose or port remaps.