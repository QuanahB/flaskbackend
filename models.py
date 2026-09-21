"""
SQL tables for the store.

These map to the TypeScript types in my-react-router-app/app/lib/types.ts.
If you add a column here, update the matching serializer in serializers.py
and the TS type so the frontend keeps compiling against real JSON.
"""

from datetime import datetime, timezone

from extensions import db


def _utcnow():
    """Timezone-aware timestamp for created_at columns."""
    return datetime.now(timezone.utc)


class Category(db.Model):
    """Product grouping (e.g. Apparel). Optional on Product."""

    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)

    products = db.relationship("Product", back_populates="category")


class Product(db.Model):
    """Catalog item. `price` is major currency units (19.99), matching the TS type."""

    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    # Numeric stays precise in SQL; we serialize it as a JSON number for React.
    price = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(8), nullable=False, default="USD")
    image_url = db.Column(db.String(500), nullable=True)
    video_url = db.Column(db.String(500), nullable=True)
    stock = db.Column(db.Integer, nullable=False, default=0)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    category = db.relationship("Category", back_populates="products")
    cart_items = db.relationship("CartItem", back_populates="product")


class Cart(db.Model):
    """One shopping cart, keyed from the Flask session (`session['cart_id']`)."""

    __tablename__ = "carts"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    items = db.relationship(
        "CartItem",
        back_populates="cart",
        cascade="all, delete-orphan",
        order_by="CartItem.id",
    )


class CartItem(db.Model):
    """A line in a cart: product + quantity."""

    __tablename__ = "cart_items"

    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey("carts.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    cart = db.relationship("Cart", back_populates="items")
    product = db.relationship("Product", back_populates="cart_items")


class Order(db.Model):
    """Placed order. Cart is emptied after checkout; history lives here."""

    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(32), nullable=False, default="pending")
    total = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(8), nullable=False, default="USD")
    email = db.Column(db.String(200), nullable=False)
    shipping_name = db.Column(db.String(200), nullable=False)
    shipping_address = db.Column(db.String(300), nullable=False)
    shipping_city = db.Column(db.String(120), nullable=False)
    shipping_postal_code = db.Column(db.String(32), nullable=False)
    shipping_country = db.Column(db.String(80), nullable=True)
    # Stripe Checkout Session id (cs_test_...) so webhooks can find this row.
    stripe_checkout_session_id = db.Column(db.String(255), nullable=True, unique=True)
    # PaymentIntent id (pi_...) for refunds / Dashboard lookup later.
    stripe_payment_intent_id = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    items = db.relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderItem.id",
    )


class OrderItem(db.Model):
    """Snapshot of a cart line at checkout time (qty is frozen even if stock changes later)."""

    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    # Unit price copied from the product so later catalog price changes do not rewrite history.
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)

    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product")
