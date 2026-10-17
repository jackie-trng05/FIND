# Evidence Index

One named pack per student consolidates their distinct local CRUD, AI integration, CI context and contribution-draft evidence. Shared execution evidence is stored once, not copied into every student's pack.

| Student | CI | Backend checks | Overall local sign-off | Evidence pack |
| --- | --- | --- | --- | --- |
| student-1 | PASS | 8/8 PASS | PENDING | [student-1 results](../../local/student-1/test-results.md) |
| student-2 | PASS | 8/8 PASS | PENDING | [student-2 results](../../local/student-2/test-results.md) |
| student-3 | PASS | 8/8 PASS | PENDING | [student-3 results](../../local/student-3/test-results.md) |
| student-4 | PASS | 8/8 PASS | PENDING | [student-4 results](../../local/student-4/test-results.md) |
| student-5 | PASS | 8/8 PASS | PENDING | [student-5 results](../../local/student-5/test-results.md) |

Canonical reports from main: [pre-commit](../../pre-commit/) and [post-commit](../../post-commit/). They are read directly and are not duplicated in local evidence. Local reports follow the same category/student layout.

Shared evidence: [group-evidence.json](group-evidence.json). Machine-readable retained record index: [report-audit.jsonl](report-audit.jsonl).

Each pack's `records` list identifies its evidence by `event.kind`, with `feature`, `scanner` or `mode` where applicable. CI context preserves distinct run URLs, unit totals, tested commits and endpoint assertions without copying canonical post-commit output. Local records preserve authenticated checks and synthetic AI output.

Duplicate captures, superseded attempts and verbose CI logs were removed. Original execution timestamps, commits, statuses and checksums are retained; consolidation is not a new execution. Remaining FAIL/PENDING records are compactly disclosed, not changed to PASS. Cloud deployment and human evidence remain pending.
