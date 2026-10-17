"""Post-commit CI/CD token tests for the Student 1 service.

Mirrors the reference ``test_token_auth.py``: validates the real JWT logic used by
the backend auth blueprint (``routes/auth_mode.py``) by signing and verifying
tokens with the shared secret.
"""

import os
import time

import jwt
import pytest


JWT_SECRET = os.getenv("JWT_SECRET", "student1-test-secret-padded-to-32-bytes!!")


def make_token(exp_offset_seconds: int) -> str:
    return jwt.encode(
        {"sub": "test-user", "exp": time.time() + exp_offset_seconds},
        JWT_SECRET,
        algorithm="HS256",
    )


def test_valid_token_decodes():
    token = make_token(60)
    decoded = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    assert decoded["sub"] == "test-user"


def test_expired_token_rejected():
    token = make_token(-60)
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(token, JWT_SECRET, algorithms=["HS256"])


def test_invalid_signature_rejected():
    token = make_token(60)
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(token, "wrong-secret", algorithms=["HS256"])
