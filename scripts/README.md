# FIND Cloud Deployment

Azure Container Apps deployment for the **complete integrated FIND application**.
Per the repository `README.md`, cloud deployment targets one shared deployment of
the whole app — not individual student microservices.

## What gets deployed

18 Container Apps in a single Container Apps environment:

| Tier | Apps | Ingress | Target port |
|------|------|---------|-------------|
| Shared frontend (entry point) | `shared-frontend` | external | 3000 |
| Shared API | `shared-api` | external | 5000 |
| Shared DB | `shared-db` | internal | 6000 |
| Student frontends | `student-1..5-frontend` | external | 3000 / 3002–3005 |
| Student backends | `student-1..5-backend` | external | 5001–5005 |
| Student DBs | `student-1..5-db` | internal | 6001–6005 |

**Ingress rationale:** FIND frontends call APIs from the browser via `*_PUBLIC_URL`
env vars, so every frontend, every student backend, and `shared-api` need public
(external) ingress. Only the databases are internal-only. No nginx reverse proxy is
needed (unlike the original lab) because FIND already parameterises all cross-service
URLs through environment variables.

**Shared static assets:** locally, `docker-compose` mounts the shared CSS
(`shared/css`) and shared JS (`shared/frontend/static/js`) into the frontends as
volumes. Azure Container Apps have no bind mounts, so the frontend images **bake these
assets in** at build time — the 6 frontends build from the repo-root context (`docker
build -f <service>/frontend/Dockerfile .`) and `COPY` the shared folders to
`/app/shared-css` and `/app/shared-js`. Compose still mounts the same paths at runtime
(the mounts shadow the baked copies, preserving live editing).

**Circular URLs:** `shared-frontend` needs each student frontend URL while student
frontends need `shared-frontend`'s `LOGIN_URL`/`FIND_HOME_URL`. Azure Container Apps
FQDNs are deterministic once the environment exists
(`https://<app>.<envDefaultDomain>` external, `https://<app>.internal.<envDefaultDomain>`
internal), so `deploy-azure.sh` reads the environment's default domain and computes
every URL up front, breaking the cycle.

**Deployment profile:** `AI_MODE_ENABLED`, `MCP_ENABLED`, `RAG_ENABLED`,
`MULTI_AGENT_ENABLED` are all set to `false`. The `mcp-server`, `rag-server`,
`multi-agent-server`, and Ollama run locally only and are not deployed.

## Scripts (run in order)

| Script | Purpose |
|--------|---------|
| `gh-secrets-setup.sh` | One-time, local. Creates the `find-github-oidc` app registration + federated credential and pushes `AZURE_*` secrets to GitHub Actions. |
| `env-setup.sh` | Creates the resource group, tags it with generated `registryName`/`envName`. |
| `build-images.sh` | Creates the ACR (admin access disabled) and builds/pushes all 18 images, authenticating to the registry with the Azure identity via `az acr login`. |
| `deploy-azure-env.sh` | Creates the Container Apps environment. |
| `deploy-azure.sh` | Deploys all 18 Container Apps with full env wiring. |
| `deployment-testing.sh` | Validates `shared-frontend` and writes `reports/deploy/deployment-results.md`. |
| `cleanup.sh` | Deletes the resource group to stop billing. |

Local run:

```bash
bash scripts/gh-secrets-setup.sh    # one-time
bash scripts/env-setup.sh
bash scripts/build-images.sh
bash scripts/deploy-azure-env.sh
bash scripts/deploy-azure.sh
bash scripts/deployment-testing.sh
```

CI/CD: `.github/workflows/cicd_azure.yaml` (manual `workflow_dispatch`) runs
the `pre_commit` evidence tests, then the deploy sequence above, authenticating via
OIDC (`azure/login@v2`) with a fresh login before each slow step.

### Registry authentication (passwordless)

`build-images.sh` pushes images with the **Azure identity**, not a stored registry
password:

- The registry is created with **admin access disabled**.
- Docker authenticates via `az acr login --name <registry>`, which exchanges the
  current Azure credential (the OIDC login in CI, or your `az login` locally) for a
  short-lived registry token. No `ACR_PASSWORD` secret is needed.
- **Permissions:** the workflow identity already has subscription-wide `Contributor`
  (which permits push). The script also grants **`AcrPush`** at the registry scope to
  cover ABAC-enabled registries, and retries `az acr login` to absorb role-assignment
  propagation delay.
- **Local runs:** work after `az login`, provided your user can push to the registry
  (Owner/Contributor/AcrPush).
- **Image pulls** by the Container Apps stay on each app's **managed identity**
  (`--registry-identity system`) — unaffected by admin access being disabled.
- `az acr login` still writes a short-lived token into the local Docker config; on
  ephemeral CI runners this is discarded with the runner.

## Before a live deploy

A couple of items should be verified before relying on a live deployment:

1. **Shared DB URL is env-driven.** `shared/backend/app.py` reads the shared
   database URL from `SHARED_DB_URL` (defaulting to the Docker-network name for
   local `docker-compose`). `deploy-azure.sh` passes the internal Container Apps
   FQDN as `SHARED_DB_URL` to `shared-api`, so it reaches `shared-db` in the cloud.

2. **Cross-subdomain auth cookie.** `shared-api` sets `session_token` with
   `domain=COOKIE_DOMAIN`. `deploy-azure.sh` sets `COOKIE_DOMAIN` to the environment
   default domain so the cookie is valid across all `*.<envDefaultDomain>` apps.
   Verify the browser accepts it (a leading-dot form may be required depending on the
   app's cookie handling).

3. **Costs.** 18 always-on Container Apps (min 1 replica each) plus ACR incur Azure
   charges. Run `cleanup.sh` when finished.
