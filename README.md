# Anredseller

A fashion storefront with a separate owner dashboard, persistent product catalog, photo uploads and manual order management. The public design uses a full-screen fashion campaign, transparent navigation, an editorial serif wordmark and a [black/charcoal theme](docs/BLACK_THEME.md) with ivory actions across the storefront and owner portal.

## One store, separate owner and buyer accounts

| Who     | Page                      | What they can do                                                                                               |
| ------- | ------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Owner   | `/admin` or `/admin.html` | Log in, add/edit/delete products, upload photos, save drafts or publish, manage stock and view customer orders |
| Visitor | `/` and `/produk.html`    | Browse published products, search the catalog and choose size/color without logging in |
| Buyer | `/akun` | Register/log in, manage profile and addresses, save cart/wishlist across devices, checkout and view private order history |

The public store and [owner portal](admin-portal/README.md) deploy from this **one repository and the same `main` branch**, using two projects and two domains. For **Vercel + Supabase**, follow [the deployment guide](docs/VERCEL_SUPABASE.md): the store runs from the repository root with PostgreSQL/private Storage; admin runs from `admin-portal/` and connects through the server gateway. Both folders include `vercel.json`. No separate repository, branch, ZIP upload or second database is required. [render.yaml](render.yaml) remains an alternative for a persistent-disk deployment.

Published products are loaded from the server database in every browser. Saving a cart or wishlist and placing an order require a buyer account. Drafts require owner authentication. Order details are available to the authenticated buyer who placed the order and to the owner. Data is not stored only in the owner's browser.

## Run locally

Python 3.12+ is required. Use the existing checkout.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python server.py create-admin
.venv/bin/python server.py run
```

Create the owner email and password interactively in the terminal; no default credentials exist. Without `DATABASE_URL`, local development uses SQLite and local uploads. With PostgreSQL, supply a stable session secret and Supabase Storage settings, then apply the SQL migrations. Vercel requires this remote-storage mode and does not fall back to a temporary SQLite database. See [Vercel + Supabase](docs/VERCEL_SUPABASE.md) or [the general hosting guide](docs/HOSTING.md).

Opening HTML directly or running `python -m http.server` provides a static example preview. It cannot save admin changes, upload photos or submit real orders. GitHub Pages alone cannot host this backend.

## Implemented

- Fashion-first, responsive public storefront with categories, search, filtering and sorting.
- Five-photo editorial [homepage campaign](docs/CAMPAIGN_SLIDER.md) with arrows, touch swipe, keyboard navigation and reduced-motion support.
- Owner login, server-revoked sessions, password hashing, CSRF protection and login throttling.
- Product editor: name, description, category, brand, price/discount, [stock per size](docs/SIZE_STOCK.md), colors, materials/care and up to eight images. Restock or add sizes on the same product; total stock is calculated automatically.
- Shared [product photo galleries](docs/PRODUCT_GALLERY.md): upload four photos at once, choose the cover, then browse with arrows/swipe on cards and arrows/thumbnails on product details.
- Validated image uploads, WebP conversion and a private Supabase bucket; local disk is available for development.
- Draft/published visibility, stale-edit conflict detection, PostgreSQL support and local SQLite support.
- Customer registration/login, profile editing, password changes, and single-use email recovery through Resend that revokes existing sessions.
- Verified buyer ratings with editable reviews and sold-unit counts based on completed orders. See [ratings and recovery setup](docs/REVIEWS_AND_RECOVERY.md).
- Private saved addresses with a default shipping address and automatic checkout prefilling.
- Server-backed wishlist and variant cart shared across the customer's devices.
- Authenticated checkout and order history scoped to the buyer account; account identity is checked by the server.
- Separate admin and customer sessions; signing into one role does not grant the other role.
- Server-validated orders, authoritative prices, stock reservation and idempotent order submission.
- [Transaction safety](docs/TRANSACTION_SAFETY.md): private manual payment verification, sequential fulfillment, buyer cancellation, opt-in payment deadlines, one-time stock restoration, and owner activity history.
- Email-first signup and legacy email verification, with hashed single-use tokens and session revocation. Enable after migration 005 and Resend setup.
- WhatsApp payment handoff with order reference and server-calculated total; separate customer-service chat and owner-editable contact numbers. See [WhatsApp guide](docs/WHATSAPP.md).
- Owner-managed campaign/category/banner/account photos and optional social links in the footer. See [content management](docs/STORE_CONTENT.md).
- Owner-managed [promo codes](docs/PROMO_CODES.md) for partner collaborations: percentage/fixed discounts, minimum spend, caps, dates, total/account limits, order attribution and server-verified checkout totals. Uses existing database tables; no additional migration.
- Existing keyboard accessibility, wishlist and responsive navigation.
- A responsive [React 404 page](docs/REACT_404.md) with shadcn/Tailwind/TypeScript source, real HTTP 404 responses, working recovery links and pre-rendered fallback.

## Operational limits

Payments and shipping are not automated. Recovery emails require a verified Resend sender and server configuration. Orders await the owner's manual confirmation. Stock can be tracked per size; colors share stock within that size. Legacy products retain pooled stock until the owner allocates it explicitly. Mandatory email verification requires explicit activation after sender/schema setup; it is off by default for rollout compatibility. Stock per size/color combination, reseller pricing tiers, shipping integration, refunds, and MFA remain on the [staged audit roadmap](docs/ROADMAP.md). Initial example products and photography must be replaced or unpublished before launch; see [asset sources](assets/SOURCES.md).

Vercel stores data in Supabase PostgreSQL and photos in private Supabase Storage; session signing uses a stable environment secret. Apply [database](migrations/001_supabase.sql), [ratings/recovery](migrations/004_reviews_recovery.sql), [email verification](migrations/005_email_verification.sql) and [bucket](migrations/002_supabase_storage.sql) migrations before connecting the production projects. The application does not create cloud tables or seed demonstration products during cold starts. PostgreSQL serializes application transactions using one advisory lock per schema, suitable for a small store rather than high marketplace traffic. SQLite deployments require one store instance and a persistent disk.

## Validation

```sh
.venv/bin/python -m unittest discover -s tests -v
```

Backend tests cover owner/customer authorization, CSRF, session revocation, account isolation, cross-device state, address ownership, order ownership, legacy-order privacy, draft/public visibility, CRUD, uploads, persistence, validation, server prices, variants, stock, duplicate submission, conflicts and cancellations.

With Python Playwright and Chromium installed, run:

```sh
python3 tests/browser_smoke.py
python3 tests/responsive_smoke.py
ANREDSELLER_TEST_ADMIN_PORTAL=1 python3 tests/browser_smoke.py
python3 tests/browser_promos_smoke.py
python3 tests/browser_transaction_safety_smoke.py
```

This starts a temporary store with disposable test credentials and data, uses separate owner/visitor browser contexts, and exercises photo upload → draft → publish → public product → customer registration → saved address → cross-device cart/wishlist → authenticated checkout → private customer history → owner order → unpublish → logout. It does not create an account in the development or production database.

The responsive suite separately checks all pages at 14 portrait/landscape viewport sizes from 320px to 1440px, with long product/profile names, brand names, email and shipping data. It checks page overflow, header overlap, form controls, expanded menus, dialogs and the mobile campaign crop. Set `ANREDSELLER_SCREENSHOT_DIR` to retain screenshots in a chosen directory.

The separate-portal mode starts both services on different origins and verifies owner login, uploads/publication, shared customer orders, account isolation and logout through the gateway. Backend tests also cover gateway access, secure cookies, CSRF, route restrictions and refusal to follow upstream redirects.

Set `ANREDSELLER_TEST_DATABASE_URL` to a disposable local PostgreSQL database to run the same backend contracts against PostgreSQL and exercise the full browser workflow with PostgreSQL/Storage HTTP fixtures. Tests also cover concurrent checkout without overselling or duplicate reservation, both Supabase key formats, Storage errors/redirects and serverless filesystem independence. Without a test database, the PostgreSQL contracts are explicitly skipped. Never point test configuration at production.

See [docs/UI_GUIDE.md](docs/UI_GUIDE.md) for the approved visual direction and UI/UX Pro Max guidance.

Customer accounts use email and password. See [account security notes](docs/AUTH_SECURITY_REVIEW.md).
