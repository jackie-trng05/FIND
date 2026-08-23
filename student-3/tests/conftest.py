"""Pytest configuration for the Student 3 test suite.

Adds the database and backend service source folders to ``sys.path`` so the
tests can import ``app`` (database service) and the backend view/service
modules directly, and points the database service at a temporary data folder
so tests never touch the seeded container database.
"""

import os
import sys
import tempfile

STUDENT_3_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Isolate the database service's SQLite file before it is imported.
_TMP_DATA = tempfile.mkdtemp(prefix="student3-test-")
os.environ.setdefault("DATA_DIR", _TMP_DATA)

sys.path.insert(0, os.path.join(STUDENT_3_DIR, "database"))
sys.path.insert(0, os.path.join(STUDENT_3_DIR, "backend"))
