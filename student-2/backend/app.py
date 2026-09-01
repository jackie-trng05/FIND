"""Student 2 Backend/API microservice (Job Posting Management).

Flask application exposing the JobPostingService. It renders HTML fragments for
the HTMX frontend and proxies data operations to the database microservice.
It also hosts the AI-Mode endpoint (skill/qualification suggestions) that calls
the approved open-source LLM through Ollama.

Container port: 5002 (host port 16008 per the canonical port table).
"""

from pathlib import Path
import sys

from flask import Flask
from flask_cors import CORS

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from routes.ai_mode import ai_mode_bp
from routes.job_postings import job_postings_bp
from services.config import FRONTEND_PUBLIC_URL, PORT


def create_app() -> Flask:
    app = Flask(__name__)
    # Frontend is served from a different origin (port 16007). We use cookies
    # for auth (same session cookie as the profile feature), so credentials
    # must be allowed and the origin must be specific (not "*").
    CORS(
        app,
        supports_credentials=True,
        origins=[FRONTEND_PUBLIC_URL],
        expose_headers=["HX-Redirect", "HX-Trigger"],
    )

    app.register_blueprint(job_postings_bp)
    app.register_blueprint(ai_mode_bp)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)
