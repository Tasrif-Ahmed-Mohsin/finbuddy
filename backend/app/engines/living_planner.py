"""Living-money constrained optimiser (problem N-06 in docs/01_problem_research.md).

Question: "I need N CNY this month. What is the cheapest way to get it that never breaks a limit?"

Decision: how much to send by bank transfer (TT) to the student's own Chinese account, and how much
to withdraw at ATMs with the Bangladeshi card.

Constraints (all from the corridor rule pack):
  * card transactions this month  <= monthly transaction cap (30, field data)
  * card BDT charged this month   <= monthly BDT cap (5 lakh, field data)
  * ATM CNY this month            <= monthly ATM cap
  * ATM CNY per day               <= daily cap  ->  enough days left
  * living remittance this month  <= Bangladesh living-cost cap (USD)
  * money needed before a TT can arrive (bridge) must come from the ATM

The search space is small, so we evaluate every option on a grid (exact, transparent, testable)
instead of using a black-box solver. Every option records *why* it is infeasible.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_FLOOR, Decimal

from app.corridors.loader import Corridor
from app.engines.cost import CostBreakdown, atm_cost, tt_cost
from app.market import BankQuote, Market
from app.money import D, ceil_div, q2

ATM_NOTE = Decimal(100)

@dataclass
class LivingRequest:
    need_cny: Decimal
    bridge_cny: Decimal = Decimal(0)  # cash needed before a bank transfer could arrive
    has_cn_account: bool = True
    card_spent_bdt: Decimal = Decimal(0)  # already charged to the BD card this month
    card_tx_used: int = 0  # card transactions already used this month
    reserved_card_tx: int = 0  # card payments the student expects to make anyway
    living_remitted_usd: Decimal = Decimal(0)  # already remitted for living this month
    days_available: int = 30
    step_cny: Decimal = Decimal(100)


@dataclass
class LivingOption:
    tt_cny: Decimal
    quote: BankQuote | None
    withdrawals: list[Decimal]
    components: list[CostBreakdown]
    violations: list[str] = field(default_factory=list)
    cap_usage: dict = field(default_factory=dict)

    @property
    def feasible(self) -> bool:
        return not self.violations

    @property
    def total_bdt(self) -> Decimal:
        return q2(sum((c.total_bdt for c in self.components), Decimal(0)))

    @property
    def overhead_bdt(self) -> Decimal:
        return q2(sum((c.overhead_bdt for c in self.components), Decimal(0)))

    def to_dict(self) -> dict:
        return {
            "tt_cny": str(q2(self.tt_cny)),
            "bank": self.quote.bank if self.quote else None,
            "quote_id": self.quote.quote_id if self.quote else None,
            "atm_withdrawals_cny": [str(q2(w)) for w in self.withdrawals],
            "total_bdt": str(self.total_bdt),
            "overhead_bdt": str(self.overhead_bdt),
            "feasible": self.feasible,
            "violations": self.violations,
            "cap_usage": self.cap_usage,
            "components": [c.to_dict() for c in self.components],
        }


@dataclass
class LivingPlan:
    best: LivingOption | None
    baseline_all_atm: LivingOption
    options_evaluated: int
    steps: list[str]
    limits: dict

    @property
    def savings_vs_baseline_bdt(self) -> Decimal | None:
        if self.best is None:
            return None
        return q2(self.baseline_all_atm.total_bdt - self.best.total_bdt)

    def to_dict(self) -> dict:
        return {
            "feasible": self.best is not None,
            "best": self.best.to_dict() if self.best else None,
            "baseline_all_atm": self.baseline_all_atm.to_dict(),
            "savings_vs_all_atm_bdt": str(self.savings_vs_baseline_bdt) if self.best else None,
            "baseline_feasible": self.baseline_all_atm.feasible,
            "options_evaluated": self.options_evaluated,
            "steps": self.steps,
            "limits": self.limits,
        }


def split_withdrawals(amount_cny: Decimal, per_withdrawal_cap: Decimal) -> list[Decimal]:
    """Withdraw the maximum each time (fewest fixed fees); the last withdrawal takes the remainder."""
    if amount_cny <= 0:
        return []
    n = ceil_div(amount_cny, per_withdrawal_cap)
    out = [per_withdrawal_cap] * (n - 1)
    out.append(amount_cny - per_withdrawal_cap * (n - 1))
    return out


def best_quote_for(amount_cny: Decimal, market: Market) -> tuple[BankQuote, CostBreakdown]:
    """Cheapest bank for this amount (fixed fee vs rate trade-off depends on the amount)."""
    priced = [(q, tt_cost(amount_cny, q, market.mid.bdt_per_cny, route="tt_own_account")) for q in market.quotes]
    return min(priced, key=lambda item: item[1].total_bdt)


def plan_living(req: LivingRequest, corridor: Corridor, market: Market) -> LivingPlan:
    need = D(req.need_cny)
    if need <= 0:
        raise ValueError("need_cny must be positive")
    mid = market.mid.bdt_per_cny
    cny_per_usd = market.mid.cny_per_usd

    daily_cap_cny = corridor.v("bd_card_atm_daily_cap_usd") * cny_per_usd
    per_withdrawal_cap = min(corridor.v("cn_atm_max_per_withdrawal_cny"), daily_cap_cny)
    # Chinese ATMs dispense 100-yuan notes: withdrawals are whole multiples of 100.
    per_withdrawal_cap = (per_withdrawal_cap / ATM_NOTE).quantize(Decimal(1), rounding=ROUND_FLOOR) * ATM_NOTE
    monthly_atm_cap_cny = corridor.v("bd_card_atm_monthly_cap_usd") * cny_per_usd
    tx_left = corridor.i("bd_student_card_tx_cap_per_month") - req.card_tx_used - req.reserved_card_tx
    bdt_left = corridor.v("bd_student_card_cap_bdt_per_month") - D(req.card_spent_bdt)
    living_left_usd = corridor.v("bd_living_remit_cap_usd_per_month") - D(req.living_remitted_usd)

    limits = {
        "per_withdrawal_cap_cny": str(q2(per_withdrawal_cap)),
        "daily_atm_cap_cny": str(q2(daily_cap_cny)),
        "monthly_atm_cap_cny": str(q2(monthly_atm_cap_cny)),
        "card_tx_left": tx_left,
        "card_bdt_left": str(q2(bdt_left)),
        "living_remit_left_usd": str(q2(living_left_usd)),
    }

    def evaluate(tt: Decimal) -> LivingOption:
        atm = ATM_NOTE * ceil_div(need - tt, ATM_NOTE)  # round the ATM part up to whole notes
        withdrawals = split_withdrawals(atm, per_withdrawal_cap)
        components: list[CostBreakdown] = []
        quote = None
        violations: list[str] = []
        if tt > 0:
            if not req.has_cn_account:
                violations.append("no_cn_account: a transfer needs the student's own Chinese bank account")
            quote, tt_breakdown = best_quote_for(tt, market)
            components.append(tt_breakdown)
            if atm < min(D(req.bridge_cny), need):
                violations.append(
                    f"bridge: {q2(D(req.bridge_cny))} CNY is needed before a transfer can arrive, ATM part is only {q2(atm)}"
                )
            tt_usd = tt / cny_per_usd
            if tt_usd > living_left_usd:
                violations.append(
                    f"living_remit_cap: {q2(tt_usd)} USD exceeds the {q2(living_left_usd)} USD left this month"
                )
        atm_breakdown = atm_cost(withdrawals, corridor, mid) if withdrawals else None
        if atm_breakdown:
            components.append(atm_breakdown)
            n = len(withdrawals)
            if n > tx_left:
                violations.append(f"tx_cap: needs {n} card transactions, only {tx_left} left this month")
            if atm_breakdown.total_bdt > bdt_left:
                violations.append(
                    f"card_bdt_cap: card would be charged {q2(atm_breakdown.total_bdt)} BDT, only {q2(bdt_left)} left"
                )
            if atm > monthly_atm_cap_cny:
                violations.append(f"atm_monthly_cap: {q2(atm)} CNY exceeds {q2(monthly_atm_cap_cny)} CNY")
            days_needed = ceil_div(atm, daily_cap_cny)
            if days_needed > req.days_available:
                violations.append(f"atm_daily_cap: needs {days_needed} days of withdrawals, {req.days_available} available")
        card_tx_after = req.card_tx_used + req.reserved_card_tx + len(withdrawals)
        card_bdt_after = D(req.card_spent_bdt) + (atm_breakdown.total_bdt if atm_breakdown else 0)
        cap_usage = {
            "card_tx_after": card_tx_after,
            "card_tx_cap": corridor.i("bd_student_card_tx_cap_per_month"),
            "card_bdt_after": str(q2(card_bdt_after)),
            "card_bdt_cap": str(corridor.v("bd_student_card_cap_bdt_per_month")),
            "living_remit_usd_after": str(q2(D(req.living_remitted_usd) + tt / cny_per_usd)),
            "living_remit_usd_cap": str(corridor.v("bd_living_remit_cap_usd_per_month")),
        }
        return LivingOption(tt, quote, withdrawals, components, violations, cap_usage)

    step = D(req.step_cny)
    grid = {min(need, step * k) for k in range(0, ceil_div(need, step) + 1)}
    grid.add(need)
    options = [evaluate(tt) for tt in sorted(grid)]
    baseline = options[0]  # tt == 0 -> everything by ATM
    feasible = [o for o in options if o.feasible]
    best = min(feasible, key=lambda o: (o.total_bdt, len(o.withdrawals))) if feasible else None

    steps: list[str] = []
    if best:
        if best.tt_cny > 0 and best.quote:
            steps.append(
                f"Send {q2(best.tt_cny)} CNY by bank transfer to your own Chinese account via {best.quote.bank} "
                f"(arrives in about {corridor.i('bd_tt_transfer_days')} days)."
            )
        day, used_today = 1, Decimal(0)
        for w in best.withdrawals:
            if used_today + w > daily_cap_cny:
                day, used_today = day + 1, Decimal(0)
            used_today += w
            steps.append(f"Day {day}: withdraw {q2(w)} CNY at a big state-bank ATM.")
    return LivingPlan(best, baseline, len(options), steps, limits)
