"""Market data: the mid-market rate (real, from app/fx.py) and bank prices, each with its basis.

A bank price has two halves, and the app always says where each came from:
  * the RATE: a bank's own published daily sheet (`published`), a real payment someone made (`real_payment`),
    a quote the user entered (`user_quote`), or a markup estimate (`estimate`);
  * the FEES: the bank's published schedule of charges (commission by amount + correspondent + SWIFT + VAT),
    or, where a bank does not publish them, a labelled assumption.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

import yaml

from app.money import D

DATA_DIR = Path(__file__).parent / "data"
FOUR_PLACES = Decimal("0.0001")
BASES = ("published", "real_payment", "user_quote", "estimate")


@dataclass(frozen=True)
class FeeSchedule:
    """Per-transfer fees from a bank's schedule of charges (BDT, before VAT)."""
    bank_id: str
    tiers: tuple[tuple[Decimal | None, Decimal], ...]  # (up to BDT value sent, commission); None = no limit
    correspondent: Decimal
    swift: Decimal
    vat_pct: Decimal
    confidence: str  # official | secondary | assumption (the weakest of its parts)
    source: str

    def lines(self, principal_bdt: Decimal) -> list[tuple[str, Decimal]]:
        commission = next(fee for up_to, fee in self.tiers if up_to is None or principal_bdt <= up_to)
        parts = [(label, amt) for label, amt in (("Bank commission", commission), ("Correspondent bank charge", self.correspondent),
                                                 ("SWIFT charge", self.swift)) if amt > 0]
        vat = sum((a for _, a in parts), Decimal(0)) * self.vat_pct / 100
        return parts + [(f"VAT {self.vat_pct}% on fees", vat)]

    def total(self, principal_bdt: Decimal) -> Decimal:
        return sum((a for _, a in self.lines(principal_bdt)), Decimal(0))

    def to_dict(self) -> dict:
        return {"bank_id": self.bank_id, "tiers": [[str(u) if u is not None else None, str(f)] for u, f in self.tiers],
                "correspondent_bdt": str(self.correspondent), "swift_bdt": str(self.swift), "vat_pct": str(self.vat_pct),
                "confidence": self.confidence, "source": self.source}


@dataclass(frozen=True)
class BankQuote:
    quote_id: str
    bank: str
    bdt_per_cny: Decimal  # what the bank charges per 1 CNY sent by TT
    fixed_fee_bdt: Decimal  # per transfer, VAT included (used when there is no fee schedule)
    as_of: str
    source: str
    sample: bool  # True = an estimate
    markup_pct: Decimal | None = None
    basis: str = "estimate"  # published | real_payment | user_quote | estimate
    fees: FeeSchedule | None = None

    def fee_lines(self, principal_bdt: Decimal) -> list[tuple[str, Decimal]]:
        return self.fees.lines(principal_bdt) if self.fees else [("Bank transfer fee", self.fixed_fee_bdt)]

    def fee_total(self, principal_bdt: Decimal) -> Decimal:
        return sum((a for _, a in self.fee_lines(principal_bdt)), Decimal(0))

    @property
    def fees_assumed(self) -> bool:
        return self.fees is not None and self.fees.confidence == "assumption"


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
        """True while any price relies on an estimated rate or assumed fees."""
        return any(q.sample or q.fees_assumed for q in self.quotes)

    @property
    def quality(self) -> str:
        """published = every rate and fee is real or published · mixed · estimated = only estimates."""
        if not self.quotes or all(q.sample for q in self.quotes):
            return "estimated"
        return "mixed" if self.quotes_estimated else "published"


def load_quote_config(path: Path = DATA_DIR / "bank_quotes.yaml", fees_path: Path = DATA_DIR / "bank_fees.yaml") -> dict:
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    cfg["fees"] = yaml.safe_load(fees_path.read_text(encoding="utf-8")) if fees_path.exists() else {"banks": {}}
    return cfg


def fee_schedule(bank_id: str, fees_cfg: dict) -> FeeSchedule | None:
    """The bank's published per-transfer fees, or a labelled assumption copied from a published peer."""
    bank = fees_cfg.get("banks", {}).get(bank_id)
    t = bank and bank.get("transfer")
    if not t:
        return None
    if "like" in t:
        peer = fee_schedule(t["like"], fees_cfg)
        if peer is None:
            return None
        return FeeSchedule(bank_id, peer.tiers, peer.correspondent, peer.swift, peer.vat_pct, t.get("confidence", "assumption"),
                           t.get("source", f"assumed like {t['like']}"))
    if t.get("correspondent") is None:
        return None  # part of the fee is not published: do not invent it
    tiers = tuple((D(str(u)) if u is not None else None, D(str(f))) for u, f in t["commission_tiers"])
    order = ["official", "secondary", "assumption"]
    weakest = max((t.get(k, "official") for k in ("commission_confidence", "correspondent_confidence", "swift_confidence")),
                  key=order.index)
    return FeeSchedule(bank_id, tiers, D(str(t["correspondent"])), D(str(t.get("swift") or 0)), D(str(fees_cfg.get("vat_pct", 15))),
                       weakest, t.get("commission_source", ""))


def student_file_fees(fees_cfg: dict) -> list[dict]:
    """Opening and yearly renewal fees per bank, including VAT, with sources (for a comparison table)."""
    vat = D(str(fees_cfg.get("vat_pct", 15)))
    out = []
    for bank_id, b in fees_cfg.get("banks", {}).items():
        sf = b.get("student_file") or {}

        def incl(x):
            return str((D(str(x)) * (1 + vat / 100)).quantize(Decimal(1))) if x is not None else None

        out.append({"bank_id": bank_id, "bank": b["name"], "opening_bdt": incl(sf.get("opening")),
                    "renewal_bdt": incl(sf.get("renewal")), "confidence": sf.get("confidence", "assumption"),
                    "source": sf.get("source", ""), "url": sf.get("url", "")})
    return out


def build_market(mid: MidRates, cfg: dict, real_quotes: list[BankQuote] | None = None, published=None) -> Market:
    """`published`: a BankRateStore (app/bank_rates.py) with banks' own daily sheets, or None."""
    fees_cfg = cfg.get("fees", {"banks": {}})
    quotes: list[BankQuote] = []
    notes: list[str] = []

    for pq in cfg.get("published_quotes", []):
        pr = published.latest(pq["rate_source"], date.fromisoformat(mid.as_of)) if published is not None else None
        if pr is None:
            notes.append(f"No published rate sheet available for {pq['bank']}")
            continue
        # Same day (± 3) and a real market rate: use the bank's published number as it is. Otherwise (tests, or an
        # old sheet) apply the bank's own published markup over its mid-rate to today's market rate.
        fresh = not mid.sample and abs((date.fromisoformat(mid.as_of) - date.fromisoformat(pr.date)).days) <= 3
        rate = pr.cny_tt_selling if fresh else (mid.bdt_per_cny * pr.cny_tt_selling / pr.cny_bank_mid).quantize(FOUR_PLACES)
        how = "as published" if fresh else "applied as its markup over the bank's own mid-rate"
        source = f"{pq['bank']} daily rate sheet {pr.date}: CNY TT selling ৳{pr.cny_tt_selling} ({how}; banks call these indicative)"
        quotes.append(BankQuote(pq["quote_id"], pq["bank"], rate, D(0), pr.date, source, False,
                                ((rate / mid.bdt_per_cny - 1) * 100).quantize(Decimal("0.01")), "published",
                                fee_schedule(pq["fees"], fees_cfg)))

    for q in cfg.get("field_quotes", []):
        markup = D(q["markup_pct"])
        rate = (mid.bdt_per_cny * (1 + markup / 100)).quantize(FOUR_PLACES)
        quotes.append(BankQuote(q["quote_id"], q["bank"], rate, D(q.get("fixed_fee_bdt", "0")), mid.as_of, q["source"], False,
                                markup, "real_payment", fee_schedule(q["fees"], fees_cfg) if q.get("fees") else None))

    for q in cfg.get("estimated_quotes", []) or []:
        markup = D(q["markup_pct"])
        rate = (mid.bdt_per_cny * (1 + markup / 100)).quantize(FOUR_PLACES)
        quotes.append(BankQuote(q["quote_id"], q["bank"], rate, D(q["fixed_fee_bdt"]), mid.as_of, q.get("source", cfg["source"]),
                                True, markup, "estimate", fee_schedule(q["fees"], fees_cfg) if q.get("fees") else None))

    for rq in real_quotes or []:
        markup = ((rq.bdt_per_cny / mid.bdt_per_cny - 1) * 100).quantize(Decimal("0.01"))
        quotes.append(BankQuote(rq.quote_id, rq.bank, rq.bdt_per_cny, rq.fixed_fee_bdt, rq.as_of, rq.source, False, markup,
                                "user_quote"))
    return Market(mid, quotes, notes)


def load_market() -> Market:
    """Market with the current mid-market rate (mode from SATHI_FX_MODE), published sheets and the quote config."""
    from app.bank_rates import BankRateStore  # local imports: these modules depend on this one
    from app.fx import FxProvider

    return build_market(FxProvider().latest(), load_quote_config(), published=BankRateStore())
