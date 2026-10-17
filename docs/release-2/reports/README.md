# Release 2 Report Pack

This is repository evidence, not the group PDF. Reports follow [Lab 10, sections 5-8](https://github.com/Georges034302/asd-labs/blob/main/Lab_10_Multi_Agent_Coordination.md) and [Lab 11, sections 4-8](https://github.com/Georges034302/asd-labs/blob/main/Lab_11_Testing_Deployment_and_Operations.md), extended for all five FIND features. Example outputs are never recorded as real results.

## Reports and Ownership

| File | Assessment coverage | Population |
| --- | --- | --- |
| [pre-commit-security-report.md](pre-commit-security-report.md) | Each student's three security scans, findings and retests | Security command / git hooks |
| [test-results.md](test-results.md) | Each student's two endpoint functions and assigned CI workflow | Import downloaded CI artifacts |
| [local-deployment-report.md](local-deployment-report.md) | Each feature's integrated local CRUD and AI services; multiple terminals | Docker snapshot plus human execution records |
| [deployment-results.md](deployment-results.md) | Each feature in the shared cloud deployment; AI disabled; human release decision | Actual cloud validation records and workflow logs |
| [multi-agent-workflow-report.md](multi-agent-workflow-report.md) | Workflow history, evidence counts, human decisions and audit linkage | Snapshot existing server logs |
| [multi-agent-validation-report.md](multi-agent-validation-report.md) | Lab 10 OBSERVE / IMPLEMENTATION / REVIEW | Live two-model review and saved validation transcript |
| [ai-review-summary.md](ai-review-summary.md) | Lab 11 pre-test, CI/CD and cloud reviews; release decision | Live reviews and explicit human decision |
| [contribution-logs.md](contribution-logs.md) | Five identifiable contribution records and GitHub commit/PR URLs | Human records |
| [completion-checklist.md](completion-checklist.md) | Pending evidence and stale reviews | Automatically regenerated |

Four individual report categories are consolidated with five identifiable student sections/rows; the brief does not prescribe 23 separate files. Review transcripts in `evidence/` are the corresponding review/validation logs, not another invented result. Optional bonus claims require additional genuine evidence and are not assumed.

## Approved Production Fixes

Shared authentication and Student 5 database/session calls now use five-second default timeouts. Both backends return generic JSON 504 responses for upstream timeouts and 503 for transport failures, without exposing upstream exception details. Existing explicit finite read-timeout overrides are preserved; `None` uses the finite default.

Forced debugging was removed from the 12 approved shared/frontend/database launchers. These use Flask's default debug-off behavior and retain explicit `FLASK_DEBUG=1` local opt-in. Five additional student backend launchers still force debugging; they were outside the approved list of 12 and have not been changed. The change does not make Flask's development server a production WSGI server.

Local regression transcripts are linked from the security and testing reports. They do not prove GitHub CI, individual commit-hook participation, cloud deployment or that existing containers were rebuilt. SQL construction, required container bindings, local Ollama placeholders and unrelated fallback behavior were not rewritten. Container images must be rebuilt before these source changes affect the running deployment.

## Setup

Run from the repository root in PowerShell, using a project virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r shared/release2-requirements.txt
python -m pip install -r requirements.txt
python shared/release2_reports.py refresh
python -m pre_commit install
$env:FIND_STUDENT_ID = 'student-1'
```

Use your own student ID. `language: system` deliberately uses the active environment. The hooks scan the selected student plus shared code and all local AI servers. With no student ID, scans are labelled `group`, not attributed to every teammate. Ruff uses security (`S`) rules, with pytest assertions excluded. Like Lab 11, pip-audit scans packages installed in the active project environment, including reporting tools. Install the dependencies relevant to your contribution there first. It does not audit every container or unresolved service manifest; audit deployed images separately where required. Each scan has a 180-second limit and records timeouts as failures.

## Security Evidence

```powershell
python shared/release2_reports.py security --student student-1 --scanner ruff
python shared/release2_reports.py security --student student-1 --scanner detect-secrets
python shared/release2_reports.py security --student student-1 --scanner pip-audit
```

These manual runs are useful preflight checks but do not prove the commit workflow. On your next authorised commit, installed hooks run the same commands, fail the commit when scans fail and capture evidence. Retain the commit terminal transcript as well. No commit is made by this reporting task. Fix or explicitly document real findings; do not suppress them to manufacture passing evidence.

Hooks use `--hook` to capture into ignored `.release2-hook-evidence/`, avoiding a permanently changing staged report on every commit attempt. After a real commit-hook execution, import its evidence for review and inclusion in a subsequent evidence commit:

```powershell
python shared/release2_reports.py import-hooks
```

Import preserves the original capture timestamp and tested HEAD/dirty state and skips already-imported records. `pre-commit run --all-files` is a preflight, not proof that a real commit invoked hooks: retain the actual commit transcript. Do not run `--hook` manually and present it as a commit. Secret scan evidence stores finding counts by file, never secret values; inspect findings privately. Review all other logs and screenshots for secrets/personal data before committing.

## CI Evidence

Run each existing `student-N-ci.yml` on GitHub after an authorised push, then download its `student-N-post-commit-evidence` artifact. Import the extracted folder or its ZIP:

```powershell
python shared/release2_reports.py import-ci --student student-1 --source C:/Evidence/student-1-post-commit-evidence --run-url https://github.com/OWNER/REPO/actions/runs/RUN_ID --commit FULL_40_CHARACTER_TESTED_SHA
```

Repeat for students 2-5. Imported packs must contain nonempty `test-results.md` and `test-audit.jsonl`, with a matching tested commit SHA. FAIL remains FAIL. Import validates the supplied pack; it does not authenticate GitHub or verify an entire workflow's final status. Retain full successful workflow logs, a coverage mapping naming the two endpoint functions, and expected/actual assertions alongside the pack. Existing endpoint suites target the database/API service; verify the assessor's backend/API interpretation rather than claiming untested authenticated backend routes.

## Local and Cloud Evidence

```powershell
python shared/release2_reports.py snapshot
python shared/release2_reports.py workflow
python shared/release2_reports.py template --kind local --student student-1
python shared/release2_reports.py template --kind cloud --student student-1
```

`snapshot` is read-only: it records Docker Compose service state without restarting anything. `workflow` reads the existing Multi-Agent JSONL files without modifying them; its privacy-minimised snapshot records statuses, counts and human-decision linkage. It does not prove frontend execution. Current Planner and Worker execution is concurrent; review this against the brief's plan-driven sequence rather than assuming structural presence proves compliance.

Complete the generated `inputs/student-1-local.json` and `inputs/student-1-cloud.json` using real observations. Repeat for all five students. Required check keys are supplied in each template. Every check needs `PASS`, `FAIL` or `PENDING` and a specific evidence reference. Include:

- Named reviewer, actual UTC timestamp, feature and frontend URL.
- Captured terminal/service logs, browser evidence and expected/actual CRUD results with record IDs (redact personal data).
- Local: AI-Mode, MCP, RAG, Multi-Agent and human review through the frontend/backend path; start each non-containerised service in a separate terminal and retain its transcript.
- Cloud: Azure or AWS, resources, successful `cloud-deployment.yml` URL/logs, frontend/API/database/CRUD and persistence validation; verify all four AI services are disabled by default.
- Limitations, failures, corrections and retest evidence. A health check alone is insufficient.

Store sanitised supporting files under `evidence/` and reference them in the JSON, then import:

```powershell
python shared/release2_reports.py record --kind local --student student-1 --source docs/release-2/reports/inputs/student-1-local.json
python shared/release2_reports.py record --kind cloud --student student-1 --source docs/release-2/reports/inputs/student-1-cloud.json
```

Template commands never overwrite an existing input. Refresh regenerates reports but preserves input files and timestamped evidence. Importing a human record validates its shape, not the truth of a screenshot, URL or observation. The reviewer is responsible for that verification. Deployment infrastructure and deployment workflow implementation are separate work; this tool cannot deploy an application or manufacture their execution logs.

## Agentic Reviews

With Ollama running and the configured implementation/reviewer models available:

```powershell
python shared/release2_reports.py review --mode multi_agent
python shared/release2_reports.py review --mode pre_test
python shared/release2_reports.py review --mode cicd_test
python shared/release2_reports.py review --mode deployment
```

The same evidence-capture path is used by the interactive agentic-loop Release 2 menu. Reports and exact OBSERVE / IMPLEMENTATION / REVIEW transcripts are saved automatically, including failures. Reviews consume latest captured artifacts or derived structured summaries linked to full artifacts, not just filenames. With no execution evidence, a review is explicitly a gap review, never proof of execution. Missing students and pending checks must be flagged. COMPLETE means two models returned assessment sections and required evidence labels, not that the application passed or the human approved it. This is not a factual-accuracy guarantee: inspect both model outputs and reject unsupported claims. Rerun after changing inputs; stale reviews are listed in the completion checklist. Excessive input is rejected rather than silently truncated.

## Contributions and Final Decision

```powershell
python shared/release2_reports.py template --kind contribution --student student-1
python shared/release2_reports.py template --kind release --student group
```

Complete contribution inputs for all five students with responsibilities, actual work and real commit/PR URLs. Complete the release input with a named human reviewer, UTC timestamp, justification and READY/NOT READY. A READY entry is rejected while required evidence is missing or reviews are stale. A model response cannot approve the release.

```powershell
python shared/release2_reports.py record --kind contribution --student student-1 --source docs/release-2/reports/inputs/student-1-contribution.json
python shared/release2_reports.py record --kind release --student group --source docs/release-2/reports/inputs/group-release.json
python shared/release2_reports.py status
```

`status` exits 1 for remaining evidence gaps. Even a complete checklist requires human verification against the final release commit. Do not edit generated Markdown to replace PENDING with PASS.