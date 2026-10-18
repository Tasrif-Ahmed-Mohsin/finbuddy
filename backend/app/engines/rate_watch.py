"""Rate watch: a bank's published CNY price vs the market, day by day, and whether timing it pays.

Families ask "should we wait for a better rate?". We answer from the bank's own daily sheets instead of guessing:
  * the bank's markup over the market (median, middle half, range), and where today's sheet sits;
  * a backtest of the timing rule people use: "today looks expensive (markup in the top quarter), so wait up to
    three sheets and take the cheapest". We count how often that lowered the taka price and by how much.
For Eastern Bank (Mar–Oct 2026) waiting saved about 0.02% on average: the markup swings are mostly the market
moving under a smooth bank price, not the bank being expensive. Fixed fees (৳3,680 a transfer) matter far more,
so Bluefin does not time the market; it avoids extra transfers and stuck days.
"""
from __future__ import annotations

import statistics
from datetime import date

from app.bank_rates import PublishedRate
from app.fx import FxPoint

WAIT_SHEETS = 3


def _q(xs: list[float], k: int) -> float:
    return statistics.quantiles(xs, n=4, method="inclusive")[k]


def rate_watch(published: list[PublishedRate], fx: list[FxPoint], bank_id: str, today: date | None = None) -> dict | None:
    mid = {p.date: p.bdt_per_cny for p in fx}
    cutoff = (today or date.max).isoformat()
    rs = [r for r in published if r.bank_id == bank_id and r.date in mid and r.date <= cutoff]
    if len(rs) < 2 * WAIT_SHEETS + 2:
        return None
    tt = [float(r.cny_tt_selling) for r in rs]
    mk = [(t / mid[r.date] - 1) * 100 for t, r in zip(tt, rs)]
    p25, p75 = _q(mk, 0), _q(mk, 2)

    high = [i for i in range(len(rs) - WAIT_SHEETS) if mk[i] >= p75]
    savings = [(tt[i] - min(tt[i + 1:i + 1 + WAIT_SHEETS])) / tt[i] * 100 for i in high]
    latest = mk[-1]
    position = "high" if latest >= p75 else "low" if latest <= p25 else "usual"
    return {
        "bank_id": bank_id,
        "sheets": len(rs), "from": rs[0].date, "to": rs[-1].date,
        "series": [{"date": r.date, "market": round(mid[r.date], 4), "bank": float(r.cny_tt_selling), "markup_pct": round(m, 2)}
                   for r, m in zip(rs, mk)],
        "markup": {"median": round(statistics.median(mk), 2), "p25": round(p25, 2), "p75": round(p75, 2),
                   "low": round(min(mk), 2), "high": round(max(mk), 2)},
        "latest": {"date": rs[-1].date, "markup_pct": round(latest, 2), "position": position,
                   "share_of_days_cheaper_pct": round(100 * sum(1 for x in mk if x < latest) / len(mk), 1)},
        "timing_backtest": {
            "rule": f"after a sheet with a markup in the top quarter, wait up to {WAIT_SHEETS} sheets and take the cheapest",
            "cases": len(high),
            "cheaper_cases": sum(1 for s in savings if s > 0),
            "mean_saving_pct": round(statistics.fmean(savings), 3) if savings else None,
            "saving_per_lakh_bdt": round(statistics.fmean(savings) * 1000) if savings else None,  # % of ৳1,00,000
        },
    }
