from pathlib import Path
import sys

from flask import Flask
from flask_cors import CORS

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from routes.ai_mode import ai_mode_bp
from routes.interviews import interviews_bp
from services.config import FRONTEND_PUBLIC_URL, PORT


def create_app():
    app = Flask(__name__)
    # The HTMX front-end (a different origin) calls this API with the shared
    # session cookie, so credentialed CORS must be scoped to that origin and the
    # HX-* response headers must be exposed for HTMX to act on them.
    CORS(
        app,
        supports_credentials=True,
        origins=[FRONTEND_PUBLIC_URL],
        expose_headers=["HX-Redirect", "HX-Trigger"],
    )

    app.register_blueprint(interviews_bp)
    app.register_blueprint(ai_mode_bp)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)
