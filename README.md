# FIND

## Project Overview

FIND is a job application management system with multi-service application organised into shared services and individual student modules.

The repository is structured so that shared functionality can be developed separately from each student's implementation.

## Repository Conventions

FIND is maintained as one team-owned repository and one integrated application. Keep shared
functionality separate from student-owned features, and validate each feature before integrating
it into the complete application.

| Path | Responsibility |
| --- | --- |
| `.github/workflows/` | GitHub Actions and CI/CD workflows |
| `docs/` | Project documentation, architecture diagrams, and reports |
| `shared/` | Integrated home page, shared CSS, JavaScript, assets, and common configuration |
| `student-1/` through `student-5/` | Student-owned frontend, backend, database, tests, and Docker artefacts |
| `agentic_loop/` | Development-time architecture and service review tooling and prompts |
| `docker-compose.yml` | Shared local orchestration for the integrated application |

Feature-specific AI integrations belong to their owning student backend; `agentic_loop/` is
development tooling rather than a product service. Cloud deployment must target the complete
integrated application, with one shared deployment on Microsoft Azure or Amazon Web Services,
not individual student microservices.


<a id="project-structure"></a>

## Project Structure

```text
FIND/
├── .github/
│   └── workflows/
│       ├── student-1-ci.yml
│       ├── student-2-ci.yml
│       ├── student-3-ci.yml
│       ├── student-4-ci.yml
│       └── student-5-ci.yml
├── LICENSE
├── README.md
├── requirements.txt                  # root dependencies for dev tooling
├── docker-compose.yml                # integrated local service orchestration
│
├── agentic_loop/                     # review tool for architecture/service checks
│   ├── __init__.py
│   ├── agentic_loop.py               # runs the review loop from the repo root
│   ├── main.py                       # interactive menu for review modes
│   ├── README.md
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── architecture_collector.py # inspects Compose services and boundaries
│   │   ├── db_collector.py           # checks database service evidence
│   │   ├── devops_collector.py       # checks CI/CD workflow evidence
│   │   └── endpoints_collector.py    # checks API endpoint evidence
│   ├── config/
│   │   ├── __init__.py
│   │   └── review_config.py          # review modes, prompt paths, and models
│   ├── core/
│   │   ├── __init__.py
│   │   ├── ai_runner.py              # sends prompts to the configured LLM
│   │   ├── orchestrator.py           # runs observe -> implement -> review -> summary
│   │   ├── prompt_registry.py        # loads and validates prompt files
│   │   └── reporter.py               # prints review results and evidence
│   ├── pipelines/
│   │   ├── __init__.py
│   │   ├── architecture_pipeline.py  # architecture review steps
│   │   ├── devops_pipeline.py        # DevOps review steps
│   │   └── service_pipeline.py       # service implementation review steps
│   └── prompts/
│       ├── architecture/
│       │   ├── implementation/
│       │   │   ├── architecture_system_prompt.txt
│       │   │   └── architecture_task_prompt.txt
│       │   ├── review/
│       │   │   └── agent_review_prompt.txt
│       │   └── students/
│       │       ├── student-1/architecture_task_prompt.txt
│       │       ├── student-2/architecture_task_prompt.txt
│       │       ├── student-3/architecture_task_prompt.txt
│       │       ├── student-4/architecture_task_prompt.txt
│       │       └── student-5/architecture_task_prompt.txt
│       ├── devops/
│       │   ├── implementation/devops_pipeline_review_prompt.txt
│       │   └── review/devops_evidence_review_prompt.txt
│       └── service/
│           └── implementation/
│               ├── context_prompt.txt
│               ├── system_prompt.txt
│               └── task_prompt.txt
│
├── shared/                           # integrated application shell and services
│   ├── css/
│   │   └── theme.css
│   ├── backend/
│   │   ├── app.py                    # shared backend Flask entrypoint
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── database/
│   │   ├── app.py                    # shared database API service
│   │   ├── Dockerfile
│   │   ├── init_db.py                # creates shared tables and seed data
│   │   └── requirements.txt
│   └── frontend/
│       ├── app.py                    # shared frontend Flask entrypoint
│       ├── Dockerfile
│       ├── requirements.txt
│       ├── css/styles.css
│       ├── js/app.js
│       ├── static/js/
│       │   ├── auth.js
│       │   └── find-app.js
│       └── templates/
│           ├── dashboard.html
│           ├── index.html
│           ├── login.html
│           └── register.html
│
├── student-1/                        # profiles and resumes
│   ├── backend/
│   │   ├── app.py                    # profile backend entrypoint
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── prompts/
│   │   │   ├── system_prompt.txt
│   │   │   └── task_prompt.txt
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── ai_mode.py            # AI profile suggestions endpoint
│   │   │   └── profiles.py           # profile CRUD endpoints
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── config.py             # service URLs and settings
│   │   │   ├── database_api.py       # profile database client
│   │   │   ├── integration_api.py    # calls other FIND services
│   │   │   ├── llm_client.py         # Ollama/LLM client
│   │   │   └── prompt_loader.py      # reads prompt text files
│   │   └── views/
│   │       ├── __init__.py
│   │       └── html_formatters.py    # shared HTML response helpers
│   ├── database/
│   │   ├── app.py                    # profile database API
│   │   ├── Dockerfile
│   │   ├── init_db.py                # profile schema and resume seed setup
│   │   ├── requirements.txt
│   │   └── seed_data/resumes/
│   │       └── resume_profile_1.pdf ... resume_profile_10.pdf
│   ├── frontend/
│   │   ├── app.py                    # profile frontend entrypoint
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── templates/
│   │       ├── base.html
│   │       └── profile.html
│   └── tests/
│       ├── conftest.py
│       ├── requirements.txt
│       ├── test_backend.py
│       ├── test_database.py
│       └── test_frontend.py
│
├── student-2/                        # job postings
│   ├── backend/
│   │   ├── app.py                    # job posting backend entrypoint
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── prompts/
│   │   │   ├── system_prompt.txt
│   │   │   └── task_prompt.txt
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── ai_mode.py            # AI job posting helper endpoints
│   │   │   └── job_postings.py       # job posting CRUD endpoints
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── config.py             # service URLs and settings
│   │   │   ├── database_api.py       # job posting database client
│   │   │   ├── integration_api.py    # calls other FIND services
│   │   │   ├── llm_client.py         # Ollama/LLM client
│   │   │   └── prompt_loader.py      # reads prompt text files
│   │   └── views/
│   │       ├── __init__.py
│   │       └── html_formatters.py    # shared HTML response helpers
│   ├── database/
│   │   ├── app.py                    # job posting database API
│   │   ├── Dockerfile
│   │   ├── init_db.py                # job posting schema and seed data
│   │   ├── requirements.txt
│   │   └── data/.gitkeep
│   ├── frontend/
│   │   ├── app.py                    # job posting frontend entrypoint
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── css/styles.css
│   │   └── templates/
│   │       ├── base.html
│   │       ├── detail.html
│   │       ├── list.html
│   │       └── new.html
│   └── tests/
│       ├── conftest.py
│       ├── requirements.txt
│       ├── test_backend.py
│       └── test_database.py
│
├── student-3/                        # applications
│   ├── backend/
│   │   ├── app.py                    # application backend entrypoint
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── prompts/
│   │   │   ├── system_prompt.txt
│   │   │   └── task_prompt.txt
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── ai_mode.py            # AI application helper endpoints
│   │   │   └── applications.py       # application workflow endpoints
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── config.py             # service URLs and settings
│   │   │   ├── database_api.py       # application database client
│   │   │   ├── integration_api.py    # calls other FIND services
│   │   │   ├── llm_client.py         # Ollama/LLM client
│   │   │   └── prompt_loader.py      # reads prompt text files
│   │   └── views/
│   │       ├── __init__.py
│   │       └── html_formatters.py    # shared HTML response helpers
│   ├── database/
│   │   ├── app.py                    # application database API
│   │   ├── Dockerfile
│   │   ├── init_db.py                # application schema and seed data
│   │   └── requirements.txt
│   ├── frontend/
│   │   ├── app.py                    # application frontend entrypoint
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── css/styles.css
│   │   └── templates/
│   │       ├── apply.html
│   │       ├── base.html
│   │       ├── candidate.html
│   │       ├── detail.html
│   │       ├── list.html
│   │       └── fragments/
│   │           ├── application_detail.html
│   │           ├── apply_form.html
│   │           └── candidate_profile.html
│   └── tests/
│       ├── conftest.py
│       ├── requirements.txt
│       ├── test_backend.py
│       └── test_database.py
│
├── student-4/                        # interviews
│   ├── backend/
│   │   ├── app.py                    # interview backend entrypoint
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── prompts/
│   │   │   ├── system_prompt.txt
│   │   │   └── task_prompt.txt
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── ai_mode.py            # AI interview helper endpoints
│   │   │   └── interviews.py         # interview scheduling endpoints
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── config.py             # service URLs and settings
│   │   │   ├── database_api.py       # interview database client
│   │   │   ├── integration_api.py    # calls other FIND services
│   │   │   ├── llm_client.py         # Ollama/LLM client
│   │   │   └── prompt_loader.py      # reads prompt text files
│   │   └── views/
│   │       ├── __init__.py
│   │       └── html_formatters.py    # shared HTML response helpers
│   ├── database/
│   │   ├── app.py                    # interview database API
│   │   ├── Dockerfile
│   │   ├── init_db.py                # interview schema and seed data
│   │   └── requirements.txt
│   ├── frontend/
│   │   ├── app.py                    # interview frontend entrypoint
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── css/styles.css
│   │   └── templates/
│   │       ├── applications.html
│   │       ├── base.html
│   │       ├── details.html
│   │       ├── index.html
│   │       ├── list.html
│   │       ├── requests.html
│   │       ├── schedule.html
│   │       └── to-complete.html
│   └── tests/
│       ├── conftest.py
│       ├── requirements.txt
│       ├── test_backend.py
│       └── test_database.py
│
├── student-5/                        # evaluations
│   ├── backend/
│   │   ├── app.py                    # evaluation backend entrypoint
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── prompts/
│   │   │   ├── system_prompt.txt
│   │   │   └── task_prompt.txt
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── ai_mode.py            # AI evaluation helper endpoints
│   │   │   └── evaluations.py        # candidate evaluation endpoints
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── config.py             # service URLs and settings
│   │   │   ├── database_api.py       # evaluation database client
│   │   │   ├── integration_api.py    # calls other FIND services
│   │   │   ├── llm_client.py         # Ollama/LLM client
│   │   │   └── prompt_loader.py      # reads prompt text files
│   │   └── views/
│   │       ├── __init__.py
│   │       └── html_formatters.py    # shared HTML response helpers
│   ├── database/
│   │   ├── app.py                    # evaluation database API
│   │   ├── Dockerfile
│   │   ├── init_db.py                # evaluation schema and seed data
│   │   └── requirements.txt
│   ├── frontend/
│   │   ├── app.py                    # evaluation frontend entrypoint
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── templates/
│   │       ├── evaluation_form.html
│   │       └── evaluations.html
│   └── tests/
│       ├── conftest.py
│       ├── requirements.txt
│       ├── test_backend.py
│       ├── test_database.py
│       └── test_frontend.py
│
└── docs/
    └── release-0/reports/            # CI evidence reports
        └── student-1/ ... student-5/
            ├── pytest-output.txt
            ├── pytest-results.xml
            ├── report.json
            ├── report.md
            └── run-view.md
```


---

# Setup Instructions

## Prerequisites

FIND uses Docker and Docker Compose to build and run the application services.

Before running FIND, verify that Docker and Docker Compose are installed.

Open **PowerShell** and run:

```powershell
docker --version
docker-compose --version
```

If both commands return version information, Docker is installed.

### If Docker is Not Installed

If Docker or Docker Compose is not found, install **Docker Desktop**.

Run **PowerShell as Administrator** and enter:

```powershell
winget install -e --id Docker.DockerDesktop
```

> **Important:** Docker Desktop must be running before starting the FIND services.

If the commands are still not recognised after installation, restart PowerShell again and verify that Docker Desktop is running.

---

## Navigate to the Repository

Open PowerShell and navigate to the FIND repository:

```powershell
cd C:\git\FIND
```

> **Note:** Your individual Git repository path might be different. If so, replace `C:\git\FIND` with the path to your local FIND repository.

---

# How to Run

## Start FIND

Build the Docker images and start the services:

```powershell
docker-compose up --build
```

The first build may take some time because Docker needs to download the required base images and install service dependencies.

---

## Stop FIND

To stop and remove the containers created by Docker Compose:

```powershell
docker-compose down
```

To remove stopped containers:

```powershell
docker-compose rm -f
```


> **Note:** `docker-compose down` normally removes the containers created by the FIND Compose project. Use `docker-compose rm -f` when you specifically want to remove stopped service containers.

---

## Rebuild Containers

If you have changed a Dockerfile, dependencies, or Docker configuration, rebuild and recreate the containers with:

```powershell
docker-compose up --build --force-recreate
```

This will:

* rebuild the Docker images;
* recreate the containers;
* start the services using the newly built images.

---

# Quick Links and Canonical Port Assignments

The table below is the canonical list of host and container ports for the shared services and all student modules. Use the host-mapped ports when accessing services from a browser or the host machine.

The port mappings follow the course-provided architecture and should not be changed until discussed as a group.

| Module    | Service       | Host Port | Container Port | Quick Links |
| --------- | ------------- | --------: | -------------: | ----------- |
| Shared    | Frontend      |   `16001` |         `3000` | [Open](http://localhost:16001) |
| Shared    | Backend / API |   `16002` |         `5000` | [Open](http://localhost:16002) |
| Shared    | Database      |   `16003` |         `6000` | [Open](http://localhost:16003) |
| Student 1 | Frontend      |   `16004` |         `3000` | [Open](http://localhost:16004) |
| Student 1 | Backend       |   `16005` |         `5001` | [Open](http://localhost:16005) |
| Student 1 | Database      |   `16006` |         `6001` | [Open](http://localhost:16006) |
| Student 2 | Frontend      |   `16007` |         `3002` | [Open](http://localhost:16007) |
| Student 2 | Backend       |   `16008` |         `5002` | [Open](http://localhost:16008) |
| Student 2 | Database      |   `16009` |         `6002` | [Open](http://localhost:16009) |
| Student 3 | Frontend      |   `16010` |         `3003` | [Open](http://localhost:16010) |
| Student 3 | Backend       |   `16011` |         `5003` | [Open](http://localhost:16011) |
| Student 3 | Database      |   `16012` |         `6003` | [Open](http://localhost:16012) |
| Student 4 | Frontend      |   `16013` |         `3004` | [Open](http://localhost:16013) |
| Student 4 | Backend       |   `16014` |         `5004` | [Open](http://localhost:16014) |
| Student 4 | Database      |   `16015` |         `6004` | [Open](http://localhost:16015) |
| Student 5 | Frontend      |   `16016` |         `3005` | [Open](http://localhost:16016) |
| Student 5 | Backend       |   `16017` |         `5005` | [Open](http://localhost:16017) |
| Student 5 | Database      |   `16018` |         `6005` | [Open](http://localhost:16018) |

Database links are provided for local inspection and debugging only; they are not end-user entry points.

---

## Docker Desktop Is Not Running

If Docker commands work but Docker Compose cannot connect to Docker, check that Docker Desktop is running.

Start Docker Desktop and wait until it has finished starting before running:

```powershell
docker-compose up --build
```