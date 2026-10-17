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
| group | ruff | FAIL | [evidence](evidence/c529ddf0d6f143be8186e08c545b1484-group-ruff.txt); 2026-10-17T00:04:57.550553+00:00; commit b8397c671c18 (dirty=True) |
| group | detect-secrets | FAIL | [evidence](evidence/28a4e0a1c73642c5b70cd00a689e8542-group-detect-secrets.txt); 2026-10-17T00:07:13.567455+00:00; commit b8397c671c18 (dirty=True) |
| group | pip-audit | FAIL | [evidence](evidence/d6cbbf23297544caaafe7992ed13feb5-group-pip-audit.txt); 2026-10-17T00:09:43.937621+00:00; commit b8397c671c18 (dirty=True) |

Each student must capture all three scans and the actual commit-hook transcript. A manual run is not evidence that git commit invoked the hooks. Group scans do not establish individual participation. Findings and retests remain in the linked evidence.
