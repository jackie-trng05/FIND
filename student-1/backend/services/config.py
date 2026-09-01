"""Environment-driven configuration for the Student 1 (User Profile) backend.

Service URLs, AI-Mode settings and upload constraints are read from the
environment here so routes, services and views share a single source of truth.
"""

import os

# --------------------------------------------------------------------------- #
# Internal service URLs (container network)                                    #
# --------------------------------------------------------------------------- #
DATABASE_SERVICE_URL = os.environ["DATABASE_SERVICE_URL"]
SHARED_API_URL = os.environ["SHARED_API_URL"]

# --------------------------------------------------------------------------- #
# Browser-facing URLs (host-mapped ports the browser talks to directly)        #
# --------------------------------------------------------------------------- #
BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:16005")
FRONTEND_PUBLIC_URL = os.getenv("FRONTEND_PUBLIC_URL", "http://localhost:16004")

# --------------------------------------------------------------------------- #
# AI-Mode (Ollama)                                                             #
# --------------------------------------------------------------------------- #
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

PORT = int(os.getenv("PORT", "5001"))
TIMEOUT = 5

# --------------------------------------------------------------------------- #
# Resume upload constraints                                                    #
# --------------------------------------------------------------------------- #
ALLOWED_FILE_TYPES = {"application/pdf"}
MAX_FILE_SIZE = 5 * 1024 * 1024
