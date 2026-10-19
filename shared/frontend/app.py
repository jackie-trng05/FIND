from flask import Flask, render_template, send_from_directory, redirect
from flask_cors import CORS
import os

app = Flask(__name__, template_folder="templates", static_folder="static")

# B5 (Cloud Endpoint Security): restrict CORS to known origins instead of a
# wildcard. Falls back to same-origin only when ALLOWED_ORIGINS is unset.
ALLOWED_ORIGINS = [o for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o]
if ALLOWED_ORIGINS:
    CORS(app, origins=ALLOWED_ORIGINS)

# B5 (Cloud Endpoint Security): mark HSTS on only when served over TLS (cloud).
TLS_ENABLED = os.getenv("COOKIE_SECURE", "false").lower() == "true"

student_1_url = os.environ["STUDENT_1_FRONTEND_URL"]
student_2_url = os.environ["STUDENT_2_FRONTEND_URL"]
student_3_url = os.environ["STUDENT_3_FRONTEND_URL"]
student_4_url = os.environ["STUDENT_4_FRONTEND_URL"]
student_5_url = os.environ["STUDENT_5_FRONTEND_URL"]
shared_api_public_url = os.environ["SHARED_API_PUBLIC_URL"]


@app.after_request
def add_no_cache_headers(response):
    if response.content_type and "text/html" in response.content_type:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
    # B5 (Cloud Endpoint Security): defence-in-depth security headers.
    if TLS_ENABLED:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def index():
    return redirect("/login")


@app.get("/login")
def login_page():
    return render_template("login.html", shared_api_public_url=shared_api_public_url)


@app.get("/register")
def register_page():
    return render_template("register.html", shared_api_public_url=shared_api_public_url)


@app.get("/dashboard")
def dashboard_page():
    return render_template(
        "dashboard.html",
        student_1_url=student_1_url,
        student_2_url=student_2_url,
        student_3_url=student_3_url,
        student_4_url=student_4_url,
        student_5_url=student_5_url,
        shared_api_public_url=shared_api_public_url,
    )


@app.get("/css/<path:filename>")
def shared_css(filename):
    return send_from_directory("/app/shared-css", filename)


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "3000")), debug=debug)
