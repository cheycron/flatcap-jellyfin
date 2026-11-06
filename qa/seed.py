#!/usr/bin/env python3
"""Seed a THROWAWAY Jellyfin (default http://127.0.0.1:18096) for the Flatcap screenshots.

    python3 qa/seed.py [base_url]

Completes the startup wizard with the demo admin `ada`, adds the two demo libraries (movies at /demo-media/movies,
shows at /demo-media/shows) with internet metadata and image fetchers OFF (so only the generated artwork and .nfo files
are used), waits for the scan, then marks some items played and some partly watched so the played indicator and
the resume bars show. Never point this at a real server. Standard library only. Not run by CI.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:18096"
USER, PASSWORD = "ada", "Demo-pass-2026!"
AUTH = 'MediaBrowser Client="Flatcap QA", Device="qa", DeviceId="flatcap-qa", Version="1.0"'


def call(method: str, path: str, body=None, token: str | None = None):
    headers = {"Content-Type": "application/json", "Authorization": AUTH + (f', Token="{token}"' if token else "")}
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{method} {path} -> {e.code} {e.read()[:300]!r}")


def wait_up() -> None:
    for _ in range(60):
        try:
            return call("GET", "/System/Info/Public") and None
        except (SystemExit, OSError):
            time.sleep(2)
    raise SystemExit("server did not come up")


def main() -> None:
    wait_up()
    pub = call("GET", "/System/Info/Public")
    print("server", pub["Version"], "wizard done:", pub["StartupWizardCompleted"])
    if not pub["StartupWizardCompleted"]:
        call("POST", "/Startup/Configuration", {"UICulture": "en-US", "MetadataCountryCode": "US", "PreferredMetadataLanguage": "en"})
        call("GET", "/Startup/User")
        call("POST", "/Startup/User", {"Name": USER, "Password": PASSWORD})
        call("POST", "/Startup/RemoteAccess", {"EnableRemoteAccess": False, "EnableAutomaticPortMapping": False})
        call("POST", "/Startup/Complete")
    auth = call("POST", "/Users/AuthenticateByName", {"Username": USER, "Pw": PASSWORD})
    token, uid = auth["AccessToken"], auth["User"]["Id"]
    cfg = call("GET", "/System/Configuration", token=token)
    cfg["ServerName"] = "Flatcap Demo"
    call("POST", "/System/Configuration", cfg, token)
    have = {f["Name"] for f in call("GET", "/Library/VirtualFolders", token=token)}
    for name, ctype, path, typ in (("Movies", "movies", "/demo-media/movies", "Movie"), ("Shows", "tvshows", "/demo-media/shows", "Series")):
        if name in have:
            continue
        opts = {"EnableInternetProviders": False, "EnableRealtimeMonitor": False, "SaveLocalMetadata": False,
                "LocalMetadataReaderOrder": ["Nfo"], "MetadataSavers": [],
                "TypeOptions": [{"Type": t, "MetadataFetchers": [], "ImageFetchers": []}
                                for t in ((typ,) if typ == "Movie" else ("Series", "Season", "Episode"))],
                "PathInfos": [{"Path": path}]}
        call("POST", f"/Library/VirtualFolders?name={name}&collectionType={ctype}&refreshLibrary=true", {"LibraryOptions": opts}, token)
    for _ in range(90):
        items = call("GET", f"/Items?userId={uid}&Recursive=true&IncludeItemTypes=Movie,Episode", token=token)["Items"]
        if len(items) >= 13:
            break
        time.sleep(2)
    print("items", len(items))
    by = {i["Name"]: i["Id"] for i in items}
    played = ["Paper Comet", "Glass Meridian", "Kite Season", "Calibration"]
    partial = {"Lantern Harbor": 0.62, "The Quiet Orchard": 0.35, "Northbound Echo": 0.18, "Dark Frames": 0.5}
    for n in played:
        if n in by:
            call("POST", f"/UserPlayedItems/{by[n]}?userId={uid}", token=token)
    for n, frac in partial.items():
        if n in by:
            ticks = int(frac * 60 * 10_000_000)
            call("POST", f"/UserItems/{by[n]}/UserData?userId={uid}", {"PlaybackPositionTicks": ticks, "Played": False}, token)
    # one favorite so the heart state shows
    if "Marrow Lane" in by:
        call("POST", f"/UserFavoriteItems/{by['Marrow Lane']}?userId={uid}", token=token)
    print("seeded; user id", uid)


if __name__ == "__main__":
    main()
