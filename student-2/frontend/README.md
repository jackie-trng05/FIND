# Student 2 — Frontend (Job Posting Management)

HTMX UI for the JobPostingService. A small Flask server renders the pages and
injects the backend URL used by the browser's HTMX requests.

## Pages

- **`/`** — admin list of all job postings in a table (filtered to Published by
  default). Filter by status, type, location, or keyword. A **+ New posting**
  button opens the create page.
- **`/new`** — create a job posting, alongside the AI "suggest skills &
  qualifications" helper (with a loading indicator).
- **`/postings/<id>`** — view a single posting and edit, publish/unpublish, or
  delete it.

Staff ID is assigned automatically by the backend, so it is not part of the
create/edit form.

## Run

```bash
pip install -r requirements.txt
python server.py            # serves on http://localhost:3002
```

Environment variables:

| Variable             | Default                  | Purpose                                |
| -------------------- | ------------------------ | -------------------------------------- |
| `PORT`               | `3002`                   | Port the server listens on             |
| `BACKEND_PUBLIC_URL` | `http://localhost:16008` | Backend URL the browser calls via HTMX |

In Docker Compose this is published on host port **16007**.

