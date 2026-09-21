"""Checkout (Stripe) and order lookup — checkout() / getOrder() in api.ts."""

from flask import Blueprint, current_app, jsonify, request
import stripe

from cart_session import get_or_create_cart
from extensions import db
from models import Order, OrderItem
from serializers import order_to_dict
from stripe_payments import (
    configure_stripe,
    create_checkout_session,
    fulfill_paid_order,
    payment_session_is_paid,
)

orders_bp = Blueprint("orders", __name__)


@orders_bp.post("/checkout")
def checkout():
    """
    POST /api/checkout

    Body matches CheckoutInput (email + shipping).
    Creates a pending Order from the SQL cart, then a Stripe Checkout Session.
    Stock is not reduced and the cart is not emptied until Stripe confirms
    payment (webhook or GET /api/checkout/confirm).
    """
    error = configure_stripe()
    if error:
        return jsonify(message=error), 503

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

    for item in cart.items:
        if item.quantity > item.product.stock:
            return (
                jsonify(message=f"Not enough stock for {item.product.name}"),
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

    db.session.commit()
    # Re-load items/products for Stripe line_items after commit.
    db.session.refresh(order)

    try:
        session = create_checkout_session(order, cart)
    except stripe.StripeError as exc:
        return jsonify(message=getattr(exc, "user_message", None) or str(exc)), 502

    order.stripe_checkout_session_id = session.id
    db.session.commit()

    # Shape matches CheckoutStart in app/lib/types.ts
    return (
        jsonify(checkout_url=session.url, order=order_to_dict(order)),
        201,
    )


@orders_bp.get("/checkout/confirm")
def confirm_checkout():
    """
    GET /api/checkout/confirm?session_id=cs_test_...

    Used by the cart success page. Retrieves the session from Stripe (not from
    the query string trust) and fulfills the order if payment_status is paid.
    Idempotent with the webhook.
    """
    error = configure_stripe()
    if error:
        return jsonify(message=error), 503

    session_id = request.args.get("session_id")
    if not session_id:
        return jsonify(message="session_id is required"), 400

    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except stripe.StripeError as exc:
        return jsonify(message=getattr(exc, "user_message", None) or str(exc)), 502

    order = _order_from_session(session)
    if order is None:
        return jsonify(message="Order not found for this Stripe session"), 404

    if payment_session_is_paid(session):
        order = fulfill_paid_order(order, session)

    return jsonify(order_to_dict(order))


@orders_bp.post("/stripe/webhook")
def stripe_webhook():
    """
    POST /api/stripe/webhook

    Stripe CLI: stripe listen --forward-to localhost:5000/api/stripe/webhook
    Put the printed whsec_... in STRIPE_WEBHOOK_SECRET.
    """
    error = configure_stripe()
    if error:
        return jsonify(message=error), 503

    webhook_secret = current_app.config.get("STRIPE_WEBHOOK_SECRET") or ""
    if not webhook_secret:
        return jsonify(message="STRIPE_WEBHOOK_SECRET is not set"), 503

    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except (ValueError, stripe.SignatureVerificationError):
        return jsonify(message="Invalid Stripe webhook signature"), 400

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        # event object is a dict; retrieve to get a typed Session when needed.
        session_id = session.get("id")
        if session_id:
            full = stripe.checkout.Session.retrieve(session_id)
            order = _order_from_session(full)
            if order is not None and payment_session_is_paid(full):
                fulfill_paid_order(order, full)

    return jsonify(received=True)


@orders_bp.get("/orders/<int:order_id>")
def get_order(order_id: int):
    """GET /api/orders/:id — confirmation / tracking."""
    order = db.session.get(Order, order_id)
    if order is None:
        return jsonify(message="Order not found"), 404
    return jsonify(order_to_dict(order))


def _order_from_session(session: stripe.checkout.Session) -> Order | None:
    order = Order.query.filter_by(stripe_checkout_session_id=session.id).first()
    if order is not None:
        return order
    metadata = session.metadata or {}
    raw_id = metadata.get("order_id") or session.client_reference_id
    if not raw_id:
        return None
    return db.session.get(Order, int(raw_id))
