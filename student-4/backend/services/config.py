"""Environment-driven configuration for the Student 4 (Interview) backend.

Service URLs and AI-Mode settings are read from the environment here so
routes, services and views share a single source of truth.
"""

import os

# --------------------------------------------------------------------------- #
# Internal service URLs (container network)                                    #
# --------------------------------------------------------------------------- #
DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://student-4-db:6004")
SHARED_API_URL = os.getenv("SHARED_API_URL", "http://find-shared-api:5000")
SHARED_DB_URL = os.getenv("SHARED_DB_URL", "http://find-shared-db:6000")
APPLICATIONS_DB_URL = os.getenv("APPLICATIONS_DB_URL", "http://student-3-db:6003")
POSTINGS_DB_URL = os.getenv("POSTINGS_DB_URL", "http://student-2-db:6002")

# --------------------------------------------------------------------------- #
# Browser-facing URLs (host-mapped ports the browser talks to directly)        #
# --------------------------------------------------------------------------- #
FRONTEND_PUBLIC_URL = os.getenv("FRONTEND_PUBLIC_URL", "http://localhost:16013")
BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:16014")

# --------------------------------------------------------------------------- #
# AI-Mode (Ollama)                                                             #
# --------------------------------------------------------------------------- #
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")

PORT = int(os.getenv("PORT", "5004"))
TIMEOUT = 5
