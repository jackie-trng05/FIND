from flask import Flask, render_template, send_from_directory, request, redirect, Response, jsonify
from flask_cors import CORS
import os
import requests as http_requests

app = Flask(__name__, template_folder="templates")
CORS(app, supports_credentials=True)

BACKEND_PUBLIC_URL = os.environ.get("BACKEND_PUBLIC_URL", "http://localhost:16017")
FIND_HOME_URL = os.environ.get("FIND_HOME_URL", "http://localhost:16001/dashboard")


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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3005, debug=True)
