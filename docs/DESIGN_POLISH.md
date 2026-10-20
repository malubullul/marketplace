# Anredseller — editorial polish

Skill: [design-taste-frontend](../.agents/skills/design-taste-frontend/SKILL.md), installed with the requested `npx skills add Leonxlnx/taste-skill` (Codex agent, project-local copy). The installed version is recorded in `skills-lock.json`. No frontend framework or shopping/authentication API migration.

## Direction and subject

Public direction: **The specimen catalogue**, seed **530515494**. This is a restyle: the previously approved full-bleed Signore-inspired campaign and its portrait phone crop remain. The draw informs the isolated product presentation, shared type, quieter surfaces and full-width brand close. Palette kept from Anredseller: dark wood photography, olive, stone and paper.

Inventory of real project material:

- Anredseller name and existing serif wordmark.
- Archive campaign: two models wearing brown suede against dark wood.
- Its portrait framing must keep both people visible.
- Three real catalogue categories: sneakers, apparel, essentials.
- Existing product image assets and Indonesian rupiah prices.
- Owner-managed publishing, stock and product variants.
- A customer account saves addresses, wishlist, cart and private orders.
- Shipping threshold Rp200.000 already appears in the store logic.
- Checkout creates orders for manual store confirmation.
- Reseller terms and an email-delivery service are not configured.

Idea: **The Anredseller Archive campaign becomes the opening spread of a personal wardrobe archive: view the collection, choose a category, and save the pieces to your account.** The live element is the actual collection selector, with keyboard support and counts computed from the rendered catalogue.

Font draw: Switzer. One trial redraw to Chillax was made when the Fontshare API was inaccessible; it was reverted after the original Switzer files became available through `@carrot-kpi/switzer-font@0.1.0`. Regular, medium and semibold WOFF2 files are now served locally. Georgia is used only for the existing brand wordmark. No stock photography, fabricated proof or new product claims added.

Admin direction: **Framed sheet**, seed **2058406519**, sharing the store palette and fonts. Its question: “Which products are ready for customers, and what needs my attention?” Its face is an olive-grey frame and Anredseller wordmark; its evidence is the actual stock/publishing strip and real product thumbnails. Primary job: add or edit a product. No invented analytics or totals.

## Copy and structure

| Section | Claim and evidence | Final copy / action |
| --- | --- | --- |
| Campaign | Fashion shown through the existing Archive photograph | The Archive. Worn your way. / Jelajahi koleksi |
| Collection | Browse actual products, prices and availability | The everyday edit. / category selector |
| Category edit | Sneakers and everyday apparel offer two entry points | Find your everyday. / real catalogue links |
| Reseller | Explain the existing concept, including its setup limits | Good taste. Shared. / Kenali program reseller |
| Email interest | Save interest locally; delivery is not active | Keep in the loop. / explicit local-storage note |
| Footer | Return to shopping, help or a personal account | Your next good find. / oversized Anredseller close |

Layout words: photograph → interactive catalogue → asymmetric category pair → split photo/statement → form band → typographic close. Phone catalogue filters fold into an accessible disclosure so visitors reach products earlier. Without JavaScript, the original filter panel remains visible. Wishlist hearts use SVG and stay visible to touch users.

## Screenshot critique

ROUND 1

Seen in one second: the suede campaign and its two people.
Idea: the campaign leads into a personal wardrobe archive.
Live thing: actual collection tabs and computed item counts.
Layout words: photograph, catalogue, pair, split, form, wordmark.
Scores: design 7.0 · usability 7.5 · creativity 6.0 · content 7.0 → overall **6.0** after cap.
Caps applied: inspector FAIL for the retained announcement above the masthead.
Top three problems: header and content margins differed; a footer action inherited 10px type; mobile catalogue filters pushed products far below the first screen. Corrected the shared frame/type and introduced a real filter disclosure.

ROUND 2 — final

Seen in one second: a fashion campaign with a clear shopping action.
Idea: a wardrobe archive continues from the campaign into actual choices.
Live thing: category selection, real counts and saved-product actions.
Layout words: photograph, catalogue, pair, split, form, wordmark.
Scores: design 7.5 · usability 8.0 · creativity 6.5 · content 7.0 → overall **7.45/10**. Self-assessment, not an external award score.
Caps applied: none after final browser inspection (the shipping-announcement exception below is explicit).
Remaining limitations: product images are still demonstration assets, some sneaker images have a lavender backdrop baked into the files, and the reseller panel reuses the campaign image. Real merchandise photography would improve coherence more than further decoration.

Admin inspection: `--allow no-title` is needed because the skill app probe uses `document.querySelector("h1")` and reads the hidden login heading before the visible dashboard heading. The actual authenticated screen has a visible `h1` (“Koleksi produk.”), verified in the DOM and screenshots. The shipped app and its headings are not modified to accommodate this probe limitation.

Admin critique: the actual product list is the dominant block, totals come from existing server data, and the add-product action remains one click away. The light sidebar and white sheet share their outer edges. Phone rows keep product identity, price, stock, publishing state and actions. Empty and dialog states are exercised by the existing browser tests.

## Inspection allowances and assets

- The homepage shipping/Archive announcement strip was removed at the owner's request. Its markup, ticker styles and reserved 28px space are removed; the masthead now starts at the top and the desktop campaign fills the viewport. Shipping calculations at checkout remain as configured.
- Neutral scrims remain over real campaign photography for readable text. Lint comments identify only those exact declarations and declarations that remove inherited shadows.
- Genuine catalogue controls and product objects carry `data-ui`, as allowed for real interface fragments.
- Small product metadata and several display sizes are intentional commerce/brand roles. No suitable authentic campaign footage exists, so no unrelated stock video was inserted. Reduced-motion users get the complete still page.
- Existing generated campaign and product assets are documented in [SOURCES.md](../assets/SOURCES.md). No newly found photographs or clips require credits.
- Replace demo products, prices, images and sample reviews with the owner's actual merchandise before launch. The reseller program and email delivery still need business configuration.

## Verification

Homepage now includes the manual five-photo [campaign slider](CAMPAIGN_SLIDER.md), retaining the original Archive photograph and adding four generated editorial scenes. Its focused browser coverage and latest native inspection are recorded in that guide.

Final measurements and checks are recorded below after the final run. Browser accounts and orders used for validation are disposable test data; they are not written to the development or production store.

- Source lint on the new theme/home interactions: **0 FAIL, 0 WARN**. The legacy base styles remain for compatibility; the browser measures their final computed result.
- Home inspector: **0 FAIL, 2 WARN** at 1440, 768 and 390px, with the documented announcement allowance. Warnings are the deliberate commerce/display type scale and lack of authentic campaign footage. Body copy increased from 12px to 16px; decorative numbering and tiny tracked labels were removed; 10 real raster assets render.
- Authenticated admin inspector: **0 FAIL, 0 WARN** at the same widths, with the documented hidden-heading probe allowance. Uses an isolated temporary database and owner session.
- Backend suite: **32 tests run, 31 passed, 1 PostgreSQL integration suite skipped** because no test PostgreSQL URL was supplied for this visual pass.
- Existing full browser workflow: **passed**, including independent admin/store origins, photo upload and publishing, signup/login, addresses, wishlist, cart across devices, checkout, private receipts, account isolation and logout.
- Responsive suite: **231 checks passed**, 13 pages/states and 14 viewport sizes, including 320px and phone landscape. A 320px order-status overflow found during the compact-row change was fixed by scoping that layout to product rows.
- Additional browser checks: mobile filter disclosure, real category results/counts, local font loading, final screenshots and no uncaught browser errors.
- `git diff --check` and JavaScript syntax checks pass.

This pass does not configure Supabase, Vercel domains, payment processing or real email delivery.
