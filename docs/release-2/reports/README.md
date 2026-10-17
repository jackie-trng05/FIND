# Release 2 Reports

This is repository evidence, not the group PDF. Reports reference [Lab 10](https://github.com/Georges034302/asd-labs/blob/main/Lab_10_Multi_Agent_Coordination.md) and [Lab 11](https://github.com/Georges034302/asd-labs/blob/main/Lab_11_Testing_Deployment_and_Operations.md). Example output is not execution evidence.

## Report Index

| Location | Content |
| --- | --- |
| [../pre-commit/](../pre-commit/) | Five per-student security reports from main, preserved unchanged |
| [../post-commit/](../post-commit/) | Per-student CI test results and commit audits from main, preserved unchanged |
| [../local/](../local/) | One local result and supporting evidence pack per student |
| [local-deployment-report.md](local-deployment-report.md) | Shared overview of authenticated backend CRUD and AI integrations |
| [deployment-results.md](deployment-results.md) | Explicit cloud TODOs; no deployment success claimed |
| [multi-agent-workflow-report.md](multi-agent-workflow-report.md) | Agent execution, grounding and audited human decisions |
| [multi-agent-validation-report.md](multi-agent-validation-report.md) | Shared model-review capture status |
| [ai-review-summary.md](ai-review-summary.md) | Shared pre-test, CI/CD and deployment review capture status |
| [contribution-logs.md](contribution-logs.md) | Existing unconfirmed contribution records; left pending |
| [evidence/README.md](evidence/README.md) | Supporting evidence index and shared capture pack |

## Evidence Scope

Reports are static documents. Update them only from actual execution or supplied human evidence; no custom generator, importer or release gate is required. Keep one report per student for individual report types and one shared report for shared types. Do not duplicate existing captures.

CI evidence applies to commit `cae018c09a9cb7702730dbbbb3977523168f4fc0`, not automatically to later commits. Hook reports retain their original temporary commit IDs and timestamps; they do not independently establish student identity. Local images were rebuilt from `d261e66` before the retained synthetic integration checks.

All five features have passing backend CRUD and AI integration checks. These do not establish full browser CRUD, factual AI quality or human approval. RAG checks demonstrate source-linked retrieval. The latest workflow snapshot records grounded, non-fallback execution and audited human decisions with reason and evidence for all five callers, including Student 1's rerun.

Cloud deployment, full frontend testing, confirmed contributions and final release approval remain deferred. Cloud reports retain explicit TODOs. No missing human decisions or participation are invented.

## Historical Shared Checks

The retained broader Ruff retest reported 14 findings: six `S104`, five `S603`, two `S607` and one `S102`. Its subprocess warnings included the now-removed reporting scripts. Other warnings concern all-interface service bindings and execution of tracked launcher code in a regression test. This historical scan is not a new scan of the cleaned-up checkout. Do not force loopback bindings without checking Docker-host connectivity.

The secret scan flagged three local Ollama SDK API-key placeholders, not discovered production credentials. The existing pip-audit capture passed. Original scan statuses and scope remain in [evidence/group-evidence.json](evidence/group-evidence.json); no suppressions or secret values were added.

The former report helper marked the latest pre-test review FAIL because its reviewer said "all students" instead of listing five IDs, and the Multi-Agent review FAIL because its reviewer omitted literal `PENDING`. Both model stages returned text. Those historical labels describe the removed helper's wording checks, not application-test failures or verified assessment requirements. They are preserved as recorded, not silently changed to PASS. CI review completed both stages; completion does not establish factual accuracy or human approval.

## Existing Tooling

Use the repository's existing per-student hooks, CI workflows and agentic-loop collectors/pipelines. The agentic-loop menu does not regenerate this report pack. Retain actual command output, workflow URLs, tested commits and human evidence alongside any future report update.