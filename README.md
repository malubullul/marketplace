# Anredseller

A responsive fashion reseller storefront concept built with HTML, CSS and vanilla JavaScript. The homepage opens with a full-screen fashion campaign, a transparent header, a centered serif wordmark and a monochrome archive ticker. Warm ivory and olive accents carry through the catalog and shopping pages.

## Development

Use the existing checkout; no Node package installation or build step is required.

```sh
cd /workspace/marketplace
python3 -m http.server 8000 --bind 127.0.0.1 --directory /workspace/marketplace
```

## Features

- Fashion-first homepage with interactive collection tabs.
- Search, category/price/stock filters, sorting and pagination.
- Product details, wishlist and persistent cart.
- Checkout form validation and simulated order confirmation.
- Mobile navigation, information dialogs and reseller program overview.
- Local assets; no external font or image requests are needed at runtime.

## Demo limitations

The products, stock, prices, shipping options and review data are illustrative. Checkout does not charge a payment method, deliver an order or send an email. Newsletter interest is stored locally and does not subscribe to an external email service. The reseller overview describes a proposed program; it does not register an account.

Before launch, replace the demo catalog with verified product details and licensed product photography, set store policies and contact information, and connect inventory, authentication, order storage, payments and email services.

## Structure

- `index.html`: editorial storefront
- `produk.html`: searchable, filterable catalog
- `detail.html`: product details
- `keranjang.html`: cart
- `checkout.html`: demonstration checkout
- `konfirmasi.html`: demonstration order confirmation
- `css/style.css`: shared shopping page styles
- `css/store.css`: Anredseller visual theme and responsive layout
- `js/store.js`: shared navigation, footer and accessible dialogs
- `js/data.js`: example catalog and helpers
- `js/app.js`: product cards, collection tabs and local newsletter interest
- `assets/`: local image assets; see `assets/SOURCES.md`

## Validation

The implementation was exercised in Chromium with Python Playwright: collection tabs, wishlist add/remove, search, category filtering, sorting, cart persistence, checkout validation and confirmation, newsletter feedback, reseller dialog and mobile navigation. Responsive checks cover 390, 768, 1024 and 1440px. No application package or test runner is required for serving the site.

## UI/UX guidance

See [docs/UI_GUIDE.md](docs/UI_GUIDE.md) for the approved visual direction and the UI/UX Pro Max review: mobile controls, readable product text, keyboard-operated category tabs and accessible wishlist/dialog states.
