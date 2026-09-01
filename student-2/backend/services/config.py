"""Environment-driven configuration for the Student 2 (Job Posting) backend.

Service URLs, AI-Mode settings and shared constants are read from the
environment here so routes, services and views share a single source of truth.
"""

import os

# --------------------------------------------------------------------------- #
# Internal service URLs (container network)                                    #
# --------------------------------------------------------------------------- #
DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://student-2-db:6002")
SHARED_API_URL = os.getenv("SHARED_API_URL", "http://find-shared-api:5000")
# Student-3's (applications) database service, used to check whether the current
# applicant already has an application for a posting.
APPLICATIONS_DB_URL = os.getenv("APPLICATIONS_DB_URL", "http://student-3-db:6003")

# --------------------------------------------------------------------------- #
# Browser-facing URLs (host-mapped ports the browser talks to directly)        #
# --------------------------------------------------------------------------- #
BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:16008")
FRONTEND_PUBLIC_URL = os.getenv("FRONTEND_PUBLIC_URL", "http://localhost:16007")

# --------------------------------------------------------------------------- #
# AI-Mode (Ollama)                                                             #
# --------------------------------------------------------------------------- #
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")

PORT = int(os.getenv("PORT", "5002"))
TIMEOUT = 5

# Fallback owner id if a posting is somehow created without a session user.
DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "1")

DB_UNAVAILABLE = (
    "Could not reach the database service. Make sure the student-2-db "
    "container is running."
)
