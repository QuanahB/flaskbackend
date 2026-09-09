"""
Insert a starter catalog the first time the database is created.

Names/prices match the React mock-data.ts samples so the shop page looks
familiar when you switch from mocks to live SQL.
"""

from extensions import db
from models import Category, Product


def seed_if_empty() -> None:
    """No-op when products already exist, so restarting Flask does not duplicate rows."""
    if Product.query.first() is not None:
        return

    apparel = Category(name="Apparel", slug="apparel")
    goods = Category(name="Goods", slug="goods")
    db.session.add_all([apparel, goods])
    db.session.flush()  # assign category ids before products reference them

    db.session.add_all(
        [
            Product(
                name="Linen overshirt",
                slug="linen-overshirt",
                description="Light layer for warm weather.",
                price=88,
                stock=12,
                category_id=apparel.id,
            ),
            Product(
                name="Canvas tote",
                slug="canvas-tote",
                description="Everyday bag with a wide strap.",
                price=34,
                stock=24,
                category_id=goods.id,
            ),
            Product(
                name="Wool beanie",
                slug="wool-beanie",
                description="Ribbed knit, one size.",
                price=22,
                stock=40,
                category_id=apparel.id,
            ),
            Product(
                name="House soap",
                slug="house-soap",
                description="Cedar and bergamot bar.",
                price=12,
                stock=60,
                category_id=goods.id,
            ),
        ]
    )
    db.session.commit()
