"""Shared fixtures for loading the Student 1 Flask services in isolation for testing."""
import importlib.util
import os
import sqlite3
import sys

import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
STUDENT1_DIR = os.path.dirname(TESTS_DIR)

SHARED_API_URL = "http://shared-api.test"
DB_SERVICE_URL = "http://db-service.test"
STUDENT1_BACKEND_URL = "http://backend-service.test"
COOKIE_DOMAIN = "localhost"


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
            profile_id INTEGER NOT NULL,
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
def backend_app(monkeypatch):
    """Student 1 backend service, with outbound URLs pointed at fake hosts for requests_mock."""
    monkeypatch.setenv("SHARED_API_URL", SHARED_API_URL)
    monkeypatch.setenv("DB_SERVICE_URL", DB_SERVICE_URL)
    module = _load_module("student1_backend_app", os.path.join(STUDENT1_DIR, "backend", "app.py"))
    module.app.config.update(TESTING=True)
    return module.app


@pytest.fixture
def backend_client(backend_app):
    return backend_app.test_client()


@pytest.fixture
def frontend_app(monkeypatch):
    """Student 1 frontend service, with its backend URL pointed at a fake host for requests_mock."""
    monkeypatch.setenv("STUDENT1_BACKEND_URL", STUDENT1_BACKEND_URL)
    monkeypatch.setenv("COOKIE_DOMAIN", COOKIE_DOMAIN)
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
