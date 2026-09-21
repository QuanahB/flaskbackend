"""
SQLite does not add new columns when db.create_all() sees an existing table.

After we added Stripe ids on Order, older instance/store.db files need a
one-time ALTER TABLE. Harmless if the columns already exist.
"""

from sqlalchemy import inspect, text

from extensions import db


def ensure_sqlite_columns() -> None:
    inspector = inspect(db.engine)
    if "orders" not in inspector.get_table_names():
        return

    existing = {col["name"] for col in inspector.get_columns("orders")}
    statements = []
    if "stripe_checkout_session_id" not in existing:
        statements.append(
            "ALTER TABLE orders ADD COLUMN stripe_checkout_session_id VARCHAR(255)"
        )
    if "stripe_payment_intent_id" not in existing:
        statements.append(
            "ALTER TABLE orders ADD COLUMN stripe_payment_intent_id VARCHAR(255)"
        )

    if not statements:
        return

    with db.engine.begin() as conn:
        for sql in statements:
            conn.execute(text(sql))
