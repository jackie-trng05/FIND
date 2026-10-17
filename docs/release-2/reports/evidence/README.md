# Evidence Index

One named pack per student consolidates their retained CI, local CRUD, AI integration and contribution-draft evidence. Shared execution evidence is stored once, not copied into every student's pack.

| Student | CI | Backend checks | Overall local sign-off | Evidence pack |
| --- | --- | --- | --- | --- |
| student-1 | PASS | 8/8 PASS | PENDING | [student-1-evidence.json](student-1-evidence.json) |
| student-2 | PASS | 8/8 PASS | PENDING | [student-2-evidence.json](student-2-evidence.json) |
| student-3 | PASS | 8/8 PASS | PENDING | [student-3-evidence.json](student-3-evidence.json) |
| student-4 | PASS | 8/8 PASS | PENDING | [student-4-evidence.json](student-4-evidence.json) |
| student-5 | PASS | 8/8 PASS | PENDING | [student-5-evidence.json](student-5-evidence.json) |

Shared evidence: [group-evidence.json](group-evidence.json). Machine-readable retained record index: [report-audit.jsonl](report-audit.jsonl).

Each pack's `records` list identifies its evidence by `event.kind`, with `feature`, `scanner` or `mode` where applicable. CI records preserve run URLs, tested commits, actual results and endpoint assertions. Local records preserve authenticated checks and synthetic AI output.

Duplicate captures, superseded attempts and verbose CI logs were removed. Original execution timestamps, commits, statuses and checksums are retained; consolidation is not a new execution. Remaining FAIL/PENDING records are compactly disclosed, not changed to PASS. Cloud deployment and human evidence remain pending.
