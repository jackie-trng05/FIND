# MCP Tool Review (shared)

Shared across all five FIND student features. Records risks surfaced by the
agentic-loop MCP review (llama3.1:8b) and the mitigations applied to the shared
MCP server.

## Risk identified

**Path traversal in `project_files`.** The `project_files` tool takes a
caller-supplied `directory_path` and lists its contents. Because the argument
is attacker-controllable (it flows from each student frontend's MCP tab through
the backend `/mcp/project-files` route to the shared server), a naive
implementation that joined the input onto the repo root without validation
could be walked outside the workspace with `../` segments (e.g. `../..`,
`../../Users`, or an absolute path), exposing host files that MCP is not meant
to serve. This is the highest-severity finding because it is the only tool that
reads the **filesystem** rather than a scoped database record — the other six
tools are already bounded to specific tables/ids.

## Correction applied

**Path is resolved and confined to the repository root before any listing**, in
`list_project_files` ([mcp-server/tools.py](../../../mcp-server/tools.py)):

```python
_REPO_ROOT = config.REPO_ROOT.resolve()

def list_project_files(directory_path: str = ".") -> dict:
    target = (_REPO_ROOT / directory_path).resolve()
    if _REPO_ROOT not in target.parents and target != _REPO_ROOT:
        return retrieval.empty_context(
            f"Path is outside the repository workspace: {directory_path}"
        )
    ...
```

Both the input and the repo root are `.resolve()`d (collapsing `..` and
symlinks), then the target is rejected unless it is the repo root itself or a
descendant of it. Rejections return a grounded `empty_context` with a `Low`
confidence message instead of raising or leaking a path, so the frontend still
gets a well-formed fragment. The same repo-root anchoring is applied to
`read_ci_report`, so neither shared tool can escape the workspace.

## Retest

Re-ran the tool directly against an escape attempt and a valid path after the
guard was in place:

```bash
cd mcp-server
python -c "import json, tools; print(json.dumps(tools.list_project_files('../..'), indent=2))"
python -c "import json, tools; print(json.dumps(tools.list_project_files('docs/release-1'), indent=2))"
```

```text
# escape attempt — BLOCKED
{ "answer_data": { "error": "Path is outside the repository workspace: ../.." },
  "sources": [], "confidence": "Low" }

# valid in-repo path — ALLOWED
{ "answer_data": { "directory": "docs/release-1", "entries": [ "reports" ] },
  "sources": [ { "table": "filesystem", "record_id": "docs/release-1" } ],
  "confidence": "High" }
```

**Result: boundary enforced.** The `../..` traversal is rejected with no
directory contents and no host path returned, while a legitimate
repository-relative path resolves normally with High confidence and a citation.
The end-to-end path was also re-exercised through the backend route in
[run-report.md](run-report.md) §3 (`POST /mcp/project-files`), which returns
only in-repo entries. This closes the residual `project_files` risk noted in
[boundary-analysis.md](boundary-analysis.md).
