"""Shared configuration and domain constants for the Application service.

Centralises environment-driven service URLs and the status/resume constants
used across the routes, services and views packages so they are defined once.
"""

import os

# --------------------------------------------------------------------------- #
# Browser-facing URLs (host-mapped ports the browser talks to directly)       #
# --------------------------------------------------------------------------- #
FRONTEND_PUBLIC_URL = os.getenv("FRONTEND_PUBLIC_URL", "http://localhost:16010")
BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:16011")
INTERVIEWS_URL = os.getenv("INTERVIEWS_PUBLIC_URL", "http://localhost:16013")
EVALUATIONS_URL = os.getenv("EVALUATIONS_PUBLIC_URL", "http://localhost:16016")

# --------------------------------------------------------------------------- #
# Internal service URLs (container network)                                   #
# --------------------------------------------------------------------------- #
DATABASE_SERVICE_URL = os.environ["DATABASE_SERVICE_URL"]
SHARED_API_URL = os.environ["SHARED_API_URL"]
SHARED_DB_URL = os.environ["SHARED_DB_URL"]
POSTINGS_DB_URL = os.environ["POSTINGS_DB_URL"]
STUDENT_1_DB_URL = os.environ["STUDENT_1_DB_URL"]
INTERVIEWS_DB_URL = os.getenv("INTERVIEWS_DB_URL", "http://student-4-db:6004")

PORT = int(os.getenv("PORT", "5003"))
TIMEOUT = 5

_DB_UNAVAILABLE = (
    "Could not reach the database service. Make sure the student-3-db "
    "container is running."
)

# --------------------------------------------------------------------------- #
# Application status constants                                                #
# --------------------------------------------------------------------------- #
VALID_STATUSES = (
    "Draft", "Submitted", "Shortlisted", "Interview Requested",
    "Interview Scheduled", "Interview Completed", "Evaluation Completed",
    "Hired", "Rejected", "Withdrawn",
)
WITHDRAWABLE_STATUSES = (
    "Submitted", "Shortlisted", "Interview Requested", "Interview Scheduled",
    "Interview Completed", "Evaluation Completed",
)
DELETABLE_STATUSES = ("Draft",)
INTERVIEW_ACTION_STATUSES = ("Shortlisted",)

# --------------------------------------------------------------------------- #
# Resume upload constraints                                                   #
# --------------------------------------------------------------------------- #
MAX_RESUME_BYTES = 5 * 1024 * 1024
ALLOWED_RESUME_MIME = {
    "application/pdf": "PDF",
}
ALLOWED_RESUME_EXTS = (".pdf",)
