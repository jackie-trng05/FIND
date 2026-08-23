# FIND

## Project Overview

FIND is a job application management system with multi-service application organised into shared services and individual student modules.

The repository is structured so that shared functionality can be developed separately from each student's implementation.


### Shared Services

The `shared/` directory contains services that are shared across the application:

```text
shared/
├── frontend/
├── backend/
└── database/
```

### Student Services

Each student has their own frontend, backend, and database service.

For example:

```text
student-1/
├── frontend/
├── backend/
└── database/
```

Additional students follow the same general structure:

```text
student-X/
├── frontend/
├── backend/
└── database/
```

The port assignments for each student follow the canonical port allocation on this README file.

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

# Quick Links

The following links provide quick access to the services for testing when the Docker containers are running.

### Shared Services

- **Shared Frontend:** http://localhost:16001
- **Shared API:** http://localhost:16002
- **Shared Database:** http://localhost:16003

### Student 1

- **Student 1 Frontend:** http://localhost:16004
- **Student 1 Backend:** http://localhost:16005
- **Student 1 Database:** http://localhost:16006

### Student 2

- **Student 2 Frontend:** http://localhost:16007
- **Student 2 Backend:** http://localhost:16008
- **Student 2 Database:** http://localhost:16009

### Student 3

- **Student 3 Frontend:** http://localhost:16010
- **Student 3 Backend:** http://localhost:16011
- **Student 3 Database:** http://localhost:16012

### Student 4

- **Student 4 Frontend:** http://localhost:16013
- **Student 4 Backend:** http://localhost:16014
- **Student 4 Database:** http://localhost:16015

### Student 5

- **Student 5 Frontend:** http://localhost:16016
- **Student 5 Backend:** http://localhost:16017
- **Student 5 Database:** http://localhost:16018

> **Note:** Student 2–5 links will only be available once their corresponding Docker containers have been implemented and added to `docker-compose.yml`.

---

# Canonical Port Assignments

The following table contains the canonical host and container port assignments for the shared services and all student modules.

The port mappings follow the course-provided architecture and should not be changed until discussed as a group.

| Module     | Service       | Host Port | Container Port | Container Implemented |
| ---------- | ------------- | --------: | -------------: | :-------------------: |
| Shared     | Frontend      |   `16001` |         `3000` |           Y           |
| Shared     | Backend / API |   `16002` |         `5000` |           Y           |
| Shared     | Database      |   `16003` |         `6000` |           Y           |
| Student 1  | Frontend      |   `16004` |         `3000` |           Y           |
| Student 1  | Backend       |   `16005` |         `5001` |           Y           |
| Student 1  | Database      |   `16006` |         `6001` |           Y           |
| Student 2  | Frontend      |   `16007` |         `3002` |           N           |
| Student 2  | Backend       |   `16008` |         `5002` |           N           |
| Student 2  | Database      |   `16009` |         `6002` |           N           |
| Student 3  | Frontend      |   `16010` |         `3003` |           N           |
| Student 3  | Backend       |   `16011` |         `5003` |           N           |
| Student 3  | Database      |   `16012` |         `6003` |           N           |
| Student 4  | Frontend      |   `16013` |         `3004` |           N           |
| Student 4  | Backend       |   `16014` |         `5004` |           N           |
| Student 4  | Database      |   `16015` |         `6004` |           N           |
| Student 5  | Frontend      |   `16016` |         `3005` |           N           |
| Student 5  | Backend       |   `16017` |         `5005` |           N           |
| Student 5  | Database      |   `16018` |         `6005` |           N           |

---

## Docker Desktop Is Not Running

If Docker commands work but Docker Compose cannot connect to Docker, check that Docker Desktop is running.

Start Docker Desktop and wait until it has finished starting before running:

```powershell
docker-compose up --build
```