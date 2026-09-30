# MCP Run Report (shared)

Shared across all five FIND student features — the MCP server is a single
non-containerised host process (`mcp-server/`, streamable-HTTP, port 16050).

Manual MCP validation evidence. Paste the real terminal output and UI
screenshots produced by the Lab 07 §5 validation steps into the placeholders
below. Nothing writes this file automatically.

## 1. Server startup (Terminal A)

Command:

```bash
cd mcp-server
python -m pip install -r requirements.txt
python server.py
```

Output:

```text
Starting FIND MCP Server (shared, non-containerised)...
Transport: streamable-http  Address: 0.0.0.0:16050
Server status: RUNNING
Available tools:
- project_files
- ci_report
- applicant_profile
- applications_for_job
- job_postings
- interview_details
- evaluation_scores
INFO:     Started server process [49484]
INFO:     Waiting for application startup.
INFO     StreamableHTTP session manager started
INFO:     Application startup complete.
```

> Note: a second `python server.py` on the same host reports
> `[Errno 10048] ... only one usage of each socket address ... on ('0.0.0.0', 16050)` —
> confirming the single shared instance is already listening on port 16050. All
> five student backends reach it via `host.docker.internal:16050/mcp`.

## 2. Tool execution (Terminal B)

Command:

```bash
cd mcp-server
python tools.py
```

Output:

```text
# project_files (shared)
{
  "answer_data": {
    "directory": ".",
    "entries": [".dockerignore", ".git", ".github", ".gitignore", ".pytest_cache",
      ".venv", "LICENSE", "README.md", "agentic_loop", "debug.log",
      "docker-compose.yml", "docs", "mcp-server", "rag-server", "requirements.txt",
      "shared", "student-1", "student-2", "student-3", "student-4", "student-5"]
  },
  "sources": [{ "table": "filesystem", "record_id": "." }],
  "confidence": "High"
}

# ci_report (shared) — reads the CI report.json files
{
  "answer_data": {
    "count": 5,
    "reports": [
      { "path": "docs/release-0/reports/student-1/report.json",
        "report": { "workflow_name": "student-1-ci", "branch": "25/merge",
          "tests": { "status": "passed", "total": 82, "passed": 82, "failed": 0 } } },
      { "path": "docs/release-0/reports/student-2/report.json",
        "report": { "workflow_name": "student-2-ci",
          "tests": { "status": "passed", "total": 15, "passed": 15, "failed": 0 } } },
      { "path": "docs/release-0/reports/student-3/report.json",
        "report": { "workflow_name": "student-3-ci",
          "tests": { "status": "passed", "total": 24, "passed": 24, "failed": 0 } } },
      { "path": "docs/release-0/reports/student-4/report.json",
        "report": { "workflow_name": "student-4-ci",
          "tests": { "status": "passed", "total": 40, "passed": 40, "failed": 0 } } },
      { "path": "docs/release-0/reports/student-5/report.json",
        "report": { "workflow_name": "student-5-ci",
          "tests": { "status": "passed", "total": 60, "passed": 60, "failed": 0 } } }
    ]
  },
  "sources": [ { "table": "ci_evidence", "record_id": "docs/release-0/reports/student-1/report.json" }, ... ],
  "confidence": "High"
}

# applicant_profile (student-1) — user_id 1
{
  "answer_data": { "user_id": 1, "profile": { "professional_title": "HR Manager",
    "location": "Sydney, Australia", "phone": "+61400000001" },
    "resume": { "file_name": "resume_profile_1.pdf", "file_type": "application/pdf" } },
  "sources": [ { "table": "profiles", "record_id": 1, "field": "professional_title" }, ... ],
  "confidence": "High"
}

# applications_for_job (student-3) — job_posting_id 1
{
  "answer_data": { "job_posting_id": 1, "status_filter": null, "count": 2,
    "applications": [
      { "application_id": 11, "user_id": 9, "application_status": "Interview Completed" },
      { "application_id": 1,  "user_id": 6, "application_status": "Submitted" } ] },
  "sources": [ { "table": "applications", "record_id": 11, "field": "application_status" }, ... ],
  "confidence": "Medium"
}

# evaluation_scores (student-5) — application_id 13
{
  "answer_data": { "application_id": 13, "evaluation_id": 1,
    "scores": { "technical": 5, "education": 4, "communication": 4,
      "problem_solving": 5, "professionalism": 4 },
    "overall_score": 4.4, "recommendation": "Hire", "status": "finalized" },
  "sources": [ { "table": "evaluations", "record_id": 1, "field": "Evaluation_OverallScore" }, ... ],
  "confidence": "High"
}

# job_postings (student-2) — status=Published, q=python
{
  "answer_data": { "filters": { "status": "Published", "q": "python" }, "count": 1,
    "postings": [ { "job_posting_id": 1, "title": "Senior Software Engineer",
      "job_type": "Full time", "location": "Sydney, NSW", "status": "Published" } ] },
  "sources": [ { "table": "job_postings", "record_id": 1, "field": "Requirements" }, ... ],
  "confidence": "High"
}

# interview_details (student-4) — application_id 4
{
  "answer_data": { "application_id": 4, "interview_id": 1,
    "interview_datetime": "2026-08-15 10:00",
    "interview_link": "https://meet.find.app/int-1",
    "notes": { "Technical": "...", "Communication": "..." }, "status": "completed" },
  "sources": [ { "table": "interviews", "record_id": 1, "field": "interview_datetime" }, ... ],
  "confidence": "High"
}
```

## 3. Endpoint tests (curl)

Student backend ports (from `docker compose ps`): s1=16005, s2=16008,
s3=16011, s4=16014, s5=16017. Each backend exposes the two shared tools
(`project_files`, `ci_report`) plus that student's own retrieval tool. One
curl per student is shown below (all with `X-MCP-Mode: on`), followed by the
MCP-OFF guard check.

```bash
# status flags (any backend)
curl.exe -s http://localhost:16011/mcp/status

# student-1 (16005) — applicant_profile (session-scoped: retrieves the logged-in user)
curl.exe -s -X POST http://localhost:16005/mcp/applicant-profile -H "X-MCP-Mode: on"

# student-2 (16008) — job_postings
curl.exe -s -X POST http://localhost:16008/mcp/job-postings -H "X-MCP-Mode: on" -d "status=Published" -d "query=python"

# student-3 (16011) — applications_for_job
curl.exe -s -X POST http://localhost:16011/mcp/applications-for-job -H "X-MCP-Mode: on" -d "job_posting_id=1"

# student-4 (16014) — interview_details
curl.exe -s -X POST http://localhost:16014/mcp/interview-details -H "X-MCP-Mode: on" -d "application_id=4"

# student-5 (16017) — evaluation_scores
curl.exe -s -X POST http://localhost:16017/mcp/evaluation-scores -H "X-MCP-Mode: on" -d "application_id=13"

# shared tool on any backend — project_files
curl.exe -s -X POST http://localhost:16011/mcp/project-files -H "X-MCP-Mode: on" -d "directory_path=."

# toggle OFF (proves the guard) — any endpoint returns the disabled fragment
curl.exe -s -X POST http://localhost:16011/mcp/applications-for-job -H "X-MCP-Mode: off" -d "job_posting_id=1"
```

Output:

```text
# GET /mcp/status
{ "ai_mode_enabled": true, "mcp_enabled": true }

# student-1 — POST /mcp/applicant-profile
# applicant_profile is session-scoped (returns the CURRENT logged-in user's
# profile), so an anonymous curl is correctly rejected. It is exercised through
# the authenticated UI / with a session cookie; the tool itself is verified in §2.
{ "error": "Not authenticated" }

# student-2 — POST /mcp/job-postings
<h3>MCP Tool: job_postings</h3>
<span class="badge badge-success">Confidence: High</span>
<pre class="mcp-answer">{ "filters": { "status": "Published", "q": "python" }, "count": 1,
  "postings": [ { "job_posting_id": 1, "title": "Senior Software Engineer",
    "job_type": "Full time", "location": "Sydney, NSW", "status": "Published" } ] }</pre>
<h4>Citations</h4><ul class="mcp-citations">
  <li>job_postings.Requirements (1)</li><li>job_postings.Job_Description (1)</li></ul>

# student-3 — POST /mcp/applications-for-job
<h3>MCP Tool: applications_for_job (job 1)</h3>
<span class="badge badge-warning">Confidence: Medium</span>
<pre class="mcp-answer">{ "job_posting_id": 1, "count": 2, "applications": [
  { "application_id": 11, "application_status": "Interview Completed" },
  { "application_id": 1,  "application_status": "Submitted" } ] }</pre>
<h4>Citations</h4><ul class="mcp-citations">
  <li>applications.application_status (11)</li><li>applications.resume_id (11)</li>
  <li>applications.application_status (1)</li><li>applications.resume_id (1)</li></ul>

# student-4 — POST /mcp/interview-details
<h3>MCP Tool: interview_details (application 4)</h3>
<span class="badge badge-success">Confidence: High</span>
<pre class="mcp-answer">{ "application_id": 4, "interview_id": 1,
  "interview_datetime": "2026-08-15 10:00",
  "interview_link": "https://meet.find.app/int-1",
  "notes": { "Technical": "...", "Education": "...", "Communication": "...",
    "Problem Solving": "...", "Professionalism": "..." }, "status": "completed" }</pre>
<h4>Citations</h4><ul class="mcp-citations">
  <li>interviews.interview_datetime (1)</li><li>interviews.interview_link (1)</li>
  <li>interviews.interview_notes.Technical (1)</li> ... </ul>

# student-5 — POST /mcp/evaluation-scores
<h3>MCP Tool: evaluation_scores (application 13)</h3>
<span class="badge badge-success">Confidence: High</span>
<pre class="mcp-answer">{ "application_id": 13, "evaluation_id": 1,
  "scores": { "technical": 5, "education": 4, "communication": 4,
    "problem_solving": 5, "professionalism": 4 },
  "overall_score": 4.4, "recommendation": "Hire", "status": "finalized" }</pre>
<h4>Citations</h4><ul class="mcp-citations">
  <li>evaluations.Evaluation_TechnicalScore (1)</li> ...
  <li>evaluations.Evaluation_OverallScore (1)</li>
  <li>evaluations.Evaluation_FinalRecommendation (1)</li></ul>

# shared — POST /mcp/project-files
<h3>MCP Tool: project_files</h3>
<span class="badge badge-success">Confidence: High</span>
<pre class="mcp-answer">{ "directory": ".", "entries": [ ".dockerignore", ..., "student-5" ] }</pre>
<h4>Citations</h4><ul class="mcp-citations"><li>filesystem (.)</li></ul>

# MCP OFF (guard fires on every /mcp/... endpoint)
<p class="feature-state feature-off">MCP Mode is disabled.</p>
```

## 4. UI test

Each student frontend exposes an MCP tab that calls the backend `/mcp/...`
routes above. With the toggle ON the tab renders the grounded fragment
(answer + confidence badge + citations); with it OFF the guard returns the
"MCP Mode is disabled" fragment.

| Feature | Frontend | MCP ON result | MCP OFF result |
| --- | --- | --- | --- |
| student-1 | :16004 | applicant_profile fragment + High badge + citations | "MCP Mode is disabled" |
| student-2 | :16007 | job_postings fragment + High badge + citations | "MCP Mode is disabled" |
| student-3 | :16010 | applications_for_job fragment + Medium badge + citations | "MCP Mode is disabled" |
| student-4 | :16013 | interview_details fragment + High badge + citations | "MCP Mode is disabled" |
| student-5 | :16016 | evaluation_scores fragment + High badge + citations | "MCP Mode is disabled" |


