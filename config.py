"""
Flask settings for the store API.

The React storefront talks to this app over HTTP (see my-react-router-app
app/lib/config.ts). Nothing in this file is sent to the browser except
what individual routes choose to jsonify.
"""

import os


class Config:
    """Default development config. Override with environment variables in production."""

    # Used to sign the session cookie that remembers which cart belongs to
    # the shopper. Change this before deploying anywhere public.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")

    # SQLite file path is set in create_app() so it lives in instance/store.db
    # next to this project, not in a surprise system directory.
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session cookie: HttpOnly so JavaScript cannot read it; SameSite=Lax so
    # the Vite-proxied storefront on localhost:5173 can still send it.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False  # True only when serving HTTPS

    # Origins allowed to call Flask *directly* (bypassing the Vite proxy).
    # The local React Router dev server is 5173.
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")

    # Stripe secret key (sk_test_...) — never sent to the browser.
    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
    # Webhook signing secret (whsec_...) from `stripe listen` or the Dashboard.
    STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    # Storefront origin used for Stripe success/cancel redirects.
    FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")
