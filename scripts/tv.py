"""Flatcap TV: the rules that turn the Slate file into a minimal, TV-first variant ("artwork first, interface second").

Everything here is generated from `src/theme.json`: colors are `var(--fc-*)` roles (the `:root:root` block of the file), sizes
come from `metrics`/`typography`, and the two scrim opacities below are the only numbers that carry a contrast argument
(`scripts/build.py --check` measures them over a white and a black backdrop). Standard library only.
"""
from __future__ import annotations

import color as C

HDR_ALPHA = 0.88      # header over a backdrop: canvas scrim in the icon band, fading to 0 at the lower edge of the bar
SCRIM_ALPHA = 0.92    # item page: canvas scrim over the artwork where the title and metadata sit
PAGE_DIM = 0.90       # full-page backdrop (user setting "Backdrops"): Jellyfin dims it with the canvas at 86%; Flatcap TV makes it 90%
PLUGIN_TOKENS = {".je-header-actions-row"}  # Jellyfin Enhanced (plugin) class, not part of the 12.4.0 web client inventory
# Classes the web client's JavaScript sets on its DOM; no stylesheet of the bundle names them (verified in the 12.4.0 bundle and a live page)
DOM_TOKENS = {".btnPlay", ".section0", ".verticalSection"}

CV = "rgb(var(--fc-canvas-rgb)/%s)"  # canvas at an opacity (channels declared next to the roles in the same file)


def _grad(*stops: str, to: str = "to bottom") -> str:
    return f"linear-gradient({to},{','.join(stops)})"


def tv_css(theme: dict) -> str:
    m, ty = theme["metrics"], theme["typography"]
    t = {
        "fw": m["focus.width"], "fo": m["focus.offset"], "fast": m["motion.fast"], "rc": m["radius.control"],
        "rp": m["radius.panel"], "s2": m["space.2"], "s3": m["space.3"], "s4": m["space.4"], "s6": m["space.6"],
        "s8": m["space.8"], "s12": m["space.12"], "title": ty["font.size.title"], "heading": ty["font.size.heading"],
        "body": ty["font.size.body"], "meta": ty["font.size.meta"], "ui": ty["font.ui"], "semi": ty["font.weight.semibold"],
        "med": ty["font.weight.medium"],
    }
    hdr_scrim = _grad(CV % HDR_ALPHA, CV % HDR_ALPHA + " 55%", CV % 0)
    # the backdrop of an item page is the full-page one (`.backdropImage`, dimmed by `.backgroundContainer.withBackdrop`); the hero is the top 52vh
    item_scrim = _grad(CV % 0.30, CV % 0.55 + " 20vh", CV % SCRIM_ALPHA + " calc(52vh - 10em)", "var(--fc-canvas) 52vh", "var(--fc-canvas)")
    ring = "outline:@fw@ solid var(--fc-ring)!important;outline-offset:@fo@"
    card = "html .itemsContainer .card"
    on_card = f"{card}:is(:hover,:focus-visible,.show-focus:focus) .cardBox"

    R: list = [
        ("/* Flatcap TV: header */", None),
        # Header: flat, Slate surface; over a backdrop a matte canvas scrim instead of a bar. The player OSD header is not touched.
        ("html .skinHeader-withBackground:not(.osdHeader)",
         "background-color:var(--fc-surface);background-image:none;box-shadow:none;backdrop-filter:none;-webkit-backdrop-filter:none"),
        ("html .skinHeader.semiTransparent:not(.osdHeader)", f"background-color:transparent;background-image:{hdr_scrim}"),
        ("html header.MuiAppBar-root", "background-color:var(--fc-surface);background-image:none;box-shadow:none;backdrop-filter:none;-webkit-backdrop-filter:none"),
        ("html:has(.skinHeader.semiTransparent:not(.osdHeader)) header.MuiAppBar-root", f"background-color:transparent;background-image:{hdr_scrim}"),
        ("html .skinHeader:not(.osdHeader) .headerButton,html .skinHeader:not(.osdHeader) .pageTitle,html .skinHeader:not(.osdHeader) .emby-tab-button:not(.emby-tab-button-active)", "color:var(--fc-muted)"),
        ("html .skinHeader:not(.osdHeader) .headerButton:hover,html .skinHeader:not(.osdHeader) .emby-tab-button:not(.emby-tab-button-active):hover", "color:var(--fc-text)"),
        ("html .skinHeader:not(.osdHeader) .emby-tab-button-active", "color:var(--fc-accent)"),
        ("html header.MuiAppBar-root :is(.MuiButton-colorInherit,.MuiIconButton-colorInherit):not(.MuiButtonGroup-groupedContained)", "color:var(--fc-muted)"),
        ("html header.MuiAppBar-root :is(.MuiButton-colorInherit,.MuiIconButton-colorInherit):not(.MuiButtonGroup-groupedContained):hover", "color:var(--fc-text)"),
        ("html header.MuiAppBar-root .MuiButton-colorPrimary:not(.MuiButtonGroup-groupedContained)", "color:var(--fc-accent)"),
        # Compatibility: with Jellyfin Enhanced the header row is `header.MuiAppBar-root .je-header-actions-row`; hide the legacy logo/title that overlapped it
        ("html:has(.je-header-actions-row) .skinHeader .pageTitle.pageTitleWithLogo", "display:none"),

        ("/* Flatcap TV: home rows */", None),
        ("html .sectionTitle-cards,html .sectionTitleContainer-cards .sectionTitle,html .sectionTitleTextButton>.sectionTitle",
         "font-family:@ui@;font-size:@title@;font-weight:@med@;line-height:1.3;letter-spacing:0;text-transform:none;color:var(--fc-text2)"),
        ("html .sectionTitleContainer-cards", "padding-top:@s4@"),
        ("html .verticalSection:not(.hide)", "margin-bottom:@s8@"),
        ("html .section0 .cardText-first", "font-size:@meta@"),
        ("@media(min-width:50em)", [
            ("html .overflowPortraitCard,html .overflowSquareCard", "width:21vw"),
            ("html .overflowBackdropCard,html .overflowSmallBackdropCard", "width:30vw"),
            ("html .section0 .overflowBackdropCard", "width:24vw")]),
        ("@media(min-width:75em)", [
            ("html .overflowPortraitCard,html .overflowSquareCard", "width:17vw"),
            ("html .overflowBackdropCard,html .overflowSmallBackdropCard", "width:27vw"),
            ("html .portraitCard,html .squareCard", "width:16.6666666667%"),
            ("html .section0 .overflowBackdropCard", "width:19vw")]),
        ("@media(min-width:100em)", [
            ("html .overflowPortraitCard,html .overflowSquareCard", "width:14vw"),
            ("html .overflowBackdropCard,html .overflowSmallBackdropCard", "width:22vw"),
            ("html .portraitCard,html .squareCard", "width:14.2857142857%"),
            ("html .section0 .overflowBackdropCard", "width:15vw")]),

        ("/* Flatcap TV: cards (flat; titles under the poster stay visible) */", None),
        ("html .cardBox:not(.visualCardBox) .cardPadder,html .cardContent-shadow", "box-shadow:none"),
        ("html .cardImageContainer,html .cardContent,html .cardOverlayContainer,html .cardBox:not(.visualCardBox) .cardPadder", "border-radius:@rc@"),
        ("html .cardText-first,html .cardText-first .textActionButton", "color:var(--fc-text);font-size:@body@"),
        ("html .cardText-secondary,html .cardText-secondary .textActionButton", "color:var(--fc-muted);font-size:@meta@"),
        ("html .playedIndicator,html .countIndicator", "background:var(--fc-accent);color:var(--fc-on);box-shadow:none"),
        ("html .playedIndicator", "font-size:62%"),
        ("html .countIndicator", "font-size:76%"),
        ("html .itemProgressBar", "height:3px"),

        ("/* Flatcap TV: focus and hover (ring in the focus role, card scales, neighbours stay put) */", None),
        (f"{card} .cardBox", "transition:transform @fast@ ease-out;will-change:transform"),
        ("html .card.show-focus .cardBox.visualCardBox,html .card.show-focus .cardBox:not(.visualCardBox) .cardScalable", "border:0!important;border-radius:0"),
        ("html .card.show-focus:not(.show-animation) .cardBox", "margin-left:.6em;margin-right:.6em;margin-top:.6em"),
        (on_card, f"transform:scale(1.04)!important;{ring}"),
        (f"{card}:has(:focus-visible) .cardBox", f"transform:scale(1.04)!important;{ring}"),
        ("html .itemsContainer .card .cardContent:focus-visible", "outline:none!important"),
        ("html .emby-button.show-focus:focus", "transform:scale(1.04)"),
        ("@media(prefers-reduced-motion:reduce)", [
            (f"{card} .cardBox", "transition:none;will-change:auto"),
            (on_card, "transform:none!important"),
            (f"{card}:has(:focus-visible) .cardBox", "transform:none!important"),
            ("html .emby-button.show-focus:focus", "transform:none")]),

        ("/* Flatcap TV: item page (matte scrim to the canvas; one primary Play, the rest icon buttons) */", None),
        ("html .layout-desktop .itemBackdrop", "height:52vh"),
        ("html .backgroundContainer.withBackdrop", f"opacity:{PAGE_DIM}"),
        ("html.layout-desktop:has(.itemDetailPage:not(.hide)) .backgroundContainer.withBackdrop", f"background-color:transparent;background-image:{item_scrim};opacity:1"),
        ("html .detailRibbon", "background:none;background-color:transparent"),
        ("html .layout-desktop .detailRibbon", "height:9em;margin-top:-9em"),
        ("html .itemName.parentNameLast,html h1.itemName", "font-family:@ui@;font-size:2.4rem;font-weight:@semi@;line-height:1.15;color:var(--fc-text)"),
        ("html .itemMiscInfo,html .itemMiscInfo .mediaInfoItem,html .endsAt", "color:var(--fc-muted);font-size:@body@"),
        ("html .detailLogo", "width:30vw;height:20vh;top:6vh"),
        ("html .mainDetailButtons .detailButton", "background:transparent;color:var(--fc-muted);border-radius:@rc@"),
        ("html .mainDetailButtons .detailButton:hover", "background:var(--fc-hover);color:var(--fc-text)"),
        ("html .mainDetailButtons .btnPlay",
         "background:var(--fc-accent);color:var(--fc-on);min-width:3.5em;padding-left:@s4@;padding-right:@s4@"),
        ("html .mainDetailButtons .btnPlay:hover", "background:var(--fc-accent-hover);color:var(--fc-on)"),
        ("html .mainDetailButtons .btnPlay .detailButton-icon", "color:var(--fc-on)"),
        ("html .mainDetailButtons .detailButton:focus-visible", ring),
    ]

    out: list[str] = []

    def sub(s: str) -> str:
        for k, v in t.items():
            s = s.replace(f"@{k}@", v)
        return s

    for sel, body in R:
        if body is None:
            out.append(sel)
        elif isinstance(body, list):
            out.append(f"{sel}{{" + "".join(f"{sub(s)}{{{sub(b)}}}" for s, b in body) + "}")
        else:
            out.append(f"{sub(sel)}{{{sub(body)}}}")
    out += ["", optional_block(t)]
    return "\n".join(out)


def optional_block(t: dict) -> str:
    """Commented out: users delete the first and the last line to turn it on. Cards without artwork keep their title."""
    hide = ("html .itemsContainer .card:not(:hover):not(:focus-within):not(.show-focus:focus) "
            ".cardBox:has(.cardImageContainer:not(.defaultCardBackground)) .cardText")
    return ("/* Optional: show titles only on focus or hover. To turn it on, delete this line and the last line of this block.\n"
            f"html .itemsContainer .cardText{{transition:opacity {t['fast']} ease-out}}\n"
            f"{hide}{{opacity:0}}\n"
            "Optional: end of block */")


# --- contrast pairs for the TV surfaces (Slate roles) ------------------------------------------------------------------

def _flat(theme: dict, alpha: float, frame: str) -> str:
    c = C.parse(theme["themes"]["slate"]["bg.canvas"])
    return C.fmt(C.over((c[0], c[1], c[2], alpha), C.parse(frame)))


def pairs(theme: dict) -> list[tuple[str, str, str, str, float, str]]:
    t = theme["themes"]["slate"]
    out = []
    mode = "tv"
    for s in ("surface", "canvas"):
        for n, tg in (("text.primary", 7.0), ("text.muted", 5.0), ("accent.fg", 5.0), ("text.secondary", 5.0)):
            out.append((mode, f"{n} on bg.{s} (header, section titles, card titles, metadata)", t[n], t[f"bg.{s}"], tg, "tv"))
    for frame, name in (("#FFFFFF", "white"), ("#000000", "black")):
        hdr = _flat(theme, HDR_ALPHA, frame)
        for n, tg in (("text.primary", 7.0), ("text.muted", 4.5), ("accent.fg", 4.5)):
            out.append((mode, f"{n} (header icons, tabs, active) on header scrim (canvas @{HDR_ALPHA * 100:.0f}%) over a {name} backdrop", t[n], hdr, tg, "tv"))
        pg = _flat(theme, PAGE_DIM, frame)
        for n, tg in (("text.primary", 7.0), ("text.secondary", 5.0), ("text.muted", 5.0), ("accent.fg", 5.0)):
            out.append((mode, f"{n} (any page text) on the full-page backdrop dim (canvas @{PAGE_DIM * 100:.0f}%) over a {name} backdrop", t[n], pg, tg, "tv"))
        scr = _flat(theme, SCRIM_ALPHA, frame)
        for n, tg in (("text.primary", 7.0), ("text.secondary", 5.0), ("text.muted", 5.0), ("accent.fg", 5.0), ("warning.fg", 4.5)):
            out.append((mode, f"{n} (item title, metadata, overview) on item scrim (canvas @{SCRIM_ALPHA * 100:.0f}%) over a {name} backdrop", t[n], scr, tg, "tv"))
    for n in ("accent.fill", "accent.hover"):
        out.append((mode, f"accent.on on {n} (primary Play button, played and count badge)", t["accent.on"], t[n], 4.5, "tv"))
    for s in ("canvas", "surface", "raised"):
        out.append((mode, f"focus.ring on bg.{s} (2px card ring, offset 2px: the gap shows the page surface)", t["focus.ring"], t[f"bg.{s}"], 3.0, "tv"))
    out.append((mode, "focus.ring on a black poster edge", t["focus.ring"], "#000000", 3.0, "tv"))
    out.append((mode, "focus.ring on a white poster edge (report only: the 2px offset keeps the ring off the artwork)", t["focus.ring"], "#FFFFFF", 1.0, "report"))
    out.append((mode, "accent.fill badge edge on a white poster (report only: the badge glyph carries the meaning, accent.on on accent.fill is measured above)", t["accent.fill"], "#FFFFFF", 1.0, "report"))
    return out
