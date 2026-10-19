# FIND Cloud Security Controls — B5 & B6 Evidence

This document maps the **B5 (Cloud Endpoint Security)** and **B6 (Cloud Data
Security)** criteria to the controls implemented in FIND, with configuration
references and validation evidence.

- **Repeatable validation:** [`scripts/security-validation.py`](../../../scripts/security-validation.py)
- **Captured run output:** [`security-validation-output.txt`](./security-validation-output.txt) — **13/13 checks passed**

---

## B5 — Cloud Endpoint Security

Controls protecting the exposed cloud frontend/API endpoints.

| Control | Implementation | Configuration reference |
| --- | --- | --- |
| TLS/HTTPS on every public endpoint | Azure Container Apps terminates TLS; all external FQDNs are `https://` | `ext()` helper in [`scripts/deploy-azure.sh`](../../../scripts/deploy-azure.sh) |
| Attack-surface reduction | Databases and all AI servers use **internal** ingress; only frontends + shared API are **external** | `deploy_app ... internal` calls in [`scripts/deploy-azure.sh`](../../../scripts/deploy-azure.sh) |
| CORS allow-list (no wildcard) | Shared API restricted to known frontend origins; shared frontend/db CORS gated behind `ALLOWED_ORIGINS` | [`shared/backend/app.py`](../../../shared/backend/app.py), [`shared/frontend/app.py`](../../../shared/frontend/app.py), [`shared/database/app.py`](../../../shared/database/app.py) |
| Secure session cookie | `HttpOnly`, `Secure` (cloud), `SameSite=Lax`, scoped `COOKIE_DOMAIN`, 24h expiry | `set_cookie(...)` in [`shared/backend/app.py`](../../../shared/backend/app.py); `COOKIE_SECURE=true` in [`scripts/deploy-azure.sh`](../../../scripts/deploy-azure.sh) |
| Security response headers | HSTS (TLS only), `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` | `set_security_headers` / `add_no_cache_headers` in the shared apps |
| Brute-force / credential-stuffing mitigation | Per-IP rate limiting on `/api/auth/login` and `/register` (429 after burst) | `_rate_limited(...)` in [`shared/backend/app.py`](../../../shared/backend/app.py) |
| No interactive debugger exposed | Flask debug mode is env-gated (`FLASK_DEBUG`), **off by default** in the cloud | `__main__` blocks in all shared apps |

## B6 — Cloud Data Security

Controls protecting cloud application data, secrets, credentials, and stored data.

| Control | Implementation | Configuration reference |
| --- | --- | --- |
| Strong password storage | Salted, memory-hard **scrypt** KDF (Werkzeug), replacing bare unsalted SHA-256; same password → different hashes | `hash_password` / `verify_password` in [`shared/backend/app.py`](../../../shared/backend/app.py); seeds in [`shared/database/init_db.py`](../../../shared/database/init_db.py) |
| Safe credential migration | Legacy SHA-256 hashes still verify, so existing data is not locked out during upgrade | `verify_password(...)` in [`shared/backend/app.py`](../../../shared/backend/app.py) |
| Secret management (no plaintext) | LLM API key injected as a Container Apps secret (`secretref:llm-api-key`), never an inline env var | `SECRET_ARGS` / `LLM_API_KEY=secretref:llm-api-key` in [`scripts/deploy-azure.sh`](../../../scripts/deploy-azure.sh) |
| No stored registry credentials | ACR pulls use a user-assigned **managed identity** granted `AcrPull` | `ACR_PULL_IDENTITY` block in [`scripts/deploy-azure.sh`](../../../scripts/deploy-azure.sh) |
| No long-lived cloud secret in CI | GitHub Actions authenticates to Azure via **OIDC federated credentials** | [`scripts/gh-secrets-setup.sh`](../../../scripts/gh-secrets-setup.sh) |
| Data-in-transit protection | Session cookie marked `Secure`; HSTS forces HTTPS | `COOKIE_SECURE=true` in [`scripts/deploy-azure.sh`](../../../scripts/deploy-azure.sh) |
| Encryption at rest | Container Apps / platform-managed storage is encrypted at rest by Azure by default | Azure platform control |

---

## Validation

Run locally (no cloud resources required — uses Flask's test client with a
mocked database):

```bash
python scripts/security-validation.py
```

Latest result (see [`security-validation-output.txt`](./security-validation-output.txt)):

```text
[PASS] B6 password hash is a salted KDF (scrypt/pbkdf2, not bare SHA-256) -> scrypt:32768:8:1
[PASS] B6 same password yields different hashes (random salt)
[PASS] B5 login succeeds (200) -> HTTP 200
[PASS] B5 session cookie is HttpOnly
[PASS] B5 session cookie is Secure
[PASS] B5 session cookie is SameSite=Lax
[PASS] B5 HSTS header present
[PASS] B5 X-Content-Type-Options nosniff
[PASS] B5 X-Frame-Options DENY
[PASS] B5 Referrer-Policy no-referrer
[PASS] B5 wrong password rejected (401)
[PASS] B5 auth endpoint rate-limited (429 after burst)
[PASS] B6 legacy SHA-256 hash still verifies (graceful migration)

=== Security validation: 13/13 checks passed ===
```

### Deployed-endpoint spot checks

After `scripts/deploy-azure.sh`, confirm the live controls against the public
entry point:

```bash
# TLS + security headers on the shared frontend
curl -sI https://shared-frontend.<envDefaultDomain>/health

# CORS allow-list on the shared API (rejected origin is not echoed back)
curl -s -I -H "Origin: https://evil.example" \
  https://shared-api.<envDefaultDomain>/health

# Secure/HttpOnly session cookie on login
curl -s -i -X POST https://shared-api.<envDefaultDomain>/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"applicant1@email.com","password":"apply123"}' | grep -i set-cookie
```

### Local environment note

All hardening is environment-driven so local `docker-compose` dev over plain
HTTP keeps working: `COOKIE_SECURE`/HSTS default to **off** locally and are set
to **true** in [`scripts/deploy-azure.sh`](../../../scripts/deploy-azure.sh);
`FLASK_DEBUG` defaults to **off** everywhere.
