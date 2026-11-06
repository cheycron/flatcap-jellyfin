#!/usr/bin/env python3
"""Turn the qa/scan.mjs outputs (stock vs themed) into the markdown of docs/qa-report.md.

    python3 qa/summarize.py /tmp/fc-jf/scan-stock.json /tmp/fc-jf/scan-slate.json "Slate"

A computed color that is identical before and after is counted as "still Jellyfin's": the metric is by value, per view.
"""
import json
import sys

stock, themed, name = (json.load(open(sys.argv[1])), json.load(open(sys.argv[2])), sys.argv[3])
print(f"### {name}\n")
print("| View | Distinct color uses (stock) | Same value after | Element-uses stock | Element-uses unchanged |")
print("| :--- | ---: | ---: | ---: | ---: |")
detail = []
for v in stock:
    if v not in themed:
        continue
    same = [k for k in stock[v] if k in themed[v]]
    tot = sum(x["n"] for x in stock[v].values())
    unch = sum(themed[v][k]["n"] for k in same)
    print(f"| {v} | {len(stock[v])} | {len(same)} | {tot} | {unch} ({100 * unch / max(tot, 1):.0f}%) |")
    for k in same:
        detail.append((v, k, themed[v][k]["n"], ", ".join(themed[v][k]["ex"])))
print("\nColor uses whose value did not change (excluding the Dashboard, which receives no Custom CSS):\n")
print("| View | Property \\| value | Elements | Examples |")
print("| :--- | :--- | ---: | :--- |")
for v, k, n, ex in detail:
    if v != "dashboard":
        p, val = k.split("|", 1)
        print(f"| {v} | `{p}: {val[:70]}` | {n} | `{ex}` |")
