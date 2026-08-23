# Student 2 — Database microservice (Job Posting Management)

SQLite-backed Flask REST API. This is the only service that reads/writes the
`job_postings.db` file. The backend/API microservice calls it over HTTP.

- Container port: `6002`
- Host port: `16009` (canonical port table)
- Table: `job_postings` (seeded with 12 records — meets the 10-record minimum)

## Endpoints

| Method | Path | Description |
| ------ | ---- | ----------- |
| GET | `/health` | Health check |
| GET | `/job-postings` | List postings (filters: `status`, `job_type`, `location`, `q`) |
| GET | `/job-postings/{id}` | Get one posting |
| POST | `/job-postings` | Create a posting (JSON body) |
| PUT | `/job-postings/{id}` | Update a posting (JSON body) |
| PUT | `/job-postings/{id}/publish` | Publish a posting |
| PUT | `/job-postings/{id}/unpublish` | Return a posting to Draft |
| DELETE | `/job-postings/{id}` | Delete a posting |

## Run locally (without Docker)

```powershell
pip install -r requirements.txt
$env:DATA_DIR="./data"; python init_db.py
$env:DATA_DIR="./data"; python app.py
```

