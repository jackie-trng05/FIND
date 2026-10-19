"""B5/B6 security control validation for FIND shared services.

Runs the shared-api (and shared-db seed) in-process with a mocked database and
asserts the Cloud Endpoint Security (B5) and Cloud Data Security (B6) controls.
Usage: python scripts/security-validation.py
"""

import importlib.util
import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}" + (f" -> {detail}" if detail else ""))


def load_module(path, name, env):
    os.environ.update(env)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# --- Load shared-api with a mocked database service ---------------------------
backend = load_module(
    os.path.join(ROOT, "shared", "backend", "app.py"),
    "find_shared_api",
    {
        "COOKIE_DOMAIN": "find.example.com",
        "ALLOWED_ORIGINS": "https://find.example.com,https://student-1.example.com",
        "COOKIE_SECURE": "true",
        "AUTH_RATE_LIMIT_MAX": "5",
        "AUTH_RATE_LIMIT_WINDOW": "60",
    },
)

# B6: hash the seed password the way the DB service does, then stub the DB.
stored_hash = backend.hash_password("apply123")
_db = {"email": "applicant1@email.com", "hash": stored_hash, "token": None}


class FakeResp:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


def fake_get(url, params=None, **kwargs):
    params = params or {}
    if url.endswith("/users/by-email"):
        if params.get("email") == _db["email"]:
            return FakeResp(200, {
                "user_id": 1, "user_email": _db["email"],
                "user_password_hash": _db["hash"], "user_role": "applicant",
                "user_first_name": "Emily", "user_last_name": "Johnson",
            })
        return FakeResp(404)
    if url.endswith("/sessions/by-token"):
        return FakeResp(200, {"user_id": 1})
    return FakeResp(404)


def fake_post(url, json=None, **kwargs):
    if url.endswith("/sessions"):
        _db["token"] = json["session_token"]
    return FakeResp(201, {"user_id": 1})


backend.requests = types.SimpleNamespace(get=fake_get, post=fake_post, delete=lambda *a, **k: FakeResp(200))
client = backend.app.test_client()

# --- B6: salted, non-reversible password hashing ------------------------------
check("B6 password hash is a salted KDF (scrypt/pbkdf2, not bare SHA-256)",
      stored_hash.split(":")[0] in ("scrypt", "pbkdf2", "argon2")
      and backend.verify_password(stored_hash, "apply123")
      and not backend.verify_password(stored_hash, "wrong"),
      stored_hash.split("$")[0])

check("B6 same password yields different hashes (random salt)",
      backend.hash_password("apply123") != backend.hash_password("apply123"))

# --- B5: valid login issues a Secure, HttpOnly, SameSite cookie ---------------
resp = client.post("/api/auth/login", json={"email": "applicant1@email.com", "password": "apply123"})
set_cookie = resp.headers.get("Set-Cookie", "")
check("B5 login succeeds (200)", resp.status_code == 200, f"HTTP {resp.status_code}")
check("B5 session cookie is HttpOnly", "HttpOnly" in set_cookie)
check("B5 session cookie is Secure", "Secure" in set_cookie)
check("B5 session cookie is SameSite=Lax", "SameSite=Lax" in set_cookie)

# --- B5: security headers present ---------------------------------------------
headers = resp.headers
check("B5 HSTS header present", headers.get("Strict-Transport-Security", "").startswith("max-age="))
check("B5 X-Content-Type-Options nosniff", headers.get("X-Content-Type-Options") == "nosniff")
check("B5 X-Frame-Options DENY", headers.get("X-Frame-Options") == "DENY")
check("B5 Referrer-Policy no-referrer", headers.get("Referrer-Policy") == "no-referrer")

# --- B5: wrong password rejected, no token leak -------------------------------
bad = client.post("/api/auth/login", json={"email": "applicant1@email.com", "password": "nope"})
check("B5 wrong password rejected (401)", bad.status_code == 401, f"HTTP {bad.status_code}")

# --- B5: per-IP rate limiting on auth endpoint --------------------------------
codes = [client.post("/api/auth/login",
                     json={"email": "x@y.com", "password": "z"}).status_code for _ in range(10)]
check("B5 auth endpoint rate-limited (429 after burst)", 429 in codes,
      f"status codes: {codes}")

# --- B6: legacy SHA-256 hashes still verify (safe migration) -------------------
import hashlib
legacy = hashlib.sha256("legacy-pass".encode()).hexdigest()
check("B6 legacy SHA-256 hash still verifies (graceful migration)",
      backend.verify_password(legacy, "legacy-pass")
      and not backend.verify_password(legacy, "other"))

# --- Summary ------------------------------------------------------------------
passed = sum(1 for _, ok, _ in RESULTS if ok)
total = len(RESULTS)
print(f"\n=== Security validation: {passed}/{total} checks passed ===")
sys.exit(0 if passed == total else 1)
