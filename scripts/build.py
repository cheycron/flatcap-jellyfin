#!/usr/bin/env python3
"""Build the Flatcap 2.0 Jellyfin Custom CSS files from src/theme.json.

    python3 scripts/build.py --sync     write themes/*.css and the generated blocks of README.md and docs/*.md
    python3 scripts/build.py --check    fail on: stale generated files, a --jf-* variable or a class/id that is not in
                                        src/jellyfin-inventory.json (Jellyfin 12.4.0), or a missed contrast target

Jellyfin 12.4 paints the web client with MUI `--jf-*` custom properties (declared at runtime on `[data-theme]`) plus
legacy theme CSS that hard-codes some colors. The CSS maps the Flatcap roles onto both. Python 3.10+, stdlib only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import color as C  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
THEME = ROOT / "src" / "theme.json"
INV = ROOT / "src" / "jellyfin-inventory.json"
FILES = {"slate": "flatcap-slate.css", "daylight": "flatcap-daylight.css", "system": "flatcap-system.css", "tv": "flatcap-tv.css"}

# --fc-* roles used by the rules: css name -> theme.json key
ROLES = {
    "canvas": "bg.canvas", "surface": "bg.surface", "raised": "bg.raised", "hover": "bg.hover", "selected": "bg.selected",
    "line": "border.subtle", "control": "border.control", "text": "text.primary", "text2": "text.secondary",
    "muted": "text.muted", "off": "text.disabled", "accent": "accent.fill", "accent-hover": "accent.hover",
    "on": "accent.on", "ring": "focus.ring", "ok": "success.fg", "ok-bg": "success.bg", "warn": "warning.fg",
    "warn-bg": "warning.bg", "bad": "danger.fg", "bad-bg": "danger.bg", "info": "info.fg", "info-bg": "info.bg",
}
ALPHA_BAR = 0.72  # `.skinHeader.semiTransparent` (header over a backdrop): canvas at this opacity
from tv import DOM_TOKENS, HDR_ALPHA, PLUGIN_TOKENS, SCRIM_ALPHA, pairs as tv_pairs, tv_css  # noqa: E402  (Flatcap TV rules live in scripts/tv.py)

# --jf-* variable -> role (a name from ROLES). A `*Channel` twin ("r g b") is emitted when the client declares one.
JF = {
    "background-default": "canvas", "background-paper": "surface", "AppBar-defaultBg": "surface",
    "text-primary": "text", "text-secondary": "text2", "text-disabled": "off", "text-icon": "muted",
    "action-active": "text2", "action-disabled": "off", "action-hover": "hover", "action-focus": "hover",
    "action-selected": "selected", "action-disabledBackground": "hover", "divider": "line",
    "primary-main": "accent", "primary-light": "accent-hover", "primary-dark": "accent-hover", "primary-contrastText": "on",
    "secondary-main": "ring", "secondary-light": "ring", "secondary-dark": "ring", "secondary-contrastText": "on",
    "error-main": "bad", "error-light": "bad", "error-dark": "bad", "error-contrastText": "on",
    "success-main": "ok", "success-light": "ok", "success-dark": "ok", "success-contrastText": "on",
    "warning-main": "warn", "warning-light": "warn", "warning-dark": "warn", "warning-contrastText": "on",
    "info-main": "info", "info-light": "info", "info-dark": "info", "info-contrastText": "on",
    "starIcon-main": "warn",
    "Alert-errorColor": "bad", "Alert-errorStandardBg": "bad-bg", "Alert-errorFilledBg": "bad", "Alert-errorFilledColor": "on", "Alert-errorIconColor": "bad",
    "Alert-successColor": "ok", "Alert-successStandardBg": "ok-bg", "Alert-successFilledBg": "ok", "Alert-successFilledColor": "on", "Alert-successIconColor": "ok",
    "Alert-warningColor": "warn", "Alert-warningStandardBg": "warn-bg", "Alert-warningFilledBg": "warn", "Alert-warningFilledColor": "on", "Alert-warningIconColor": "warn",
    "Alert-infoColor": "info", "Alert-infoStandardBg": "info-bg", "Alert-infoFilledBg": "info", "Alert-infoFilledColor": "on", "Alert-infoIconColor": "info",
    "SnackbarContent-bg": "raised", "SnackbarContent-color": "text", "Tooltip-bg": "raised",
    "FilledInput-bg": "raised", "FilledInput-hoverBg": "hover", "FilledInput-disabledBg": "surface", "FilledInput-borderColor": "control",
    "Button-inheritContainedBg": "raised", "Button-inheritContainedHoverBg": "hover",
    "LinearProgress-primaryBg": "line", "LinearProgress-secondaryBg": "line", "Slider-primaryTrack": "line", "Slider-secondaryTrack": "line",
    "TableCell-border": "line", "Avatar-defaultBg": "hover", "Chip-defaultBorder": "line", "Skeleton-bg": "hover",
}
# Variables a dark "on video / on poster" container re-declares, so Daylight stays readable on the video player
OSD_JF = ["text-primary", "text-secondary", "text-disabled", "action-active", "action-hover", "action-focus", "action-selected",
          "divider", "primary-main", "primary-light", "primary-dark", "primary-contrastText", "secondary-main",
          "secondary-light", "secondary-dark", "secondary-contrastText", "error-main", "error-light", "starIcon-main"]
OSD_SCOPE = ".videoOsdBottom,.osdHeader,.upNextContainer,.sliderBubble,.skip-button,.itemProgressBar,.iconOsd"

FONT_STACK = '"IBM Plex Sans","Segoe UI",system-ui,"Noto Sans",sans-serif'
UI_STACK_DOC = '"IBM Plex Sans", "Segoe UI", system-ui, sans-serif'

# Legacy hard-coded colors (selector -> {property: value}); value is a role name, `var(...)`/literal CSS, or a (role, role) switch
RULES: list[tuple[str, dict[str, str]]] = [
    (".collapseContent,.formDialogFooter:not(.formDialogFooter-clear),.formDialogHeader:not(.formDialogHeader-clear)", {"background-color": "surface"}),
    (".paperList,.visualCardBox", {"background-color": "surface"}),
    (".cardBox:not(.visualCardBox) .cardPadder", {"background-color": "surface"}),
    (".dialog", {"background-color": "raised"}),
    (".drawer-open,.mainDrawer", {"background-color": "surface"}),
    (".emby-scrollbuttons", {"color": "text"}),
    (".checkboxIcon", {"color": "on"}),
    (".starIcon", {"color": "warn"}),
    (".playbackProgress>div", {"background-color": "accent"}),
    (".transcodingProgress>div", {"background-color": "warn"}),
    (".recordingProgressBar::-webkit-progress-value,.recordingProgressBar::-moz-progress-bar,.recordingProgressBar[aria-valuenow]:before", {"background-color": "bad"}),
    ("progress::-webkit-progress-value,progress::-moz-progress-bar,progress[aria-valuenow]:before", {"background-color": "accent"}),
    ("progress::-webkit-progress-bar", {"background": "line"}),
    (".cardImageContainer .MuiLinearProgress-bar", {"background-color": "dark-accent"}),
    (".mdl-slider", {"color": "accent"}),
    (".mdl-slider-background-flex", {"background": "line"}),
    (".mdl-slider-background-upper", {"background": "off"}),
    (".mdl-slider-background-lower,.mdl-slider::-webkit-slider-thumb,.mdl-slider::-moz-range-thumb", {"background": "accent"}),
    (".sliderMarker.watched", {"background-color": "accent"}),
    (".sliderMarker.unwatched", {"background-color": "off"}),
    (".sliderBubble,.skip-button,.upNextDialog-button", {"background": "raised", "color": "text"}),
    (".iconOsd", {"background": "raised", "color": "text", "backdrop-filter": "none", "-webkit-backdrop-filter": "none"}),
    (".iconOsdProgressInner", {"background": "accent"}),
    (".iconOsdProgressOuter", {"background": "line"}),
    (".mdl-spinner__layer-1,.mdl-spinner__layer-2,.mdl-spinner__layer-3,.mdl-spinner__layer-4", {"border-color": "accent"}),
    (".mdl-radio__focus-circle", {"background": "accent"}),
    (".mdl-switch__thumb", {"background": "control"}),
    (".mdl-switch__track", {"background": "line"}),
    (".mdl-switch__input:checked+.mdl-switch__label+.mdl-switch__trackContainer>.mdl-switch__thumb", {"background": "accent"}),
    (".mdl-switch__input:checked+.mdl-switch__label+.mdl-switch__trackContainer>.mdl-switch__track", {"background": "selected"}),
    (".videoOsdBottom,.skinHeader-withBackground.osdHeader", {"color": "text"}),
]
# Rules emitted for the dark video/poster scope (no prefix); the scope redeclares the roles instead of repeating rules.
FOCUS = "a:not(.card),button:not(.card),input,select,textarea,[tabindex]:not(.card)"
FOCUS_CARD = ".card:focus-visible .cardBox"


def load() -> dict:
    return json.loads(THEME.read_text(encoding="utf-8"))


def inv() -> dict:
    return json.loads(INV.read_text(encoding="utf-8"))


def rgb(h: str) -> tuple[int, int, int]:
    c = C.parse(h)
    return tuple(round(v * 255) for v in c[:3])  # type: ignore[return-value]


def chan(h: str) -> str:
    return " ".join(map(str, rgb(h)))


def roles(theme: dict, mode: str) -> dict[str, str]:
    return {n: theme["themes"][mode][k] for n, k in ROLES.items()}


def jf_names(i: dict) -> set[str]:
    names = {n[len("--jf-"):] for n in i["palette_all_names"] if n.startswith("--jf-")}
    for rules in i["theme_css"].values():  # names the built-in themes reference with a var() fallback only
        for decls in rules.values():
            for v in decls.values():
                names |= {m.lower() and m for m in re.findall(r"--jf-([A-Za-z0-9-]+)", str(v))}
    return names


def block(theme: dict, mode: str, i: dict, indent: str = "") -> list[str]:
    r = roles(theme, mode)
    names = jf_names(i)
    out = [f"--fc-{n}:{h}" for n, h in r.items()]
    out.append(f"--fc-dark-accent:{theme['themes']['slate']['accent.fill']}")  # on posters: the Slate accent in every mode
    for k, role in JF.items():
        out.append(f"--jf-palette-{k}:var(--fc-{role})")
        if f"palette-{k}Channel" in names:
            out.append(f"--jf-palette-{k}Channel:{chan(r[role])}")
    out.append("--jf-palette-AppBar-transparentBg:rgb(%s/%s)" % (chan(r["canvas"]), ALPHA_BAR))
    out += [f"--jf-font-{f}:{v}" for f, v in font_vars(i).items()]
    return out


def font_vars(i: dict) -> dict[str, str]:
    res = {}
    for k, v in i["palette"]["dark"].items():
        if k.startswith("--jf-font-") and '"Noto Sans",sans-serif' in v:
            res[k[len("--jf-font-"):]] = v.replace('"Noto Sans",sans-serif', FONT_STACK)
    return res


def osd_block(theme: dict, i: dict) -> str:
    r = roles(theme, "slate")
    names = jf_names(i)
    d = [f"--fc-{n}:{h}" for n, h in r.items()]
    for k in OSD_JF:
        d.append(f"--jf-palette-{k}:var(--fc-{JF[k]})")
        if f"palette-{k}Channel" in names:
            d.append(f"--jf-palette-{k}Channel:{chan(r[JF[k]])}")
    return f"{OSD_SCOPE}{{{';'.join(d)}}}"


def rules_css() -> str:
    out = []
    for sel, props in RULES:
        body = ";".join(f"{p}:{'var(--fc-%s)' % v if v in ROLES or v == 'dark-accent' else v}" for p, v in props.items())
        sels = sel.split(",")
        # a vendor pseudo-element (::-moz-*) in a list makes the whole list invalid in Chromium: one rule each
        groups = [[s for s in sels if "-moz-" not in s]] + [[s] for s in sels if "-moz-" in s]
        for g in groups:
            if g:
                out.append(",".join("html " + s for s in g) + f"{{{body}}}")
    out.append("html,html[lang|=ja],html[lang|=ko],html[lang|=zh-CN],html[lang|=zh-TW],html[lang|=zh-HK]"
               "{font-family:\"IBM Plex Sans\",\"Segoe UI\",system-ui,\"Noto Sans\",\"Noto Sans JP\",\"Noto Sans KR\",\"Noto Sans SC\",\"Noto Sans TC\",\"Noto Sans HK\",sans-serif}")
    # Jellyfin sets `outline:none!important` on .card, .cardBox, .emby-button and .paper-icon-button-light
    out.append(f"html :is({FOCUS}):focus-visible,html {FOCUS_CARD}{{outline:2px solid var(--fc-ring)!important;outline-offset:2px}}")
    return "\n".join(out)


def header(theme: dict, name: str, what: str) -> str:
    return (f"/* Flatcap {theme['version']} for Jellyfin 12.4: {what}. Paste into Dashboard > Branding > Custom CSS "
            f"(base theme: Dark). Generated by scripts/build.py from src/theme.json: do not edit. */\n")


def emit(theme: dict, kind: str, i: dict) -> str:
    if kind == "tv":
        v = ";".join(block(theme, "slate", i) + [f"--fc-canvas-rgb:{chan(theme['themes']['slate']['bg.canvas'])}"])
        return (header(theme, kind, "Flatcap TV (dark, TV-first: artwork first, interface second)") + f":root:root{{{v}}}\n"
                + rules_css() + "\n" + osd_block(theme, i) + "\n" + tv_css(theme) + "\n")
    if kind in ("slate", "daylight"):
        v = ";".join(block(theme, kind, i))
        core = f":root:root{{{v}}}"
        what = f"Flatcap {kind.title()} ({'dark' if kind == 'slate' else 'light'})"
    else:
        d, l = ";".join(block(theme, "slate", i)), ";".join(block(theme, "daylight", i))
        core = f":root:root{{{d}}}\n@media (prefers-color-scheme:light){{:root:root{{{l}}}}}"
        what = "Flatcap system (Slate, or Daylight when the system is light)"
    return header(theme, kind, what) + core + "\n" + rules_css() + "\n" + osd_block(theme, i) + "\n"


def outputs(theme: dict, i: dict) -> dict[Path, str]:
    return {ROOT / "themes" / f: emit(theme, k, i) for k, f in FILES.items()}


# --- checks --------------------------------------------------------------------------------------------------------

def inventory_errors(i: dict, outs: dict[Path, str]) -> list[str]:
    errs = []
    names, toks = jf_names(i), set(i["tokens"])
    selectors = set()
    for p, css in outs.items():
        for m in re.finditer(r"--jf-([A-Za-z0-9-]+):", css):
            if m.group(1) not in names:
                errs.append(f"{p.name}: --jf-{m.group(1)} is not in the Jellyfin {i['jellyfin_web']} inventory")
        for sel in (re.findall(r"(?m)^([^@{}/][^{}]*)\{", css) + re.findall(r"\}\s*([^@{}/][^{}]*)\{", css)
                    + re.findall(r"\{\s*([^@{}/\s][^{}]*)\{", css)):
            selectors.add(sel)
    for sel in selectors:
        for t in re.findall(r"[.#][A-Za-z_][\w-]*", re.sub(r"\[[^\]]*\]", "", sel)):
            if t not in toks and t not in PLUGIN_TOKENS and t not in DOM_TOKENS and not (t.startswith(".Mui") and t[1:].split("-")[0] in set(i.get("mui_components", []))):
                errs.append(f"selector token {t} is not in the Jellyfin {i['jellyfin_web']} inventory ({sel[:60]})")
    return sorted(set(errs))


def hexc(h: str) -> C.RGBA:
    return C.parse(h)


def ratio(fg: str, bg: str) -> float:
    return C.contrast(C.over(hexc(fg), hexc(bg)) if C.parse(fg)[3] < 1 else hexc(fg), hexc(bg))


def over_scrim(base: str, scrim: tuple[float, float, float, float], frame: str) -> str:
    s = (scrim[0] / 255, scrim[1] / 255, scrim[2] / 255, scrim[3])
    return C.fmt(C.over(s, hexc(frame)))


def pairs(theme: dict) -> list[tuple[str, str, str, str, float, str]]:
    """(mode, label, fg, bg, target, group). Page pairs per mode; video/poster pairs use Slate (the OSD scope)."""
    out = []
    for mode in ("slate", "daylight"):
        t = theme["themes"][mode]
        g = lambda k: t[k]  # noqa: E731
        for s in ("canvas", "surface", "raised"):
            out.append((mode, f"text.primary on bg.{s}", g("text.primary"), g(f"bg.{s}"), 7.0, "text"))
            out.append((mode, f"text.secondary on bg.{s} (Jellyfin body text)", g("text.secondary"), g(f"bg.{s}"), 5.0, "text"))
            out.append((mode, f"text.muted on bg.{s}", g("text.muted"), g(f"bg.{s}"), 5.0, "text"))
            out.append((mode, f"accent.fg link/active tab on bg.{s}", g("accent.fg"), g(f"bg.{s}"), 5.0, "text"))
            out.append((mode, f"focus.ring on bg.{s} (card focus border, ring)", g("focus.ring"), g(f"bg.{s}"), 3.0, "focus"))
            out.append((mode, f"border.control on bg.{s} (inputs)", g("border.control"), g(f"bg.{s}"), 3.0, "outline"))
        for s in ("hover", "selected"):
            out.append((mode, f"text.primary on bg.{s} (list hover, selection)", g("text.primary"), g(f"bg.{s}"), 7.0, "text"))
            out.append((mode, f"text.secondary on bg.{s}", g("text.secondary"), g(f"bg.{s}"), 5.0, "text"))
        for n in ("accent.fill", "accent.hover", "accent.pressed", "focus.ring", "success.fg", "warning.fg", "danger.fg", "info.fg"):
            out.append((mode, f"accent.on on {n} (button, nav selected, badge, focused button)", g("accent.on"), g(n), 4.5, "fill"))
        for fg, bg in (("success.fg", "success.bg"), ("warning.fg", "warning.bg"), ("danger.fg", "danger.bg"), ("info.fg", "info.bg")):
            out.append((mode, f"{fg} on {bg} (alert)", g(fg), g(bg), 4.5, "feedback"))
        out.append((mode, "text.primary on bg.raised (toast, tooltip, dialog)", g("text.primary"), g("bg.raised"), 7.0, "feedback"))
        out.append((mode, "accent.fill on bg.surface (played/count badge edge, active control)", g("accent.fill"), g("bg.surface"), 3.0, "outline"))
        out.append((mode, "accent.fill on bg.canvas (progress bar, slider, switch thumb)", g("accent.fill"), g("bg.canvas"), 3.0, "outline"))
        out.append((mode, "accent.fill on border.subtle (page progress fill vs track)", g("accent.fill"), g("border.subtle"), 3.0, "outline"))
        out.append((mode, "accent.fill on bg.selected (switch thumb vs checked track)", g("accent.fill"), g("bg.selected"), 3.0, "outline"))
        out.append((mode, "text.primary on header over a white backdrop (canvas @%.0f%%)" % (ALPHA_BAR * 100), g("text.primary"),
                    C.fmt(C.over((*C.parse(g("bg.canvas"))[:3], ALPHA_BAR), hexc("#FFFFFF"))), 4.5, "text"))
        out.append((mode, "text.primary on header over a black backdrop (canvas @%.0f%%)" % (ALPHA_BAR * 100), g("text.primary"),
                    C.fmt(C.over((*C.parse(g("bg.canvas"))[:3], ALPHA_BAR), hexc("#000000"))), 4.5, "text"))
        # increased-contrast text is not shipped in this port: Jellyfin has no contrast preference (see docs).
    # Dark video/poster scope (Slate roles in every file). The scrim is Jellyfin's own: rgba(16,16,16,.75) at the OSD edge.
    t = theme["themes"]["slate"]
    for frame, name in (("#FFFFFF", "white frame"), ("#000000", "black frame")):
        scrim = over_scrim("", (16, 16, 16, 0.75), frame)
        out.append(("osd", f"OSD text #fff on scrim over a {name}", "#FFFFFF", scrim, 7.0, "osd"))
        out.append(("osd", f"OSD text.primary (slate) on scrim over a {name}", t["text.primary"], scrim, 7.0 if frame == "#000000" else 4.5, "osd"))
        out.append(("osd", f"OSD played bar / thumb (accent) on scrim over a {name}", t["accent.fill"], scrim, 3.0, "osd"))
        out.append(("osd", f"OSD focus.ring on scrim over a {name}", t["focus.ring"], scrim, 3.0, "osd"))
        trk = over_scrim("", (51, 51, 51, 0.8), frame)
        out.append(("osd", f"Resume bar (accent) on Jellyfin's poster track rgba(51,51,51,.8) over a {name}", t["accent.fill"], trk, 3.0, "osd"))
    out.append(("osd", "OSD popup text.primary on bg.raised (slider bubble, skip button)", t["text.primary"], t["bg.raised"], 7.0, "osd"))
    # Report-only rows (target 1.0): the unfilled/buffered parts of the OSD slider.
    bright = over_scrim("", (16, 16, 16, 0.75), "#FFFFFF")
    out.append(("osd", "OSD track (border.subtle) on scrim over a white frame (report only)", t["border.subtle"], bright, 1.0, "report"))
    out.append(("osd", "OSD buffered (text.disabled) on scrim over a white frame (report only)", t["text.disabled"], bright, 1.0, "report"))
    out.append(("osd", "OSD played (accent) vs buffered (text.disabled) (report only)", t["accent.fill"], t["text.disabled"], 1.0, "report"))
    return out + tv_pairs(theme)


def rows(theme: dict) -> list[dict]:
    return [{"mode": m, "label": lab, "fg": fg, "bg": bg, "target": tg, "group": gr, "ratio": ratio(fg, bg)}
            for m, lab, fg, bg, tg, gr in pairs(theme)]


def contrast_errors(theme: dict) -> list[str]:
    return [f"{r['mode']}: {r['label']} = {r['ratio']:.2f} < {r['target']}" for r in rows(theme) if r["ratio"] < r["target"]]


def validate_core(theme: dict) -> list[str]:
    errs = []
    if theme.get("version") != "2.0.0":
        errs.append(f"src/theme.json version is {theme.get('version')}, expected 2.0.0")
    for mode in ("slate", "daylight"):
        for k in ROLES.values():
            if not C.is_hex(theme["themes"][mode].get(k, "")):
                errs.append(f"{mode}: missing or non-hex {k}")
    return errs


# --- generated doc blocks ------------------------------------------------------------------------------------------

def md_themes(theme: dict) -> str:
    sizes = {k: len((ROOT / "themes" / f).read_bytes()) if (ROOT / "themes" / f).exists() else 0 for k, f in FILES.items()}
    r = ["| File | Mode | Base theme to select | Size |", "| :--- | :--- | :--- | ---: |"]
    for k, mode in (("slate", "dark"), ("daylight", "light"), ("system", "follows `prefers-color-scheme`")):
        r.append(f"| `themes/{FILES[k]}` | {mode} | Dark (default) | {sizes[k] / 1024:.1f} KB |")
    return "\n".join(r)


def md_fonts(theme: dict) -> str:
    return ("| Use | Stack (exact) |\n| :--- | :--- |\n"
            f"| Interface (`--jf-font-*` and `html`) | `{FONT_STACK.replace(',', ', ')}` (the `html` rule also lists the Noto Sans CJK families the client ships) |\n\n"
            "The CSS does not install fonts. Without IBM Plex Sans on the device, the stack falls back to Segoe UI, system-ui, then Noto Sans (the client's own font).")


def md_vars(theme: dict) -> str:
    r = roles(theme, "slate")
    d = roles(theme, "daylight")
    lines = ["| `--jf-palette-…` | Flatcap role | Slate | Daylight |", "| :--- | :--- | :--- | :--- |"]
    inv_names = None
    for k, role in JF.items():
        key = ROLES[role]
        lines.append(f"| `{k}` | `{key}` | `{r[role]}` | `{d[role]}` |")
    lines.append("| `AppBar-transparentBg` | `bg.canvas` at %.0f%% | `%s` | `%s` |" % (ALPHA_BAR * 100, r["canvas"], d["canvas"]))
    return "\n".join(lines)


def md_rules(theme: dict) -> str:
    lines = ["| Selector (prefixed with `html ` in the CSS) | Property | Role |", "| :--- | :--- | :--- |"]
    for sel, props in RULES:
        for p, v in props.items():
            lines.append(f"| `{sel}` | `{p}` | `{ROLES[v] if v in ROLES else ('accent.fill (Slate, in every mode)' if v == 'dark-accent' else v)}` |")
    lines.append(f"| `:is({FOCUS}):focus-visible`, `{FOCUS_CARD}` | `outline` (`!important`: Jellyfin sets `outline:none!important`) | `focus.ring`, 2px, offset 2px |")
    lines.append(f"| `{OSD_SCOPE}` | roles + `--jf-palette-*` re-declared with the Slate values | dark video / poster scope |")
    return "\n".join(lines)


def md_contrast(theme: dict) -> str:
    lines = ["| Scope | Pair | Ratio | Target | Result |", "| :--- | :--- | ---: | ---: | :--- |"]
    for r in rows(theme):
        res = "report only" if r["group"] == "report" else ("pass" if r["ratio"] >= r["target"] else "**FAIL**")
        tg = "-" if r["group"] == "report" else f"{r['target']:g}"
        lines.append(f"| {r['mode']} | {r['label']} `{r['fg'].upper()}` / `{r['bg'].upper()}` | {r['ratio']:.2f} | {tg} | {res} |")
    return "\n".join(lines)


def md_inventory(theme: dict) -> str:
    i = inv()
    c = i["counts"]
    out = [f"Source: the web client bundled with Jellyfin **{i['jellyfin_web']}** (`ghcr.io/linuxserver/jellyfin:12.4ubu2604-ls57`).", "",
           "| Item | Count |", "| :--- | ---: |",
           f"| Runtime `--jf-*` variables (dark and light themes) | {c['palette_vars']} |",
           f"| Distinct palette colors across both themes | {c['palette_colors']} |",
           f"| Color-bearing rules in `themes/dark/theme.css` | {c['theme_css_rules_dark']} |",
           f"| Color-bearing rules in `themes/light/theme.css` | {c['theme_css_rules_light']} |",
           f"| Application stylesheets scanned | {c['app_css_files']} |",
           f"| Color-bearing application rules | {c['app_css_color_rules']} |",
           f"| Class and id tokens in the bundle | {c['tokens']} |", "",
           "Dark and light palette values that Flatcap replaces:", "",
           "| Variable | Dark | Light | Flatcap role |", "| :--- | :--- | :--- | :--- |"]
    d, l = i["palette"]["dark"], i["palette"]["light"]
    for k in JF:
        n = f"--jf-palette-{k}"
        if n in d:
            out.append(f"| `{n}` | `{d[n]}` | `{l[n]}` | `{ROLES[JF[k]]}` |")
        else:
            out.append(f"| `{n}` | (fallback only) | (fallback only) | `{ROLES[JF[k]]}` |")
    return "\n".join(out)


BLOCKS = {"themes": md_themes, "fonts": md_fonts, "vars": md_vars, "rules": md_rules, "contrast": md_contrast, "inventory": md_inventory}
DOCS = [ROOT / "README.md", ROOT / "docs" / "mapping.md", ROOT / "docs" / "inventory.md", ROOT / "docs" / "qa-report.md"]


def render(path: Path, theme: dict) -> str:
    text = path.read_text(encoding="utf-8")
    for name, fn in BLOCKS.items():
        pat = re.compile(rf"(<!-- build:{name} -->\n).*?(\n<!-- /build:{name} -->)", re.S)
        text = pat.sub(lambda m: m.group(1) + fn(theme) + m.group(2), text)
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--sync", action="store_true")
    g.add_argument("--check", action="store_true")
    a = ap.parse_args()
    theme, i = load(), inv()
    errs = validate_core(theme)
    outs = outputs(theme, i)
    if a.sync:
        for p, css in outs.items():
            p.parent.mkdir(exist_ok=True)
            p.write_text(css, encoding="utf-8")
        for p in DOCS:
            if p.exists():
                p.write_text(render(p, theme), encoding="utf-8")
        print("synced:", ", ".join(p.name for p in outs))
        errs += inventory_errors(i, outs) + contrast_errors(theme)
        for e in errs:
            print("WARN", e)
        return 0
    stale = []
    for p, css in outs.items():
        if not p.exists() or p.read_text(encoding="utf-8") != css:
            stale.append(str(p.relative_to(ROOT)))
    for p in DOCS:
        if p.exists() and p.read_text(encoding="utf-8") != render(p, theme):
            stale.append(str(p.relative_to(ROOT)))
    errs += [f"stale generated file: {s} (run --sync)" for s in stale]
    errs += inventory_errors(i, outs) + contrast_errors(theme)
    if errs:
        print("\n".join(errs))
        return 1
    print(f"ok: {len(outs)} CSS files and {len([p for p in DOCS if p.exists()])} docs current, every --jf-* variable and class/id is in the "
          f"Jellyfin {i['jellyfin_web']} inventory, contrast targets met")
    return 0


if __name__ == "__main__":
    sys.exit(main())
