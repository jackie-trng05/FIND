"""Student 1 Frontend microservice (User Profile Management).

A small Flask server that renders the HTMX page. The backend URL (used by all
HTMX hx-* attributes in the browser) is injected from an environment variable
so the same image works in any environment. The browser calls the backend
directly (cookie-based session, same convention as student-2/3) so this
server no longer proxies any API calls.

Container port 3000 (host port 16004 per the canonical port table).
"""

import os

from flask import Flask, render_template, send_from_directory

app = Flask(__name__, template_folder="templates")

BACKEND_PUBLIC_URL = os.environ["BACKEND_PUBLIC_URL"]
SHARED_API_PUBLIC_URL = os.environ["SHARED_API_PUBLIC_URL"]
LOGIN_URL = os.environ["LOGIN_URL"]
HOME_URL = os.environ["FIND_HOME_URL"]
PORT = int(os.getenv("PORT", "3000"))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def index():
    return render_template(
        "profile.html",
        backend_url=BACKEND_PUBLIC_URL,
        shared_api_public_url=SHARED_API_PUBLIC_URL,
        login_url=LOGIN_URL,
        home_url=HOME_URL,
    )


@app.get("/profile")
def profile_page():
    return index()


@app.get("/css/<path:filename>")
def serve_css(filename):
    return send_from_directory("/app/shared-css", filename)


@app.get("/js/<path:filename>")
def serve_js(filename):
    return send_from_directory("/app/shared-js", filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)

