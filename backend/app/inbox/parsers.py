"""Rule-based transaction extraction from bank SMS / email text (EN, ZH, BN).

Rules first (transparent, offline, free); the LLM is only a fallback for formats the rules miss.
NOTE: patterns are built from typical bank-alert wording. They must be validated against real,
anonymised samples from users (see docs/01_problem_research.md, follow-up questions).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

CURRENCY_TOKENS = {
    "BDT": "BDT", "TK": "BDT", "TK.": "BDT", "TAKA": "BDT", "৳": "BDT", "টাকা": "BDT",
    "USD": "USD", "US$": "USD", "$": "USD",
    "CNY": "CNY", "RMB": "CNY", "¥": "CNY", "￥": "CNY", "元": "CNY", "YUAN": "CNY", "人民币": "CNY",
}
_CUR = r"(BDT|Tk\.?|TK\.?|Taka|৳|টাকা|USD|US\$|\$|CNY|RMB|¥|￥|人民币|元|yuan)"
_AMT = r"(\d[\d,]*(?:\.\d{1,2})?)"
PREFIX = re.compile(_CUR + r"\s?" + _AMT, re.IGNORECASE)
SUFFIX = re.compile(_AMT + r"\s?" + _CUR, re.IGNORECASE)
BALANCE = re.compile(r"(?:\bavl\.?\s*bal(?:ance)?\b|\bavailable\s+balance\b|\bbalance\b|\bbal\b\.?|余额|ব্যালেন্স)[^\d]{0,16}" + _AMT, re.IGNORECASE)
# \bcharges?\b does not match "charged": "charged BDT 500" is the amount, not a fee.
FEE = re.compile(r"(?:\bfees?\b|\bcharges?\b|\bcommission\b|手续费|ফি |চার্জ)[^\d]{0,12}" + _AMT, re.IGNORECASE)
# (?!\d) instead of \b: in "尾号3317的" there is no word boundary between a digit and a CJK character.
LAST4 = re.compile(r"(?:a/c|ac|acct|account|card(?:\s+ending)?|ending|尾号|কার্ড)\s*(?:no\.?|number|#|:)?\s*[x*•]*(\d{4})(?!\d)", re.IGNORECASE)
COUNTERPARTY = re.compile(r"\b(?:at|to|from)\s+([A-Z][A-Za-z0-9 &.\-]{2,40}?)(?=\s+on\b|\s+dated\b|[.,;]|$)")

DEBIT = ["debited", "withdrawal", "withdrawn", "spent", "purchase", "paid", "deducted", "charged", "sent", "used for",
         "支出", "消费", "取款", "扣款", "转出", "付款", "ডেবিট", "উত্তোলন", "খরচ", "পরিশোধ"]
CREDIT = ["credited", "received", "deposited", "refund", "refunded", "收入", "存入", "转入", "入账", "退款", "জমা", "ক্রেডিট"]
KINDS = [
    ("atm", ["atm", "cash withdrawal", "取款", "取现", "এটিএম"]),
    ("fee", ["fee charged", "charge for", "手续费", "annual fee"]),
    ("transfer", ["transfer", "remittance", "swift", "tt ", "汇款", "转账", "রেমিট্যান্স", "ট্রান্সফার"]),
    ("refund", ["refund", "退款"]),
    ("pos", ["pos", "purchase", "merchant", "spent", "消费", "支付宝", "alipay", "wechat"]),
]


@dataclass
class ParsedTxn:
    amount: Decimal
    currency: str
    direction: str | None  # debit | credit | None
    kind: str
    account_last4: str | None = None
    balance_after: Decimal | None = None
    fee: Decimal | None = None
    home_bdt: Decimal | None = None  # BDT equivalent shown in the message, if any
    counterparty: str | None = None
    parser: str = "rules"
    confidence: float = 0.6
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {k: (str(v) if isinstance(v, Decimal) else v) for k, v in self.__dict__.items()}


def to_decimal(s: str) -> Decimal | None:
    try:
        return Decimal(s.replace(",", ""))
    except (InvalidOperation, AttributeError):
        return None


def _earliest(text_l: str, words: list[str]) -> int:
    hits = [text_l.find(w) for w in words if text_l.find(w) >= 0]
    return min(hits) if hits else -1


def parse(text: str) -> ParsedTxn | None:
    t = text.translate(BN_DIGITS)
    tl = t.lower()

    bal_m = BALANCE.search(t)
    fee_m = FEE.search(t)
    excluded = [m.span() for m in (bal_m, fee_m) if m]

    def outside(span: tuple[int, int]) -> bool:
        return not any(a <= span[0] < b or a < span[1] <= b for a, b in excluded)

    amounts: list[tuple[int, Decimal, str]] = []
    for m in PREFIX.finditer(t):
        if outside(m.span()):
            amt = to_decimal(m.group(2))
            if amt is not None and amt > 0:
                amounts.append((m.start(), amt, CURRENCY_TOKENS.get(m.group(1).upper(), CURRENCY_TOKENS.get(m.group(1), "BDT"))))
    for m in SUFFIX.finditer(t):
        if outside(m.span()):
            amt = to_decimal(m.group(1))
            if amt is not None and amt > 0 and not any(abs(m.start() - s) < 3 for s, _, _ in amounts):
                amounts.append((m.start(), amt, CURRENCY_TOKENS.get(m.group(2).upper(), CURRENCY_TOKENS.get(m.group(2), "BDT"))))
    if not amounts:
        return None
    amounts.sort(key=lambda a: a[0])
    _, amount, currency = amounts[0]
    home_bdt = next((a for _, a, c in amounts[1:] if c == "BDT"), None) if currency != "BDT" else None

    d, c = _earliest(tl, DEBIT), _earliest(tl, CREDIT)
    direction = None
    if d >= 0 and (c < 0 or d < c):
        direction = "debit"
    elif c >= 0:
        direction = "credit"

    kind = next((k for k, words in KINDS if any(w in tl for w in words)), "other")
    last4 = LAST4.search(t)
    cp = COUNTERPARTY.search(t)
    return ParsedTxn(
        amount=amount,
        currency=currency,
        direction=direction,
        kind=kind,
        account_last4=last4.group(1) if last4 else None,
        balance_after=to_decimal(bal_m.group(1)) if bal_m else None,
        fee=to_decimal(fee_m.group(1)) if fee_m else None,
        home_bdt=home_bdt,
        counterparty=cp.group(1).strip() if cp else None,
        confidence=0.9 if direction else 0.6,
    )
