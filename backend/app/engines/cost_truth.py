"""Cost truth: where a family's money really goes (exchange-rate markup vs fees).

Our first real payment (Interview #1) showed the bank's exchange rate was close to the market rate,
while the fixed charge was several times larger. This module recomputes that from the saved real
mid-market history, so the claim stays checkable and updates when more real payments are added. It also
compares the payment with what other banks PUBLISHED for the same weeks (their own daily rate sheets).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.money import D, q2


def field_payment_truth(fp: dict, history: list, published: list | None = None) -> dict:
    """`history`: FxPoint list (date, bdt_per_cny). `published`: PublishedRate list (banks' daily sheets).

    The window is used because the exact payment day is unknown.
    """
    start, end = (date.fromisoformat(x) for x in fp["window"])
    window = [D(str(round(p.bdt_per_cny, 6))) for p in history if start <= date.fromisoformat(p.date) <= end]
    if not window:
        raise ValueError(f"no exchange-rate history between {start} and {end}")
    mid = sum(window, Decimal(0)) / len(window)
    amount, rate, fee = D(fp["amount_cny"]), D(fp["bdt_per_cny"]), D(fp["fee_bdt"])
    markup_bdt = amount * (rate - mid)
    paid = amount * rate + fee
    out = {
        "id": fp["id"], "bank": fp["bank"], "purpose": fp["purpose"], "amount_cny": str(q2(amount)),
        "bdt_per_cny_paid": str(rate), "mid_avg": str(q2(mid)), "mid_low": str(q2(min(window))), "mid_high": str(q2(max(window))),
        "window": fp["window"], "paid_bdt": str(q2(paid)),
        "rate_markup_bdt": str(q2(markup_bdt)), "rate_markup_pct": str(q2((rate / mid - 1) * 100)),
        "fee_bdt": str(q2(fee)),
        "fee_vs_rate": str(q2(fee / markup_bdt)) if markup_bdt > 0 else None,
        "fee_note": fp.get("fee_note"),
        "source": fp["source"],
        "note": "The exact payment day is not known, so the rate is compared with the market average over the window.",
        "published_same_window": None,
    }
    sheets = [r for r in (published or []) if fp["window"][0] <= r.date <= fp["window"][1]]
    if sheets:
        sell = [r.cny_tt_selling for r in sheets]
        avg = sum(sell, Decimal(0)) / len(sell)
        out["published_same_window"] = {
            "bank_id": sheets[0].bank_id, "sheets": len(sheets), "avg": str(q2(avg)), "low": str(min(sell)), "high": str(max(sell)),
            "paid_vs_published_avg_pct": str(q2((rate / avg - 1) * 100)),
            "paid_below_every_sheet": rate < min(sell),
        }
    return out
