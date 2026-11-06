#!/usr/bin/env python3
"""Generate the synthetic demo library used for the Flatcap Jellyfin screenshots.

    python3 qa/make_media.py /tmp/fc-jf/media

Everything is made here: gradient/geometric "posters" and "backdrops" drawn with Pillow, titles invented,
videos rendered by ffmpeg from the backdrop with a running clock. No third-party artwork, no real people.
Needs Python 3.10+, Pillow and ffmpeg (with drawtext). Not run by CI.
"""
from __future__ import annotations

import colorsys
import math
import random
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

MOVIES = [  # title, year, hue, plot, shape
    ("Lantern Harbor", 2019, 0.58, "A night ferry pilot keeps a failing lighthouse alive for one more winter.", "circles"),
    ("The Quiet Orchard", 2021, 0.33, "Three siblings return to an abandoned orchard and decide whether to sell it.", "stripes"),
    ("Paper Comet", 2018, 0.08, "A cartographer redraws the sky after a comet that nobody else remembers.", "rays"),
    ("Glass Meridian", 2023, 0.50, "A survey crew crosses a frozen salt flat and finds a line on the map that moves.", "grid"),
    ("Saltwater Chorus", 2017, 0.62, "Fishing towns along one coast share a single song and one rule about it.", "waves"),
    ("Ember & Slate", 2022, 0.02, "Two restorers argue over how much of an old theater should be left broken.", "circles"),
    ("Northbound Echo", 2020, 0.72, "A radio relay operator hears tomorrow's weather report a day too early.", "rays"),
    ("Velvet Static", 2016, 0.85, "A synth repair shop becomes the last stop for a band that never existed.", "stripes"),
    ("Marrow Lane", 2024, 0.14, "A baker, a courier and a city inspector share one very long Tuesday.", "grid"),
    ("Kite Season", 2015, 0.42, "A village paints its roofs to guide a festival of kites home.", "waves"),
]
SHOW = ("Observatory Nine", 2022, 0.66, "Staff at a remote observatory log strange but entirely polite anomalies.",
        [("Calibration", "The new technician learns which dials are allowed to be wrong."),
         ("Dark Frames", "A week of cloud cover tests the crew's patience and its coffee supply."),
         ("Parallax", "A visitor measures the same star twice and gets two answers.")])


def col(h: float, s: float, v: float) -> tuple[int, int, int]:
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return int(r * 255), int(g * 255), int(b * 255)


def gradient(w: int, h: int, c1, c2, angle: float = 0.35) -> Image.Image:
    img = Image.new("RGB", (w, h))
    px = img.load()
    ca, sa = math.cos(angle), math.sin(angle)
    span = abs(w * ca) + abs(h * sa)
    for y in range(h):
        for x in range(w):
            t = max(0.0, min(1.0, (x * ca + y * sa) / span + 0.2))
            px[x, y] = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
    return img


def shapes(img: Image.Image, hue: float, kind: str, seed: int) -> None:
    rnd = random.Random(seed)
    w, h = img.size
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for i in range(9):
        c = col(hue + rnd.uniform(-0.08, 0.08), rnd.uniform(0.25, 0.6), rnd.uniform(0.7, 1.0)) + (rnd.randint(30, 90),)
        if kind == "circles":
            r = rnd.randint(h // 8, h // 2)
            x, y = rnd.randint(0, w), rnd.randint(0, h)
            d.ellipse((x - r, y - r, x + r, y + r), fill=c)
        elif kind == "stripes":
            x = rnd.randint(-w // 4, w)
            d.polygon([(x, 0), (x + w // 7, 0), (x + w // 7 - h // 3, h), (x - h // 3, h)], fill=c)
        elif kind == "rays":
            cx, cy = w * 0.5, h * 0.62
            a = rnd.uniform(0, math.tau)
            d.polygon([(cx, cy), (cx + math.cos(a) * w * 2, cy + math.sin(a) * w * 2),
                       (cx + math.cos(a + 0.18) * w * 2, cy + math.sin(a + 0.18) * w * 2)], fill=c)
        elif kind == "grid":
            s = max(w, h) // 8
            x, y = rnd.randrange(0, w, s), rnd.randrange(0, h, s)
            d.rectangle((x, y, x + s * rnd.randint(1, 3), y + s * rnd.randint(1, 3)), fill=c)
        else:  # waves
            y0 = rnd.randint(0, h)
            pts = [(x, y0 + math.sin(x / (w / 6) + i) * h / 10) for x in range(0, w + 8, 8)]
            d.polygon(pts + [(w, h), (0, h)], fill=c)
    img.paste(Image.alpha_composite(img.convert("RGBA"), ov.filter(ImageFilter.GaussianBlur(2))).convert("RGB"))


def wrap(draw: ImageDraw.ImageDraw, text: str, font, width: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        t = (cur + " " + word).strip()
        if draw.textlength(t, font=font) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = word
    lines.append(cur)
    return lines


def poster(path: Path, title: str, year: int, hue: float, kind: str, seed: int) -> None:
    w, h = 600, 900
    img = gradient(w, h, col(hue, 0.55, 0.30), col(hue + 0.06, 0.45, 0.78), 1.2)
    shapes(img, hue, kind, seed)
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT, 56)
    lines = wrap(d, title.upper(), f, w - 100)
    y = h - 90 - 70 * len(lines)
    d.rectangle((0, y - 40, w, h), fill=(0, 0, 0))
    img.paste(Image.blend(img.crop((0, y - 40, w, h)), Image.new("RGB", (w, h - y + 40), (10, 12, 16)), 0.62), (0, y - 40))
    d = ImageDraw.Draw(img)
    for ln in lines:
        d.text((50, y), ln, font=f, fill=(244, 246, 248))
        y += 70
    d.text((50, h - 62), str(year), font=ImageFont.truetype(FONT_R, 30), fill=(210, 216, 224))
    img.save(path, quality=90)


def backdrop(path: Path, title: str, hue: float, kind: str, seed: int, size=(1920, 1080)) -> None:
    w, h = size
    img = gradient(w, h, col(hue, 0.6, 0.22), col(hue + 0.08, 0.4, 0.70), 0.2)
    shapes(img, hue, kind, seed + 99)
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT, 110)
    d.text((w // 2, h // 2), title.upper(), font=f, fill=(255, 255, 255), anchor="mm")
    img.save(path, quality=88)


def video(out: Path, img: Path, title: str, secs: int, hue: float) -> None:
    tone = 220 + int(hue * 300)
    cmd = ["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", "12", "-t", str(secs), "-i", str(img),
           "-f", "lavfi", "-t", str(secs), "-i", f"sine=frequency={tone}:sample_rate=44100",
           "-vf", "scale=960:540,drawbox=x=0:y=ih-14:w=iw*t/%d:h=14:color=white@0.8:t=fill,"
                  "drawtext=fontfile=%s:text='%%{pts\\:hms}':fontsize=44:fontcolor=white:x=40:y=40:box=1:boxcolor=black@0.5:boxborderw=12" % (secs, FONT_R),
           "-c:v", "libx264", "-preset", "ultrafast", "-crf", "34", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "48k", "-shortest", str(out)]
    subprocess.run(cmd, check=True)


def nfo(path: Path, root: str, title: str, year: int, plot: str, extra: str = "") -> None:
    path.write_text(f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<{root}>\n  <title>{title}</title>\n'
                    f"  <year>{year}</year>\n  <plot>{plot}</plot>\n  <genre>Drama</genre>\n{extra}</{root}>\n")


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/fc-jf/media")
    for n, (title, year, hue, plot, kind) in enumerate(MOVIES):
        d = root / "movies" / f"{title} ({year})"
        d.mkdir(parents=True, exist_ok=True)
        poster(d / "poster.jpg", title, year, hue, kind, n)
        backdrop(d / "backdrop.jpg", title, hue, kind, n)
        video(d / f"{title} ({year}).mp4", d / "backdrop.jpg", title, 60, hue)
        nfo(d / "movie.nfo", "movie", title, year, plot, "  <runtime>1</runtime>\n  <rating>7.4</rating>\n  <mpaa>PG</mpaa>\n")
        print("movie", title)
    title, year, hue, plot, eps = SHOW
    d = root / "shows" / f"{title} ({year})"
    (d / "Season 01").mkdir(parents=True, exist_ok=True)
    poster(d / "poster.jpg", title, year, hue, "grid", 50)
    backdrop(d / "backdrop.jpg", title, hue, "grid", 50)
    nfo(d / "tvshow.nfo", "tvshow", title, year, plot)
    for i, (et, ep_plot) in enumerate(eps, 1):
        f = d / "Season 01" / f"{title} S01E{i:02d}.mp4"
        eb = d / "Season 01" / f"ep{i}.jpg"
        backdrop(eb, f"{title} - {et}", hue + i * 0.03, "rays", 60 + i, (1280, 720))
        video(f, eb, et, 45, hue)
        eb.rename(d / "Season 01" / f"{title} S01E{i:02d}-thumb.jpg")
        nfo(d / "Season 01" / f"{title} S01E{i:02d}.nfo", "episodedetails", et, year, ep_plot,
            f"  <season>1</season>\n  <episode>{i}</episode>\n")
    print("show", title)


if __name__ == "__main__":
    main()
