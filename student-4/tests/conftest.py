"""Pytest configuration for the Student 4 test suite.

Adds the database and backend service source folders to ``sys.path`` so the
tests can import the database service ``app`` and the backend
``routes``/``services``/``views`` packages directly.
"""

import os
import sys

STUDENT_4_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

sys.path.insert(0, os.path.join(STUDENT_4_DIR, "database"))
sys.path.insert(0, os.path.join(STUDENT_4_DIR, "backend"))
