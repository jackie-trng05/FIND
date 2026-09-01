"""Student 1 Backend/API microservice (User Profile Management).

Flask application that renders HTML fragments for the HTMX frontend and
proxies data operations to the student-1 database microservice, after
validating the shared session cookie against shared-api.

Container port 5001 (host port 16005 per the canonical port table).
"""

from flask import Flask
from flask_cors import CORS

from routes.ai_mode import ai_mode_bp
from routes.profiles import profiles_bp
from services.config import FRONTEND_PUBLIC_URL, MAX_FILE_SIZE, PORT


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE

    CORS(
        app,
        supports_credentials=True,
        origins=[FRONTEND_PUBLIC_URL],
        expose_headers=["HX-Redirect", "HX-Trigger"],
    )

    app.register_blueprint(profiles_bp)
    app.register_blueprint(ai_mode_bp)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)
