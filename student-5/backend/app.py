"""Student 5 Backend/API microservice (Candidate Evaluation).

Flask application that serves the evaluation JSON API and the HTML fragments
the HTMX frontend swaps in, proxying data operations to the student-5 database
service and validating sessions against the shared-api.

Container port 5005 (host port 16017 per the canonical port table).
"""

from pathlib import Path
import sys

from flask import Flask
from flask_cors import CORS

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from routes.ai_mode import ai_mode_bp
from routes.evaluations import evaluations_bp
from services.config import FRONTEND_PUBLIC_URL, PORT


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(
        app,
        resources={r"/api/*": {"origins": [FRONTEND_PUBLIC_URL, "http://localhost:16016"]}},
        supports_credentials=True,
        expose_headers=["HX-Redirect", "HX-Trigger"],
    )

    app.register_blueprint(evaluations_bp)
    app.register_blueprint(ai_mode_bp)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)
