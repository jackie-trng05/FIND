# Release 2 Post-Commit CI/CD Testing Report

Generated from captured evidence. PENDING means not demonstrated. Do not edit generated reports: record evidence and refresh instead. Source inspection and health checks are not proof of integrated functionality.

| Student | CI status | Evidence |
| --- | --- | --- |
| student-1 | PASS | [evidence](evidence/student-1-evidence.json); captured 2026-10-17T00:45:23.800343+00:00; tested commit cae018c09a9c (capture dirty=True) |
| student-2 | PASS | [evidence](evidence/student-2-evidence.json); captured 2026-10-17T00:45:29.676521+00:00; tested commit cae018c09a9c (capture dirty=True) |
| student-3 | PASS | [evidence](evidence/student-3-evidence.json); captured 2026-10-17T00:45:36.554752+00:00; tested commit cae018c09a9c (capture dirty=True) |
| student-4 | PASS | [evidence](evidence/student-4-evidence.json); captured 2026-10-17T00:45:41.901715+00:00; tested commit cae018c09a9c (capture dirty=True) |
| student-5 | PASS | [evidence](evidence/student-5-evidence.json); captured 2026-10-17T00:45:47.136507+00:00; tested commit cae018c09a9c (capture dirty=True) |

## Downloaded CI Unit and Post-Commit Tests

| Student | Unit tests | Post-commit cases |
| --- | --- | --- |
| student-1 | 108/108 passed; passed | 6 captured |
| student-2 | 32/32 passed; passed | 7 captured |
| student-3 | 43/43 passed; passed | 7 captured |
| student-4 | 59/59 passed; passed | 6 captured |
| student-5 | 66/66 passed; passed | 7 captured |

## Workflow Provenance and Endpoint Assertions

- student-1: CAPTURED | [evidence](evidence/student-1-evidence.json); captured 2026-10-17T00:45:29.451724+00:00; tested commit cae018c09a9c (capture dirty=True)
- student-2: CAPTURED | [evidence](evidence/student-2-evidence.json); captured 2026-10-17T00:45:36.257055+00:00; tested commit cae018c09a9c (capture dirty=True)
- student-3: CAPTURED | [evidence](evidence/student-3-evidence.json); captured 2026-10-17T00:45:41.655483+00:00; tested commit cae018c09a9c (capture dirty=True)
- student-4: CAPTURED | [evidence](evidence/student-4-evidence.json); captured 2026-10-17T00:45:46.906953+00:00; tested commit cae018c09a9c (capture dirty=True)
- student-5: CAPTURED | [evidence](evidence/student-5-evidence.json); captured 2026-10-17T00:45:52.235195+00:00; tested commit cae018c09a9c (capture dirty=True)

Latest local production-fix regressions (not GitHub CI): PASS | [evidence](evidence/group-evidence.json); captured 2026-10-17T01:35:39.707324+00:00; tested commit d261e6649ac3 (capture dirty=True).

Each evidence pack must identify two assigned endpoint functions, expected/actual results, the workflow URL and tested commit SHA. Token-library tests and health checks alone do not meet the two-endpoint requirement. Existing suites target database/API services: confirm the assigned backend/API boundary or supplement backend-facing coverage. Successful imports do not certify coverage.
