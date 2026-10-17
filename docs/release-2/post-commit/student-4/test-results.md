============================= test session starts ==============================
platform linux -- Python 3.11.17, pytest-9.1.1, pluggy-1.7.0 -- /opt/hostedtoolcache/Python/3.11.17/x64/bin/python
cachedir: .pytest_cache
rootdir: /home/runner/work/FIND/FIND
configfile: pyproject.toml
collecting ... collected 6 items

tests/post_commit/test_api_interviews.py::test_service_health PASSED     [ 16%]
tests/post_commit/test_api_interviews.py::test_interviews_exist PASSED   [ 33%]
tests/post_commit/test_api_interviews.py::test_interview_by_id PASSED    [ 50%]
tests/post_commit/test_token_auth.py::test_valid_token_decodes PASSED    [ 66%]
tests/post_commit/test_token_auth.py::test_expired_token_rejected PASSED [ 83%]
tests/post_commit/test_token_auth.py::test_invalid_signature_rejected PASSED [100%]

=============================== warnings summary ===============================
student-4/tests/post_commit/test_token_auth.py::test_invalid_signature_rejected
  /opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/jwt/api_jwt.py:370: InsecureKeyLengthWarning: The HMAC key is 12 bytes long, which is below the minimum recommended length of 32 bytes for SHA256. See RFC 7518 Section 3.2.
    decoded = self.decode_complete(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
========================= 6 passed, 1 warning in 0.29s =========================
