"""Tuition planner (problems P-05, P-06, N-04).

Universities in China count a fee as paid only when the money ARRIVES (e.g. Nanjing Medical
University). So we plan backwards:

    send-by date = deadline - transfer days (field data: ~7) - safety buffer

and rank Bangladeshi banks by all-in cost for the exact amount.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.corridors.loader import Corridor
from app.engines.cost import tt_cost
from app.engines.fx_range import RateRange
from app.market import Market
from app.money import D, q2


@dataclass
class TuitionRequest:
    amount_cny: Decimal
    deadline: date
    today: date
    current_quote_id: str | None = None  # the family's usual bank, if known


def plan_tuition(req: TuitionRequest, corridor: Corridor, market: Market, fx: RateRange | None = None) -> dict:
    amount = D(req.amount_cny)
    if amount <= 0:
        raise ValueError("amount_cny must be positive")
    transfer_days = corridor.i("bd_tt_transfer_days")
    buffer_days = corridor.i("tuition_buffer_days")
    send_by = req.deadline - timedelta(days=transfer_days + buffer_days)
    latest_possible = req.deadline - timedelta(days=transfer_days)
    days_left = (send_by - req.today).days

    if req.today > latest_possible:
        status = "at_risk_late"  # even sending today, it likely arrives after the deadline
    elif req.today > send_by:
        status = "urgent_no_buffer"
    elif days_left <= 2:
        status = "urgent"
    else:
        status = "on_track"

    mid = market.mid.bdt_per_cny
    options = sorted(
        [(q, tt_cost(amount, q, mid, route="tt_tuition")) for q in market.quotes],
        key=lambda item: item[1].total_bdt,
    )
    best_q, best = options[0]
    worst_q, worst = options[-1]
    current = next(((q, c) for q, c in options if q.quote_id == req.current_quote_id), None)

    result = {
        "amount_cny": str(q2(amount)),
        "deadline": req.deadline.isoformat(),
        "send_by": send_by.isoformat(),
        "days_left_to_send": days_left,
        "status": status,
        "transfer_days": transfer_days,
        "buffer_days": buffer_days,
        "options": [{"bank": q.bank, "quote_id": q.quote_id, "sample": q.sample, **c.to_dict()} for q, c in options],
        "best_quote_id": best_q.quote_id,
        "savings_best_vs_worst_bdt": str(q2(worst.total_bdt - best.total_bdt)),
        "savings_best_vs_current_bdt": str(q2(current[1].total_bdt - best.total_bdt)) if current else None,
        "wait_risk": None,
        "wait_risk_note": "FX history not loaded yet" if fx is None else None,
    }

    if fx is not None and fx.spot > 0:
        # If the family waits until the send-by date, the bank's rate moves roughly with the market.
        scale_lo, scale_hi = Decimal(str(fx.low / fx.spot)), Decimal(str(fx.high / fx.spot))
        pay_now = best.total_bdt
        principal = amount * best_q.bdt_per_cny
        result["wait_risk"] = {
            "pay_now_bdt": str(q2(pay_now)),
            "if_wait_low_bdt": str(q2(principal * scale_lo + best_q.fixed_fee_bdt)),
            "if_wait_high_bdt": str(q2(principal * scale_hi + best_q.fixed_fee_bdt)),
            "level": fx.level,
            "horizon_days": fx.horizon_days,
            "honest_note": (
                "Waiting has no expected gain under a random walk; it only adds risk. "
                "Pay now for certainty, or set a target-rate alert with a hard send-by date."
            ),
        }
    return result
