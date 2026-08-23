"""Cross-service reads and writes for interview scheduling.

Interviews are linked to applications owned by Student 3. To keep services
independent, this module talks to the other students' *database containers*
directly over HTTP (never their backends):

  * Applications  -> Student 3 DB  (APPLICATION_DB_URL)
  * Job postings  -> Student 2 DB  (JOB_POSTING_DB_URL)
  * Users         -> shared DB     (SHARED_DB_URL)

It provides batch lookups used to enrich raw interview rows with applicant and
job-posting details, and a helper to keep the linked application's status in
sync with the interview lifecycle.
"""

import os

import requests

APPLICATION_DB_URL = os.getenv("APPLICATION_DB_URL", "http://student-3-db:6003")
JOB_POSTING_DB_URL = os.getenv("JOB_POSTING_DB_URL", "http://student-2-db:6002")
SHARED_DB_URL = os.getenv("SHARED_DB_URL", "http://find-shared-db:6000")

TIMEOUT = 5


# --------------------------------------------------------------------------- #
# Applications (Student 3 DB)                                                  #
# --------------------------------------------------------------------------- #

def list_applications(status=None):
    """All applications, optionally filtered by status. [] on failure."""
    try:
        params = {"status": status} if status else {}
        resp = requests.get(
            f"{APPLICATION_DB_URL}/applications", params=params, timeout=TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return []


def get_application(application_id):
    """A single application, or None if unavailable."""
    try:
        resp = requests.get(
            f"{APPLICATION_DB_URL}/applications/{application_id}", timeout=TIMEOUT
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


def set_application_status(application_id, status):
    """Sync the linked application's status. Returns True on success."""
    try:
        resp = requests.put(
            f"{APPLICATION_DB_URL}/applications/{application_id}",
            json={"Application_Status": status},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return True
    except requests.RequestException:
        return False


# --------------------------------------------------------------------------- #
# Job postings (Student 2 DB) & users (shared DB)                             #
# --------------------------------------------------------------------------- #

def _postings_by_id():
    try:
        resp = requests.get(f"{JOB_POSTING_DB_URL}/job-postings", timeout=TIMEOUT)
        resp.raise_for_status()
        return {str(p.get("JobPosting_Id")): p for p in resp.json()}
    except requests.RequestException:
        return {}


def _users_by_id():
    try:
        resp = requests.get(f"{SHARED_DB_URL}/users", timeout=TIMEOUT)
        resp.raise_for_status()
        return {str(u.get("user_id")): u for u in resp.json()}
    except requests.RequestException:
        return {}


def _full_name(user):
    if not user:
        return ""
    return f"{user.get('user_first_name', '')} {user.get('user_last_name', '')}".strip()


# --------------------------------------------------------------------------- #
# Enrichment                                                                   #
# --------------------------------------------------------------------------- #

def enrich_interviews(interviews):
    """Add applicant/job-posting/staff details onto raw interview rows.

    Resolves each interview's ``application_id`` -> application (Student 3) ->
    applicant + job posting, and each ``staff_id`` -> user name (shared DB).
    Missing services degrade gracefully to empty strings.
    """
    apps_by_id = {str(a.get("Application_Id")): a for a in list_applications()}
    postings = _postings_by_id()
    users = _users_by_id()

    enriched = []
    for row in interviews:
        item = dict(row)
        app = apps_by_id.get(str(row.get("application_id"))) or {}
        applicant_id = app.get("User_Id")
        posting_id = app.get("JobPosting_Id")
        posting = postings.get(str(posting_id)) or {}

        item["applicant_id"] = applicant_id or ""
        item["applicant_name"] = _full_name(users.get(str(applicant_id)))
        item["job_posting_id"] = posting_id or ""
        item["job_posting_title"] = posting.get("Job_Title", "")
        item["application_status"] = app.get("Application_Status", "")
        item["staff_name"] = _full_name(users.get(str(row.get("staff_id"))))
        enriched.append(item)
    return enriched


def enrich_one(interview):
    """Enrich a single interview row."""
    result = enrich_interviews([interview])
    return result[0] if result else dict(interview)


def shortlisted_for_staff(staff_id):
    """Shortlisted applications for job postings created by ``staff_id``.

    Returns a list of dicts shaped for the schedule/To-Schedule views. Postings
    ownership comes from Student 2's DB; if no postings match this staff member
    (e.g. seed IDs differ), all shortlisted applications are returned so the
    workflow is still demonstrable.
    """
    postings = _postings_by_id()
    users = _users_by_id()
    owned = {pid for pid, p in postings.items() if str(p.get("Staff_Id")) == str(staff_id)}

    apps = list_applications(status="Shortlisted")
    result = []
    for app in apps:
        posting_id = str(app.get("JobPosting_Id"))
        if owned and posting_id not in owned:
            continue
        posting = postings.get(posting_id) or {}
        result.append({
            "application_id": app.get("Application_Id"),
            "applicant_id": app.get("User_Id"),
            "applicant_name": _full_name(users.get(str(app.get("User_Id")))),
            "job_posting_id": app.get("JobPosting_Id"),
            "job_posting_title": posting.get("Job_Title", f"Posting #{posting_id}"),
            "application_status": app.get("Application_Status", "Shortlisted"),
        })
    return result
