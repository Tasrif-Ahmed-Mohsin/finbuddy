"""All-in cost engine.

For every way of getting CNY into the student's hands, compute what it really costs in BDT
and how much of that is overhead versus the mid-market rate:

    overhead = total BDT paid - (CNY delivered x mid-market BDT/CNY)

Every line item is returned so the app can show *where* the money goes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.corridors.loader import Corridor
from app.market import BankQuote
from app.money import D, q2

HUNDRED = Decimal(100)


@dataclass
class CostLine:
    label: str
    bdt: Decimal


@dataclass
class CostBreakdown:
    route: str
    delivered_cny: Decimal
    total_bdt: Decimal
    mid_value_bdt: Decimal
    lines: list[CostLine]
    card_transactions: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def overhead_bdt(self) -> Decimal:
        return q2(self.total_bdt - self.mid_value_bdt)

    @property
    def overhead_pct(self) -> Decimal:
        if self.mid_value_bdt == 0:
            return Decimal(0)
        return q2(self.overhead_bdt / self.mid_value_bdt * HUNDRED)

    def to_dict(self) -> dict:
        return {
            "route": self.route,
            "delivered_cny": str(q2(self.delivered_cny)),
            "total_bdt": str(q2(self.total_bdt)),
            "mid_value_bdt": str(q2(self.mid_value_bdt)),
            "overhead_bdt": str(self.overhead_bdt),
            "overhead_pct": str(self.overhead_pct),
            "card_transactions": self.card_transactions,
            "lines": [{"label": l.label, "bdt": str(q2(l.bdt))} for l in self.lines],
            "notes": self.notes,
        }


def tt_cost(
    delivered_cny: Decimal,
    quote: BankQuote,
    mid_bdt_per_cny: Decimal,
    intermediary_fee_cny: Decimal = Decimal(0),
    route: str = "tt",
) -> CostBreakdown:
    """Bank telegraphic transfer (TT) in CNY from Bangladesh.

    If an intermediary bank deducts a fee on the way, the sender must send more so that the
    payee still receives `delivered_cny`.
    """
    delivered_cny = D(delivered_cny)
    sent_cny = delivered_cny + intermediary_fee_cny
    mid_value = delivered_cny * mid_bdt_per_cny
    fx_markup = sent_cny * (quote.bdt_per_cny - mid_bdt_per_cny)
    intermediary_bdt = intermediary_fee_cny * mid_bdt_per_cny
    lines = [
        CostLine("Amount at mid-market rate", mid_value),
        CostLine(f"Exchange-rate markup ({quote.bank})", fx_markup),
    ]
    if intermediary_fee_cny:
        lines.append(CostLine("Intermediary bank deduction (covered)", intermediary_bdt))
    lines.append(CostLine("Bank transfer fee", quote.fixed_fee_bdt))
    total = sent_cny * quote.bdt_per_cny + quote.fixed_fee_bdt
    notes = ["Rates are SAMPLE data, not a real quote"] if quote.sample else []
    return CostBreakdown(route, delivered_cny, total, mid_value, lines, 0, notes)


def card_bdt_per_cny(corridor: Corridor, mid_bdt_per_cny: Decimal) -> Decimal:
    """Rate a Bangladeshi card is charged at for CNY: mid x (1 + card markup) x (1 + non-USD factor)."""
    markup = corridor.v("bd_card_fx_markup_pct") / HUNDRED
    factor = corridor.v("bd_card_non_usd_factor_pct") / HUNDRED
    return mid_bdt_per_cny * (1 + markup) * (1 + factor)


def atm_cost(
    withdrawals_cny: list[Decimal],
    corridor: Corridor,
    mid_bdt_per_cny: Decimal,
) -> CostBreakdown:
    """ATM withdrawals in China with a Bangladeshi card.

    Per withdrawal: (amount + Chinese ATM fee) is charged at the card rate, plus the
    Bangladeshi bank's fixed fee (~345 BDT, field data).
    """
    markup = corridor.v("bd_card_fx_markup_pct") / HUNDRED
    factor = corridor.v("bd_card_non_usd_factor_pct") / HUNDRED
    cn_fee = corridor.v("cn_atm_foreign_card_fee_cny")
    bd_fee = corridor.v("bd_card_atm_fixed_fee_bdt")
    n = len(withdrawals_cny)
    delivered = sum((D(w) for w in withdrawals_cny), Decimal(0))
    charged_cny = delivered + cn_fee * n

    mid_value = delivered * mid_bdt_per_cny
    card_markup = charged_cny * mid_bdt_per_cny * markup
    non_usd = charged_cny * mid_bdt_per_cny * (1 + markup) * factor
    cn_fee_bdt = cn_fee * n * mid_bdt_per_cny
    bd_fee_total = bd_fee * n
    lines = [
        CostLine("Amount at mid-market rate", mid_value),
        CostLine("Card exchange-rate markup (estimate)", card_markup),
        CostLine("Non-USD currency factor", non_usd),
        CostLine(f"Chinese ATM fees ({n} x {cn_fee} CNY)", cn_fee_bdt),
        CostLine(f"Bangladeshi bank ATM fees ({n} x {bd_fee} BDT)", bd_fee_total),
    ]
    total = mid_value + card_markup + non_usd + cn_fee_bdt + bd_fee_total
    return CostBreakdown("atm", delivered, total, mid_value, lines, card_transactions=n)


def alipay_card_cost(
    payments_cny: list[Decimal],
    corridor: Corridor,
    mid_bdt_per_cny: Decimal,
) -> CostBreakdown:
    """Paying with a Bangladeshi card linked to Alipay: 3% service fee on payments above RMB 200."""
    threshold = corridor.v("cn_alipay_fee_threshold_cny")
    fee_pct = corridor.v("cn_alipay_foreign_card_fee_pct") / HUNDRED
    rate = card_bdt_per_cny(corridor, mid_bdt_per_cny)
    delivered = sum((D(p) for p in payments_cny), Decimal(0))
    service_fee_cny = sum((D(p) * fee_pct for p in payments_cny if D(p) > threshold), Decimal(0))
    mid_value = delivered * mid_bdt_per_cny
    card_fx = delivered * (rate - mid_bdt_per_cny)
    service_bdt = service_fee_cny * rate
    lines = [
        CostLine("Amount at mid-market rate", mid_value),
        CostLine("Card exchange-rate markup + non-USD factor", card_fx),
        CostLine(f"Alipay foreign-card fee ({corridor.v('cn_alipay_foreign_card_fee_pct')}% above {threshold} CNY)", service_bdt),
    ]
    total = mid_value + card_fx + service_bdt
    return CostBreakdown("alipay_card", delivered, total, mid_value, lines, card_transactions=len(payments_cny))
