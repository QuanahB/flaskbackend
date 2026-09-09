"""Catalog routes — listProducts / getProduct / getProductBySlug in api.ts."""

from flask import Blueprint, jsonify, request
from sqlalchemy import or_

from extensions import db
from models import Category, Product
from serializers import product_to_dict

products_bp = Blueprint("products", __name__)


@products_bp.get("/products")
def list_products():
    """
    GET /api/products

    Optional query params (all from ProductListParams):
      category  — category slug, e.g. apparel
      search    — case-insensitive match on name or description
      in_stock  — "true" to hide zero-stock rows
    """
    query = Product.query

    category_slug = request.args.get("category")
    if category_slug:
        query = query.join(Category).filter(Category.slug == category_slug)

    search = request.args.get("search")
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(Product.name.ilike(like), Product.description.ilike(like))
        )

    in_stock = request.args.get("in_stock")
    if in_stock is not None and in_stock.lower() in ("1", "true", "yes"):
        query = query.filter(Product.stock > 0)

    products = query.order_by(Product.id).all()
    return jsonify([product_to_dict(product) for product in products])


@products_bp.get("/products/<int:product_id>")
def get_product(product_id: int):
    """GET /api/products/:id"""
    product = db.session.get(Product, product_id)
    if product is None:
        return jsonify(message="Product not found"), 404
    return jsonify(product_to_dict(product))


@products_bp.get("/products/slug/<slug>")
def get_product_by_slug(slug: str):
    """GET /api/products/slug/:slug"""
    product = Product.query.filter_by(slug=slug).first()
    if product is None:
        return jsonify(message="Product not found"), 404
    return jsonify(product_to_dict(product))
