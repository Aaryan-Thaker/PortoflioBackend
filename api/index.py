# api/index.py
import logging
import os
from flask import Flask, jsonify
from flask_cors import CORS

# Import DB setup
from api.database.db import ensure_tables

# Auth system
from api.auth.routes import auth_bp

# Finance sections
from api.finance.routes import finance_bp          # For portfolio, transactions, valuation, etc.
from api.finance.risk import risk_bp               # For risk questionnaire endpoints

logging.basicConfig(level=logging.INFO)  # DEBUG locally, INFO in prod
logger = logging.getLogger(__name__)

DEFAULT_ALLOWED_ORIGINS = "http://localhost:3000,https://turiya-portfolio-platform.vercel.app"


def create_app(test_config=None):
    app = Flask(__name__)
    if test_config:
        app.config.update(test_config)

    # Resolve environment and secrets
    flask_env = os.environ.get("FLASK_ENV", "development").lower()
    secret_key = app.config.get("SECRET_KEY") or os.environ.get("FLASK_SECRET_KEY")

    if flask_env == "production":
        if not secret_key:
            raise ValueError("FLASK_SECRET_KEY environment variable must be set in production")
        app.secret_key = secret_key
    elif flask_env == "development":
        app.secret_key = secret_key or "dev_secret_key_change_in_production"
        if not secret_key:
            logger.warning("⚠️ Running in development with fallback secret key. Set FLASK_SECRET_KEY in production.")
    else:
        # e.g. testing or custom non-prod environments
        app.secret_key = secret_key or "dev_secret_key_change_in_production"

    # Configure CORS reading dynamically from ALLOWED_ORIGINS
    raw_origins = os.environ.get("ALLOWED_ORIGINS", DEFAULT_ALLOWED_ORIGINS)
    allowed_origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

    CORS(
        app,
        resources={r"/api/*": {"origins": allowed_origins}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    )

    # Register blueprints (no url_prefix to keep existing route names unchanged)
    app.register_blueprint(auth_bp)
    app.register_blueprint(finance_bp)
    app.register_blueprint(risk_bp)

    # Simple health check endpoint
    @app.route('/api/ping', methods=['GET'])
    def ping():
        return jsonify({'ping': 'pong'})

    # Ensure DB tables exist (skip during unit testing)
    if not app.config.get("TESTING"):
        try:
            ensure_tables()
        except Exception:
            logger.exception("Error ensuring tables at startup")

    return app


app = create_app()

if __name__ == '__main__':
    # Dev run only
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
