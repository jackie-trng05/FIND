from flask import Flask, render_template, send_from_directory, redirect
from flask_cors import CORS
import os

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)


@app.after_request
def add_no_cache_headers(response):
    if response.content_type and "text/html" in response.content_type:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
    return response


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def index():
    return redirect("/login")


@app.get("/login")
def login_page():
    return render_template("login.html")


@app.get("/register")
def register_page():
    return render_template("register.html")


@app.get("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")


@app.get("/css/<path:filename>")
def shared_css(filename):
    return send_from_directory("/app/shared-css", filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
