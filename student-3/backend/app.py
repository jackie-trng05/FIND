"""Student 3 Backend/API microservice (Application Management).

Flask application that renders HTML fragments for the HTMX frontend, proxies
data operations to the student-3 database service, validates sessions against
the shared-api, and hosts an AI-Mode candidate screening endpoint (Ollama).

The application is composed from focused packages:
  * ``services`` - configuration, data access (own DB and other services'
                   DBs), LLM client, prompt loader
  * ``views``    - HTML fragment builders for HTMX
  * ``routes``   - request handlers grouped into blueprints

Container port 5003 (host 16011).
"""

from pathlib import Path
import sys

from flask import Flask
from flask_cors import CORS

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from routes.ai_mode import ai_mode_bp
from routes.applications import applications_bp
from services.config import FRONTEND_PUBLIC_URL, PORT


def create_app() -> Flask:
    app = Flask(__name__)
    # Frontend is served from a different origin (host port 16010). Auth uses a
    # shared session cookie, so credentials must be allowed and the origin must
    # be specific (not "*"). HX-Redirect/HX-Trigger are exposed for HTMX.
    CORS(
        app,
        supports_credentials=True,
        origins=[FRONTEND_PUBLIC_URL],
        expose_headers=["HX-Redirect", "HX-Trigger"],
    )

    app.register_blueprint(applications_bp)
    app.register_blueprint(ai_mode_bp)

    @app.get("/")
    def index():
        return "<p>student-3 backend (Application Management) running</p>", 200

    @app.get("/health")
    def health():
        return {"status": "ok"}, 200

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)
