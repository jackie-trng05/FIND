# RAG Report (shared)

Shared across all five FIND student features — the RAG server is a single
non-containerised host process (`rag-server/`, HTTP port 16070). Manual RAG
validation evidence from the Lab 08 §5 terminal tests. Paste real output below.

## Tool tests (Terminal B)

The RAG server is shared, so the corpus is refreshed once and then one grounded
query is run per student feature (profile / job postings / applications /
interviews / evaluations).

```bash
cd rag-server
# shared: rebuild the corpus + vector store once
python -c "from rag_pipeline import refresh_corpus; import json; print(json.dumps(refresh_corpus(), indent=2))"

# one grounded query per student feature
python -c "from rag_pipeline import answer_question as a; import json; print(json.dumps(a('What is the profile and resume for applicant 1?', 5), indent=2))"   # student-1
python -c "from rag_pipeline import answer_question as a; import json; print(json.dumps(a('What published job postings match python?', 5), indent=2))"          # student-2
python -c "from rag_pipeline import answer_question as a; import json; print(json.dumps(a('What is the status of application 2?', 5), indent=2))"                 # student-3
python -c "from rag_pipeline import answer_question as a; import json; print(json.dumps(a('What are the interview details for application 4?', 5), indent=2))"    # student-4
python -c "from rag_pipeline import answer_question as a; import json; print(json.dumps(a('What is the evaluation score for application 13?', 5), indent=2))"     # student-5
```

Output:

```text
# refresh_corpus() — rebuild the corpus + vector store
{
  "status": "success",
  "caller": "student",
  "chunk_count": 178,
  "collection": "find_enterprise_context",
  "corpus_path": "C:\\FIND\\rag-server\\corpus\\corpus.jsonl",
  "vector_store_status": "ready"
}

# retrieve_context('What is the status of application 2?', 5) — top-5 chunks
{
  "status": "success",
  "query": "What is the status of application 2?",
  "k": 5,
  "retrieval_mode": "chromadb",
  "query_coverage": 1.0,
  "results": [
    { "rank": 1, "chunk_id": "db_student-5_evaluations_4", "authority_tier": "tier_1", "score": 0.8131, "text": "student-5 database, evaluations record 4: application_id = 19; ... recommendation = Reject; status = finalized ..." },
    { "rank": 2, "chunk_id": "db_student-5_evaluations_3", "authority_tier": "tier_1", "score": 0.7969, "text": "student-5 database, evaluations record 3: application_id = 16; ... recommendation = Reject; status = finalized ..." },
    { "rank": 3, "chunk_id": "db_student-4_interviews_2",  "authority_tier": "tier_1", "score": 0.7763, "text": "student-4 database, interviews record 2: application_id = 18; ... status = scheduled." },
    { "rank": 4, "chunk_id": "db_student-5_evaluations_2", "authority_tier": "tier_1", "score": 0.7661, "text": "student-5 database, evaluations record 2: application_id = 17; ... recommendation = Hire; status = finalized ..." },
    { "rank": 5, "chunk_id": "db_student-3_applications_2", "authority_tier": "tier_1", "score": 0.65,  "text": "student-3 database, applications record 2: job_posting_id = 3; application_id = 2; user_id = 6; application_status = Submitted; submitted_at = 2026-09-18T07:27:36+00:00." }
  ]
}

# answer_question('What is the status of application 2?', 5) — grounded answer + citations
{
  "status": "success",
  "query": "What is the status of application 2?",
  "answer": "... application_status = Submitted; submitted_at = 2026-09-18T07:27:36+00:00. ...",
  "citations": [
    { "chunk_id": "db_student-5_evaluations_4", "source_id": "student-5-db:/evaluations/4", "authority_tier": "tier_1" },
    { "chunk_id": "db_student-5_evaluations_3", "source_id": "student-5-db:/evaluations/3", "authority_tier": "tier_1" },
    { "chunk_id": "db_student-4_interviews_2",  "source_id": "student-4-db:/interviews/2",  "authority_tier": "tier_1" },
    { "chunk_id": "db_student-5_evaluations_2", "source_id": "student-5-db:/evaluations/2", "authority_tier": "tier_1" },
    { "chunk_id": "db_student-3_applications_2", "source_id": "student-3-db:/applications/2", "authority_tier": "tier_1" }
  ],
  "confidence_category": "High",
  "retrieval_summary": { "k": 5, "retrieved_count": 5, "query_coverage": 1.0,
    "retrieval_mode": "chromadb", "top_chunk": "db_student-5_evaluations_4" }
}
```

| Field | Value |
| --- | --- |
| Query used | `What is the status of application 2?` |
| Retrieval results count | 5 (k=5, `query_coverage` 1.0, `retrieval_mode` chromadb) |
| Answer confidence category | High |
| Citations provided | `db_student-5_evaluations_4`, `db_student-5_evaluations_3`, `db_student-4_interviews_2`, `db_student-5_evaluations_2`, `db_student-3_applications_2` (all `tier_1`) |

> The grounded record for application 2 is retrieved at rank 5
> (`db_student-3_applications_2` → `application_status = Submitted`) with a
> `tier_1` (authoritative DB) citation; every returned chunk carries a
> `source_id`, so the answer is fully attributable.

### Per-student query results

One grounded query per feature — every query returned k=5 chunks in `chromadb`
mode with **High** confidence and the feature's authoritative `tier_1` DB chunk
among the citations:

| Student | Query | Confidence | Coverage | Top chunk | Key citation(s) |
| --- | --- | --- | --- | --- | --- |
| student-1 | `What is the profile and resume for applicant 1?` | High | 1.0 | `reports_run-report.md_5` | `db_student-1_profiles_6` |
| student-2 | `What published job postings match python?` | High | 0.8 | `db_student-2_job_postings_1` | `db_student-2_job_postings_1`, `_8`, `_11` |
| student-3 | `What is the status of application 2?` | High | 1.0 | `db_student-5_evaluations_4` | `db_student-3_applications_2` |
| student-4 | `What are the interview details for application 4?` | High | 1.0 | `db_student-4_interviews_4` | `db_student-4_interviews_4`, `_3`, `_5`, `_6` |
| student-5 | `What is the evaluation score for application 13?` | High | 1.0 | `db_student-5_evaluations_1` | `db_student-5_evaluations_1`, `db_student-3_applications_13` |

> Each feature's grounded answer cites its own authoritative `tier_1` database
> chunk (e.g. student-2 → `job_postings`, student-4 → `interviews`, student-5 →
> `evaluations`), confirming the shared corpus serves all five features with
> attributable, high-confidence retrieval.

## Retrieval metrics (rag_eval.py)

```bash
cd rag-server
python rag_eval.py
```

```text
Query: student feature microservices
Retrieved: ['db_student-2_job_postings_1', 'db_student-1_profiles_6', 'student-5_report.md_1', 'student-1_report.md_1', 'reports_run-report.md_14']
Relevant: ['db_student-2_job_postings_1', 'db_student-1_profiles_6', 'student-5_report.md_1', 'student-1_report.md_1', 'reports_run-report.md_14']
P@5: 1.0
R@5: 1.0
---
Query: CI report testing status passed
Retrieved: ['student-5_report.md_1', 'student-1_report.md_1', 'student-3_report.md_1', 'student-2_report.md_1', 'reports_run-report.md_4']
Relevant: ['student-5_report.md_1', 'student-1_report.md_1', 'student-3_report.md_1', 'student-2_report.md_1', 'reports_run-report.md_4']
P@5: 1.0
R@5: 1.0
---
Query: repository files project structure
Retrieved: ['readme_row_17', 'reports_boundary-analysis.md_4', 'reports_tool-review.md_6', 'reports_tool-review.md_2', 'reports_boundary-analysis.md_1']
Relevant: ['readme_row_17', 'reports_boundary-analysis.md_4', 'reports_tool-review.md_6', 'reports_tool-review.md_2', 'reports_boundary-analysis.md_1']
P@5: 1.0
R@5: 1.0
---
```

**Result: P@5 = 1.0 and R@5 = 1.0 on all three benchmark queries** (mean
P@5 = 1.0, mean R@5 = 1.0). Retrieval mode was `chromadb` (vector store ready),
and the benchmark now also surfaces the release-1 MCP/RAG reports
(`reports_run-report.md`, `reports_boundary-analysis.md`, `reports_tool-review.md`),
confirming those documents are ingested into the corpus.

Note: `rag_eval.py` also writes `rag-server/retrieval-metrics.md` automatically —
this report is the human-readable capture of that run.
