"""
Turn SQLAlchemy rows into JSON dicts that match app/lib/types.ts.

Keep field names in snake_case — the React types already use product_id,
image_url, line_total, etc. Do not wrap payloads in { data: ... } unless
you also change api.ts.
"""


def _money(value) -> float:
    """Numeric/Decimal → JSON number (major currency units)."""
    return float(value)


def _iso(dt) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def category_to_dict(category) -> dict:
    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
    }


def product_to_dict(product) -> dict:
    payload = {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "description": product.description,
        "price": _money(product.price),
        "currency": product.currency,
        "stock": product.stock,
        "category_id": product.category_id,
        "created_at": _iso(product.created_at),
    }
    # Omit empty media URLs so ProductImage can fall back to bundled assets.
    if product.image_url:
        payload["image_url"] = product.image_url
    if product.video_url:
        payload["video_url"] = product.video_url
    if product.category is not None:
        payload["category"] = category_to_dict(product.category)
    return payload


def cart_item_to_dict(item) -> dict:
    unit = _money(item.product.price)
    return {
        "id": item.id,
        "product_id": item.product_id,
        "product": product_to_dict(item.product),
        "quantity": item.quantity,
        "line_total": round(unit * item.quantity, 2),
    }


def cart_to_dict(cart) -> dict:
    items = [cart_item_to_dict(item) for item in cart.items]
    subtotal = round(sum(item["line_total"] for item in items), 2)
    item_count = sum(item["quantity"] for item in items)
    return {
        "id": cart.id,
        "items": items,
        "subtotal": subtotal,
        "item_count": item_count,
    }


def order_item_to_dict(item) -> dict:
    unit = _money(item.unit_price)
    payload = {
        "id": item.id,
        "product_id": item.product_id,
        "quantity": item.quantity,
        "line_total": round(unit * item.quantity, 2),
    }
    if item.product is not None:
        payload["product"] = product_to_dict(item.product)
    return payload


def order_to_dict(order) -> dict:
    return {
        "id": order.id,
        "status": order.status,
        "total": _money(order.total),
        "currency": order.currency,
        "created_at": _iso(order.created_at),
        "items": [order_item_to_dict(item) for item in order.items],
    }
