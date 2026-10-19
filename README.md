# Anredseller

A fashion storefront with a separate owner dashboard, persistent product catalog, photo uploads and manual order management. The public design uses a full-screen fashion campaign, transparent navigation and an editorial serif wordmark.

## Two entrances, one store

| Who     | Page                      | What they can do                                                                                               |
| ------- | ------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Owner   | `/admin` or `/admin.html` | Log in, add/edit/delete products, upload photos, save drafts or publish, manage stock and view customer orders |
| Visitor | `/` and `/produk.html`    | Browse published products without logging in, choose size/color, use cart and submit an order                  |

Published products are loaded from the server database in every browser. Drafts and order details require owner authentication. Data is not stored only in the owner's browser.

## Run locally

Python 3.12+ is required. Use the existing checkout.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python server.py create-admin
.venv/bin/python server.py run
```

Create the owner email and password interactively in the terminal; no default credentials exist. For production use Gunicorn, HTTPS and persistent storage. See [the hosting and owner guide](docs/HOSTING.md), including the supplied Render blueprint.

Opening HTML directly or running `python -m http.server` provides a static example preview. It cannot save admin changes, upload photos or submit real orders. GitHub Pages alone cannot host this backend.

## Implemented

- Fashion-first, responsive public storefront with categories, search, filtering and sorting.
- Owner login, server-revoked sessions, password hashing, CSRF protection and login throttling.
- Product editor: name, description, category, brand, price/discount, total stock, sizes, colors, materials/care and up to eight images.
- Validated image uploads with locally stored WebP output.
- Draft/published visibility, stale-edit conflict detection, persistent SQLite data.
- Distinct cart lines for size/color selections.
- Server-validated orders, authoritative prices, stock reservation and idempotent order submission.
- Owner order view, status changes and one-time stock restoration on cancellation.
- Existing keyboard accessibility, wishlist and responsive navigation.

## Operational limits

Payments, email and shipping are not automated. Orders await the owner's manual confirmation. Stock is total per product, not separate stock for each variant. No customer accounts or reseller pricing tiers are implemented. Initial example products and photography must be replaced or unpublished before launch; see [asset sources](assets/SOURCES.md).

SQLite and uploaded images require a persistent disk. The supplied deployment runs one instance with one Gunicorn worker and four threads. Multiple application instances require shared database/object storage.

## Validation

```sh
.venv/bin/python -m unittest discover -s tests -v
```

Backend tests cover owner authorization, CSRF, session revocation, draft/public visibility, CRUD, uploads, persistence, validation, server prices, variants, stock, duplicate submission, conflicts and cancellations.

With Python Playwright and Chromium installed, run:

```sh
python3 tests/browser_smoke.py
```

This starts a temporary store with disposable test credentials and data, uses separate owner/visitor browser contexts, and exercises photo upload → draft → publish → public product → variant cart → checkout → owner order → unpublish → logout. It does not create an account in the development or production database.

See [docs/UI_GUIDE.md](docs/UI_GUIDE.md) for the approved visual direction and UI/UX Pro Max guidance.
