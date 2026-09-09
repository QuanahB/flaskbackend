"""Checkout and order lookup — checkout() / getOrder() in api.ts."""

from flask import Blueprint, jsonify, request

from cart_session import get_or_create_cart
from extensions import db
from models import Order, OrderItem
from serializers import order_to_dict

orders_bp = Blueprint("orders", __name__)


@orders_bp.post("/checkout")
def checkout():
    """
    POST /api/checkout

    Body matches CheckoutInput: email + shipping fields.
    Creates an Order, decrements product stock, then empties the cart.
    """
    body = request.get_json(silent=True) or {}
    required = (
        "email",
        "shipping_name",
        "shipping_address",
        "shipping_city",
        "shipping_postal_code",
    )
    missing = [field for field in required if not body.get(field)]
    if missing:
        return jsonify(message=f"Missing fields: {', '.join(missing)}"), 400

    cart = get_or_create_cart()
    if not cart.items:
        return jsonify(message="Cart is empty"), 400

    # Fail the whole checkout if any line is over stock (no partial orders).
    for item in cart.items:
        if item.quantity > item.product.stock:
            return (
                jsonify(
                    message=f"Not enough stock for {item.product.name}",
                ),
                400,
            )

    subtotal = sum(float(item.product.price) * item.quantity for item in cart.items)
    order = Order(
        status="pending",
        total=round(subtotal, 2),
        currency=cart.items[0].product.currency or "USD",
        email=body["email"],
        shipping_name=body["shipping_name"],
        shipping_address=body["shipping_address"],
        shipping_city=body["shipping_city"],
        shipping_postal_code=body["shipping_postal_code"],
        shipping_country=body.get("shipping_country") or "US",
    )
    db.session.add(order)
    db.session.flush()

    for item in cart.items:
        db.session.add(
            OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.product.price,
            )
        )
        item.product.stock -= item.quantity

    cart.items.clear()
    db.session.commit()
    return jsonify(order_to_dict(order)), 201


@orders_bp.get("/orders/<int:order_id>")
def get_order(order_id: int):
    """GET /api/orders/:id — confirmation / tracking."""
    order = db.session.get(Order, order_id)
    if order is None:
        return jsonify(message="Order not found"), 404
    return jsonify(order_to_dict(order))
