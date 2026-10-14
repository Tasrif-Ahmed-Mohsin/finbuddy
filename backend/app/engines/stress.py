"""Stress test and "what if": is "0 stuck days" robust, or one lucky simulation?

The year plan assumes the student spends exactly the planned amount every day, transfers take exactly 7 days and
the estimated holiday dates are right. Reality is messier, so we re-run the same year many times with:
  * spending: each month ±30% of the plan, plus a few one-off expenses (books, a doctor, a deposit);
  * transfers: each one 0–3 days later than planned (correspondent banks, compliance checks);
  * holidays: the lunar dates (Eid, Spring Festival, Puja…), which governments set only weeks ahead, shifted
    −2…+2 days.
The planner never sees the real values in advance: it uses the plan and reacts to the real balance each day,
exactly like the live autopilot. Seeded, so the numbers in our documents can be reproduced.

"What if" runs single named scenarios (taka weakens 10%, spending +30%, every transfer 3 days late, holidays 2
days later, and all bad things at once).
"""
from __future__ import annotations

import random
import statistics
from collections.abc import Callable
from datetime import date, timedelta
from decimal import Decimal

from app.corridors.loader import Corridor
from app.engines.year_plan import BankCalendar, Closure, Policy, Situation, simulate
from app.market import Market, MidRates
from app.money import q2

SPEND_RANGE = (0.7, 1.3)  # monthly spending vs plan
SHOCKS_PER_YEAR = (1, 4)  # one-off expenses
SHOCK_CNY = (300, 1500)
MAX_EXTRA_DELAY = 3  # days
HOLIDAY_SHIFT = 2  # ± days, lunar (assumption-labelled) holidays only


def shift_estimated_holidays(cal: BankCalendar, days: int) -> BankCalendar:
    moved = [Closure(c.country, c.name, c.start + timedelta(days=days), c.end + timedelta(days=days), c.confidence,
                     c.source, c.name_bn, c.name_zh) if c.confidence == "assumption" else c for c in cal.closures]
    return BankCalendar(cal.weekends, moved, cal.reviewed)


def _spender(policy: Policy, rng: random.Random, start: date, end: date, scale: float | None = None):
    """Daily spending: a monthly level around the plan, plus a few one-off expenses."""
    months: dict[str, Decimal] = {}
    days = (end - start).days + 1
    shocks = {start + timedelta(days=rng.randrange(days)): Decimal(rng.randrange(*SHOCK_CNY) // 100 * 100)
              for _ in range(rng.randint(*SHOCKS_PER_YEAR))} if scale is None else {}

    def spend(d: date) -> Decimal:
        key = d.strftime("%Y-%m")
        if key not in months:
            f = scale if scale is not None else rng.uniform(*SPEND_RANGE)
            months[key] = (policy.daily_spend_cny * Decimal(str(round(f, 3)))).quantize(Decimal("0.01"))
        return months[key] + shocks.get(d, Decimal(0))
    return spend


def _summary(xs: list[int]) -> dict:
    xs = sorted(xs)
    return {"zero_share_pct": round(100 * sum(1 for x in xs if x == 0) / len(xs), 1), "median": statistics.median(xs),
            "p90": xs[int(0.9 * (len(xs) - 1))], "worst": xs[-1], "mean": round(statistics.fmean(xs), 1)}


def stress_test(sit: Situation, policy: Policy, cal: BankCalendar, corridor: Corridor, market: Market,
                runs: int = 200, seed: int = 2026) -> dict:
    rng = random.Random(seed)
    today_stuck, sathi_stuck, sathi_atm = [], [], []
    worst = None
    for _ in range(runs):
        shift = rng.randint(-HOLIDAY_SHIFT, HOLIDAY_SHIFT)
        reality = shift_estimated_holidays(cal, shift) if shift else cal
        run_seed = rng.random()
        results = {}
        for strategy in ("today", "sathi"):
            r = random.Random(run_seed)  # both strategies face the SAME messy year
            res = simulate(strategy, sit, policy, cal, corridor, market, spend=_spender(policy, r, sit.start, sit.end),
                           delay=lambda r=r: r.randint(0, MAX_EXTRA_DELAY), reality=reality)
            results[strategy] = res
        today_stuck.append(len(results["today"].stuck))
        sathi_stuck.append(len(results["sathi"].stuck))
        sathi_atm.append(len(results["sathi"].atm))
        if worst is None or len(results["sathi"].stuck) > worst[0]:
            worst = (len(results["sathi"].stuck), shift, results["sathi"].periods[:3])
    return {
        "runs": runs, "seed": seed,
        "assumptions": {"monthly_spending_vs_plan": f"{int(SPEND_RANGE[0] * 100)}–{int(SPEND_RANGE[1] * 100)}%",
                        "one_off_expenses": f"{SHOCKS_PER_YEAR[0]}–{SHOCKS_PER_YEAR[1]} a year, ¥{SHOCK_CNY[0]}–{SHOCK_CNY[1]}",
                        "extra_transfer_delay_days": f"0–{MAX_EXTRA_DELAY}",
                        "lunar_holiday_shift_days": f"−{HOLIDAY_SHIFT}…+{HOLIDAY_SHIFT}"},
        "stuck_days": {"today": _summary(today_stuck), "sathi": _summary(sathi_stuck)},
        "sathi_atm_bridges_median": statistics.median(sathi_atm),
        "sathi_worst": {"stuck_days": worst[0], "holiday_shift": worst[1], "periods": worst[2]} if worst else None,
        "method": ("The same messy year is used for both strategies in each run. The planner sees only the plan and the "
                   "real balance, never the future, like the live autopilot."),
    }


def _family_pays(res) -> Decimal:
    return sum((c.total_bdt for c in res.costs), Decimal(0))


def what_if(sit: Situation, policy: Policy, cal: BankCalendar, corridor: Corridor, market: Market,
            rebuild: Callable[[MidRates], Market]) -> list[dict]:
    """Named scenarios. `rebuild(mid)` makes a market at another market rate (same banks, same fees).

    For the exchange-rate scenario both sides use the banks' markups over the market rate, because a published
    sheet is a fixed taka number for one day and would hide the move.
    """
    later = shift_estimated_holidays(cal, 2)
    mid = market.mid
    est_mid = MidRates(mid.bdt_per_usd, mid.cny_per_usd, mid.as_of, mid.source, True)
    weak_mid = MidRates(mid.bdt_per_usd * Decimal("1.10"), mid.cny_per_usd, mid.as_of, mid.source, True)
    est_market, weak_market = rebuild(est_mid), rebuild(weak_mid)
    more = lambda: _spender(policy, random.Random(1), sit.start, sit.end, 1.3)  # noqa: E731
    scenarios = [
        ("taka_weakens_10", dict(market=weak_market), est_market),
        ("spending_plus_30", dict(spend=more()), market),
        ("transfers_3_days_late", dict(delay=lambda: 3), market),
        ("holidays_2_days_later", dict(reality=later), market),
        ("all_at_once", dict(market=weak_market, spend=more(), delay=lambda: 3, reality=later), est_market),
    ]
    out = []
    for key, kw, base_market in scenarios:
        m = kw.pop("market", market)
        base = simulate("sathi", sit, policy, cal, corridor, base_market)
        today = simulate("today", sit, policy, cal, corridor, m, **kw)
        sathi = simulate("sathi", sit, policy, cal, corridor, m, **kw)
        pays, base_pays = _family_pays(sathi), _family_pays(base)
        out.append({"key": key, "stuck_days_sathi": len(sathi.stuck), "stuck_days_today": len(today.stuck),
                    "family_pays_bdt": str(q2(pays)), "change_bdt": str(q2(pays - base_pays)),
                    "overhead_pct": sathi.cost_summary()["overhead_pct"],
                    "overhead_pct_today": today.cost_summary()["overhead_pct"],
                    "transfers": len(sathi.transfers), "atm_bridges": len(sathi.atm)})
    return out
