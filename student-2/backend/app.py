"""Student 2 Backend/API microservice (Job Posting Management).

Flask application exposing the JobPostingService. It renders HTML fragments for
the HTMX frontend and proxies data operations to the database microservice.
It also hosts the AI-Mode endpoint (skill/qualification suggestions) that calls
the approved open-source LLM through Ollama.

Container port: 5002 (host port 16008 per the canonical port table).
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
from routes.job_postings import job_postings_bp


def create_app() -> Flask:
    app = Flask(__name__)
    # Frontend is served from a different origin (port 16007). We use cookies
    # for auth (same session cookie as the profile feature), so credentials
    # must be allowed and the origin must be specific (not "*").
    frontend_origin = os.getenv("FRONTEND_PUBLIC_URL", "http://localhost:16007")
    CORS(
        app,
        supports_credentials=True,
        origins=[frontend_origin],
        expose_headers=["HX-Redirect", "HX-Trigger"],
    )

    app.register_blueprint(job_postings_bp)
    app.register_blueprint(ai_mode_bp)
    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5002"))
    app.run(host="0.0.0.0", port=port, debug=True)
