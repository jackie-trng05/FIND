# MCP Integration Report (shared)

Shared across all five FIND student features. Overall assessment of the shared
MCP integration, derived from the agentic-loop MCP mode IMPLEMENTATION
(qwen2.5:0.5b) and REVIEW (llama3.1:8b) output.

## Strengths

- **Seven single-purpose tools with clear boundaries.** The shared server
  exposes exactly `project_files`, `ci_report`, `applicant_profile`,
  `job_postings`, `applications_for_job`, `interview_details` and
  `evaluation_scores` — each does one read-only retrieval and nothing else (no
  writes, no side effects). Boundaries are enumerated in
  [boundary-analysis.md](boundary-analysis.md).
- **Uniform, grounded response contract.** Every tool returns the same
  retrieval-context shape (`answer_data` + `sources` + `confidence`) built via
  `retrieval.build_context`, so AI-Mode answers are always grounded with
  citations and a confidence category. This is visible in the identical fragment
  structure across all five backends in [run-report.md](run-report.md) §3.
- **One server reused by five backends.** A single non-containerised MCP host
  process (streamable-HTTP, port 16050) is shared by all five student backends
  through `services.mcp_client`; containers reach it via
  `host.docker.internal`. This avoids five divergent implementations and keeps
  the tool contract consistent for every feature.
- **Clean frontend/back-end separation.** The browser never talks to MCP
  directly — it calls each backend's `/mcp/...` routes (HTMX), which proxy to the
  shared server. This keeps the MCP endpoint off the public surface.
- **Explicit feature gating.** `MCP_ENABLED` (and the `X-MCP-Mode` toggle
  header) cleanly disable the endpoints, returning a well-formed "MCP Mode is
  disabled" fragment — verified in [run-report.md](run-report.md) §3. CI sets the
  flags to `false` so the pipeline never needs Ollama or the MCP process.
- **Least-data retrieval.** Tools project only the fields needed
  (e.g. `_APPLICATION_FIELDS`, the evaluation score map), rather than returning
  whole rows, limiting incidental data exposure.

## Risks

- **No authentication on the shared MCP host process — NOTED.** The server binds
  `0.0.0.0:16050` and trusts any caller that can reach it. This is acceptable for
  the local/lab topology (loopback + `host.docker.internal`), but the process
  itself performs no auth; access control currently lives in the backend routes.
- **Path exposure via `project_files` — MITIGATED.** The traversal risk is
  closed by repo-root confinement and re-tested in
  [tool-review.md](tool-review.md); no host paths outside the workspace are
  returned.
- **Session scope depends on the calling backend — NOTED.** `applicant_profile`
  is only safe because the student-1 backend supplies the authenticated
  `user_id`; an anonymous call to that route is correctly rejected
  (`Not authenticated`, [run-report.md](run-report.md) §3). The server tool
  trusts the id it is given, so the identity boundary is enforced upstream.
- **Shared blast radius — NOTED.** Because one process serves all five features,
  an outage or a bad tool change affects every backend at once.

## Recommendations

- **Bind MCP to loopback and/or add a shared token.** Bind `127.0.0.1:16050`
  (with Docker reaching it via the gateway) or require a static
  bearer/`X-MCP-Key` header on the server so a stray process on the host cannot
  call the tools; keep the per-backend route auth as the outer layer.
- **Centralise the path-confinement helper.** Factor the repo-root check used by
  `project_files`/`ci_report` into a single `resolve_within_repo()` helper so any
  future filesystem-touching tool inherits the guard by construction.
- **Add a lightweight health/version endpoint and per-tool audit logging** on the
  shared server so the five backends can detect an unhealthy MCP process and so
  tool calls are traceable across features (mirrors the RAG server's audit log).
