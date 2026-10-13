"""Year plan: the "never stuck" money plan for the academic year (core algorithm; problems N-03, N-05, N-06).

Question: over the whole year, on which days would the student have no way to get money, and which
transfer schedule avoids every one of them at the lowest cost?

The student's money in China runs down every day. New money can arrive in two ways:
  * ATM withdrawals with the Bangladeshi card: instant, but only while the card endorsement is valid
    (renewing it needs the student in person at the bank in Bangladesh, field data) and within the card's
    daily and monthly limits. Expensive: a fixed fee per withdrawal plus card surcharges.
  * A bank transfer (TT) from the Student File to the student's own Chinese account: cheaper per yuan and
    independent of the card, but it can only be sent on a Bangladeshi bank day (Sun–Thu, not on holidays
    such as Eid), takes about 7 days, and lands only on a Chinese bank day (not during Spring Festival).
A "stuck day" is a day the student cannot pay for food, transport or rent.

We simulate the year day by day (exact and explainable, like the living optimiser) under two strategies:
  * today: what a careful family does now: ATM while the card works; once it stops, a transfer when about a
    week of money is left (they know a transfer takes a week, but not when the card stops or banks close).
  * sathi: the look-ahead rule in `topup_decision`, the same function the live autopilot uses: send on the
    last bank day that still lands while a cushion remains, counting weekends and holidays in BOTH countries.
Both strategies use the cheapest bank for each transfer and today's exchange rate (no rate forecast).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_FLOOR, Decimal
from pathlib import Path

import yaml

from app.corridors.loader import Corridor
from app.engines.cost import CostBreakdown, atm_cost
from app.engines.living_planner import ATM_NOTE, best_quote_for
from app.market import Market
from app.money import D, ceil_div, q2

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ONE_DAY = timedelta(days=1)


# ---- bank calendar ------------------------------------------------------------------
@dataclass(frozen=True)
class Closure:
    country: str  # BD | CN
    name: str
    start: date
    end: date
    confidence: str
    source: str
    name_bn: str = ""
    name_zh: str = ""

    def to_dict(self) -> dict:
        return {"country": self.country, "name": self.name, "name_bn": self.name_bn or self.name, "name_zh": self.name_zh or self.name,
                "from": self.start.isoformat(), "to": self.end.isoformat(), "confidence": self.confidence, "source": self.source}


class BankCalendar:
    """Bank days in Bangladesh (sending) and China (crediting)."""

    def __init__(self, weekends: dict[str, set[int]], closures: list[Closure], reviewed: str = ""):
        self.weekends, self.closures, self.reviewed = weekends, closures, reviewed

    def closed_because(self, country: str, d: date) -> str | None:
        for c in self.closures:
            if c.country == country and c.start <= d <= c.end:
                return c.name
        return "weekend" if d.weekday() in self.weekends[country] else None

    def is_open(self, country: str, d: date) -> bool:
        return self.closed_because(country, d) is None

    def next_open(self, country: str, d: date) -> date:
        for _ in range(60):
            if self.is_open(country, d):
                return d
            d += ONE_DAY
        raise ValueError(f"no {country} bank day within 60 days of {d}")

    def arrival(self, send: date, transfer_days: int) -> date:
        return self.next_open("CN", send + timedelta(days=transfer_days))

    def holidays_between(self, country: str, a: date, b: date) -> list[str]:
        """Names of holidays (not weekends) that close banks on some day in [a, b]."""
        return [c.name for c in self.closures if c.country == country and c.start <= b and c.end >= a]

    def names(self) -> dict[str, dict[str, str]]:
        return {c.name: {"en": c.name, "bn": c.name_bn or c.name, "zh": c.name_zh or c.name} for c in self.closures}

    def closures_in(self, a: date, b: date) -> list[Closure]:
        return sorted((c for c in self.closures if c.start <= b and c.end >= a), key=lambda c: c.start)


def load_calendar(path: Path = DATA_DIR / "bank_holidays.yaml") -> BankCalendar:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    closures = [Closure(c["country"], c["name"], c["from"], c["to"], c["confidence"], c["source"], c.get("name_bn", ""),
                        c.get("name_zh", "")) for c in raw["closures"]]
    return BankCalendar({k: set(v) for k, v in raw["weekends"].items()}, closures, str(raw.get("reviewed", "")))


# ---- the look-ahead rule (shared with the live autopilot) ------------------------------------
@dataclass(frozen=True)
class Policy:
    daily_spend_cny: Decimal
    transfer_days: int
    safety_days: int  # money left when a transfer lands: a cushion for delays
    target_days: int  # each transfer covers about this many days (one fixed fee per cycle)
    min_transfer_cny: Decimal

    @classmethod
    def from_corridor(cls, corridor: Corridor, monthly_living_cny: Decimal) -> "Policy":
        return cls(q2(D(monthly_living_cny) / 30), corridor.i("bd_tt_transfer_days"), corridor.i("living_safety_days"),
                   corridor.i("living_target_days"), corridor.v("min_living_transfer_cny"))


def project(balance: Decimal, in_transit: list[tuple[date, Decimal]], today: date, day: date, daily: Decimal) -> Decimal:
    """Money left at the END of `day` if nothing new is sent (today's spending included)."""
    arrived = sum((amt for d, amt in in_transit if today < d <= day), Decimal(0))
    return balance + arrived - daily * ((day - today).days + 1)


def runs_out_on(balance: Decimal, in_transit: list[tuple[date, Decimal]], today: date, daily: Decimal,
                horizon_days: int = 120) -> date | None:
    for k in range(horizon_days):
        d = today + timedelta(days=k)
        if project(balance, in_transit, today, d, daily) < 0:
            return d
    return None


@dataclass
class TopupDecision:
    send_on: date
    lands: date
    amount_cny: Decimal
    bridge_cny: Decimal  # cash still needed before this transfer lands (0 = none)
    next_chance: date  # the next Bangladeshi bank day after today
    wait_would_land: date  # when a transfer sent at that next chance would land
    low_on: date  # first day the money would drop below the cushion if we waited
    safety_days: int
    closures: list[str]  # holidays that make waiting unsafe
    reason: str

    def to_dict(self) -> dict:
        return {"send_on": self.send_on.isoformat(), "lands": self.lands.isoformat(), "amount_cny": str(self.amount_cny),
                "bridge_cny": str(self.bridge_cny), "next_chance": self.next_chance.isoformat(),
                "wait_would_land": self.wait_would_land.isoformat(), "low_on": self.low_on.isoformat(),
                "safety_days": self.safety_days, "closures": self.closures, "reason": self.reason}


def topup_decision(today: date, balance: Decimal, in_transit: list[tuple[date, Decimal]], policy: Policy,
                   cal: BankCalendar) -> TopupDecision | None:
    """Send a living-money transfer today? If yes, how much?

    Waiting is safe if a transfer sent at the NEXT Bangladeshi bank day would still land while the student
    has at least `safety_days` of money (and never runs out before). Otherwise send today, sized so that after
    it lands the student has `target_days + safety_days` of money (one transfer per ~target_days).
    """
    if not cal.is_open("BD", today):
        return None  # branches are closed: nothing can be sent today
    daily = policy.daily_spend_cny
    nxt = cal.next_open("BD", today + ONE_DAY)
    wait_lands = cal.arrival(nxt, policy.transfer_days)
    window = [today + timedelta(days=k) for k in range((wait_lands - today).days)]
    low = daily * policy.safety_days
    if all(project(balance, in_transit, today, d, daily) >= 0 for d in window) and \
            project(balance, in_transit, today, wait_lands - ONE_DAY, daily) >= low:
        return None
    lands = cal.arrival(today, policy.transfer_days)
    before_landing = [today + timedelta(days=k) for k in range((lands - today).days)]
    at_landing = project(balance, in_transit, today, lands - ONE_DAY, daily)
    need = daily * (policy.target_days + policy.safety_days) - max(at_landing, Decimal(0))
    amount = max(policy.min_transfer_cny, ATM_NOTE * ceil_div(need, ATM_NOTE))
    worst = min((project(balance, in_transit, today, d, daily) for d in before_landing), default=Decimal(0))
    bridge = ATM_NOTE * ceil_div(-worst, ATM_NOTE) if worst < 0 else Decimal(0)
    closures = list(dict.fromkeys(cal.holidays_between("BD", today + ONE_DAY, nxt - ONE_DAY)
                                  + cal.holidays_between("CN", nxt + timedelta(days=policy.transfer_days), wait_lands)))
    low_on = next((d for d in window if project(balance, in_transit, today, d, daily) < low), wait_lands - ONE_DAY)
    if closures:
        reason = (f"Banks are closed for {', '.join(closures)}: a transfer sent at the next chance ({nxt.isoformat()}) "
                  f"would land only on {wait_lands.isoformat()}, after the money runs low.")
    else:
        reason = (f"Money drops below {policy.safety_days} days on {low_on.isoformat()}; "
                  f"a transfer sent today lands on {lands.isoformat()}.")
    return TopupDecision(today, lands, amount, bridge, nxt, wait_lands, low_on, policy.safety_days, closures, reason)


# ---- year simulation ---------------------------------------------------------------------
@dataclass
class Situation:
    start: date
    end: date
    balance_cny: Decimal
    in_transit: list[tuple[date, Decimal]]
    card_valid_until: date | None  # card endorsement: the card works abroad until this day
    card_active: bool
    student_file_valid_until: date
    card_tx_used: int = 0  # this month, already
    card_bdt_used: Decimal = Decimal(0)
    tuition: tuple[date, date, Decimal] | None = None  # (send_by, deadline, amount) — shown on the timeline


@dataclass
class StrategyResult:
    name: str
    stuck: list[date] = field(default_factory=list)
    transfers: list[dict] = field(default_factory=list)
    atm: list[dict] = field(default_factory=list)
    costs: list[CostBreakdown] = field(default_factory=list)
    periods: list[dict] = field(default_factory=list)

    def cost_summary(self) -> dict:
        rate = sum((c.by_kind("rate") for c in self.costs), Decimal(0))
        fees = sum((c.by_kind("fee") for c in self.costs), Decimal(0))
        mid_value = sum((c.mid_value_bdt for c in self.costs), Decimal(0))
        return {"delivered_cny": str(q2(sum((c.delivered_cny for c in self.costs), Decimal(0)))),
                "total_bdt": str(q2(sum((c.total_bdt for c in self.costs), Decimal(0)))),
                "rate_bdt": str(q2(rate)), "fees_bdt": str(q2(fees)), "overhead_bdt": str(q2(rate + fees)),
                "overhead_pct": str(q2((rate + fees) / mid_value * 100)) if mid_value else "0",
                "transfers": len(self.transfers), "atm_withdrawals": len(self.atm)}

    def to_dict(self) -> dict:
        return {"name": self.name, "stuck_days": len(self.stuck), "stuck_periods": self.periods,
                "transfers": self.transfers, "atm": self.atm, "cost": self.cost_summary()}


def _per_withdrawal_cap(corridor: Corridor, cny_per_usd: Decimal) -> tuple[Decimal, Decimal]:
    daily_cap = corridor.v("bd_card_atm_daily_cap_usd") * cny_per_usd
    per = min(corridor.v("cn_atm_max_per_withdrawal_cny"), daily_cap)
    return (per / ATM_NOTE).quantize(Decimal(1), rounding=ROUND_FLOOR) * ATM_NOTE, daily_cap


def simulate(strategy: str, sit: Situation, policy: Policy, cal: BankCalendar, corridor: Corridor,
             market: Market) -> StrategyResult:
    if strategy not in ("today", "sathi"):
        raise ValueError(f"unknown strategy '{strategy}'")
    mid, cny_per_usd = market.mid.bdt_per_cny, market.mid.cny_per_usd
    daily = policy.daily_spend_cny
    per_wd, _ = _per_withdrawal_cap(corridor, cny_per_usd)
    atm_month_cap = corridor.v("bd_card_atm_monthly_cap_usd") * cny_per_usd
    tx_cap, bdt_cap = corridor.i("bd_student_card_tx_cap_per_month"), corridor.v("bd_student_card_cap_bdt_per_month")
    living_cap = corridor.v("bd_living_remit_cap_usd_per_month") * cny_per_usd
    reorder, low_cash = corridor.i("baseline_reorder_days"), corridor.i("atm_low_cash_days")

    res = StrategyResult(strategy)
    bal, transit = D(sit.balance_cny), sorted(sit.in_transit)
    month: dict[str, dict] = {sit.start.strftime("%Y-%m"): {"tx": sit.card_tx_used, "bdt": D(sit.card_bdt_used),
                                                           "atm": Decimal(0), "living": Decimal(0)}}
    asked_on: date | None = None  # today strategy: the day the family noticed money was needed

    def usage(d: date) -> dict:
        return month.setdefault(d.strftime("%Y-%m"), {"tx": 0, "bdt": Decimal(0), "atm": Decimal(0), "living": Decimal(0)})

    def send(d: date, amount: Decimal, why: str, closures: list[str]) -> None:
        u = usage(d)
        amount = min(amount, ATM_NOTE * ((living_cap - u["living"]) // ATM_NOTE))  # Bangladesh's monthly living cap
        if amount < policy.min_transfer_cny:
            return
        quote, cost = best_quote_for(amount, market)
        lands = cal.arrival(d, policy.transfer_days)
        transit.append((lands, amount))
        transit.sort()
        u["living"] += amount
        res.costs.append(cost)
        res.transfers.append({"send_on": d.isoformat(), "lands": lands.isoformat(), "amount_cny": str(q2(amount)),
                              "total_bdt": str(q2(cost.total_bdt)), "bank": quote.bank, "why": why, "closures": closures})

    def withdraw(d: date, amount: Decimal) -> Decimal:
        u = usage(d)
        amount = min(amount, per_wd, ATM_NOTE * ((atm_month_cap - u["atm"]) // ATM_NOTE))
        if amount <= 0 or u["tx"] + 1 > tx_cap:
            return Decimal(0)
        cost = atm_cost([amount], corridor, mid)
        if u["bdt"] + cost.total_bdt > bdt_cap:
            return Decimal(0)
        u["tx"], u["bdt"], u["atm"] = u["tx"] + 1, u["bdt"] + cost.total_bdt, u["atm"] + amount
        res.costs.append(cost)
        res.atm.append({"date": d.isoformat(), "amount_cny": str(q2(amount)), "total_bdt": str(q2(cost.total_bdt))})
        return amount

    d = sit.start
    while d <= sit.end:
        bal += sum((amt for ad, amt in transit if ad == d), Decimal(0))
        transit = [t for t in transit if t[0] > d]
        card_ok = sit.card_active and sit.card_valid_until is not None and d <= sit.card_valid_until
        file_ok = d <= sit.student_file_valid_until

        if strategy == "sathi":
            dec = topup_decision(d, bal, transit, policy, cal) if file_ok else None
            if dec:
                send(d, dec.amount_cny, dec.reason, dec.closures)
            if card_ok:  # bridge with cash only until the next transfer can land
                until = transit[0][0] if transit else cal.arrival(cal.next_open("BD", d), policy.transfer_days)
                worst = min((project(bal, transit, d, d + timedelta(days=k), daily) for k in range((until - d).days)),
                            default=Decimal(0))
                if worst < 0:
                    bal += withdraw(d, ATM_NOTE * ceil_div(-worst, ATM_NOTE))
        else:
            if card_ok:
                if bal < daily * low_cash:
                    bal += withdraw(d, per_wd)
            elif file_ok and not transit and bal < daily * reorder:
                asked_on = asked_on or d
                if cal.is_open("BD", d):
                    lands = cal.arrival(d, policy.transfer_days)
                    closures = list(dict.fromkeys(cal.holidays_between("BD", asked_on, d)
                                                  + cal.holidays_between("CN", d + timedelta(days=policy.transfer_days), lands)))
                    send(d, daily * policy.target_days, "The student asked for money", closures)
                    asked_on = None

        if bal >= daily:
            bal -= daily
        else:
            res.stuck.append(d)
            bal = Decimal(0)
        d += ONE_DAY

    res.periods = _stuck_periods(res, sit, cal)
    return res


def _stuck_periods(res: StrategyResult, sit: Situation, cal: BankCalendar) -> list[dict]:
    periods: list[list[date]] = []
    for d in res.stuck:
        if periods and d - periods[-1][-1] == ONE_DAY:
            periods[-1].append(d)
        else:
            periods.append([d])
    out, out_after_card = [], False
    for p in periods:
        first, last = p[0], p[-1]
        reasons = []
        if sit.card_valid_until and first > sit.card_valid_until and not out_after_card:
            out_after_card = True
            reasons.append(f"The card stopped working abroad when the endorsement ended on {sit.card_valid_until.isoformat()} "
                           "(renewing it needs the student at the bank in Bangladesh).")
        ending = next((t for t in res.transfers if t["lands"] == (last + ONE_DAY).isoformat()), None)
        if ending and ending["closures"]:
            reasons.append(f"Banks were closed for {', '.join(ending['closures'])}, which delayed the transfer.")
        elif ending and cal.closed_because("BD", first):
            reasons.append("Bangladeshi banks do not send transfers on Fridays and Saturdays.")
        if not reasons:
            reasons.append("The money ran out before the transfer arrived: a week's notice was not enough.")
        out.append({"from": first.isoformat(), "to": last.isoformat(), "days": len(p), "reasons": reasons})
    return out


def plan_year(sit: Situation, policy: Policy, cal: BankCalendar, corridor: Corridor, market: Market) -> dict:
    today = simulate("today", sit, policy, cal, corridor, market)
    sathi = simulate("sathi", sit, policy, cal, corridor, market)
    t_cost, s_cost = today.cost_summary(), sathi.cost_summary()
    events: list[dict] = []
    for t in sathi.transfers:
        events.append({"date": t["send_on"], "type": "transfer_send", "amount_cny": t["amount_cny"], "total_bdt": t["total_bdt"],
                       "bank": t["bank"], "lands": t["lands"], "why": t["why"]})
    for a in sathi.atm:
        events.append({"date": a["date"], "type": "atm_bridge", "amount_cny": a["amount_cny"], "total_bdt": a["total_bdt"]})
    if sit.card_valid_until and sit.start <= sit.card_valid_until <= sit.end:
        events.append({"date": sit.card_valid_until.isoformat(), "type": "card_stops",
                       "why": "Card endorsement ends; renewal needs the student in person in Bangladesh."})
    if sit.tuition:
        send_by, deadline, amount = sit.tuition
        events.append({"date": send_by.isoformat(), "type": "tuition_send_by", "amount_cny": str(q2(amount)),
                       "deadline": deadline.isoformat()})
    for c in cal.closures_in(sit.start, sit.end):
        events.append({"date": c.start.isoformat(), "type": "bank_closure", **c.to_dict()})
    for p in today.periods:
        events.append({"date": p["from"], "type": "stuck_without_sathi", "days": p["days"], "to": p["to"], "reasons": p["reasons"]})
    events.sort(key=lambda e: (e["date"], e["type"]))

    rate_t, fees_t = D(t_cost["rate_bdt"]), D(t_cost["fees_bdt"])
    # Compare costs for the SAME money: today's overhead rate applied to what the Sathi plan delivers.
    sathi_mid = sum((c.mid_value_bdt for c in sathi.costs), Decimal(0))
    saved = D(t_cost["overhead_pct"]) / 100 * sathi_mid - D(s_cost["overhead_bdt"])
    return {
        "horizon": {"from": sit.start.isoformat(), "to": sit.end.isoformat(), "days": (sit.end - sit.start).days + 1},
        "inputs": {"daily_spend_cny": str(policy.daily_spend_cny), "start_balance_cny": str(q2(sit.balance_cny)),
                   "card_valid_until": sit.card_valid_until.isoformat() if sit.card_valid_until else None,
                   "student_file_valid_until": sit.student_file_valid_until.isoformat(),
                   "transfer_days": policy.transfer_days, "safety_days": policy.safety_days, "target_days": policy.target_days},
        "headline": {
            "stuck_days_today": len(today.stuck), "stuck_days_sathi": len(sathi.stuck),
            "overhead_today_bdt": t_cost["overhead_bdt"], "overhead_sathi_bdt": s_cost["overhead_bdt"],
            "overhead_today_pct": t_cost["overhead_pct"], "overhead_sathi_pct": s_cost["overhead_pct"],
            "saved_bdt": str(q2(saved)),
            "fees_share_today_pct": str(q2(fees_t / (fees_t + rate_t) * 100)) if fees_t + rate_t > 0 else None,
        },
        "strategies": {"today": today.to_dict(), "sathi": sathi.to_dict()},
        "events": events,
        "method": ("Day-by-day simulation of the student's money in China. 'Today' = ATM while the card works, then a "
                   "transfer when about a week of money is left. 'Sathi' = the autopilot's look-ahead rule, which counts "
                   "weekends and holidays in both countries. Same cheapest bank and today's exchange rate in both."),
    }
