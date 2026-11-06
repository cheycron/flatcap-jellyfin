#!/usr/bin/env python3
"""Build src/jellyfin-inventory.json from the web client bundled with a Jellyfin server.

    python3 scripts/inventory.py --fetch fc-jf-demo --runtime /tmp/fc-jf/runtime-vars.json   # docker cp the web dir, then scan
    python3 scripts/inventory.py --web /path/to/jellyfin-web --runtime runtime-vars.json
    python3 scripts/inventory.py --check --web /path/to/jellyfin-web --runtime runtime-vars.json

What it records (12.4.0: the web client is a React/MUI app with a CSS-variable theme, plus legacy CSS):
  * palette      the runtime `--jf-*` custom properties of :root for the built-in `dark` and `light` themes
                 (they are declared by the MUI theme in JavaScript, so they are read from a running client:
                 qa/dump-vars.mjs).
  * theme_css    every declaration with a literal color (no var() fallback) in themes/dark/theme.css and
                 themes/light/theme.css, plus the var()-driven ones: selector -> property -> value. This is the
                 real list of what the built-in themes paint.
  * app_css      color-bearing declarations of the application stylesheets (everything else under the web dir).
  * tokens       every class and id token that appears in any stylesheet of the bundle: a selector of the Flatcap
                 CSS must be built from these.
Python 3.10+, standard library only. Output is deterministic.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "src" / "jellyfin-inventory.json"

COLOR_PROPS = {"color", "background", "background-color", "border-color", "border", "border-top", "border-bottom",
               "border-left", "border-right", "border-top-color", "border-bottom-color", "border-left-color",
               "border-right-color", "outline", "outline-color", "fill", "stroke", "box-shadow", "text-shadow",
               "caret-color", "accent-color", "background-image", "color-scheme", "scrollbar-color", "filter",
               "backdrop-filter", "-webkit-backdrop-filter", "text-decoration-color"}
LITERAL = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?)\([^)]*\)|\b(?:white|black|transparent|currentcolor|red|gray|grey)\b")


def strip_comments(s: str) -> str:
    return re.sub(r"/\*.*?\*/", "", s, flags=re.S)


def parse_rules(css: str, media: str = "") -> list[tuple[str, str, str]]:
    """(media, selector, body) for every style rule; nested at-rules are flattened with their prelude as `media`."""
    out, i, n = [], 0, len(css)
    while i < n:
        j = css.find("{", i)
        if j < 0:
            break
        prelude = css[i:j].strip()
        depth, k = 1, j + 1
        while k < n and depth:
            c = css[k]
            depth += (c == "{") - (c == "}")
            k += 1
        body = css[j + 1:k - 1]
        if prelude.startswith("@"):
            if prelude.startswith(("@media", "@supports", "@layer", "@container")):
                out += parse_rules(body, (media + " " + prelude).strip())
        else:
            out.append((media, re.sub(r"\s+", " ", prelude), body))
        i = k
    return out


def decls(body: str) -> list[tuple[str, str]]:
    res = []
    for part in re.split(r";(?![^(]*\))", body):
        if ":" in part:
            k, v = part.split(":", 1)
            res.append((k.strip().lower(), v.strip()))
    return res


def colour_decls(css_path: Path, literal_only: bool = False) -> dict[str, dict[str, str]]:
    """selector (with media prefix) -> {property: value} for color-bearing declarations. The last value of a property wins
    except that a `var()` declaration with a literal fallback listed before it is kept as the var() form."""
    res: dict[str, dict[str, str]] = {}
    for media, sel, body in parse_rules(strip_comments(css_path.read_text(errors="replace"))):
        d = {}
        for k, v in decls(body):
            if k in COLOR_PROPS or k.startswith("--jf") or k.startswith("--"):
                if "var(" in v or LITERAL.search(v) or k.startswith("--") or k in ("color-scheme",):
                    if literal_only and "var(" in v:
                        continue
                    d[k] = v
        if d:
            key = (media + " " + sel).strip()
            res.setdefault(key, {}).update(d)
    return res


def tokens_of(css_path: Path) -> set[str]:
    toks: set[str] = set()
    for _, sel, _b in parse_rules(strip_comments(css_path.read_text(errors="replace"))):
        # drop attribute selectors and strings so their contents are not read as tokens
        s = re.sub(r"\[[^\]]*\]", "", sel)
        toks.update(re.findall(r"[.#][A-Za-z_][\w-]*", s))
    return toks


def build(web: Path, runtime: dict, version: str) -> dict:
    themes_dir = web / "themes"
    theme_css = {}
    for name in ("dark", "light"):
        theme_css[name] = colour_decls(themes_dir / name / "theme.css")
    app_files = sorted(p for p in web.glob("*.css"))
    app_css: dict[str, dict[str, str]] = {}
    tokens: set[str] = set()
    for p in app_files + [themes_dir / "dark" / "theme.css", themes_dir / "light" / "theme.css", themes_dir / "_base" / "theme.css"]:
        tokens |= tokens_of(p)
        if p.parent == web:
            for sel, d in colour_decls(p, literal_only=False).items():
                app_css.setdefault(sel, {}).update(d)
    # the inline <style> of index.html carries a few global rules
    html = (web / "index.html").read_text(errors="replace")
    for m in re.finditer(r"<style>(.*?)</style>", html, flags=re.S):
        tmp = Path(tempfile.mkstemp(suffix=".css")[1])
        tmp.write_text(m.group(1))
        tokens |= tokens_of(tmp)
        for sel, d in colour_decls(tmp).items():
            app_css.setdefault(sel, {}).update(d)
        tmp.unlink()
    # MUI components get class names from JavaScript (`MuiLinearProgress-bar`): record the component names the bundle spells out (slots such as `-bar` are added at runtime and were observed in the DOM)
    mui: set[str] = set()
    for p in sorted(web.glob("*.js")):
        mui |= set(re.findall(r"\bMui[A-Z][A-Za-z]+", p.read_text(errors="replace")))
    pal = {}
    for t in ("dark", "light"):
        pal[t] = {k: v for k, v in sorted(runtime[t]["vars"].items()) if k.startswith(("--jf-palette", "--jf-opacity", "--jf-card", "--jf-shape", "--jf-font", "--jf-shadows-1", "--jf-spacing", "--jf-zIndex-modal"))}
    return {
        "jellyfin_web": version,
        "palette": pal,
        "palette_all_names": sorted(runtime["dark"]["vars"]),
        "theme_css": theme_css,
        "app_css": {k: app_css[k] for k in sorted(app_css)},
        "tokens": sorted(tokens),
        "mui_components": sorted(mui),
        "counts": {
            "palette_vars": len(runtime["dark"]["vars"]),
            "palette_colors": sum(1 for k in runtime["dark"]["vars"] if k.startswith("--jf-palette") and not k.endswith("Channel")),
            "theme_css_rules_dark": len(theme_css["dark"]), "theme_css_rules_light": len(theme_css["light"]),
            "app_css_files": len(app_files), "app_css_color_rules": len(app_css), "tokens": len(tokens), "mui_components": len(mui),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fetch", metavar="CONTAINER", help="docker cp /usr/share/jellyfin/web out of a (throwaway) container")
    ap.add_argument("--web", type=Path, help="a jellyfin-web directory")
    ap.add_argument("--runtime", type=Path, required=True, help="JSON written by qa/dump-vars.mjs")
    ap.add_argument("--version", default="12.4.0")
    ap.add_argument("--check", action="store_true", help="fail if src/jellyfin-inventory.json differs from a fresh scan")
    a = ap.parse_args()
    web = a.web
    tmp = None
    if a.fetch:
        tmp = Path(tempfile.mkdtemp(prefix="jfweb-"))
        subprocess.run(["docker", "cp", f"{a.fetch}:/usr/share/jellyfin/web", str(tmp / "web")], check=True)
        web = tmp / "web"
    if not web or not web.is_dir():
        print("error: need --fetch or --web", file=sys.stderr)
        return 1
    inv = build(web, json.loads(a.runtime.read_text()), a.version)
    text = json.dumps(inv, indent=1, sort_keys=False) + "\n"
    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)
    if a.check:
        if OUT.read_text() != text:
            print("error: src/jellyfin-inventory.json is stale", file=sys.stderr)
            return 1
        print("ok: inventory matches")
        return 0
    OUT.write_text(text)
    c = inv["counts"]
    print(f"wrote {OUT.relative_to(ROOT)}: {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
