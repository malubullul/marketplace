# Anredseller UI guide

The user's visual reference is a dark editorial fashion campaign: full-screen photography, transparent navigation, a centered serif wordmark, a monochrome announcement strip, and a collection CTA at the lower left. Keep this desktop composition when refining the interface. On phones, use a portrait photo frame below the masthead with the copy following the photo so both models remain visible and text stays readable.

## Design tools

The project installs [UI/UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) for Codex at [`.agents/skills/ui-ux-pro-max/SKILL.md`](../.agents/skills/ui-ux-pro-max/SKILL.md), including its local datasets and Python search scripts. Installed with the official `ui-ux-pro-max-cli` version **2.15.0**. Its installer also includes the companion skills `banner-design`, `brand`, `design`, `design-system`, `slides` and `ui-styling`. Existing taste-skill and sharp-edges installations are preserved. These are project tools, excluded from Vercel builds, with no website runtime dependency or global installation.

Reproduce the installation from the repository root (Python 3 is already available in the cloud workspace):

```sh
npx --yes --package=ui-ux-pro-max-cli@2.15.0 uipro init --ai codex
```

The installer recommends restarting the coding assistant so the new skills are discovered. Installation was verified by running the local search against `mobile responsive` in the `ux` domain and receiving a result from `ux-guidelines.csv`. This installation does not redesign the storefront. The earlier design review used upstream commit `56ea9cf174ed86786187daa9de0e6247cb0747e4` from the separate library checkout.

The public interface uses plain HTML, CSS and JavaScript; the owner dashboard and shared API use Flask, with PostgreSQL/private Supabase Storage for Vercel or SQLite/local photos for development. Do not add a framework or Tailwind solely because a skill supports it. Search recommendations supplement the user's reference; they do not replace it. The broad luxury-commerce search returned an Apple-specific Liquid Glass style that does not fit this site, so it was rejected. Targeted minimalism and web accessibility guidance was used instead.

The canonical owner UI now lives in `admin-portal/templates/index.html` and `admin-portal/static/`. The store backend serves those same files in local single-domain mode, while the standalone portal serves them on the owner domain. Keep one UI implementation so mobile fixes apply to both. Store links use `/portal-config` to reach the configured public store.

Useful searches from this review:

```sh
python3 .agents/skills/ui-ux-pro-max/scripts/search.py "minimalism editorial monochrome" --domain style
python3 .agents/skills/ui-ux-pro-max/scripts/search.py "touch target size spacing" --domain ux
python3 .agents/skills/ui-ux-pro-max/scripts/search.py "keyboard tab navigation" --domain ux
```

## Implementation decisions

- Keep the dark campaign and warm ivory catalog. Use `--text-secondary` for readable catalog metadata and secondary prices.
- Prefer 44px web controls for comfortable touch use. WCAG's web minimum is 24 CSS px with applicable exceptions; do not confuse native pt/dp units with CSS pixels.
- Keep small outline icons inside larger hit areas. On narrow screens, expose wishlist through the menu so the wordmark and header actions do not overlap.
- Product names and prices remain readable in the two-column mobile grid. Do not shrink them to fit a single line.
- At widths up to 760px, the campaign uses a 4:5 frame with the image focused at 90% horizontally. Keep both models in the crop. Let the hero grow with its content instead of forcing a desktop viewport height.
- Stack the cart and checkout columns through 1100px. Below 600px, show checkout fields and editorial category cards in a single column. Mobile cart cards keep photo, product information, quantity controls, remove action and subtotal in explicit grid areas.
- Allow long names, brand names, email and addresses to wrap within their columns. Do not hide page overflow to conceal a layout problem. Category navigation and photo thumbnails may scroll within their own containers.
- Limit open navigation and dialogs to the available viewport height, including landscape orientation, and allow their contents to scroll.
- Category tabs support Left/Right, Home and End. Keep `aria-selected`, the active tab stop, and panel labelling synchronized with the visible products.
- Wishlist buttons expose `aria-pressed` and the current action. Dialogs have a title, native focus handling, and an Escape route.
- The announcement strip remains static. Avoid adding continuous movement without a pause control.
- Provide a visible-on-focus skip link. Keep keyboard focus visible and return it to the menu button when Escape closes the navigation.
- Preserve the operational boundary: owner authentication, shared inventory and order intake are implemented; payment, email, shipping automation and reseller pricing are not.

## Verification

Run `python3 tests/responsive_smoke.py` with Playwright and Chromium installed. It starts an isolated store and checks every page at widths from 320px through 1440px, including tablet breakpoints and phone landscape orientations. It exercises populated accounts, cart, checkout, receipts, expanded menus, search and address/product dialogs with long text. Confirm no horizontal overflow, no header overlap and no clipped controls or dialogs. It also checks that both campaign models fit the phone crop. Run the existing `tests/browser_smoke.py` workflow to verify shopping interactions. Do not describe these checks as a full WCAG audit or testing on physical devices.

## Customer accounts

Keep account pages consistent with the cream/olive storefront rather than replacing the approved editorial direction with a generated generic ecommerce palette. The customer account page provides login/registration, profile, addresses, orders and wishlist. Use visible form labels, native autocomplete, minimum 44px controls, contextual errors and explicit loading feedback. Public catalog browsing remains anonymous; customer state and checkout require sign-in. Show order status as supplied by the backend, not as proof of payment. Never display another account's cached profile, cart or receipt after account switching or logout.

## Editorial polish with taste-skill

The current visual layer is `css/editorial.css`, loaded after legacy styles on every public page. It shares locally hosted Switzer type, stone/olive tokens, clear product metadata and SVG wishlist controls. The existing Archive campaign and portrait phone framing remain. Mobile catalogue filters use a disclosure; without JavaScript the filters remain visible.

The canonical admin stylesheet uses the same fonts, with a light frame, white work area and compact product rows. Font routes are limited to the three bundled WOFF2 files. Tooling under `.agents/` and generated inspection artifacts are excluded from the Vercel deployment.

See [design direction, screenshot critique and verification](DESIGN_POLISH.md), [installed skill](../.agents/skills/design-taste-frontend/SKILL.md), and [asset provenance](../assets/SOURCES.md).

## Customer sign-in polish

Email/password entry and registration continue the same visual system. On phones the form comes first and the campaign image follows. The form's title is the visible h1. Password visibility toggles retain labels, use 44px targets and never submit the form. Account settings retain password changes and logout from all devices. See [security notes](AUTH_SECURITY_REVIEW.md).
