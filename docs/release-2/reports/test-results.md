# Release 2 Post-Commit CI/CD Testing Report

Generated from captured evidence. PENDING means not demonstrated. Do not edit generated reports: record evidence and refresh instead. Source inspection and health checks are not proof of integrated functionality.

| Student | CI status | Evidence |
| --- | --- | --- |
| student-1 | PASS | [evidence](evidence/53ae574144494073abc74659595b8499-student-1-ci.md); captured 2026-10-17T00:45:23.800343+00:00; tested commit cae018c09a9c (capture dirty=True) |
| student-2 | PASS | [evidence](evidence/257d67c1603545b3afbdcf6f3ac88a20-student-2-ci.md); captured 2026-10-17T00:45:29.676521+00:00; tested commit cae018c09a9c (capture dirty=True) |
| student-3 | PASS | [evidence](evidence/6d823e23da0a4184890c3253badef4a0-student-3-ci.md); captured 2026-10-17T00:45:36.554752+00:00; tested commit cae018c09a9c (capture dirty=True) |
| student-4 | PASS | [evidence](evidence/06459d3d53dc4e659b8bd638ce663e1b-student-4-ci.md); captured 2026-10-17T00:45:41.901715+00:00; tested commit cae018c09a9c (capture dirty=True) |
| student-5 | PASS | [evidence](evidence/64c0d2e4032c4814a8f517d967d971a5-student-5-ci.md); captured 2026-10-17T00:45:47.136507+00:00; tested commit cae018c09a9c (capture dirty=True) |

## Downloaded CI Unit and Post-Commit Tests

| Student | Unit tests | Post-commit cases |
| --- | --- | --- |
| student-1 | 108/108 passed; passed | 6 captured |
| student-2 | 32/32 passed; passed | 7 captured |
| student-3 | 43/43 passed; passed | 7 captured |
| student-4 | 59/59 passed; passed | 6 captured |
| student-5 | 66/66 passed; passed | 7 captured |

## Workflow Logs and Endpoint Assertions

- student-1: CAPTURED | [evidence](evidence/9746d3f029f443ada1e22bc7043ec9f4-student-1-ci-workflow-and-coverage.txt); captured 2026-10-17T00:45:29.451724+00:00; tested commit cae018c09a9c (capture dirty=True)
- student-2: CAPTURED | [evidence](evidence/94856a8b379749fc9c982e923bcdd5c7-student-2-ci-workflow-and-coverage.txt); captured 2026-10-17T00:45:36.257055+00:00; tested commit cae018c09a9c (capture dirty=True)
- student-3: CAPTURED | [evidence](evidence/1a28568ab6b347f6ac18d95e3f9de272-student-3-ci-workflow-and-coverage.txt); captured 2026-10-17T00:45:41.655483+00:00; tested commit cae018c09a9c (capture dirty=True)
- student-4: CAPTURED | [evidence](evidence/3de574823318476c8419e7add3d6d02e-student-4-ci-workflow-and-coverage.txt); captured 2026-10-17T00:45:46.906953+00:00; tested commit cae018c09a9c (capture dirty=True)
- student-5: CAPTURED | [evidence](evidence/a8330677b5cb4eff8333f8da66ab439b-student-5-ci-workflow-and-coverage.txt); captured 2026-10-17T00:45:52.235195+00:00; tested commit cae018c09a9c (capture dirty=True)

Latest local production-fix regressions (not GitHub CI): PASS | [evidence](evidence/069a2fd1b5b14a9982e6974066c01a2c-all-students-local-regressions.txt); captured 2026-10-17T01:35:39.707324+00:00; tested commit d261e6649ac3 (capture dirty=True).

Each evidence pack must identify two assigned endpoint functions, expected/actual results, the workflow URL and tested commit SHA. Token-library tests and health checks alone do not meet the two-endpoint requirement. Existing suites target database/API services: confirm the assigned backend/API boundary or supplement backend-facing coverage. Successful imports do not certify coverage.
