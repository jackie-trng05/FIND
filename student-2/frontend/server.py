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

from flask import Flask, render_template

# Serve the css/ folder at /css so templates can link /css/*.css.
app = Flask(__name__, static_folder="css", static_url_path="/css")

# The browser talks directly to the backend's host-mapped port.
BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:16008")
# Link back to the main FIND app (shared frontend dashboard).
HOME_URL = os.getenv("FIND_HOME_URL", "http://localhost:16001/dashboard")
PORT = int(os.getenv("PORT", "3002"))


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
