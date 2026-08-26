"""Shared fixtures for loading the Student 1 Flask services in isolation for testing."""
import importlib.util
import os
import sqlite3
import sys

import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
STUDENT1_DIR = os.path.dirname(TESTS_DIR)

SHARED_API_URL = "http://shared-api.test"
DATABASE_SERVICE_URL = "http://db-service.test"
BACKEND_PUBLIC_URL = "http://backend-service.test"
FRONTEND_PUBLIC_URL = "http://frontend-service.test"
SHARED_API_PUBLIC_URL = "http://shared-api-public.test"
LOGIN_URL = "http://frontend.test/login"
FIND_HOME_URL = "http://frontend.test/dashboard"

# These URLs are constant for the whole test run, so set them once here rather
# than per-test — the backend/frontend routes/services modules read them via
# os.environ at import time, and are only ever imported once per process.
os.environ.setdefault("SHARED_API_URL", SHARED_API_URL)
os.environ.setdefault("DATABASE_SERVICE_URL", DATABASE_SERVICE_URL)
os.environ.setdefault("BACKEND_PUBLIC_URL", BACKEND_PUBLIC_URL)
os.environ.setdefault("FRONTEND_PUBLIC_URL", FRONTEND_PUBLIC_URL)
os.environ.setdefault("SHARED_API_PUBLIC_URL", SHARED_API_PUBLIC_URL)
os.environ.setdefault("LOGIN_URL", LOGIN_URL)
os.environ.setdefault("FIND_HOME_URL", FIND_HOME_URL)

# Lets `import services`, `import views`, `import routes.*` resolve when
# backend/app.py (and its submodules) are loaded below.
sys.path.insert(0, os.path.join(STUDENT1_DIR, "backend"))


def _load_module(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _create_schema(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE profiles (
            profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            phone TEXT,
            location TEXT,
            professional_title TEXT,
            summary TEXT,
            interests TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE resumes (
            resume_id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER UNIQUE,
            file_name TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_data BLOB NOT NULL,
            uploaded_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            parsed_at TEXT,
            FOREIGN KEY (profile_id) REFERENCES profiles(profile_id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()


@pytest.fixture
def db_app(tmp_path):
    """Student 1 database service, pointed at a throwaway SQLite file per test."""
    db_path = tmp_path / "student1_test.db"
    _create_schema(str(db_path))
    module = _load_module("student1_database_app", os.path.join(STUDENT1_DIR, "database", "app.py"))
    module.DATABASE_NAME = str(db_path)
    module.app.config.update(TESTING=True)
    return module.app


@pytest.fixture
def db_client(db_app):
    return db_app.test_client()


@pytest.fixture
def backend_app():
    """Student 1 backend service (routes/views/services package)."""
    module = _load_module("student1_backend_app", os.path.join(STUDENT1_DIR, "backend", "app.py"))
    module.app.config.update(TESTING=True)
    return module.app


@pytest.fixture
def backend_client(backend_app):
    return backend_app.test_client()


@pytest.fixture
def frontend_app():
    """Student 1 frontend service (thin template-rendering server)."""
    module = _load_module("student1_frontend_app", os.path.join(STUDENT1_DIR, "frontend", "app.py"))
    module.app.config.update(TESTING=True)
    return module.app


@pytest.fixture
def frontend_client(frontend_app):
    return frontend_app.test_client()


@pytest.fixture
def auth_headers(backend_client):
    # Werkzeug's test client manages cookies via its own jar and drops a manually
    # passed Cookie header, so attach it via set_cookie instead.
    backend_client.set_cookie("session_token", "test-session")
    return {}


def mock_session(requests_mock, user):
    """Register a fake shared-api session response for the given user dict."""
    requests_mock.get(f"{SHARED_API_URL}/api/auth/session", json={"user": user})

