# Student 3 — Application Management

Individual microservices for the **Application Management** feature of the
FIND recruitment platform. Implements the applicant-facing apply/track flow
and the HR staff review flow, with an integrated AI-Mode (Ollama + Llama) for
candidate screening.

## Ports (canonical)

| Service                       | Container port | Host port |
| ----------------------------- | -------------- | --------- |
| `student-3-frontend`          | `3003`         | `16010`   |
| `student-3-backend` (API)     | `5003`         | `16011`   |
| `student-3-db` (SQLite REST)  | `6003`         | `16012`   |

## Feature scope

### Applicant view
- **Apply** button on any Published job posting opens the Application form
  (auto-populates job title, first name, last name, email).
- Required sections: **Availability** (future date), **Resume Upload**
  (PDF/DOCX, ≤5 MB), **Declaration** checkbox.
- **Save Draft** stores in-progress applications; **Delete** hard-deletes
  drafts with a themed confirmation dialog.
- **Submit** requires all validations to pass; Apply is disabled if the
  candidate already has an active application for the same posting.
- **My Applications** dashboard lists every application with columns:
  Application ID, Job title, Date submitted, Status; empty state shown when
  the applicant has none.
- **Application Detail** page shows availability, resume, current status,
  and offers **Withdraw Application**, **Continue draft**, or
  **Schedule/Reschedule Interview** actions depending on the status.

### Staff view
- **All Applications** table with sortable column headers, keyword search
  (name / email / job title), and filter dropdowns for job title, status,
  and submitted date range.
- Row click → **Candidate Profile** page. Inline **Status** dropdown on
  each row updates the application status via HTMX; changing to `Rejected`
  triggers the "Remove from recruitment?" confirmation.
- Pending-interviews banner at the top of the table shows how many
  candidates are waiting to be scheduled or evaluated.
- **Interview** and **Evaluate** buttons appear on rows whose status is
  `Shortlisted` / `Interview Scheduled` (Interview) or
  `Interview Completed` (Evaluate); they deep-link to the student-4 and
  student-5 microservices respectively.

### AI-Mode (Frontend → Backend/API → Ollama → Llama)
- Endpoint: `POST /api/applications/<id>/screen`
- **PLAN → ACT → OBSERVE → ADAPT** workflow (see `backend/app.py`).
- Extracts resume text from PDFs with `pypdf`, combines it with the job
  posting details, and asks the LLM to return a suitability score
  (0–100), matched skills, skill gaps, and a one-line summary.
- The screening result is not persisted; it is regenerated on demand each
  time "Generate AI recommendation" is clicked.

## Database schema

`applications.db` (SQLite) contains one table:

- `applications` — one row per application. Statuses:
  `Draft`, `Submitted`, `Shortlisted`, `Interview Scheduled`,
  `Interview Completed`, `Evaluation Completed`, `Hired`, `Rejected`,
  `Withdrawn`. `resume_id` is a soft cross-service reference to student-1's
  `resumes.resume_id` (SQLite databases are per-service, so this isn't a real
  foreign key — the API layer is responsible for validating it).

The database is seeded with **12 applications** across the five seeded
applicant accounts and the twelve seeded job postings from student-2.

## Local run

```powershell
# from the FIND repo root
docker compose up --build student-3-frontend student-3-backend student-3-db
```

The full FIND stack (all students + shared services + AI-Mode) can be run
with `docker compose up --build`.

## Tests

```powershell
cd student-3
pip install -r tests/requirements.txt
python -m pytest tests -q
```

## Integration points

- **shared-api** (`/api/auth/session`) — session validation on every backend
  route; role (`applicant` / `staff`) drives UI visibility.
- **shared-db** — direct read access for candidate details (first name,
  last name, email) shown on the staff table.
- **student-1-db** — resume storage. The applicant's default profile resume
  is read from student-1's `resumes` table; a resume uploaded specifically
  for an application is written there too (with `profile_id` left `NULL`,
  since it isn't the profile's default resume).
- **student-2-db** — read access for job posting title / description /
  requirements used both by the apply form and the AI screening prompt.
- **student-4 (Interviews)** — deep-linked from the "Schedule Interview"
  action.
- **student-5 (Evaluations)** — deep-linked from the "Evaluate" action.
