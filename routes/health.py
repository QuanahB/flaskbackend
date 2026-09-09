"""GET /api/health — used by the storefront home loader (getHealth)."""

from flask import Blueprint, jsonify
from sqlalchemy import text

from extensions import db

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health():
    """
    Confirm Flask is up and that SQLAlchemy can reach the SQLite file.

    Response shape matches HealthStatus in app/lib/types.ts.
    """
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify(status="ok", database="connected")
    except Exception as exc:  # pragma: no cover - defensive for a missing/locked DB
        return (
            jsonify(
                status="error",
                database="disconnected",
                message=str(exc),
            ),
            503,
        )
