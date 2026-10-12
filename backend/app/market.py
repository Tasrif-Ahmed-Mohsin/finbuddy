"""Market data: the mid-market rate (real, from app/fx.py) and bank quotes (estimated or real).

Every quote says whether it is an estimate (`sample=True`) or a real quote someone entered.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

import yaml

from app.money import D

DATA_DIR = Path(__file__).parent / "data"
FOUR_PLACES = Decimal("0.0001")


@dataclass(frozen=True)
class BankQuote:
    quote_id: str
    bank: str
    bdt_per_cny: Decimal  # what the bank charges per 1 CNY sent by TT
    fixed_fee_bdt: Decimal  # per transfer, VAT included
    as_of: str
    source: str
    sample: bool  # True = estimate, False = real quote
    markup_pct: Decimal | None = None


@dataclass(frozen=True)
class MidRates:
    bdt_per_usd: Decimal
    cny_per_usd: Decimal
    as_of: str
    source: str
    sample: bool

    @property
    def bdt_per_cny(self) -> Decimal:
        """BDT/CNY cross rate via USD (there is no deep direct BDT/CNY market)."""
        return self.bdt_per_usd / self.cny_per_usd


@dataclass
class Market:
    mid: MidRates
    quotes: list[BankQuote]
    notes: list[str] = field(default_factory=list)

    def quote(self, quote_id: str) -> BankQuote:
        for q in self.quotes:
            if q.quote_id == quote_id:
                return q
        raise KeyError(quote_id)

    @property
    def quotes_estimated(self) -> bool:
        return any(q.sample for q in self.quotes)


def load_quote_config(path: Path = DATA_DIR / "bank_quotes.yaml") -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def build_market(mid: MidRates, cfg: dict, real_quotes: list[BankQuote] | None = None) -> Market:
    quotes = []
    for q in cfg["estimated_quotes"]:
        markup = D(q["markup_pct"])
        rate = (mid.bdt_per_cny * (1 + markup / 100)).quantize(FOUR_PLACES)
        quotes.append(BankQuote(q["quote_id"], q["bank"], rate, D(q["fixed_fee_bdt"]), mid.as_of, cfg["source"], True, markup))
    for rq in real_quotes or []:
        markup = ((rq.bdt_per_cny / mid.bdt_per_cny - 1) * 100).quantize(Decimal("0.01"))
        quotes.append(BankQuote(rq.quote_id, rq.bank, rq.bdt_per_cny, rq.fixed_fee_bdt, rq.as_of, rq.source, False, markup))
    return Market(mid, quotes)


def load_market() -> Market:
    """Market with the current mid-market rate (mode from SATHI_FX_MODE) and estimated quotes."""
    from app.fx import FxProvider  # local import: app.fx depends on this module

    return build_market(FxProvider().latest(), load_quote_config())
