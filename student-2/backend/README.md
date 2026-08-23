# Student 2 — Backend/API microservice (Job Posting Management)

Flask app implementing `JobPostingService`. It renders HTML fragments for the
HTMX frontend, proxies data operations to the database microservice, and hosts
the AI-Mode endpoint that calls the approved LLM through Ollama.

- Container port: `5002`
- Host port: `16008` (canonical port table)

## Endpoints (JobPostingService)

| Method | Path | Description |
| ------ | ---- | ----------- |
| GET | `/health` | Health check |
| GET | `/job-postings?view=staff\|applicant` | List postings (filters: `status`, `job_type`, `location`, `q`) |
| GET | `/job-postings/{id}` | Posting details fragment |
| GET | `/job-postings/new` | Create-form fragment |
| GET | `/job-postings/{id}/edit` | Edit-form fragment |
| POST | `/job-postings` | Create posting |
| PUT | `/job-postings/{id}` | Update posting |
| PUT | `/job-postings/{id}/publish` | Publish posting |
| PUT | `/job-postings/{id}/unpublish` | Unpublish (back to Draft) |
| DELETE | `/job-postings/{id}` | Delete posting |
| POST | `/ai/suggest-skills` | AI: suggest skills & qualifications |

## AI-Mode — Plan -> Act -> Observe -> Adapt

`POST /ai/suggest-skills` demonstrates the shared agentic workflow:
**Plan** the prompt from the job details -> **Act** by calling Ollama ->
**Observe** the response -> **Adapt** with a stricter retry if it is too thin.

## Environment variables

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `PORT` | `5002` | Listen port |
| `DATABASE_SERVICE_URL` | `http://student-2-db:6002` | Database microservice |
| `BACKEND_PUBLIC_URL` | `http://localhost:16008` | URL the browser uses in HTMX attributes |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434/v1` | Ollama runtime |
| `OLLAMA_MODEL` | `qwen2.5:0.5b` | Approved open-source LLM |

