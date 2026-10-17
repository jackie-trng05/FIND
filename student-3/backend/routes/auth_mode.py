"""JWT auth blueprint for the Student 3 backend.

Mirrors the reference enrolment-service ``routes/auth_mode.py``: a small token issue
and verify endpoint pair backed by PyJWT. The post-commit token tests
(``tests/post_commit/test_token_auth.py``) exercise the same JWT logic and
shared secret.
"""

import os
import time

import jwt
from flask import Blueprint, jsonify, request


auth_bp = Blueprint("auth_mode", __name__)

JWT_SECRET = os.getenv("JWT_SECRET", "student3-test-secret-padded-to-32-bytes!!")


@auth_bp.post("/auth/token")
def issue_token():
    token = jwt.encode(
        {"sub": "test-user", "exp": time.time() + 300},
        JWT_SECRET,
        algorithm="HS256",
    )
    return jsonify({"token": token}), 200


@auth_bp.get("/auth/verify")
def verify_token():
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        return jsonify({"error": str(exc)}), 401
    return jsonify({"sub": decoded["sub"]}), 200
