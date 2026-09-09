"""
Cart routes — getCart / addToCart / updateCartItem / removeCartItem / clearCart.

All of these read/write the cart tied to the session cookie. React Router
SSR loaders must forward that Cookie header (see app/lib/session.ts).
"""

from flask import Blueprint, jsonify, request

from cart_session import get_or_create_cart
from extensions import db
from models import CartItem, Product
from serializers import cart_to_dict

cart_bp = Blueprint("cart", __name__)


@cart_bp.get("/cart")
def get_cart():
    """GET /api/cart — current cart, creating an empty one if this is a new session."""
    cart = get_or_create_cart()
    return jsonify(cart_to_dict(cart))


@cart_bp.delete("/cart")
def clear_cart():
    """DELETE /api/cart — remove every line (used after a successful checkout too)."""
    cart = get_or_create_cart()
    cart.items.clear()
    db.session.commit()
    return jsonify(message="Cart emptied")


@cart_bp.post("/cart/items")
def add_item():
    """POST /api/cart/items  body: { product_id, quantity? }  (AddToCartInput)."""
    body = request.get_json(silent=True) or {}
    product_id = body.get("product_id")
    quantity = int(body.get("quantity") or 1)

    if not product_id:
        return jsonify(message="product_id is required"), 400
    if quantity < 1:
        return jsonify(message="quantity must be at least 1"), 400

    product = db.session.get(Product, product_id)
    if product is None:
        return jsonify(message="Product not found"), 404

    cart = get_or_create_cart()
    existing = next((item for item in cart.items if item.product_id == product.id), None)
    new_qty = (existing.quantity if existing else 0) + quantity

    if new_qty > product.stock:
        return jsonify(message="Not enough stock for that quantity"), 400

    if existing:
        existing.quantity = new_qty
    else:
        # Append on the relationship so cart.items is current after commit.
        cart.items.append(
            CartItem(product_id=product.id, quantity=quantity)
        )

    db.session.commit()
    return jsonify(cart_to_dict(cart)), 201


@cart_bp.patch("/cart/items/<int:item_id>")
def update_item(item_id: int):
    """PATCH /api/cart/items/:id  body: { quantity }  (UpdateCartItemInput)."""
    body = request.get_json(silent=True) or {}
    quantity = body.get("quantity")
    if quantity is None:
        return jsonify(message="quantity is required"), 400

    quantity = int(quantity)
    cart = get_or_create_cart()
    item = next((row for row in cart.items if row.id == item_id), None)
    if item is None:
        return jsonify(message="Cart item not found"), 404

    if quantity < 1:
        # Treat 0 as a delete so the UI can send quantity 0 if it wants.
        db.session.delete(item)
        db.session.commit()
        return jsonify(cart_to_dict(cart))

    if quantity > item.product.stock:
        return jsonify(message="Not enough stock for that quantity"), 400

    item.quantity = quantity
    db.session.commit()
    return jsonify(cart_to_dict(cart))


@cart_bp.delete("/cart/items/<int:item_id>")
def remove_item(item_id: int):
    """DELETE /api/cart/items/:id"""
    cart = get_or_create_cart()
    item = next((row for row in cart.items if row.id == item_id), None)
    if item is None:
        return jsonify(message="Cart item not found"), 404

    db.session.delete(item)
    db.session.commit()
    return jsonify(cart_to_dict(cart))
