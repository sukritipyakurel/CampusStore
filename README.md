# Campus Store — College Merchandise E-commerce (Django + eSewa)

A complete Django store with categories, search, a session cart, checkout,
eSewa ePay v2 payments with server-side verification, order history,
SEO/analytics hooks and a simple recommendation system.

## Quick start

```bash
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                # already filled with eSewa UAT test values
python manage.py migrate
python manage.py seed_store         # demo categories + products
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000 (store) and http://127.0.0.1:8000/admin (dashboard).
Run the test suite with `python manage.py test`.

## Testing an eSewa payment (UAT)

1. Add something to the cart and check out.
2. You're redirected to eSewa's test page. Log in with the test eSewa ID,
   password and OTP listed in eSewa's developer docs (developer.esewa.com.np).
3. eSewa redirects to `/payments/esewa/success/?data=…`. The app decodes the
   data, verifies its HMAC signature, then calls eSewa's status API. Only if
   eSewa says `COMPLETE` **and** the amount matches is the order marked paid
   and stock reduced.

## How the pieces map to the plan

| Requirement | Where |
|---|---|
| Categories & products | `store/models.py`, `store/views.py`, `store/admin.py` |
| Shopping cart (session) | `cart/cart.py` (Cart class), `cart/views.py` |
| Checkout & orders | `orders/models.py` (Order, OrderItem), `orders/views.py` |
| eSewa signature & status check | `payments/esewa.py` |
| eSewa callbacks | `payments/views.py` (`pay`, `success`, `failure`) |
| Payment log (one row per attempt) | `payments/models.py` (Payment) |
| Accounts | `accounts/` (register, login, logout) + `/orders/history/` |
| Client-side scripting | `static/js/cart.js` (AJAX add/update/remove), `static/js/checkout.js` (validation) |
| Google Analytics / Meta Pixel / X pixel | `templates/base.html` `<head>`, IDs set in `.env`; purchase events in `payments/success.html` |
| SEO | per-page `<title>`/meta description, Open Graph, Product JSON-LD in `product_detail.html`; `/sitemap.xml` (`store/sitemaps.py`); `/robots.txt` |
| Recommendations | `store/recommendations.py`: same category, frequently bought together (from paid orders), recently viewed (session) |

## eSewa flow

```
Checkout form ─► Order (pending) ─► Payment row with a new transaction_uuid
      │
      ▼
payments/pay.html auto-POSTs signed fields to eSewa
  signature = base64(HMAC_SHA256(secret, "total_amount=…,transaction_uuid=…,product_code=…"))
      │
      ▼
eSewa ─► success_url?data=<base64 JSON>
      1. decode + verify signature (rejects tampered data)
      2. GET status API server-to-server
      3. COMPLETE + amount matches → order paid, stock reduced, cart cleared
Replaying the same callback does nothing (payment is already COMPLETE).
```

## Going live

- Set `ESEWA_ENV=production` plus your live `ESEWA_PRODUCT_CODE` and `ESEWA_SECRET_KEY` in `.env`.
- Set `DJANGO_DEBUG=False`, a real `DJANGO_SECRET_KEY` and `DJANGO_ALLOWED_HOSTS`.
- In admin → Sites, change `example.com` to your domain so `sitemap.xml` has correct URLs.
- Run `python manage.py collectstatic` and serve `media/` from your web server.

## Notes

- The eSewa test environment may limit transaction amounts, so seeded prices are low.
- `cart/models.py` is intentionally empty: the cart lives in the session and is
  saved to the database only when it becomes an order.
