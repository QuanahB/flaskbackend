"""
Shared Flask extensions.

Keeping SQLAlchemy here (instead of inside app.py) avoids circular imports:
models.py and route files can `from extensions import db` without importing
the Flask app object.
"""

from flask_sqlalchemy import SQLAlchemy

# All tables in models.py hang off this object. create_app() calls db.init_app(app).
db = SQLAlchemy()
