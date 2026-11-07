#!/usr/bin/env python3
"""Build the demo library used for the Flatcap Jellyfin screenshots from openly licensed artwork.

    python3 qa/make_media.py /tmp/fc-jf/art /tmp/fc-jf/media

Artwork (Blender open movies, CC BY; public-domain classics) comes from Wikimedia Commons, listed with author and
license in images/CREDITS.md. Missing files are downloaded into the art dir (Commons thumbnails, polite delay).
Posters/backdrops are cropped to 2:3 / 16:9, NFO files are written here (titles, years, one-sentence plots by the author),
and every video is a tiny generated clip of the backdrop at 1 fps, never the film. Needs Python 3.10+, Pillow and ffmpeg.
Not run by CI. Mount the output at /demo-media in the throwaway container, then run qa/seed.py.
"""
import hashlib, subprocess, sys, time, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image

ART = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/fc-jf/art")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "/tmp/fc-jf/media")

# slug, title, year, minutes, genres, rating, poster(file, cx fractional crop centre), backdrop(file, cx), plot
MOVIES = [
    ("sintel", "Sintel", 2010, 15, ["Animation", "Fantasy"], 7.5, ("sintel-poster.jpg", .5), ("sintel-bd.jpg", .5),
     "A young woman sets out to find the baby dragon she once befriended. Her search leads across a hard country and to a surprise."),
    ("tos", "Tears of Steel", 2012, 12, ["Science Fiction", "Short"], 6.9, ("tos-poster.jpg", .5), ("tos-bd2.jpg", .5),
     "A group of warriors and scientists gather in Amsterdam to try one last experiment that could stop the robots from taking over."),
    ("bbb", "Big Buck Bunny", 2008, 10, ["Animation", "Comedy"], 6.8, ("bbb-poster.jpg", .5), ("bbb-bd.png", .5),
     "A giant rabbit with a heart bigger than himself is pushed too far by three small rodents. His patience runs out in a very inventive way."),
    ("ed", "Elephants Dream", 2006, 11, ["Animation", "Science Fiction"], 6.2, ("ed-poster", .58), ("ed-bd1.jpg", .5),
     "Two strange characters explore a capricious and seemingly infinite machine. One of them is sure of what he sees, the other is not."),
    ("cl", "Cosmos Laundromat", 2015, 12, ["Animation", "Fantasy"], 7.0, ("cl-poster.jpg", .5), ("cl-bd.jpg", .5),
     "On a desolate island, a suicidal sheep named Franck meets a mysterious salesman. He offers a gift that lets Franck live a thousand lives."),
    ("spring", "Spring", 2019, 8, ["Animation", "Fantasy"], 7.4, ("spring-poster.jpg", .5), ("spring-bd2.jpg", .5),
     "A shepherd girl and her dog face ancient spirits in order to continue the cycle of life. A story about the renewal of nature."),
    ("sf", "Sprite Fright", 2021, 11, ["Animation", "Comedy", "Horror"], 6.6, ("sf-poster.jpg", .5), ("sf-bd2.jpg", .5),
     "A group of friends on a woodland picnic wakes something under the trees. The forest has its own idea of a campfire story."),
    ("charge", "Charge", 2022, 5, ["Animation", "Science Fiction"], 6.7, ("charge-poster.jpg", .5), ("charge-bd3.png", .85),
     "A battered, one-armed soldier is pursued across a ruined landscape. A last charge is the only thing left to protect."),
    ("metro", "Metropolis", 1927, 150, ["Science Fiction", "Drama", "Silent"], 8.1, ("metro-poster.jpg", .5), ("metro-bd.jpg", .5),
     "In a towering city of thinkers above and workers below, the son of the city's master crosses the divide. What he finds there threatens the order of both."),
    ("caligari", "The Cabinet of Dr. Caligari", 1920, 77, ["Horror", "Silent"], 8.0, ("caligari-poster.jpg", .5), None,
     "A traveling showman presents a sleepwalker at a fair, and a series of strange events follows the visit. A young man tries to piece together who is behind them."),
    ("general", "The General", 1926, 79, ["Comedy", "Action", "Silent"], 8.1, ("general-poster.png", .5), None,
     "A railway engineer chases a stolen locomotive behind enemy lines. The chase turns into one long, carefully timed stunt."),
    ("kid", "The Kid", 1921, 68, ["Comedy", "Drama", "Silent"], 8.2, ("kid-poster.jpg", .5), None,
     "A street-wise tramp takes in an abandoned child and raises him. Their small, improvised household is tested when officials step in."),
    ("safety", "Safety Last!", 1923, 70, ["Comedy", "Silent"], 8.1, ("safety-poster.jpg", .5), None,
     "A young man from a small town tries to make good in the city. A publicity stunt puts him on the side of a tall building."),
    ("moon", "A Trip to the Moon", 1902, 12, ["Science Fiction", "Fantasy", "Silent"], 8.0, ("moon-poster.jpg", .5), None,
     "A group of astronomers builds a capsule and fires it at the Moon. What they meet there is not what the textbooks predicted."),
]
SHOW = ("caminandes", "Caminandes", 2013, ["Animation", "Comedy", "Family"], 7.6, ("cam-poster", .72), ("cam3b.png", .5),
        "A small llama named Koro has simple ambitions and a very determined rival. Three short episodes about food, fences and friendship.",
        [("Llama Drama", "cam1.png", 3, "Koro tries to cross a road to reach a tasty bush, but a stubborn rival is in the way."),
         ("Gran Dillama", "cam2.png", 3, "Koro wants a bite of the neighbour's pasture. An electric fence and a very small helper make it difficult."),
         ("Llamigos", "cam3.png", 3, "Winter is coming and food is short. Koro and Oti find that sharing makes a better plan.")])


# local name -> (Commons file title, thumbnail width); every one is credited in images/CREDITS.md
ARTWORK = {
    "sintel-poster.jpg": ("Sintel poster.jpg", 960), "sintel-bd.jpg": ("Durian - Sintel-wallpaper-sintel.jpg", 1920),
    "tos-poster.jpg": ("Tos-poster.png", 960), "tos-bd2.jpg": ("Tears of Steel frame 09 1a.jpg", 1920),
    "bbb-poster.jpg": ("Big buck bunny poster big.jpg", 960), "bbb-bd.png": ("Big.Buck.Bunny.-.Frank.Rinky.Gimera.png", 1920),
    "ed-bd1.jpg": ("Elephants Dream s8 proog.jpg", 1920),
    "cl-poster.jpg": ("CosmosLaundromatPoster.jpg", 960), "cl-bd.jpg": ("Franck the caterpillar.jpg", 1920),
    "spring-poster.jpg": ("Spring2019PillarPosterBlender.jpg", 960), "spring-bd2.jpg": ("SpringOpenMovie-final scene.jpg", 1920),
    "sf-poster.jpg": ("Sprite Fright-movie poster.jpg", 960), "sf-bd2.jpg": ("Sprite Fright-concept art-group 02.jpg", 1920),
    "charge-poster.jpg": ("Charge-movie poster.jpg", 960), "charge-bd3.png": ("Charge-concept art-robot 01.png", 1920),
    "metro-poster.jpg": ("Boris Bilinski - Filmplakat für Metropolis restored.jpg", 960),
    "metro-bd.jpg": ("1927 Boris Bilinski (1900-1948) Plakat für den Film Metropolis, Staatliche Museen zu Berlin.jpg", 1280),
    "caligari-poster.jpg": ("The Cabinet of Doctor Caligari Movie poster.jpg", 960),
    "general-poster.png": ("The General (1926) - Movie Poster 2.png", 800),
    "kid-poster.jpg": ("The Kid (1921) poster.jpg", 960), "safety-poster.jpg": ("Safety last poster.jpg", 600),
    "moon-poster.jpg": ("Voyage dans la Lune affiche.jpg", 800),
    "cam1.png": ("Pablo Vazquez - Caminandes - Episode 1 - Llama Drama - Cover thumbnail.png", 1920),
    "cam2.png": ("Blender Foundation - Caminandes - Episode 2 - Gran Dillama - Cover thumbnail.png", 1920),
    "cam3.png": ("Blender Foundation - Caminandes - Episode 3 - Llamigos - Cover thumbnail.png", 1920),
    "cam2b.png": ("Caminandes gran dillama.png", 1920),
    "cam3b.png": ("Blender Foundation - Caminandes - Episode 3 - Llamigos - Koro and Oti share more food to eat at night.png", 1920),
}


def fetch_art():
    """Download missing artwork as Commons thumbnails. Widths below a source's width are not guaranteed to be a standard
    thumbnail size: if a request is refused, download that file by hand from its Commons page into the art dir."""
    ART.mkdir(parents=True, exist_ok=True)
    for local, (title, w) in ARTWORK.items():
        if (ART / local).exists():
            continue
        n = title.replace(" ", "_")
        h = hashlib.md5(n.encode()).hexdigest()
        q = urllib.parse.quote(n)
        url = f"https://upload.wikimedia.org/wikipedia/commons/thumb/{h[0]}/{h[:2]}/{q}/{w}px-{q}"
        for attempt in range(4):
            time.sleep(4)
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "flatcap-jellyfin-qa/1.0 (https://github.com/cheycron/flatcap-jellyfin)"})
                (ART / local).write_bytes(urllib.request.urlopen(req, timeout=90).read())
                print("fetched", local, flush=True)
                break
            except OSError as e:
                print("retry", local, str(e)[:60], flush=True)
                time.sleep(20)


def fit(img, w, h, cx=.5, cy=.5):
    """Cover-crop to w x h; cx/cy position the window in the source."""
    s = max(w / img.width, h / img.height)
    im = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    x = round((im.width - w) * cx)
    y = round((im.height - h) * cy)
    return im.crop((x, y, x + w, y + h))


def src(name, special=None):
    if name == "ed-poster":
        im = Image.open(ART / "ed-bd1.jpg").convert("RGB")
        return im.crop((int(1920 * .58) - 360, 0, int(1920 * .58) + 360, 1080))  # portrait around Proog
    if name == "cam-poster":
        im = Image.open(ART / "cam2b.png").convert("RGB")
        return im
    return Image.open(ART / name).convert("RGB")


def poster(name, cx, out):
    im = fit(src(name), 600, 900, cx, .5)
    im.save(out, quality=88, optimize=True, progressive=True)


def backdrop(name, cx, out):
    im = fit(src(name), 1920, 1080, cx, .5)
    im.save(out, quality=85, optimize=True, progressive=True)


def clip(out, bd, minutes, w=960):
    secs = minutes * 60
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", "1", "-t", str(secs), "-i", str(bd),
                    "-f", "lavfi", "-t", str(secs), "-i", "anullsrc=r=22050:cl=mono",
                    "-vf", f"scale={w}:-2,format=yuv420p", "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage", "-crf", "30", "-g", "10",
                    "-c:a", "aac", "-b:a", "16k", "-shortest", str(out)], check=True)


def esc(s):
    return s.replace("&", "&amp;")


def nfo(path, root, title, year, plot, genres, rating=None, minutes=None, extra=""):
    g = "".join(f"  <genre>{x}</genre>\n" for x in genres)
    r = f"  <rating>{rating}</rating>\n" if rating else ""
    m = f"  <runtime>{minutes}</runtime>\n" if minutes else ""
    path.write_text(f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<{root}>\n  <title>{esc(title)}</title>\n  <year>{year}</year>\n'
                    f"  <plot>{esc(plot)}</plot>\n{g}{r}{m}{extra}</{root}>\n")


def main():
    fetch_art()
    for slug, title, year, mins, genres, rating, (pf, pcx), bd, plot in MOVIES:
        d = OUT / "movies" / f"{title} ({year})"
        if d.exists():
            continue
        d.mkdir(parents=True)
        poster(pf, pcx, d / "poster.jpg")
        bf, bcx = bd or (None, 0)
        if bf:
            backdrop(bf, bcx, d / "backdrop.jpg")
        clip(d / f"{title} ({year}).mp4", d / ("backdrop.jpg" if bf else "poster.jpg"), mins)
        nfo(d / "movie.nfo", "movie", title, year, plot, genres, rating, mins, "  <mpaa>PG</mpaa>\n")
        print("movie", title, flush=True)
    slug, title, year, genres, rating, (pf, pcx), (bf, bcx), plot, eps = SHOW
    if (OUT / "shows" / f"{title} ({year})").exists():
        return
    d = OUT / "shows" / f"{title} ({year})"
    (d / "Season 01").mkdir(parents=True)
    poster(pf, pcx, d / "poster.jpg")
    backdrop(bf, bcx, d / "backdrop.jpg")
    nfo(d / "tvshow.nfo", "tvshow", title, year, plot, genres, rating, extra="  <mpaa>TV-Y</mpaa>\n")
    for i, (et, thumb, mins, ep_plot) in enumerate(eps, 1):
        base = d / "Season 01" / f"{title} S01E{i:02d}"
        fit(Image.open(ART / thumb).convert("RGB"), 1280, 720).save(f"{base}-thumb.jpg", quality=85, optimize=True)
        clip(f"{base}.mp4", f"{base}-thumb.jpg", mins, 640)
        nfo(Path(f"{base}.nfo"), "episodedetails", et, (2013, 2013, 2016)[i - 1], ep_plot, [], minutes=mins, extra=f"  <season>1</season>\n  <episode>{i}</episode>\n")
    print("show", title)


if __name__ == "__main__":
    main()
