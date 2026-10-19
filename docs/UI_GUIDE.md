# Anredseller UI guide

The user's visual reference is a dark editorial fashion campaign: full-screen photography, transparent navigation, a centered serif wordmark, a monochrome announcement strip, and a collection CTA at the lower left. Keep this composition when refining the interface.

## Design tools

Reviewed with [UI/UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) at commit `56ea9cf174ed86786187daa9de0e6247cb0747e4`. The skill and its searchable local dataset are checked out at `/workspace/library-files/ui-ux-pro-max-skill` in the cloud environment. This is a local tool checkout, not a runtime website dependency or a global plugin installation.

The website uses plain HTML, CSS and JavaScript. Do not add a framework or Tailwind solely because a skill supports it. Search recommendations supplement the user's reference; they do not replace it. The broad luxury-commerce search returned an Apple-specific Liquid Glass style that does not fit this site, so it was rejected. Targeted minimalism and web accessibility guidance was used instead.

Useful searches from this review:

```sh
python3 /workspace/library-files/ui-ux-pro-max-skill/.claude/skills/ui-ux-pro-max/scripts/search.py "minimalism editorial monochrome" --domain style
python3 /workspace/library-files/ui-ux-pro-max-skill/.claude/skills/ui-ux-pro-max/scripts/search.py "touch target size spacing" --domain ux
python3 /workspace/library-files/ui-ux-pro-max-skill/.claude/skills/ui-ux-pro-max/scripts/search.py "keyboard tab navigation" --domain ux
```

## Implementation decisions

- Keep the dark campaign and warm ivory catalog. Use `--text-secondary` for readable catalog metadata and secondary prices.
- Prefer 44px web controls for comfortable touch use. WCAG's web minimum is 24 CSS px with applicable exceptions; do not confuse native pt/dp units with CSS pixels.
- Keep small outline icons inside larger hit areas. On narrow screens, expose wishlist through the menu so the wordmark and header actions do not overlap.
- Product names and prices remain readable in the two-column mobile grid. Do not shrink them to fit a single line.
- Category tabs support Left/Right, Home and End. Keep `aria-selected`, the active tab stop, and panel labelling synchronized with the visible products.
- Wishlist buttons expose `aria-pressed` and the current action. Dialogs have a title, native focus handling, and an Escape route.
- The announcement strip remains static. Avoid adding continuous movement without a pause control.
- Provide a visible-on-focus skip link. Keep keyboard focus visible and return it to the menu button when Escape closes the navigation.
- Maintain the demo boundary: this skill improves UI/UX; it does not add real payments, authentication, inventory or reseller pricing.

## Verification

Check 320/375/390px phones, 768px tablet, and 1440px desktop. Confirm no horizontal overflow, no header overlap, keyboard-only category navigation, wishlist state, dialog focus and mobile menu access. Run the existing browser smoke workflow after shared navigation changes. Do not describe these checks as a full WCAG audit.
