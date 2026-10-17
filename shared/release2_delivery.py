"""Collect genuine Release 2 delivery evidence without changing application code."""

import argparse
import ast
import base64
import hashlib
import io
import json
import secrets
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path

from shared import release2_reports as reports


REPOSITORY = "jackie-trng05/FIND"


class ResponseFragment(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.in_pre = False
        self.payload = []
        self.elements = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))
        if tag == "pre":
            self.in_pre = True

    def handle_endtag(self, tag):
        if tag == "pre":
            self.in_pre = False

    def handle_data(self, data):
        if self.in_pre:
            self.payload.append(data)


def integration_result(kind, response, workflow=None, student=None):
    text = response.text
    failures = ("request failed", "retrieval failed", "workflow failed", "not authenticated",
                "prompt templates are missing", "mode is disabled", "model call failed",
                "fallback reason", "model output could not", "review model unavailable", "alert-error")
    if response.status_code != 200 or any(marker in text.lower() for marker in failures):
        return "FAIL", "Non-success HTTP response or explicit service/model failure"
    if kind == "rag":
        try:
            payload = json.loads("".join(ResponseFragment(text).payload))
        except (ValueError, TypeError):
            return "FAIL", "RAG response did not contain a JSON retrieval result"
        chunks = payload.get("results", []) if isinstance(payload, dict) else []
        valid = (isinstance(payload, dict) and payload.get("status") == "success"
             and isinstance(chunks, list) and any(isinstance(chunk, dict) and chunk.get("text") and chunk.get("source_id") for chunk in chunks))
        return ("PASS", "Nonempty retrieved chunks returned through backend") if valid else ("FAIL", "No grounded retrieval chunks")
    if kind == "mcp":
        valid = "Citations</h4><ul" in text and "No citations" not in text
        return ("PASS", "Backend MCP context returned explicit source citations") if valid else ("FAIL", "Missing MCP source citations")
    if kind == "multi-agent":
        if not workflow:
            return "FAIL", "Backend response could not be linked to a persisted workflow"
        agents = [workflow.get(f"{role}_result", {}) for role in ("planner", "worker", "reviewer")]
        valid = (all(agent.get("status") in ("success", "completed") for agent in agents)
                 and workflow.get("worker_result", {}).get("evidence_count", 0) > 0
                 and not any(marker in json.dumps(agents).lower() for marker in failures))
        return ("PASS", f"Three agents and grounded evidence recorded; human decision remains {workflow.get('human_decision', {}).get('status', 'pending')}") if valid else ("FAIL", "Incomplete agents, missing evidence or model fallback")
    if kind == "ai-mode" and student:
        fragment = ResponseFragment(text)
        if student == "student-1":
            fields = {attrs.get("data-target"): attrs.get("data-value") for _, attrs in fragment.elements if attrs.get("data-target")}
            valid = (all(fields.get(name) for name in ("professional_title", "summary", "interests"))
                     and "engineer" in fields.get("professional_title", "").lower())
        elif student == "student-2":
            skills = [attrs.get("value", "") for tag, attrs in fragment.elements if tag == "input" and attrs.get("type") == "checkbox"]
            valid = len(skills) >= 3 and "python" in " ".join(skills).lower()
        elif student == "student-3":
            valid = "ai-recommendation-value" in text and "Reasoning" in text and "python" in text.lower()
        elif student == "student-4":
            valid = "python" in text.lower() and text.count("?") >= 2
        else:
            try:
                scores = json.loads(text)
                valid = (isinstance(scores, dict) and not scores.get("error") and len(scores.get("rationale", "")) >= 20
                         and all(type(scores.get(name)) is int and 1 <= scores[name] <= 5
                                 for name in ("technical", "education", "communication", "problem_solving", "professionalism")))
            except (ValueError, TypeError):
                valid = False
        return ("PASS", "Expected populated AI fields and synthetic-input terms returned; not human quality approval") if valid else ("FAIL", "AI prerequisites or required output fields were not satisfied")
    return "PENDING", "Response captured; feature-specific AI output requires inspection"


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


def collect_hook_preflight():
    arguments = [sys.executable, "-m", "pre_commit", "run", "--all-files", "--verbose"]
    result = subprocess.run(arguments, cwd=reports.ROOT, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=1200, check=False)
    output = result.stdout + result.stderr
    expected = [f"{tool}-scan-student-{number}" for number in range(1, 6) for tool in ("ruff", "detect-secrets", "pip-audit")]
    seen = [identifier for identifier in expected if f"- hook id: {identifier}" in output]
    status = "PASS" if result.returncode == 0 and len(seen) == 15 and "Skipped" not in output else "FAIL"
    evidence = reports.artifact("active-hook-preflight.txt", f"Command: {subprocess.list2cmdline(arguments)}\nExit: {result.returncode}\n\n{output}")
    reports.save_event("hook-preflight", "group", status, artifact=evidence,
                       summary={"hooks_seen": seen, "expected_count": 15, "exit_code": result.returncode,
                                "scope": "Active isolated student hook environments; not individual commit participation, broader manual scans, application manifests or container images"})
    print(f"Hook preflight: {status}; {len(seen)}/15 expected hooks observed; {evidence}")
    if status == "FAIL":
        raise ValueError("Hook preflight failed or expected hooks were missing; inspect retained transcript")


def collect_contributions():
    features = ("Applicant profiles", "Job postings", "Applications", "Interviews", "Candidate evaluations")
    for student, feature in zip(reports.STUDENTS, features):
        history = reports.git("log", "-12", "--format=%H%x09%an%x09%s", "--", student)
        commits = []
        for line in history.splitlines():
            commit, author, subject = line.split("\t", 2)
            commits.append({"commit": commit, "author": author, "subject": subject,
                            "url": f"https://github.com/{REPOSITORY}/commit/{commit}"})
        draft = {"student": student, "feature": feature, "timestamp": reports.now(), "status": "UNCONFIRMED DRAFT",
                 "scope": "Latest twelve commits touching this feature path. Merge commits may touch multiple features. Authors are not mapped to student identities; human confirmation is required.",
                 "commits": commits}
        evidence = reports.artifact(f"{student}-contribution-draft.json", json.dumps(draft, indent=2))
        reports.save_event("contribution-draft", student, "CAPTURED", artifact=evidence)
        inputs = reports.REPORTS / "inputs" / f"{student}-contribution.json"
        if not inputs.exists():
            reports.template("contribution", student)
        print(f"{student}: {len(commits)} actual path-scoped commits captured; human attribution PENDING")


def synthetic_resume():
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
                             NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
    lines = ("Release2 Evidence - synthetic candidate, not a real person", "QA Automation Engineer",
             "Experience: five years of Python, pytest, SQL and REST API testing.",
             "Designed automated regression tests and GitHub Actions pipelines.",
             "Education: Bachelor of Computer Science.",
             "Skills: Python, Flask, Docker, test automation, debugging and communication.",
             "Interests: software quality, accessible software and continuous integration.")
    stream = DecodedStreamObject()
    stream.set_data(("BT /F1 12 Tf 40 740 Td " + " 0 -18 Td ".join(f"({line}) Tj" for line in lines) + " ET").encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    content = output.getvalue()
    if "QA Automation Engineer" not in PdfReader(io.BytesIO(content)).pages[0].extract_text():
        raise ValueError("Synthetic resume did not round-trip as readable text")
    return content


def collect_integrations(sessions, checks, marker, posting_id, application_id, interview_id):
    import requests

    cases = (("student-1", "applicant", 16005, "/profile/ai-suggestions", {}, "/mcp/applicant-profile", {}),
             ("student-2", "staff", 16008, "/ai/suggest-skills", {"Job_Title": "QA Engineer", "Job_Description": "Python pytest Flask Docker"}, "/mcp/job-postings", {"query": marker, "status": "Draft"}),
             ("student-3", "staff", 16011, f"/api/applications/{application_id}/screen", {}, "/mcp/applications-for-job", {"job_posting_id": posting_id}),
             ("student-4", "staff", 16014, "/ask", {"question": "Name two Python QA interview questions. Use two sentences."}, "/mcp/interview-details", {"application_id": application_id}),
             ("student-5", "staff", 16017, "/api/ai/evaluation-recommendation", {"application_id": application_id}, "/mcp/evaluation-scores", {"application_id": application_id}))
    for student, role, port, ai_route, ai_data, mcp_route, mcp_data in cases:
        workflow_request = (f"Summarise interview {interview_id}. Do not make a hiring decision." if student == "student-4" else
                            f"Summarise the QA testing evidence for job posting {posting_id}, application {application_id}. Do not make a hiring decision.")
        routes = (("ai-mode", ai_route, ai_data), ("mcp", mcp_route, mcp_data),
                  ("rag", "/rag/retrieve", {"query": "Python QA automation testing", "k": 3}),
                  ("multi-agent", "/multi-agent/workflow", {"user_request": workflow_request}))
        for kind, route, payload in routes:
            url = f"http://localhost:{port}{route}"
            document = {"student": student, "kind": kind, "url": url, "timestamp": reports.now(),
                        "scope": "Authenticated backend integration, not browser interaction or human approval"}
            try:
                arguments = {"json": payload} if student == "student-5" and kind == "ai-mode" else {"data": payload}
                response = sessions[role].post(url, timeout=180, **arguments)
                workflow = None
                if kind == "multi-agent":
                    history = reports.ROOT / "multi-agent-server" / "workflow_history.jsonl"
                    workflows = [json.loads(line) for line in history.read_text(encoding="utf-8").splitlines() if line.strip()]
                    workflow = next((item for item in reversed(workflows) if item.get("caller") == student
                                     and item.get("workflow_id", "missing") in response.text), None)
                status, detail = integration_result(kind, response, workflow, student=student)
                document.update({"status": status, "detail": detail, "http_status": response.status_code,
                                 "response_sha256": hashlib.sha256(response.content).hexdigest(), "response_length": len(response.content)})
                if kind == "ai-mode":
                    document["response"] = response.text
                if workflow:
                    document["workflow_id"] = workflow["workflow_id"]
                if kind == "rag":
                    try:
                        retrieved = json.loads("".join(ResponseFragment(response.text).payload))
                        document["retrieval"] = {key: retrieved.get(key) for key in ("status", "retrieval_mode", "query_coverage", "error")}
                        document["sources"] = [item.get("source_id") for item in retrieved.get("results", [])]
                    except (ValueError, AttributeError):
                        document["retrieval"] = "Malformed retrieval response"
                if status == "FAIL":
                    document["error_excerpt"] = response.text[:500] if kind != "multi-agent" else detail
            except (requests.RequestException, OSError, ValueError) as error:
                status, detail = "FAIL", f"{type(error).__name__}: {str(error)[:250]}"
                document.update({"status": status, "detail": detail})
            evidence = reports.artifact(f"{student}-{kind}-integration.json", json.dumps(document, indent=2))
            checks[student][kind] = {"status": status, "evidence": evidence, "detail": detail}
            reports.save_event("integration", student, status, feature=kind, artifact=evidence,
                               summary={key: value for key, value in document.items() if key != "response"})
            print(f"{student} {kind}: {status}; {detail}", flush=True)


def collect_local(include_ai=False):
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
            upload = {"files": {"resume_file": ("synthetic-qa.pdf", synthetic_resume(), "application/pdf")}} if include_ai else {}
            call(applicant, "POST", "http://localhost:16011/api/applications/save", data={"job_posting_id": posting_id}, **upload)
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
            notes = marker + "-updated. Synthetic interview exercise: candidate explained pytest fixtures, REST API tests and Docker correctly. Candidate communicated clearly and described systematic debugging."
            call(staff, "PUT", f"http://localhost:16014/interviews/{interview_id}", json={"interview_notes": notes})
            saved = call(observer, "GET", f"http://localhost:16015/interviews/{interview_id}").json()
            verify("student-4", "update", saved["interview_notes"] == notes, "Backend note update persisted")

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
        if include_ai and all(identifier is not None for identifier in (profile_id, posting_id, application_id, interview_id, evaluation_id)):
            uploaded = call(applicant, "POST", "http://localhost:16005/resume", files={"file": ("synthetic-qa.pdf", synthetic_resume(), "application/pdf")})
            if "synthetic-qa.pdf" not in uploaded.text:
                raise ValueError("Profile resume upload was not confirmed by the backend")
            collect_integrations(sessions, checks, marker, posting_id, application_id, interview_id)
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
                        "scope": "Authenticated backend API CRUD with raw persistence reads. Not full UI interaction or business-lifecycle validation. Verify container provenance against the linked service/build evidence. A fixture application's status was reset directly only for cleanup.",
                        "residuals": "Two uniquely named example.invalid test accounts remain; no supported user-delete API. Passwords and session tokens are not retained.",
                        "operations": operations}
            artifact = reports.artifact(f"{student}-local-integration.json", json.dumps(document, indent=2))
            status = "FAIL" if any(item["status"] == "FAIL" for item in checks[student].values()) else "PENDING"
            reports.save_event("local", student, status, artifact=artifact, summary={"checks": checks[student], "fixture": marker})
            print(f"{student}: {status}; CRUD: " + ", ".join(f"{name}={checks[student][name]['status']}" for name in ("create", "read", "update", "delete")), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("ci", "regressions", "local", "local-ai", "hooks-preflight", "contributions"))
    arguments = parser.parse_args()
    try:
        if arguments.action == "ci":
            collect_ci()
        elif arguments.action == "regressions":
            collect_regressions()
        elif arguments.action == "hooks-preflight":
            collect_hook_preflight()
        elif arguments.action == "contributions":
            collect_contributions()
        elif arguments.action in ("local", "local-ai"):
            collect_local(include_ai=arguments.action == "local-ai")
    except (OSError, ValueError, KeyError, StopIteration, subprocess.SubprocessError) as error:
        parser.exit(1, f"Evidence collection failed: {error}\n")


if __name__ == "__main__":
    main()