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
| group | ruff | FAIL | [evidence](evidence/8106113c828b4ef69fc176678ddbeb3e-group-ruff.txt); captured 2026-10-17T00:52:47.760356+00:00; tested commit b573b15a5074 (capture dirty=True) |
| group | detect-secrets | FAIL | [evidence](evidence/03a7a99171d648358e6f9c1fb4e34462-group-detect-secrets.txt); captured 2026-10-17T00:52:53.907564+00:00; tested commit b573b15a5074 (capture dirty=True) |
| group | pip-audit | PASS | [evidence](evidence/5f850d96a4ed477aa4dc1d36cff14258-group-pip-audit.txt); captured 2026-10-17T00:53:13.342368+00:00; tested commit b573b15a5074 (capture dirty=True) |

Latest local production-fix verification (not a commit-hook run): PASS | [evidence](evidence/70885b261e2f42ca8a104dd97ea38c95-all-students-local-regressions.txt); captured 2026-10-17T00:52:16.485389+00:00; tested commit b573b15a5074 (capture dirty=True).

Each student must capture all three scans and the actual commit-hook transcript. A manual run is not evidence that git commit invoked the hooks. Group scans do not establish individual participation. Findings and retests remain in the linked evidence.
