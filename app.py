"""
Store API application factory.

Run from this directory (with the venv active):

    flask --app app --debug run --port 5000

The React storefront (port 5173) proxies /api here during development.
JSON shapes are defined in my-react-router-app/app/lib/types.ts.
"""

from pathlib import Path

# Load flaskbackend/.env before Config reads os.environ (Stripe keys, etc.).
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

import os

from flask import Flask, jsonify
from flask_cors import CORS

from config import Config
from extensions import db
from schema import ensure_sqlite_columns
from seed import seed_if_empty


def create_app() -> Flask:
    """Build the Flask app, database, CORS, and /api routes."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    # instance/ is Flask's local data dir (gitignored). SQLite lives there.
    os.makedirs(app.instance_path, exist_ok=True)
    db_path = os.path.join(app.instance_path, "store.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    db.init_app(app)

    # credentials=True is required because the React client sends cookies.
    CORS(
        app,
        origins=app.config["CORS_ORIGINS"],
        supports_credentials=True,
    )

    from routes.cart import cart_bp
    from routes.health import health_bp
    from routes.orders import orders_bp
    from routes.products import products_bp

    # url_prefix="/api" so paths match API_BASE_URL + "products", "cart", …
    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(products_bp, url_prefix="/api")
    app.register_blueprint(cart_bp, url_prefix="/api")
    app.register_blueprint(orders_bp, url_prefix="/api")

    @app.errorhandler(404)
    def not_found(_error):
        # Same { message } envelope ApiError reads in api.ts.
        return jsonify(message="Not found"), 404

    @app.errorhandler(400)
    def bad_request(_error):
        return jsonify(message="Bad request"), 400

    with app.app_context():
        # Import models so SQLAlchemy knows the tables before create_all().
        import models  # noqa: F401

        db.create_all()
        ensure_sqlite_columns()
        seed_if_empty()

    return app


# Lets `flask --app app run` work without writing create_app in the CLI.
app = create_app()
