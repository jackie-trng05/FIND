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
- **Save Filter** stores the current filter query string as a Favorite
  Filter for re-use across sessions.
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
- **PLAN → ACT → OBSERVE → ADAPT** workflow (see
  `backend/routes/ai_mode.py`).
- Extracts resume text from PDFs with `pypdf`, combines it with the job
  posting details, and asks the LLM to return a suitability score
  (0–100), matched skills, skill gaps, and a one-line summary.
- Result is cached in the `ai_screenings` table so re-opening the profile
  does not re-invoke the model.

## Database schema

`applications.db` (SQLite) contains four tables:

- `applications` — one row per application. Statuses:
  `Draft`, `Submitted`, `Shortlisted`, `Interview Scheduled`,
  `Interview Completed`, `Evaluation Completed`, `Hired`, `Rejected`,
  `Withdrawn`.
- `resumes` — BLOB storage for uploaded PDF/DOCX files.
- `ai_screenings` — cached AI screening results keyed by `Application_Id`.
- `favorite_filters` — staff-saved filter presets.

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
- **student-2-db** — read access for job posting title / description /
  requirements used both by the apply form and the AI screening prompt.
- **student-4 (Interviews)** — deep-linked from the "Schedule Interview"
  action.
- **student-5 (Evaluations)** — deep-linked from the "Evaluate" action.
