"""Student 1 Backend/API microservice (User Profile Management).

Flask application that renders HTML fragments for the HTMX frontend and
proxies data operations to the student-1 database microservice, after
validating the shared session cookie against shared-api.

Container port 5001 (host port 16005 per the canonical port table).
"""

import os

from flask import Flask
from flask_cors import CORS

from routes.profile_pages import profile_bp
from routes.resume_pages import resume_bp
from routes.user_pages import user_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

    frontend_origin = os.getenv("FRONTEND_PUBLIC_URL", "http://localhost:16004")
    CORS(
        app,
        supports_credentials=True,
        origins=[frontend_origin],
        expose_headers=["HX-Redirect", "HX-Trigger"],
    )

    app.register_blueprint(user_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(resume_bp)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5001"))
    app.run(host="0.0.0.0", port=port, debug=True)
