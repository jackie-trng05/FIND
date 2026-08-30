"""Shared fixtures for Student 5 (Evaluation) tests."""
import importlib.util
import os
import sqlite3
import sys

import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
STUDENT5_DIR = os.path.dirname(TESTS_DIR)

SHARED_API_URL = "http://shared-api.test"
DB_SERVICE_URL = "http://db-service.test"
APPLICATIONS_DB_URL = "http://applications-db.test"
POSTINGS_DB_URL = "http://postings-db.test"
SHARED_DB_URL = "http://shared-db.test"
INTERVIEWS_DB_URL = "http://interviews-db.test"
BACKEND_PUBLIC_URL = "http://backend.test"
FRONTEND_PUBLIC_URL = "http://frontend.test"
APPLICATIONS_PUBLIC_URL = "http://applications.test"
OLLAMA_BASE_URL = "http://ollama.test/v1"

os.environ.setdefault("SHARED_API_URL", SHARED_API_URL)
os.environ.setdefault("DATABASE_SERVICE_URL", DB_SERVICE_URL)
os.environ.setdefault("APPLICATIONS_DB_URL", APPLICATIONS_DB_URL)
os.environ.setdefault("POSTINGS_DB_URL", POSTINGS_DB_URL)
os.environ.setdefault("SHARED_DB_URL", SHARED_DB_URL)
os.environ.setdefault("INTERVIEWS_DB_URL", INTERVIEWS_DB_URL)
os.environ.setdefault("BACKEND_PUBLIC_URL", BACKEND_PUBLIC_URL)
os.environ.setdefault("FRONTEND_PUBLIC_URL", FRONTEND_PUBLIC_URL)
os.environ.setdefault("APPLICATIONS_PUBLIC_URL", APPLICATIONS_PUBLIC_URL)
os.environ.setdefault("OLLAMA_BASE_URL", OLLAMA_BASE_URL)
os.environ.setdefault("OLLAMA_MODEL", "test-model")

sys.path.insert(0, os.path.join(STUDENT5_DIR, "backend"))


def _load_module(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _create_schema(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS evaluations (
            Evaluation_Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Application_Id INTEGER NOT NULL,
            User_Id INTEGER NOT NULL,
            HR_Staff_Name TEXT NOT NULL,
            HR_Staff_Number TEXT NOT NULL,
            Evaluation_TechnicalScore INTEGER CHECK(Evaluation_TechnicalScore BETWEEN 1 AND 5),
            Evaluation_EducationScore INTEGER CHECK(Evaluation_EducationScore BETWEEN 1 AND 5),
            Evaluation_CommunicationScore INTEGER CHECK(Evaluation_CommunicationScore BETWEEN 1 AND 5),
            Evaluation_ProblemSolvingScore INTEGER CHECK(Evaluation_ProblemSolvingScore BETWEEN 1 AND 5),
            Evaluation_ProfessionalismScore INTEGER CHECK(Evaluation_ProfessionalismScore BETWEEN 1 AND 5),
            Evaluation_OverallScore REAL,
            Evaluation_FinalRecommendation TEXT CHECK(Evaluation_FinalRecommendation IN ('Hire', 'Reject')),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(Application_Id)
        )
    """)
    conn.commit()
    conn.close()


@pytest.fixture
def db_app(tmp_path):
    db_path = tmp_path / "student5_test.db"
    _create_schema(str(db_path))
    module = _load_module("student5_database_app", os.path.join(STUDENT5_DIR, "database", "app.py"))
    module.DATABASE_NAME = str(db_path)
    module.app.config.update(TESTING=True)
    return module.app


@pytest.fixture
def db_client(db_app):
    return db_app.test_client()


@pytest.fixture
def backend_app():
    module = _load_module("student5_backend_app", os.path.join(STUDENT5_DIR, "backend", "app.py"))
    module.app.config.update(TESTING=True)
    return module.app


@pytest.fixture
def backend_client(backend_app):
    return backend_app.test_client()


@pytest.fixture
def frontend_app():
    module = _load_module("student5_frontend_app", os.path.join(STUDENT5_DIR, "frontend", "app.py"))
    module.app.config.update(TESTING=True)
    return module.app


@pytest.fixture
def frontend_client(frontend_app):
    return frontend_app.test_client()


@pytest.fixture
def auth_headers(backend_client):
    backend_client.set_cookie("session_token", "test-session")
    return {}


STAFF_USER = {"user_id": 1, "role": "staff", "first_name": "Alex", "last_name": "Morgan"}
APPLICANT_USER = {"user_id": 2, "role": "applicant", "first_name": "Jane", "last_name": "Doe"}


def mock_session(requests_mock, user):
    requests_mock.get(f"{SHARED_API_URL}/api/auth/session", json={"user": user})


FULL_EVALUATION = {
    "Application_Id": 200,
    "HR_Staff_Name": "Alex Morgan",
    "HR_Staff_Number": "HR-001",
    "Evaluation_TechnicalScore": 4,
    "Evaluation_EducationScore": 3,
    "Evaluation_CommunicationScore": 5,
    "Evaluation_ProblemSolvingScore": 4,
    "Evaluation_ProfessionalismScore": 4,
    "Evaluation_FinalRecommendation": "Hire",
}

DRAFT_EVALUATION = {
    "Application_Id": 201,
    "HR_Staff_Name": "Alex Morgan",
    "HR_Staff_Number": "HR-001",
}
