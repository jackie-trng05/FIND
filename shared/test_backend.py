import ast
import importlib.util
import os
from pathlib import Path
import secrets
import unittest
from unittest.mock import patch

import requests
from flask import Flask


class SharedBackendTimeoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        specification = importlib.util.spec_from_file_location("shared_auth_backend", Path(__file__).parent / "backend" / "app.py")
        cls.backend = importlib.util.module_from_spec(specification)
        with patch.dict(os.environ, {"COOKIE_DOMAIN": "localhost", "ALLOWED_ORIGINS": "http://localhost:16001"}):
            specification.loader.exec_module(cls.backend)

    def test_auth_transport_failures_are_bounded_and_sanitised(self):
        fixture_password = secrets.token_urlsafe(12)
        routes = [
            ("post", "/api/auth/register", "post", {"email": "timeout@example.test", "password": fixture_password, "role": "applicant"}),
            ("post", "/api/auth/login", "get", {"email": "timeout@example.test", "password": fixture_password}),
            ("get", "/api/auth/session", "get", None),
            ("put", "/api/auth/user", "get", {"first_name": "Test", "last_name": "User"}),
            ("post", "/api/auth/logout", "delete", None),
        ]
        for method, route, upstream_method, payload in routes:
            for exception, expected in [(requests.Timeout, 504), (requests.ConnectionError, 503)]:
                with self.subTest(route=route, exception=exception), patch.object(self.backend.requests, upstream_method, side_effect=exception("private upstream details")) as mocked:
                    response = getattr(self.backend.app.test_client(), method)(route, json=payload, headers={"Authorization": "Bearer test-session"})
                    self.assertEqual(response.status_code, expected)
                    self.assertNotIn("private", response.get_data(as_text=True))
                    self.assertEqual(mocked.call_args.kwargs["timeout"], 5)

    def test_approved_launchers_do_not_force_debug(self):
        root = Path(__file__).resolve().parents[1]
        launchers = ["shared/backend", "shared/database", "shared/frontend",
                     "student-1/backend", "student-2/backend", "student-3/backend", "student-4/backend", "student-5/backend",
                     "student-1/database", "student-1/frontend", "student-2/database", "student-2/frontend",
                     "student-3/database", "student-3/frontend", "student-4/database", "student-5/database", "student-5/frontend"]
        for folder in launchers:
            with self.subTest(service=folder):
                tree = ast.parse((root / folder / "app.py").read_text(encoding="utf-8"))
                calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                         and isinstance(node.func, ast.Attribute) and node.func.attr == "run"
                         and isinstance(node.func.value, ast.Name) and node.func.value.id == "app"]
                self.assertEqual(len(calls), 1)
                startup = next(node for node in tree.body if isinstance(node, ast.If) and calls[0] in ast.walk(node))
                code = compile(ast.Module(body=startup.body, type_ignores=[]), str(root / folder / "app.py"), "exec")
                for value, expected in [(None, False), ("true", True)]:
                    with self.subTest(environment=value), patch.dict(os.environ), \
                            patch("flask.cli.load_dotenv", return_value=False), \
                            patch("werkzeug.serving.run_simple") as run_server, patch("flask.cli.show_server_banner"):
                        os.environ.pop("FLASK_DEBUG", None)
                        if value is not None:
                            os.environ["FLASK_DEBUG"] = value
                        exec(code, {"app": Flask("launcher_regression"), "os": os, "PORT": 5000})
                        self.assertEqual(run_server.call_args.kwargs["use_debugger"], expected)
                        self.assertEqual(run_server.call_args.kwargs["use_reloader"], expected)

    def test_flask_debug_is_off_by_default_and_allows_explicit_opt_in(self):
        for value, expected in [(None, False), ("1", True)]:
            with self.subTest(environment=value), patch.dict(os.environ):
                os.environ.pop("FLASK_DEBUG", None)
                if value is not None:
                    os.environ["FLASK_DEBUG"] = value
                application = Flask("launcher_regression")
                with patch("werkzeug.serving.run_simple") as run_server:
                    application.run(load_dotenv=False)
                self.assertEqual(run_server.call_args.kwargs["use_debugger"], expected)
                self.assertEqual(run_server.call_args.kwargs["use_reloader"], expected)


if __name__ == "__main__":
    unittest.main()