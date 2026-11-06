# QA report: Flatcap 2.0 for Jellyfin, before and after

Target: Jellyfin **12.4.0** (`ghcr.io/linuxserver/jellyfin:12.4ubu2604-ls57`, `/System/Info/Public` reports `Version: 12.4.0`), throwaway container `fc-jf-demo` on `127.0.0.1:18096` with a fresh `/config` under `/tmp`, startup wizard completed with a demo admin (`ada`), removed afterwards. Browser: Google Chrome for Testing 149.0.7827.55 through `playwright-core` 1.65.0, 1440×900, `en-US`. The author's live Jellyfin (container `jellyfin`, `/mnt/appdata/jellyfin`) and every media library were never touched: all media is synthetic.

Demo library (`qa/make_media.py`, `qa/seed.py`): 10 invented movies and one invented series with 3 episodes; posters, backdrops and videos are generated (ffmpeg test patterns with titles, generated gradient art), NFO metadata, internet metadata and image fetchers switched off. Three items are partially watched (resume bars), several are marked played, one is a favorite. IBM Plex Sans is not bundled: for the screenshots it was installed from the `@fontsource/ibm-plex-sans` npm package into a private fontconfig directory under `/tmp` (`document.fonts.check('16px "IBM Plex Sans"')` was `true`).

The CSS was installed the way a user does it, as the server's Branding Custom CSS (`POST /System/Configuration/branding`, `CustomCss`), on the **Dark** theme (`<userId>-appTheme` / `-dashboardTheme` = `dark` in local storage). Scripts are in `qa/` and are not run by CI: `shoot.mjs` (screenshots), `scan.mjs` + `summarize.py` (computed-color scan), `checks.mjs` (routes, system, `@import`, disable switch, TV focus), `dump-vars.mjs` (runtime variables for the inventory).

## Static checks (literal results)

```
$ python3 scripts/build.py --check
ok: 3 CSS files and 3 docs current, every --jf-* variable and class/id is in the Jellyfin 12.4.0 inventory, contrast targets met

$ python3 scripts/inventory.py --check --web /tmp/fc-jf/web --runtime /tmp/fc-jf/runtime-vars.json
ok: inventory matches
```

`/tmp/fc-jf/web` is the web client copied out of the throwaway container (`/usr/share/jellyfin/web`). Negative tests of `--check` were run during development: a stale generated CSS file and a contrast target that no longer holds were each reported as failures, and a mutated inventory produced unknown-variable errors. Unknown-class detection was not separately demonstrated.

## What the web client does in 12.4.0 (verified in the bundle and at runtime)

- Branding Custom CSS is rendered by the client as an inline `<style>` element in the page layout; there is a per-user switch *Settings → Display → "Disable server-provided custom CSS code"* and a per-client *"Custom CSS code"* box. Checked: turning the switch on (`<userId>-disableCustomCss`) removes every Flatcap value (accent back to `#00a4dc`).
- **The `<style>` is present on** home, search, library, item, *Settings* (user preferences) and the video player (`#/video`). **It is absent on the admin Dashboard**: `dashboard`, `dashboard/branding`, `dashboard/users`, `dashboard/libraries`, `dashboard/playback/transcoding` all had no `<style>` containing Flatcap, and their computed colors were all stock (323 of 324 element-uses unchanged in the scan below). The Dashboard is not themed by Branding Custom CSS in 12.4.0.
- `--jf-*` palette variables are declared at runtime on `[data-theme]`; `:root:root{…}` from Custom CSS wins over them.
- `@import` of the raw GitHub URL: not usable. `raw.githubusercontent.com` answers `content-type: text/plain; charset=utf-8` with `x-content-type-options: nosniff` and `content-security-policy: default-src 'none'; style-src 'unsafe-inline'; sandbox` (curl, on an existing public file; this repository is not published). In Chromium a `<link rel=stylesheet>` to such a URL fired `onerror`. The Branding `@import` path itself was not observed end to end, so the exact failure mechanism there is inferred from this. Jellyfin's `index.html` carries no Content-Security-Policy. Pasting is the documented route.
- Layout switching: `localStorage.layout = "tv"` gives `html.layout-tv`; used for the TV focus check.
- The card resume bar is a MUI `LinearProgress` whose color is a literal inside generated emotion CSS (`.css-… .MuiLinearProgress-bar{background-color:rgb(0,164,220)}`), not a variable; it needs the explicit rule in the CSS (found by the scan). `outline:none!important` is set on `.card`, `.cardBox`, `.emby-button` and `.paper-icon-button-light`, so the added focus outline is `!important`.

## Contrast (computed from `src/theme.json`)

Ratios are WCAG 2.x on the values the CSS sets. The on-video rows use Jellyfin's own scrim, `rgba(16,16,16,.75)` at the edge of the OSD gradient, composited over a white and a black frame (the two worst cases for a video). "report only" rows are shown for transparency and not gated.

<!-- build:contrast -->
<!-- /build:contrast -->

Known gaps in this table: the seek bar's unfilled track and buffered part are below 3:1 over a bright video frame (they are not the only carrier of the position: the played part and thumb are, and meet 3:1); nothing measures toast text rendered in the browser (the toast uses `SnackbarContent-*`, the `text.primary` on `bg.raised` row applies); text over arbitrary artwork or backdrops is Jellyfin's own scrim and is only measured in the OSD cases above.

## Visual checks that ran

Slate and Daylight, both on the Dark base theme, 1440×900: home (My Media, Continue Watching with resume bars, Latest), movie library grid (played badges, A–Z picker, header controls), item page with backdrop, item action sheet, the video player with the on-screen controls visible, *Settings → Display* (inputs, selects, checkbox), login. `flatcap-system.css` under emulated `prefers-color-scheme: light` and `dark` (home only; computed `--fc-canvas` `#F3F5F7` / `#191D22`, accent `#285D85` / `#9BBFDF`). TV layout (`layout-tv`): keyboard Tab/ArrowRight over the library grid; the focused card gets the 2px focus-ring outline (`rgb(176, 210, 240)` in Slate, `rgb(40, 93, 133)` in Daylight, measured) on top of Jellyfin's 1.07 scale. Screenshots are in `images/`: `screenshot-slate.png`, `screenshot-daylight.png` (home) and `<view>-<mode>.png` for `library`, `detail`, `player`, `settings`, `actionsheet`, `login`, plus `tv-focus-<mode>.png`, `system-light.png`, `system-dark.png` and `dashboard-unthemed.png` (the Dashboard, which stays stock).

## Before / after scan

`qa/scan.mjs` records the computed `color`, `background-color`, borders, gradients and SVG fill of every visible element in each view, once with no Custom CSS and once per theme. A color use whose computed value is identical before and after counts as "still Jellyfin's" (by value: it can undercount if a Flatcap color happens to equal a stock one). Default state only: no hover, no open form dialogs, no toasts.

### slate

| View | Distinct color uses (stock) | Same value after | Element-uses stock | Element-uses unchanged |
| :--- | ---: | ---: | ---: | ---: |
| home | 11 | 2 | 131 | 46 (35%) |
| library | 22 | 3 | 328 | 142 (43%) |
| detail | 15 | 2 | 103 | 21 (20%) |
| actionsheet | 17 | 3 | 139 | 22 (16%) |
| player | 10 | 3 | 45 | 3 (7%) |
| dashboard | 19 | 18 | 324 | 323 (100%) |
| settings | 11 | 0 | 173 | 0 (0%) |
| login | 10 | 0 | 24 | 0 (0%) |

Color uses whose value did not change (excluding the Dashboard, which receives no Custom CSS):

| View | Property \| value | Elements | Examples |
| :--- | :--- | ---: | :--- |
| home | `color: rgba(255, 255, 255, 0.76)` | 41 | `span.material-icons.cardOverlayButtonIcon` |
| home | `background-color: rgba(51, 51, 51, 0.8)` | 5 | `div.itemProgressBar` |
| library | `border-color: rgba(255, 255, 255, 0.23)` | 2 | `button.MuiButtonBase-root.MuiButton-root` |
| library | `color: rgba(255, 255, 255, 0.76)` | 70 | `svg, path` |
| library | `fill: rgba(255, 255, 255, 0.76)` | 70 | `svg, path` |
| detail | `background-color: rgba(51, 51, 51, 0.8)` | 2 | `div.itemProgressBar` |
| detail | `color: rgba(255, 255, 255, 0.76)` | 19 | `span.material-icons.cardOverlayButtonIcon` |
| actionsheet | `background-color: rgba(51, 51, 51, 0.8)` | 2 | `div.itemProgressBar` |
| actionsheet | `color: rgba(255, 255, 255, 0.76)` | 19 | `span.material-icons.cardOverlayButtonIcon` |
| actionsheet | `background-color: rgb(0, 0, 0)` | 1 | `div.dialogBackdrop.dialogBackdropOpened` |
| player | `background-color: rgb(0, 0, 0)` | 1 | `div.videoPlayerContainer` |
| player | `background-image: linear-gradient(0deg, rgba(16, 16, 16, 0.75), rgba(16, 16, 16, 0))` | 1 | `div.videoOsdBottom.videoOsdBottom-maincontrols` |
| player | `background-image: linear-gradient(rgba(16, 16, 16, 0.75), rgba(16, 16, 16, 0))` | 1 | `div.skinHeader.skinHeader-withBackground` |


### daylight

| View | Distinct color uses (stock) | Same value after | Element-uses stock | Element-uses unchanged |
| :--- | ---: | ---: | ---: | ---: |
| home | 11 | 2 | 131 | 46 (35%) |
| library | 22 | 3 | 328 | 142 (43%) |
| detail | 15 | 2 | 103 | 21 (20%) |
| actionsheet | 17 | 3 | 139 | 22 (16%) |
| player | 10 | 3 | 45 | 3 (7%) |
| dashboard | 19 | 19 | 324 | 323 (100%) |
| settings | 11 | 0 | 173 | 0 (0%) |
| login | 10 | 0 | 24 | 0 (0%) |

Color uses whose value did not change (excluding the Dashboard, which receives no Custom CSS):

| View | Property \| value | Elements | Examples |
| :--- | :--- | ---: | :--- |
| home | `color: rgba(255, 255, 255, 0.76)` | 41 | `span.material-icons.cardOverlayButtonIcon` |
| home | `background-color: rgba(51, 51, 51, 0.8)` | 5 | `div.itemProgressBar` |
| library | `border-color: rgba(255, 255, 255, 0.23)` | 2 | `button.MuiButtonBase-root.MuiButton-root` |
| library | `color: rgba(255, 255, 255, 0.76)` | 70 | `svg, path` |
| library | `fill: rgba(255, 255, 255, 0.76)` | 70 | `svg, path` |
| detail | `background-color: rgba(51, 51, 51, 0.8)` | 2 | `div.itemProgressBar` |
| detail | `color: rgba(255, 255, 255, 0.76)` | 19 | `span.material-icons.cardOverlayButtonIcon` |
| actionsheet | `background-color: rgba(51, 51, 51, 0.8)` | 2 | `div.itemProgressBar` |
| actionsheet | `color: rgba(255, 255, 255, 0.76)` | 19 | `span.material-icons.cardOverlayButtonIcon` |
| actionsheet | `background-color: rgb(0, 0, 0)` | 1 | `div.dialogBackdrop.dialogBackdropOpened` |
| player | `background-color: rgb(0, 0, 0)` | 1 | `div.videoPlayerContainer` |
| player | `background-image: linear-gradient(0deg, rgba(16, 16, 16, 0.75), rgba(16, 16, 16, 0))` | 1 | `div.videoOsdBottom.videoOsdBottom-maincontrols` |
| player | `background-image: linear-gradient(rgba(16, 16, 16, 0.75), rgba(16, 16, 16, 0))` | 1 | `div.skinHeader.skinHeader-withBackground` |


## Flatcap TV

Same throwaway server (container `fc-tv-qa`, Jellyfin 12.4.0, synthetic media in a Docker volume, 1920×1080, Chromium via `playwright-core`), `flatcap-tv.css` as Branding Custom CSS on the Dark theme. Script: `qa/shoot-tv.mjs`.

- **Static:** `python3 scripts/build.py --check` → `ok: 4 CSS files and 4 docs current, every --jf-* variable and class/id is in the Jellyfin 12.4.0 inventory, contrast targets met`. The three existing CSS files regenerate byte-identical (git shows them unmodified). The README/doc `build:` blocks in this repo are empty markers, so the doc half of that check is only as strong as that; the new rows are produced by `md_contrast` and were read from it directly.
- **Contrast (computed, WCAG 2.x, all pass the SKILL.md targets used by the check):** header icons/tabs on the header scrim over a white backdrop: text.primary 8.45, text.muted 5.53, accent.fg 6.11 (black backdrop 12.55 / 8.22 / 9.09). Page text on the full-page dim over white: text.primary 9.00, text.secondary 6.24, text.muted 5.90. Item-page text on the 92% scrim over white: primary 9.67, secondary 6.71, muted 6.33, accent 7.00, warning 7.35. Section/card titles on canvas 12.15 / 8.43 (surface 11.07 / 7.68). Play button accent.on on accent.fill 9.30. Focus ring vs canvas 10.74, surface 9.79, raised 8.57, black poster edge 13.32. Report only (not gated): ring on a white poster edge 1.58 (the 2px offset keeps it off the artwork); badge edge on a white poster 1.92 (the glyph carries the meaning).
- **Ran:** desktop layout and TV layout (`layout-tv`), home, movie library, item page and keyboard-focused card, each at 1920×1080 with backdrops on; a bright synthetic backdrop was also uploaded to one item to check the item-page scrim and header. Screenshots: `images/tv-home.png` (TV layout), `images/tv-focus.png` (TV layout), `images/tv-library.png` (desktop), `images/tv-detail.png` (desktop). I viewed them; they show the intended result but are synthetic gradients, not real posters.
- **Jellyfin Enhanced:** the real plugin (12.14.0.0, from `raw.githubusercontent.com/n00bcodr/jellyfin-plugins/main/10.11/manifest.json`, Active after a server restart) was installed in the throwaway server. Without CSS the legacy title and the plugin row both rendered; with Flatcap TV the legacy `.pageTitleWithLogo` computes `display:none` and the plugin row is intact (`header.MuiAppBar-root .je-header-actions-row`). Not simulated.
- **Optional titles block:** uncommented in the browser: cards with artwork `cardText` opacity 0, a hovered card 1, a card whose image container has `.defaultCardBackground` 1. The no-artwork card was a cloned, class-modified card, not a real item without images.
- **Not tested:** real TV devices or remote controls (keyboard only), other browsers, mobile layout, hover/pressed states other than the above, a real library with real posters, the admin Dashboard.

## Residual Jellyfin defaults

What the scan found unchanged, and why it was left:

- **On-scrim white (`rgba(255,255,255,.76)`)**: the hover overlay buttons on cards (`.cardOverlayButton*`) and their `rgba(0,0,0,.5–.7)` scrims. They sit on artwork, which can be any color; Jellyfin's scrim is the legibility guarantee, so it was kept.
- **Resume-bar track `rgba(51,51,51,.8)`** (`.itemProgressBar`): a dark track on the poster; the fill is Flatcap's (Slate accent in both modes, measured above over a white and a black poster).
- **OSD and header gradients `rgba(16,16,16,.75)→0`**, the black `.videoPlayerContainer` and `.dialogBackdrop`: video and modal scrims. Text on the OSD scrim is measured above.
- **Outlined MUI buttons** (`border-color: rgba(255,255,255,.23)`, e.g. in the library header): a literal in generated emotion CSS; not mapped.
- **Not in the scan, seen in the stylesheets and left alone**: `.defaultCardBackground1–5` (placeholder art of items without images), the live-TV guide category colors (`.programCell-*`, `.liveTvProgram`, …), `jstree`/`vakata` widgets (folder pickers, context menus, which are light-themed legacy widgets), the `#fff`/`#000` book, comic and PDF players, scrollbar colors, and the star in the slideshow. They were not visited with the demo library, so their appearance under Flatcap is untested.

## Not tested

Daylight on the built-in Light base theme and any other built-in theme (blueradiance, appletv, purplehaze, wmc); hover, pressed and disabled states beyond the TV focus check; mobile and tablet layouts; the admin Dashboard (not themed, see above); Firefox and Safari; Jellyfin Media Player/Desktop, the Android app's web view and any TV app (the native Android, iOS and TV clients are not web-based and cannot load Custom CSS, which was not verified here); live TV, music, books, photos and playlists views; toasts and form dialogs; right-to-left layouts; CJK languages; users with a different display theme than Dark.
