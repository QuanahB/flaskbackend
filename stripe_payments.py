"""
Stripe helpers for the store API.

Secret key stays here (Flask). The React app only receives a checkout_url
and redirects the shopper to Stripe-hosted Checkout.

Amounts: our Product.price is major units (88.00). Stripe wants cents (8800).
"""

from flask import current_app
import stripe

from extensions import db
from models import Cart, Order


def dollars_to_cents(amount) -> int:
    return int(round(float(amount) * 100))


def configure_stripe() -> str:
    """Set the SDK key from config. Returns an error message, or "" if ready."""
    secret = current_app.config.get("STRIPE_SECRET_KEY") or ""
    if not secret:
        return "STRIPE_SECRET_KEY is missing. Add sk_test_... to flaskbackend/.env"
    stripe.api_key = secret
    return ""


def create_checkout_session(order: Order, cart: Cart) -> stripe.checkout.Session:
    """
    Build a Stripe Checkout Session from the SQL cart — never from a browser total.

    success_url includes {CHECKOUT_SESSION_ID}; Stripe replaces that placeholder
    after payment so our success page can confirm the session.
    """
    frontend = current_app.config["FRONTEND_ORIGIN"].rstrip("/")
    currency = (order.currency or "USD").lower()

    line_items = []
    for item in order.items:
        line_items.append(
            {
                "quantity": item.quantity,
                "price_data": {
                    "currency": currency,
                    "unit_amount": dollars_to_cents(item.unit_price),
                    "product_data": {
                        "name": item.product.name if item.product else f"Product {item.product_id}",
                    },
                },
            }
        )

    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=line_items,
        customer_email=order.email,
        client_reference_id=str(order.id),
        metadata={
            "order_id": str(order.id),
            "cart_id": str(cart.id),
        },
        success_url=(
            f"{frontend}/cart?checkout=success"
            f"&order_id={order.id}"
            "&session_id={CHECKOUT_SESSION_ID}"
        ),
        cancel_url=f"{frontend}/cart?checkout=cancel",
    )
    return session


def fulfill_paid_order(order: Order, session_obj: stripe.checkout.Session | None = None) -> Order:
    """
    Mark the order paid, decrement stock, empty the linked cart.

    Safe to call twice (webhook + success-page confirm): a paid order is a no-op.
    """
    if order.status == "paid":
        return order

    if session_obj is not None:
        order.stripe_checkout_session_id = session_obj.id
        payment_intent = session_obj.payment_intent
        if payment_intent:
            order.stripe_payment_intent_id = (
                payment_intent if isinstance(payment_intent, str) else payment_intent.id
            )

    for item in order.items:
        product = item.product
        if product is not None:
            product.stock = max(0, product.stock - item.quantity)

    cart_id = None
    if session_obj is not None and session_obj.metadata:
        raw = session_obj.metadata.get("cart_id")
        if raw:
            cart_id = int(raw)

    if cart_id:
        cart = db.session.get(Cart, cart_id)
        if cart is not None:
            cart.items.clear()

    order.status = "paid"
    db.session.commit()
    return order


def payment_session_is_paid(session_obj: stripe.checkout.Session) -> bool:
    return session_obj.payment_status == "paid"
