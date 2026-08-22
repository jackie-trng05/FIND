from flask import Flask, render_template, send_from_directory, request, redirect, Response, make_response
from flask_cors import CORS
import os
import requests as http_requests

app = Flask(__name__, template_folder="templates")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
CORS(app, supports_credentials=True)

STUDENT1_BACKEND_URL = os.environ["STUDENT1_BACKEND_URL"]
COOKIE_DOMAIN = os.environ["COOKIE_DOMAIN"]
SHARED_API_URL = os.environ.get("SHARED_API_URL", "http://find-shared-api:5000")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def index():
    return redirect("/profile")


@app.get("/profile")
def profile_page():
    return render_template("profile.html")


@app.get("/css/<path:filename>")
def shared_css(filename):
    return send_from_directory("/app/shared-css", filename)


# --- Reverse proxy routes ---

def _proxy(path, **kwargs):
    url = f"{STUDENT1_BACKEND_URL}{path}"
    cookie_header = request.headers.get("Cookie", "")
    headers = {"Cookie": cookie_header}

    if request.content_type and "multipart/form-data" in request.content_type:
        resp = http_requests.request(
            method=request.method, url=url,
            headers=headers, files={
                key: (f.filename, f.stream, f.content_type)
                for key, f in request.files.items()
            }, data=request.form, params=request.args
        )
    elif request.is_json:
        headers["Content-Type"] = "application/json"
        resp = http_requests.request(
            method=request.method, url=url,
            headers=headers, json=request.get_json(), params=request.args
        )
    else:
        resp = http_requests.request(
            method=request.method, url=url,
            headers=headers, data=request.get_data(), params=request.args
        )

    excluded_headers = {"content-encoding", "transfer-encoding", "connection"}
    response_headers = {
        k: v for k, v in resp.headers.items() if k.lower() not in excluded_headers
    }
    return Response(resp.content, status=resp.status_code, headers=response_headers)


@app.route("/api/profiles", methods=["GET", "POST"])
def proxy_profiles():
    return _proxy("/api/profiles")


@app.route("/api/profiles/<path:subpath>", methods=["GET", "POST", "PUT", "DELETE"])
def proxy_profiles_sub(subpath):
    return _proxy(f"/api/profiles/{subpath}")


@app.route("/api/resumes/<path:subpath>", methods=["GET", "DELETE"])
def proxy_resumes(subpath):
    return _proxy(f"/api/resumes/{subpath}")


@app.route("/api/auth/logout", methods=["POST"])
def proxy_logout():
    cookie_header = request.headers.get("Cookie", "")
    http_requests.post(
        f"{SHARED_API_URL}/api/auth/logout",
        headers={"Cookie": cookie_header}
    )
    proxy_resp = make_response({"message": "Logged out"}, 200)
    proxy_resp.delete_cookie("session_token", domain=COOKIE_DOMAIN)
    return proxy_resp


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
