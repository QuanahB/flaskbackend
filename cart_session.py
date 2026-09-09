"""
Helpers for the anonymous shopping cart.

The React client sends `credentials: "include"` so the browser stores Flask's
session cookie. We only stash `cart_id` in that cookie; the line items live in
SQL so they survive a server restart.
"""

from flask import session

from extensions import db
from models import Cart


def get_or_create_cart() -> Cart:
    """Return the cart for this browser session, creating one if needed."""
    cart_id = session.get("cart_id")
    # db.session.get is the SQLAlchemy 2 way; Query.get is deprecated.
    cart = db.session.get(Cart, cart_id) if cart_id else None

    if cart is None:
        cart = Cart()
        db.session.add(cart)
        db.session.commit()
        session["cart_id"] = cart.id

    return cart
