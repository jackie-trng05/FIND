"""Student 3 Backend/API microservice (Application Management).

Flask application exposing the ApplicationService. It renders HTML fragments
for the HTMX frontend, proxies data operations to the database microservice,
validates the applicant/staff session against the shared-api, and hosts the
AI-Mode endpoint (candidate screening) that calls the approved open-source
LLM through Ollama.

Container port: 5003 (host port 16011 per the canonical port table).
"""

from pathlib import Path
import os
import sys

from flask import Flask
from flask_cors import CORS

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from routes.ai_mode import ai_mode_bp
from routes.applications import applications_bp
from routes.resumes import resumes_bp


def create_app() -> Flask:
    app = Flask(__name__)
    frontend_origin = os.getenv("FRONTEND_PUBLIC_URL", "http://localhost:16010")
    CORS(
        app,
        supports_credentials=True,
        origins=[frontend_origin],
        expose_headers=["HX-Redirect", "HX-Trigger"],
    )

    app.register_blueprint(applications_bp)
    app.register_blueprint(resumes_bp)
    app.register_blueprint(ai_mode_bp)
    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5003"))
    app.run(host="0.0.0.0", port=port, debug=True)
