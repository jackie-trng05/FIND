# Pre-Commit Security Scan Report — student-2

**Project:** FIND
**Scope:** `student-2/` (per-student pre-commit hooks — Testing Implementation)
**Generated:** 2026-10-17T11:53:52+11:00
**Tooling:** Ruff 0.17.1 · detect-secrets 1.5.0 · pip-audit 2.10.1 · pre-commit 4.7.0 · Python 3.12.10

## Run manually (before committing)

```bash
python -m pytest tests/pre_commit/test_ruff_scan_student2.py \
                 tests/pre_commit/test_secrets_scan_student2.py \
                 tests/pre_commit/test_dependency_audit_student2.py -v
```

```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.7.0 -- C:\Users\Gurnoor.Saini\OneDrive - WiseTech Global Pty Ltd\Documents\uni\FIND\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\Gurnoor.Saini\OneDrive - WiseTech Global Pty Ltd\Documents\uni\FIND
configfile: pyproject.toml
plugins: platformdirs-4.13.3
collecting ... collected 3 items

tests/pre_commit/test_ruff_scan_student2.py::test_ruff_scan_passes PASSED [ 33%]
tests/pre_commit/test_secrets_scan_student2.py::test_detect_secrets_scan_passes PASSED [ 66%]
tests/pre_commit/test_dependency_audit_student2.py::test_pip_audit_passes PASSED [100%]

============================== 3 passed in 7.41s ==============================
```

## Run automatically via git commit

```bash
git add student-2/...
git commit -m "..."   # Pre-commit hooks run automatically
```

**Captured hook output during an actual `git commit` (only `student-2` hooks fire; other students are skipped by `files: ^student-2/`):**

```text
Ruff Scan (student-1)................................(no files to check)Skipped
detect-secrets Scan (student-1)......................(no files to check)Skipped
pip-audit Scan (student-1)...........................(no files to check)Skipped
Ruff Scan (student-2)....................................................Passed
detect-secrets Scan (student-2)..........................................Passed
pip-audit Scan (student-2)...............................................Passed
Ruff Scan (student-3)................................(no files to check)Skipped
detect-secrets Scan (student-3)......................(no files to check)Skipped
pip-audit Scan (student-3)...........................(no files to check)Skipped
Ruff Scan (student-4)................................(no files to check)Skipped
detect-secrets Scan (student-4)......................(no files to check)Skipped
pip-audit Scan (student-4)...........................(no files to check)Skipped
Ruff Scan (student-5)................................(no files to check)Skipped
detect-secrets Scan (student-5)......................(no files to check)Skipped
pip-audit Scan (student-5)...........................(no files to check)Skipped
[chore/precommit-security-scans d8a38fb] chore(student-2): pre-commit hook evidence (temp)
 1 file changed, 1 insertion(+)
 create mode 100644 student-2/HOOKCHECK.tmp
```
