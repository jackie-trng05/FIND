"""Collect genuine Release 2 delivery evidence without changing application code."""

import argparse
import ast
import base64
import hashlib
import json
import secrets
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from shared import release2_reports as reports


REPOSITORY = "jackie-trng05/FIND"


def command(*arguments, timeout=120):
    return subprocess.run(arguments, cwd=reports.ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", check=True, timeout=timeout).stdout


def collect_ci():
    runs = json.loads(command("gh", "api", f"repos/{REPOSITORY}/actions/runs?per_page=30"))["workflow_runs"]
    for student in reports.STUDENTS:
        run = next((item for item in runs if item["name"] == f"{student}-ci" and item["status"] == "completed"), None)
        if run is None:
            raise ValueError(f"No completed CI run found for {student}")
        commit = run["head_sha"]
        source = Path(tempfile.gettempdir()) / f"find-release2-ci-{run['id']}"
        if not (source / f"{student}-post-commit-evidence" / "test-audit.jsonl").exists():
            command("gh", "run", "download", str(run["id"]), "--repo", REPOSITORY, "--dir", str(source))
        reports.import_ci(student, source / f"{student}-post-commit-evidence", run["html_url"], commit)
        logs = command("gh", "run", "view", str(run["id"]), "--repo", REPOSITORY, "--log")
        paths = reports.git("ls-tree", "-r", "--name-only", commit, "--", f"{student}/tests/post_commit").splitlines()
        endpoint = next(path for path in paths if Path(path).name.startswith("test_api_") and path.endswith(".py"))
        response = json.loads(command("gh", "api", f"repos/{REPOSITORY}/contents/{endpoint}?ref={commit}"))
        code = base64.b64decode(response["content"]).decode("utf-8")
        functions = [{"name": node.name, "assertions": [ast.get_source_segment(code, statement)
                     for statement in ast.walk(node) if isinstance(statement, ast.Assert)]}
                     for node in ast.parse(code).body if isinstance(node, ast.FunctionDef)]
        artifact = reports.artifact(f"{student}-ci-workflow-and-coverage.txt",
            f"Run: {run['html_url']}\nTested commit: {commit}\nWorkflow conclusion: {run['conclusion']}\n"
            f"Endpoint test source: {endpoint}\n\n{code}\n\nWORKFLOW LOGS:\n{logs}")
        reports.save_event("ci-supporting", student, "CAPTURED", artifact=artifact, tested_commit=commit,
            summary={"workflow_conclusion": run["conclusion"], "endpoint_test_source": endpoint,
                     "functions": functions, "boundary": "database/API service; not authenticated-backend coverage"})
        captured = reports.latest(reports.read_events(), "ci", student)
        print(f"{student}: {captured['status']}; tested {commit}; "
              f"unit results {captured['summary'].get('unit_tests')}; "
              f"{len(captured['summary']['post_commit_tests'])} post-commit cases; full logs retained", flush=True)


def collect_regressions():
    commands = [("shared", [sys.executable, "-m", "unittest", "discover", "-s", "shared", "-p", "test_*.py", "-q"])]
    commands.extend((student, [sys.executable, "-m", "pytest", f"{student}/tests",
                              f"--ignore={student}/tests/post_commit", "-q"]) for student in reports.STUDENTS)
    results = []
    transcript = "Local isolated unit tests; not CI, cloud, browser or rebuilt-container validation.\n"
    for name, arguments in commands:
        try:
            result = subprocess.run(arguments, cwd=reports.ROOT, capture_output=True, text=True,
                                    encoding="utf-8", errors="replace", timeout=120, check=False)
            status = "PASS" if result.returncode == 0 else "FAIL"
            output = result.stdout + result.stderr
            transcript += f"\nCommand: {subprocess.list2cmdline(arguments)}\nExit: {result.returncode}\n{output}\n"
        except subprocess.TimeoutExpired:
            status, output = "FAIL", "Test execution timed out after 120 seconds"
            transcript += f"\n{name}: {output}\n"
        results.append({"suite": name, "status": status, "output_tail": output.splitlines()[-4:]})
        print(f"{name}: {status}; {' | '.join(output.splitlines()[-3:])}", flush=True)
    paths = reports.git("ls-files", "--cached", "--others", "--exclude-standard", "--", "*.py").splitlines()
    hashes = {name: hashlib.sha256((reports.ROOT / name).read_bytes()).hexdigest()
              for name in paths if (reports.ROOT / name).is_file()}
    transcript += "\nSource SHA256:\n" + json.dumps(hashes, indent=2)
    artifact = reports.artifact("all-students-local-regressions.txt", transcript)
    status = "PASS" if all(item["status"] == "PASS" for item in results) else "FAIL"
    reports.save_event("verification", "group", status, artifact=artifact,
                       summary={"suites": results, "source_sha256": hashes})
    if status == "FAIL":
        raise ValueError(f"Local regression failures retained in {reports.REPORTS / artifact}")


def collect_local():
    import requests

    marker = "release2-" + secrets.token_hex(6)
    auth = "http://localhost:16002/api/auth"
    sessions, users, checks, operations = {}, {}, {}, []
    profile_id = posting_id = application_id = interview_id = evaluation_id = None

    def call(session, method, url, **kwargs):
        response = session.request(method, url, timeout=20, **kwargs)
        operations.append({"method": method, "url": url, "status": response.status_code})
        response.raise_for_status()
        return response

    def verify(student, name, condition, detail):
        checks[student][name] = {"status": "PASS" if condition else "FAIL", "evidence": detail}
        if not condition:
            raise ValueError(f"{student}: {name}: {detail}")

    def exercise(student, action):
        try:
            action()
        except (ValueError, KeyError, IndexError, StopIteration, requests.RequestException) as error:
            checks[student]["create" if checks[student]["create"]["status"] == "PENDING" else "read"] = {
                "status": "FAIL", "evidence": f"{type(error).__name__}: {str(error)[:250]}"}
            print(f"{student}: FAIL: {type(error).__name__}: {str(error)[:250]}", flush=True)

    for student in reports.STUDENTS:
        checks[student] = {name: {"status": "PENDING", "evidence": "Not executed; human review is not automated"}
                           for name in reports.CHECKS["local"]}
    try:
        for role in ("staff", "applicant"):
            session = requests.Session()
            credentials = {"email": f"{marker}-{role}@example.invalid", "password": secrets.token_urlsafe(24),
                           "role": role, "first_name": "Release2", "last_name": "Evidence"}
            call(session, "POST", auth + "/register", json=credentials)
            login = call(session, "POST", auth + "/login", json=credentials).json()
            session.headers["Cookie"] = "session_token=" + login["token"]
            sessions[role], users[role] = session, login["user"]["user_id"]
        applicant, staff = sessions["applicant"], sessions["staff"]
        observer = requests.Session()

        def profile():
            nonlocal profile_id
            payload = {"phone": "0400000000", "location": marker, "professional_title": "QA Engineer",
                       "summary": "Synthetic evidence fixture only", "interests": "Testing"}
            call(applicant, "POST", "http://localhost:16005/profile", data=payload)
            saved = call(observer, "GET", f"http://localhost:16006/profiles/by-user/{users['applicant']}").json()
            profile_id = saved["profile_id"]
            verify("student-1", "create", saved["location"] == marker, "Authenticated backend create persisted its synthetic profile")
            read = call(applicant, "GET", "http://localhost:16005/profile")
            verify("student-1", "read", marker in read.text, "Authenticated backend returned the fixture profile")
            payload["location"] = marker + "-updated"
            call(applicant, "PUT", f"http://localhost:16005/profile/{profile_id}", data=payload)
            saved = call(observer, "GET", f"http://localhost:16006/profiles/{profile_id}").json()
            verify("student-1", "update", saved["location"] == payload["location"], "Backend update persisted the new location")

        def posting():
            nonlocal posting_id
            payload = {"Job_Title": marker, "Job_Description": "Synthetic QA automation position",
                       "Job_Type": "Full time", "Location": "Sydney", "Requirements": "Python and testing"}
            call(staff, "POST", "http://localhost:16008/job-postings", data=payload)
            saved = call(observer, "GET", "http://localhost:16009/job-postings", params={"q": marker}).json()
            fixture = next(item for item in saved if item["Job_Title"].lower() == marker)
            posting_id = fixture["JobPosting_Id"]
            verify("student-2", "create", fixture["User_Id"] == users["staff"], "Authenticated backend created the staff-owned fixture")
            read = call(staff, "GET", f"http://localhost:16008/job-postings/{posting_id}")
            verify("student-2", "read", marker.lower() in read.text.lower(), "Backend returned the fixture job panel")
            payload["Job_Description"] += " updated"
            call(staff, "PUT", f"http://localhost:16008/job-postings/{posting_id}", data=payload)
            saved = call(observer, "GET", f"http://localhost:16009/job-postings/{posting_id}").json()
            verify("student-2", "update", saved["Job_Description"] == payload["Job_Description"], "Backend update persisted the description")

        def application():
            nonlocal application_id
            call(applicant, "POST", "http://localhost:16011/api/applications/save", data={"job_posting_id": posting_id})
            rows = call(observer, "GET", "http://localhost:16012/applications", params={"user_id": users["applicant"]}).json()
            fixture = next(item for item in rows if item["job_posting_id"] == posting_id)
            application_id = fixture["application_id"]
            verify("student-3", "create", fixture["application_status"] == "Draft", "Applicant backend persisted a new Draft")
            read = call(applicant, "GET", f"http://localhost:16011/api/context/applications/{application_id}/detail").json()
            verify("student-3", "read", read.get("ok") is True, "Applicant detail context succeeded for its own fixture")
            call(applicant, "PUT", f"http://localhost:16011/api/applications/{application_id}/save",
                 data={"job_posting_id": posting_id, "declaration_accepted": "true"})
            saved = call(observer, "GET", f"http://localhost:16012/applications/{application_id}").json()
            verify("student-3", "update", bool(saved["declaration_accepted"]), "Backend draft update persisted declaration consent")

        def interview():
            nonlocal interview_id
            payload = {"application_id": application_id, "user_id": users["staff"],
                       "interview_datetime": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M"),
                       "interview_link": "https://example.invalid/interview", "interview_notes": marker}
            saved = call(staff, "POST", "http://localhost:16014/interviews", json=payload).json()
            interview_id = saved["interview_id"]
            verify("student-4", "create", int(saved["application_id"]) == application_id, "Authenticated backend created the synthetic linked interview")
            read = call(staff, "GET", f"http://localhost:16014/interviews/{interview_id}").json()
            verify("student-4", "read", read["interview_id"] == interview_id, "Backend read the created interview")
            call(staff, "PUT", f"http://localhost:16014/interviews/{interview_id}", json={"interview_notes": marker + "-updated"})
            saved = call(observer, "GET", f"http://localhost:16015/interviews/{interview_id}").json()
            verify("student-4", "update", saved["interview_notes"] == marker + "-updated", "Backend note update persisted")

        def evaluation():
            nonlocal evaluation_id
            payload = {"Application_Id": application_id, "Evaluation_TechnicalScore": 3}
            saved = call(staff, "POST", "http://localhost:16017/api/evaluations", json=payload).json()
            evaluation_id = saved["Evaluation_Id"]
            verify("student-5", "create", saved["User_Id"] == users["staff"], "Backend assigned the logged-in evaluator")
            read = call(staff, "GET", f"http://localhost:16017/api/evaluations/{evaluation_id}").json()
            verify("student-5", "read", read["Evaluation_Id"] == evaluation_id, "Backend read its synthetic evaluation")
            call(staff, "PUT", f"http://localhost:16017/api/evaluations/{evaluation_id}", json={"Evaluation_TechnicalScore": 4})
            saved = call(observer, "GET", f"http://localhost:16018/evaluations/{evaluation_id}").json()
            verify("student-5", "update", saved["Evaluation_TechnicalScore"] == 4, "Backend score update persisted")

        for student, action in zip(reports.STUDENTS, (profile, posting, application, interview, evaluation)):
            exercise(student, action)
    finally:
        observer = requests.Session()
        cleanup = (("student-4", "staff", 16014, "/interviews", 16015, "/interviews", interview_id),
               ("student-5", "staff", 16017, "/api/evaluations", 16018, "/evaluations", evaluation_id),
                   ("student-3", "applicant", 16011, "/api/applications", 16012, "/applications", application_id),
                   ("student-2", "staff", 16008, "/job-postings", 16009, "/job-postings", posting_id),
                   ("student-1", "applicant", 16005, "/profile", 16006, "/profiles", profile_id))
        for student, role, port, route, db_port, db_route, identifier in cleanup:
            if identifier is None:
                continue
            try:
                if student == "student-3":
                    call(observer, "PUT", f"http://localhost:16012/applications/{identifier}", json={"application_status": "Draft"})
                call(sessions[role], "DELETE", f"http://localhost:{port}{route}/{identifier}")
                deleted = observer.get(f"http://localhost:{db_port}{db_route}/{identifier}", timeout=20)
                operations.append({"method": "GET", "url": deleted.url, "status": deleted.status_code})
                verify(student, "delete", deleted.status_code == 404, "Authenticated backend deletion verified absent in persistence service")
            except (ValueError, requests.RequestException) as error:
                checks[student]["delete"] = {"status": "FAIL", "evidence": f"Cleanup failure: {type(error).__name__}: {str(error)[:250]}"}
        for session in sessions.values():
            try:
                call(session, "POST", auth + "/logout")
            except requests.RequestException:
                operations.append({"cleanup": "Session logout failed; temporary session may remain until expiry"})
            session.close()
        for student in reports.STUDENTS:
            document = {"collector": "GitHub Copilot automated integration check, not human sign-off", "timestamp": reports.now(),
                        "fixture": marker, "test_user_ids": users, "checks": checks[student],
                        "scope": "Authenticated backend API CRUD with raw persistence reads. Not full UI interaction or business-lifecycle validation. Existing Docker images were not rebuilt. A fixture application's status was reset directly only for cleanup.",
                        "residuals": "Two uniquely named example.invalid test accounts remain; no supported user-delete API. Passwords and session tokens are not retained.",
                        "operations": operations}
            artifact = reports.artifact(f"{student}-local-integration.json", json.dumps(document, indent=2))
            status = "FAIL" if any(item["status"] == "FAIL" for item in checks[student].values()) else "PENDING"
            reports.save_event("local", student, status, artifact=artifact, summary={"checks": checks[student], "fixture": marker})
            print(f"{student}: {status}; CRUD: " + ", ".join(f"{name}={checks[student][name]['status']}" for name in ("create", "read", "update", "delete")), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("ci", "regressions", "local"))
    arguments = parser.parse_args()
    try:
        if arguments.action == "ci":
            collect_ci()
        elif arguments.action == "regressions":
            collect_regressions()
        elif arguments.action == "local":
            collect_local()
    except (OSError, ValueError, KeyError, StopIteration, subprocess.SubprocessError) as error:
        parser.exit(1, f"Evidence collection failed: {error}\n")


if __name__ == "__main__":
    main()