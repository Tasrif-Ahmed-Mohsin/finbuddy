"""Market data: mid-market rates and bank quotes, always with date, source and a sample flag."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import yaml

from app.money import D

DATA_DIR = Path(__file__).parent / "data"


@dataclass(frozen=True)
class BankQuote:
    quote_id: str
    bank: str
    bdt_per_cny: Decimal  # what the bank charges per 1 CNY sent by TT
    fixed_fee_bdt: Decimal  # per transfer, VAT included
    as_of: str
    source: str
    sample: bool


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

    def quote(self, quote_id: str) -> BankQuote:
        for q in self.quotes:
            if q.quote_id == quote_id:
                return q
        raise KeyError(quote_id)


def load_market(name: str = "market_sample") -> Market:
    raw = yaml.safe_load((DATA_DIR / f"{name}.yaml").read_text(encoding="utf-8"))
    sample = bool(raw.get("sample", False))
    mid = MidRates(
        bdt_per_usd=D(raw["mid"]["bdt_per_usd"]),
        cny_per_usd=D(raw["mid"]["cny_per_usd"]),
        as_of=raw["as_of"],
        source=raw["source"],
        sample=sample,
    )
    quotes = [
        BankQuote(
            quote_id=q["quote_id"],
            bank=q["bank"],
            bdt_per_cny=D(q["bdt_per_cny"]),
            fixed_fee_bdt=D(q["fixed_fee_bdt"]),
            as_of=q.get("as_of", raw["as_of"]),
            source=q.get("source", raw["source"]),
            sample=bool(q.get("sample", sample)),
        )
        for q in raw["bank_quotes"]
    ]
    return Market(mid=mid, quotes=quotes)
