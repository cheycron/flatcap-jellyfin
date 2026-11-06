# Mapping: Flatcap 2.0 roles to Jellyfin 12.4

The three files have the same structure: one block of `--fc-*` role variables and `--jf-palette-*` / `--jf-font-*` variables on `:root:root` (`:root:root` so the block wins over `[data-theme]` whatever the load order), then rules for the colors that Jellyfin hard-codes, each prefixed with `html ` for the same reason, then a dark "on video / on poster" scope. `flatcap-system.css` declares the Slate set and, inside `@media (prefers-color-scheme:light)`, the Daylight set.

## Flatcap TV (`flatcap-tv.css`)

A fourth file: the Slate file plus the rules in `scripts/tv.py`, appended after the shared rules. Same role variables, no new colors; sizes come from `metrics` and `typography`. Dark base theme only.

- **Header:** flat, thin (`AppBar`), `bg.surface` on pages without a backdrop, transparent with a canvas scrim (88%, fading out at the lower edge) over backdrops; no `backdrop-filter`. Icons `text.muted`, active `accent.fg`. Rule `html:has(.je-header-actions-row) .skinHeader .pageTitle.pageTitleWithLogo{display:none}` hides the legacy logo/title when Jellyfin Enhanced's header row is in the DOM (the class is the plugin's, so it is not in the 12.4.0 inventory and is whitelisted in `scripts/tv.py`).
- **Home rows:** larger portrait/backdrop cards and row spacing, compact `.section0` (My Media) cards, section titles larger in `text.secondary` without uppercase, smaller played indicator in the accent, thinner resume bar.
- **Focus:** `.card:focus-visible`, `.card.show-focus:focus` (TV layout) and `:hover` scale 1.04 with a 2px `focus.ring` outline offset 2px; no shadow or glow; neighbours do not move (transform only); `prefers-reduced-motion: reduce` keeps the ring and drops the scale and transition.
- **Backdrops:** the user's full-page backdrop is dimmed with the canvas at 90% (stock 86%); the item page has a matte gradient to `bg.canvas` (92% where the text sits). Bigger title, muted metadata, one filled Play button (`accent.fill`, `accent.on`), the other actions are icon buttons (styling only).
- **Titles:** always visible. The last lines of the file are a commented-out optional block that hides `.cardText` on cards with artwork until focus or hover; cards whose image container has `.defaultCardBackground` keep their title.
- Player OSD: the same dark Slate block as the other files.

## Decisions

- **Base theme: Dark, for all three files.** Every color the Dark theme takes from a `--jf-*` variable is replaced through the variable; the colors it hard-codes are overridden by the rules below. Daylight therefore needs no Light base theme (it was rendered on Dark and inspected in Chromium). The built-in Light theme was not used as a base, and combining Flatcap with it was not tested.
- **Variables first.** `--jf-palette-*` carries almost everything; each also sets its `*Channel` twin (`r g b`), which Jellyfin uses in `rgba(var(--…Channel)/…)` hover and ribbon backgrounds.
- **Hierarchy kept.** `text-primary` (headings) and `text-secondary` (the client's body text) map to `text.primary` and `text.secondary`.
- **Focus.** Jellyfin fills a focused button with `secondary-main` and borders a focused card with it (0.5em border). `secondary-main` is `focus.ring`, so both use the Flatcap ring. A 2px ring outline is added for keyboard focus on links, buttons, inputs and cards.
- **Feedback.** `error-*`, `success-*`, `warning-*`, `info-*` take the Flatcap feedback colors; the text on filled feedback and on accent fills is `accent.on`. The checkbox tick (`#fff` in Jellyfin) becomes `accent.on`, because white on the Slate accent is below 3:1.
- **Dark video/poster scope.** `.videoOsdBottom, .osdHeader, .upNextContainer, .sliderBubble, .skip-button, .itemProgressBar, .iconOsd` re-declare the roles with the Slate values, so Daylight keeps readable player controls and a visible resume bar. Jellyfin's own scrims (`rgba(16,16,16,.75)` gradients, `rgba(0,0,0,.7)` card footers and overlays) are left as they are and the contrast is measured on them.
- **Removed:** `backdrop-filter:blur(5px)` on `.iconOsd` (the volume/brightness popup). Nothing else is blurred or glowing in 12.4's CSS; layout, sizes and animations are untouched.
- **Header over a backdrop:** `AppBar-transparentBg` is the canvas at 72% (stock: black at 40% / 86% light grey); text is measured over white and black.
- **Fonts:** `--jf-font-*` keep Jellyfin's sizes and weights; only the family changes. `html` (and its `lang` variants) get IBM Plex Sans first, then the Noto Sans families the client ships for CJK.

## Variables

<!-- build:vars -->
<!-- /build:vars -->

## Rules for hard-coded colors

<!-- build:rules -->
<!-- /build:rules -->

## Not mapped (still Jellyfin's colors)

Listed with evidence in [qa-report.md](qa-report.md#residual-jellyfin-defaults).
