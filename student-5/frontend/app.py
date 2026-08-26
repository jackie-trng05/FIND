from flask import Flask, render_template, send_from_directory, request, redirect, Response, jsonify
from flask_cors import CORS
import os
import requests as http_requests

app = Flask(__name__, template_folder="templates")
CORS(app, supports_credentials=True)

BACKEND_PUBLIC_URL = os.environ.get("BACKEND_PUBLIC_URL", "http://localhost:16017")
FIND_HOME_URL = os.environ.get("FIND_HOME_URL", "http://localhost:16001/dashboard")
SHARED_API_PUBLIC_URL = os.environ.get("SHARED_API_PUBLIC_URL", "http://localhost:16002")
LOGIN_URL = os.environ.get("LOGIN_URL", "http://localhost:16001/login")
APPLICATIONS_PUBLIC_URL = os.environ.get("APPLICATIONS_PUBLIC_URL", "http://localhost:16010")


@app.context_processor
def inject_public_urls():
    return {
        "shared_api_url": SHARED_API_PUBLIC_URL,
        "login_url": LOGIN_URL,
        "applications_public_url": APPLICATIONS_PUBLIC_URL,
    }


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/")
def index():
    return render_template("evaluations.html",
                           backend_url=BACKEND_PUBLIC_URL,
                           home_url=FIND_HOME_URL)


@app.get("/evaluate/<int:application_id>")
def evaluation_form(application_id):
    return render_template("evaluation_form.html",
                           application_id=application_id,
                           backend_url=BACKEND_PUBLIC_URL,
                           home_url=FIND_HOME_URL)


@app.get("/edit/<int:evaluation_id>")
def edit_evaluation(evaluation_id):
    return render_template("evaluation_form.html",
                           evaluation_id=evaluation_id,
                           application_id=None,
                           backend_url=BACKEND_PUBLIC_URL,
                           home_url=FIND_HOME_URL)


@app.get("/css/<path:filename>")
def shared_css(filename):
    return send_from_directory("/app/shared-css", filename)


@app.get("/js/<path:filename>")
def shared_js(filename):
    return send_from_directory("/app/shared-js", filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3005, debug=True)
