"""Shared configuration for the Student-5 (Evaluation) backend.

All downstream service URLs and the Ollama/AI-Mode settings are read from the
environment here so that both ``app.py`` and the AI-Mode blueprint import them
from a single source of truth.
"""

import os

SHARED_API_URL = os.environ.get("SHARED_API_URL", "http://find-shared-api:5000")
DB_SERVICE_URL = os.environ.get("DATABASE_SERVICE_URL", "http://find-student-5-db:6005")
APPLICATIONS_DB_URL = os.environ.get("APPLICATIONS_DB_URL", "http://student-3-db:6003")
POSTINGS_DB_URL = os.environ.get("POSTINGS_DB_URL", "http://student-2-db:6002")
SHARED_DB_URL = os.environ.get("SHARED_DB_URL", "http://find-shared-db:6000")
INTERVIEWS_DB_URL = os.environ.get("INTERVIEWS_DB_URL", "http://student-4-db:5002")

# Browser-facing URL of this backend, used when rendering HTMX fragments so the
# hx-* attributes point at an address the browser can reach (not the in-network
# container hostname).
BACKEND_PUBLIC_URL = os.environ.get("BACKEND_PUBLIC_URL", "http://localhost:16017")
# Browser-facing URL of the applications service (Student-3), for "View application" links.
APPLICATIONS_PUBLIC_URL = os.environ.get("APPLICATIONS_PUBLIC_URL", "http://localhost:16010")

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
