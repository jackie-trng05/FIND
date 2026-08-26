"""Student 2 Frontend microservice (Job Posting Management).

A small Flask server that renders the HTMX pages. The backend URL (used by all
HTMX ``hx-*`` attributes in the browser) is injected from an environment
variable so the same image works in any environment.

Pages:
  /                 admin list of all job postings (table)
  /new              create a new job posting (form + AI suggestions)
  /postings/<id>    view / edit / publish / delete a single posting

Container port: 3002 (host port 16007 per the canonical port table).
"""

import os

from flask import Flask, render_template, send_from_directory

app = Flask(__name__, template_folder="templates")
LOCAL_CSS_DIR = os.path.join(os.path.dirname(__file__), "css")


@app.get("/css/<path:filename>")
def serve_css(filename):
    # Local styles.css is served from this service; the shared theme.css comes
    # from the mounted shared-css volume (single source of truth).
    if os.path.exists(os.path.join(LOCAL_CSS_DIR, filename)):
        return send_from_directory(LOCAL_CSS_DIR, filename)
    return send_from_directory("/app/shared-css", filename)


@app.get("/js/<path:filename>")
def serve_js(filename):
    # Shared front-end runtime served from the mounted shared-js volume.
    return send_from_directory("/app/shared-js", filename)

# The browser talks directly to the backend's host-mapped port.
BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:16008")
# Link back to the main FIND app (shared frontend dashboard).
HOME_URL = os.getenv("FIND_HOME_URL", "http://localhost:16001/dashboard")
# Browser-facing shared auth + login URLs (used by base.html navbar script).
SHARED_API_PUBLIC_URL = os.getenv("SHARED_API_PUBLIC_URL", "http://localhost:16002")
LOGIN_URL = os.getenv("LOGIN_URL", "http://localhost:16001/login")
PORT = int(os.getenv("PORT", "3002"))


@app.context_processor
def inject_public_urls():
    return {"shared_api_url": SHARED_API_PUBLIC_URL, "login_url": LOGIN_URL}


@app.get("/")
def index():
    return render_template("list.html", backend_url=BACKEND_PUBLIC_URL, home_url=HOME_URL)


@app.get("/new")
def new_posting():
    return render_template("new.html", backend_url=BACKEND_PUBLIC_URL, home_url=HOME_URL)


@app.get("/postings/<int:posting_id>")
def posting_detail(posting_id: int):
    return render_template(
        "detail.html",
        backend_url=BACKEND_PUBLIC_URL,
        home_url=HOME_URL,
        posting_id=posting_id,
    )


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)
