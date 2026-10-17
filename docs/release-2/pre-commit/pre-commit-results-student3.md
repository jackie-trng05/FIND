# Pre-Commit Security Scan Report — student-3

**Project:** FIND
**Scope:** `student-3/` (per-student pre-commit hooks — Lab 11 Section 4, Testing Implementation)
**Generated:** 2026-10-17T11:53:52+11:00
**Tooling:** Ruff 0.17.1 · detect-secrets 1.5.0 · pip-audit 2.10.1 · pre-commit 4.7.0 · Python 3.12.10

## Run manually (before committing)

```bash
python -m pytest tests/lab11/pre_commit/test_ruff_scan_student3.py \
                 tests/lab11/pre_commit/test_secrets_scan_student3.py \
                 tests/lab11/pre_commit/test_dependency_audit_student3.py -v
```

```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.7.0 -- C:\Users\Gurnoor.Saini\OneDrive - WiseTech Global Pty Ltd\Documents\uni\FIND\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\Gurnoor.Saini\OneDrive - WiseTech Global Pty Ltd\Documents\uni\FIND
configfile: pyproject.toml
plugins: platformdirs-4.13.3
collecting ... collected 3 items

tests/lab11/pre_commit/test_ruff_scan_student3.py::test_ruff_scan_passes PASSED [ 33%]
tests/lab11/pre_commit/test_secrets_scan_student3.py::test_detect_secrets_scan_passes PASSED [ 66%]
tests/lab11/pre_commit/test_dependency_audit_student3.py::test_pip_audit_passes PASSED [100%]

============================== 3 passed in 6.87s ==============================
```

## Run automatically via git commit

```bash
git add student-3/...
git commit -m "..."   # Pre-commit hooks run automatically
```

**Captured hook output during an actual `git commit` (only `student-3` hooks fire; other students are skipped by `files: ^student-3/`):**

```text
Ruff Scan (student-1)................................(no files to check)Skipped
detect-secrets Scan (student-1)......................(no files to check)Skipped
pip-audit Scan (student-1)...........................(no files to check)Skipped
Ruff Scan (student-2)................................(no files to check)Skipped
detect-secrets Scan (student-2)......................(no files to check)Skipped
pip-audit Scan (student-2)...........................(no files to check)Skipped
Ruff Scan (student-3)....................................................Passed
detect-secrets Scan (student-3)..........................................Passed
pip-audit Scan (student-3)...............................................Passed
Ruff Scan (student-4)................................(no files to check)Skipped
detect-secrets Scan (student-4)......................(no files to check)Skipped
pip-audit Scan (student-4)...........................(no files to check)Skipped
Ruff Scan (student-5)................................(no files to check)Skipped
detect-secrets Scan (student-5)......................(no files to check)Skipped
pip-audit Scan (student-5)...........................(no files to check)Skipped
[chore/lab11-precommit-security-scans e51e64b] chore(student-3): lab11 pre-commit hook evidence (temp)
 1 file changed, 1 insertion(+)
 create mode 100644 student-3/LAB11_HOOKCHECK.tmp
```
