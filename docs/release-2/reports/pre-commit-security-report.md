# Release 2 Pre-Commit Security Testing Report

Generated from captured evidence. PENDING means not demonstrated. Do not edit generated reports: record evidence and refresh instead. Source inspection and health checks are not proof of integrated functionality.

| Student | Scanner | Status | Evidence |
| --- | --- | --- | --- |
| student-1 | ruff | PENDING | No captured evidence |
| student-1 | detect-secrets | PENDING | No captured evidence |
| student-1 | pip-audit | PENDING | No captured evidence |
| student-2 | ruff | PENDING | No captured evidence |
| student-2 | detect-secrets | PENDING | No captured evidence |
| student-2 | pip-audit | PENDING | No captured evidence |
| student-3 | ruff | PENDING | No captured evidence |
| student-3 | detect-secrets | PENDING | No captured evidence |
| student-3 | pip-audit | PENDING | No captured evidence |
| student-4 | ruff | PENDING | No captured evidence |
| student-4 | detect-secrets | PENDING | No captured evidence |
| student-4 | pip-audit | PENDING | No captured evidence |
| student-5 | ruff | PENDING | No captured evidence |
| student-5 | detect-secrets | PENDING | No captured evidence |
| student-5 | pip-audit | PENDING | No captured evidence |
| group | ruff | FAIL | [evidence](evidence/dec3623e3e154c5ba4fcacf994b9af60-group-ruff.txt); 2026-10-17T00:28:08.780289+00:00; commit 72181dcca3a7 (dirty=True) |
| group | detect-secrets | FAIL | [evidence](evidence/bbad4e0a161c419b91edb05b338a1043-group-detect-secrets.txt); 2026-10-17T00:28:13.632205+00:00; commit 72181dcca3a7 (dirty=True) |
| group | pip-audit | FAIL | [evidence](evidence/b6bf4b989daf460687f4611068cb50cd-group-pip-audit.txt); 2026-10-17T00:26:48.381653+00:00; commit 72181dcca3a7 (dirty=True) |

Latest local production-fix verification (not a commit-hook run): PASS | [evidence](evidence/c2f5bfc7e7fc4424803a36d5bc56ad74-approved-production-fix-regressions.txt); 2026-10-17T00:27:53.605960+00:00; commit 72181dcca3a7 (dirty=True).

Each student must capture all three scans and the actual commit-hook transcript. A manual run is not evidence that git commit invoked the hooks. Group scans do not establish individual participation. Findings and retests remain in the linked evidence.
