"""Real exchange rates: live mid-market rate + daily history, with offline fallback.

Source: fawazahmed0/exchange-api (CC0-1.0, public domain), daily snapshots.
  * live    : fetch today's rate (cached for an hour); if the network fails, use the last
              saved day from fx_history.csv (important for the on-site final).
  * offline : only the saved history.
  * fixture : fixed values for automated tests (deterministic numbers).
Set with SATHI_FX_MODE. History is refreshed by scripts/fetch_fx_history.py.
"""
from __future__ import annotations

import csv
import json
import os
import time
import urllib.request
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import numpy as np

from app.engines.fx_range import RateRange, coverage_backtest, rate_range
from app.market import MidRates

HISTORY_CSV = Path(__file__).resolve().parent / "data" / "fx_history.csv"
SOURCE = "fawazahmed0/exchange-api (CC0), daily mid-market"
LIVE_URLS = [
    "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json",
    "https://latest.currency-api.pages.dev/v1/currencies/usd.json",
]
FIXTURE = MidRates(Decimal("122.90"), Decimal("6.95"), "2026-10-12", "fixed test values", sample=True)
RANGE_WINDOW = 250  # ~8 months of daily data: best calibrated at short horizons in our backtest


@dataclass(frozen=True)
class FxPoint:
    date: str
    bdt_per_usd: float
    cny_per_usd: float

    @property
    def bdt_per_cny(self) -> float:
        return self.bdt_per_usd / self.cny_per_usd


def load_history(path: Path = HISTORY_CSV) -> list[FxPoint]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [FxPoint(r["date"], float(r["bdt_per_usd"]), float(r["cny_per_usd"])) for r in csv.DictReader(f)]


class FxProvider:
    def __init__(self, mode: str | None = None, history: list[FxPoint] | None = None):
        self.mode = mode or os.environ.get("SATHI_FX_MODE", "live")
        self.history = history if history is not None else load_history()
        self._live: tuple[float, MidRates] | None = None
        self.last_error: str | None = None

    # ---- current rate --------------------------------------------------------
    def latest(self) -> MidRates:
        if self.mode == "fixture":
            return FIXTURE
        if self.mode == "live":
            if self._live and time.time() - self._live[0] < 3600:
                return self._live[1]
            for url in LIVE_URLS:
                try:
                    with urllib.request.urlopen(url, timeout=6) as r:
                        j = json.load(r)
                    mid = MidRates(Decimal(str(j["usd"]["bdt"])), Decimal(str(j["usd"]["cny"])), j["date"],
                                   f"{SOURCE} (live)", sample=False)
                    self._live = (time.time(), mid)
                    self.last_error = None
                    return mid
                except Exception as e:  # network down, CDN error, bad JSON
                    self.last_error = type(e).__name__
        if not self.history:
            return FIXTURE
        p = self.history[-1]
        return MidRates(Decimal(str(p.bdt_per_usd)), Decimal(str(p.cny_per_usd)), p.date,
                        f"{SOURCE} (saved history, offline)", sample=False)

    @property
    def status(self) -> str:
        if self.mode == "fixture":
            return "fixture"
        return "live" if self._live and self.mode == "live" else "saved"

    # ---- history and ranges ----------------------------------------------------
    def series(self) -> np.ndarray:
        return np.array([p.bdt_per_cny for p in self.history], dtype=float)

    def range(self, horizon_days: int, level: float = 0.8) -> RateRange | None:
        s = self.series()
        if horizon_days < 1 or len(s) < RANGE_WINDOW + horizon_days + 1:
            return None
        return rate_range(s, horizon_days, level, window=RANGE_WINDOW)

    def backtest(self, horizon_days: int, level: float = 0.8) -> dict | None:
        return _cached_backtest(tuple(self.series().round(6)), horizon_days, level)

    def change_pct(self, days: int) -> float | None:
        if len(self.history) <= days:
            return None
        a, b = self.history[-days - 1].bdt_per_cny, self.history[-1].bdt_per_cny
        return round((b / a - 1) * 100, 2)


@lru_cache(maxsize=32)
def _cached_backtest(series: tuple, h: int, level: float) -> dict | None:
    s = np.array(series)
    if len(s) < RANGE_WINDOW + 2 * h + 10:
        return None
    return coverage_backtest(s, h, level, window=RANGE_WINDOW, step=1)
