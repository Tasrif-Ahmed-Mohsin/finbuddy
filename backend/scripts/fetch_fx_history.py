"""Download daily USD→BDT and USD→CNY history into backend/app/data/fx_history.csv.

Source: fawazahmed0/exchange-api (licence CC0-1.0, public domain), one JSON snapshot per day,
served by jsDelivr with a Cloudflare Pages mirror as fallback.
Known limitation: around official Bangladesh Bank changes the series lags by ~1–2 days
(e.g. the 8 May 2024 crawling-peg move appears on 10 May 2024).

Usage:  python scripts/fetch_fx_history.py [--start 2024-03-02] [--end YYYY-MM-DD]
Re-running only downloads dates that are missing from the CSV.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "app" / "data" / "fx_history.csv"
URLS = [
    "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{d}/v1/currencies/usd.json",
    "https://{d}.currency-api.pages.dev/v1/currencies/usd.json",
]


def fetch(d: str) -> tuple[str, float, float] | None:
    for url in URLS:
        try:
            with urllib.request.urlopen(url.format(d=d), timeout=20) as r:
                j = json.load(r)
            rates = j["usd"]
            return (j.get("date", d), float(rates["bdt"]), float(rates["cny"]))
        except Exception:
            continue
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2024-03-02")
    ap.add_argument("--end", default=date.today().isoformat())
    args = ap.parse_args()

    existing: dict[str, tuple[float, float]] = {}
    if OUT.exists():
        with OUT.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                existing[row["date"]] = (float(row["bdt_per_usd"]), float(row["cny_per_usd"]))

    start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
    wanted = [(start + timedelta(days=i)).isoformat() for i in range((end - start).days + 1)]
    todo = [d for d in wanted if d not in existing]
    print(f"{len(existing)} days cached, downloading {len(todo)}…")
    with ThreadPoolExecutor(max_workers=16) as pool:
        for d, res in zip(todo, pool.map(fetch, todo)):
            if res and res[0] == d:  # skip days where the CDN served a different snapshot
                existing[d] = (res[1], res[2])
    missing = [d for d in wanted if d not in existing]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "bdt_per_usd", "cny_per_usd"])
        for d in sorted(existing):
            w.writerow([d, f"{existing[d][0]:.6f}", f"{existing[d][1]:.6f}"])
    print(f"wrote {len(existing)} days to {OUT} ({len(missing)} missing)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
