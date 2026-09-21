# Flask store API

JSON API for **my-react-router-app**. The React UI never talks to SQL; this
app owns products, carts, and orders.

## Run (development)

From this directory:

```bash
source .venv/bin/activate
pip install -r requirements.txt
flask --app app --debug run --port 5000
```

Then in the React project:

```bash
npm run dev
```

Vite proxies `/api` → `http://127.0.0.1:5000` (see `vite.config.ts`).
The home page health banner turns green when both are up.

## Stripe (test mode)

1. Put `STRIPE_SECRET_KEY` in `flaskbackend/.env`.
2. Restart Flask after changing `.env`.
3. Optional webhook (marks orders paid even if the shopper closes the tab):

```bash
stripe listen --forward-to localhost:5000/api/stripe/webhook
```

Copy the `whsec_...` it prints into `.env` as `STRIPE_WEBHOOK_SECRET`, then restart Flask.

Pay with test card `4242 4242 4242 4242`, any future expiry, any CVC.

## Routes

| Method | Path | Frontend helper |
|---|---|---|
| GET | `/api/health` | `getHealth` |
| GET | `/api/products` | `listProducts` |
| GET | `/api/products/<id>` | `getProduct` |
| GET | `/api/products/slug/<slug>` | `getProductBySlug` |
| GET / DELETE | `/api/cart` | `getCart` / `clearCart` |
| POST | `/api/cart/items` | `addToCart` |
| PATCH / DELETE | `/api/cart/items/<id>` | `updateCartItem` / `removeCartItem` |
| POST | `/api/checkout` | `checkout` (returns `checkout_url` + pending `order`) |
| GET | `/api/checkout/confirm?session_id=` | `confirmCheckout` |
| POST | `/api/stripe/webhook` | Stripe CLI / Dashboard |
| GET | `/api/orders/<id>` | `getOrder` |

SQLite is created at `instance/store.db` on first start and seeded with four sample products.
