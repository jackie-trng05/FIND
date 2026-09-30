# MCP Tool Boundary Analysis (shared)

Shared across all five FIND student features. The MCP server exposes two shared
tools and one retrieval tool per student domain. Boundaries define what each
tool *is* and *is not* allowed to do, so agent access stays controlled.

## Tool boundaries

| Tool | Responsibility | NOT responsible for |
| --- | --- | --- |
| `project_files` | List repository files/folders under a repo-relative path | Reading file contents; judging code quality |
| `ci_report` | Read a student's CI evidence JSON | Deciding release approval; re-running CI |
| `applicant_profile` | Retrieve an applicant's profile fields + resume text | Judging candidate suitability |
| `job_postings` | Retrieve job posting records | Recommending which job to apply for |
| `applications_for_job` | Retrieve applications for a job | Ranking or scoring applicants |
| `interview_details` | Retrieve interview records | Deciding interview outcomes |
| `evaluation_scores` | Retrieve stored evaluation scores | Producing new evaluations or hiring decisions |

## Decision

**ACCEPTED.**

Every tool is **read-only retrieval**: it returns records with citations to the
source table/field and a confidence category, and none of them make, store, or
act on a decision. The boundaries above match the shared MCP server
implementation in `mcp-server/tools.py` and were confirmed by the agentic-loop
MCP-mode review, which found the tool set well-scoped with no capability creep —
each domain tool answers a single retrieval question and hands the judgement
back to a human.

The one residual risk — `project_files` being able to walk outside the
repository root — is tracked and mitigated in `tool-review.md`.
