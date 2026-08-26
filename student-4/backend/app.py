from pathlib import Path
import os
import sys

from flask import Flask
from flask_cors import CORS

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from routes.ai_mode import ai_mode_bp
from routes.normal_ui import normal_ui_bp


def create_app():
    app = Flask(__name__)
    # The HTMX front-end (a different origin) calls this API with the shared
    # session cookie, so credentialed CORS must be scoped to that origin and the
    # HX-* response headers must be exposed for HTMX to act on them.
    frontend_origin = os.getenv("FRONTEND_PUBLIC_URL", "http://localhost:16013")
    CORS(
        app,
        supports_credentials=True,
        origins=[frontend_origin],
        expose_headers=["HX-Redirect", "HX-Trigger"],
    )

    app.register_blueprint(normal_ui_bp)
    app.register_blueprint(ai_mode_bp)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
