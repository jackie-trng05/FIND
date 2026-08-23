"""Student 3 Frontend microservice (Application Management).

A small Flask server that renders the HTMX pages. The backend URL (used by
all HTMX ``hx-*`` attributes in the browser) is injected from an environment
variable so the same image works in any environment.

Pages:
  /                                  Applicant My Applications / Staff All Applications
  /apply/<job_posting_id>             Applicant apply / edit-draft form
  /applications/<application_id>      Applicant application detail page
  /applications/<application_id>/edit Applicant edit-draft page (Draft only)
  /staff/applications/<id>            Staff candidate profile page

Container port: 3003 (host port 16010 per the canonical port table).
"""

import os

from flask import Flask, render_template

app = Flask(__name__, static_folder="css", static_url_path="/css")

# The browser talks directly to the backend's host-mapped port.
BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:16011")
# Link back to the main FIND app (shared frontend dashboard).
HOME_URL = os.getenv("FIND_HOME_URL", "http://localhost:16001/dashboard")
# Link to the Job Postings page (student-2 frontend) for browsing.
JOB_POSTINGS_URL = os.getenv("JOB_POSTINGS_URL", "http://localhost:16007")
PORT = int(os.getenv("PORT", "3003"))


def _context(**extra):
    ctx = {
        "backend_url": BACKEND_PUBLIC_URL,
        "home_url": HOME_URL,
        "job_postings_url": JOB_POSTINGS_URL,
    }
    ctx.update(extra)
    return ctx


@app.get("/")
def index():
    return render_template("list.html", **_context())


@app.get("/apply/<int:job_posting_id>")
def apply(job_posting_id: int):
    return render_template("apply.html", **_context(job_posting_id=job_posting_id))


@app.get("/applications/<int:application_id>")
def application_detail(application_id: int):
    return render_template("detail.html", **_context(application_id=application_id))


@app.get("/staff/applications/<int:application_id>")
def staff_candidate_profile(application_id: int):
    return render_template(
        "candidate.html", **_context(application_id=application_id)
    )


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)
