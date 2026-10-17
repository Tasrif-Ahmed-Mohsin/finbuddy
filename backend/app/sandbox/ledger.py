"""Double-entry books for the sandbox bank: every movement of money is a journal entry whose legs sum to zero.

Each entry has two or more postings (account, currency, signed amount: + money in, − money out). Per currency, the
postings of one entry always sum to exactly zero, so money is never created or lost: it only moves. A transfer from
taka to yuan goes through the bank's FX desk (one balanced leg per currency), and money on its way sits in a
"transit" account until it lands.

Two checks run continuously (the sandbox bank calls them after every operation, and the safety fuzzer after every
step):
* trial balance: for each currency, the sum over all accounts is zero;
* reconciliation: each customer account's balance in the books equals the balance the bank shows, and the transit
  account equals the transfers still on their way.

Accounts outside the customers (where money comes from or goes to) are named by kind: equity:opening (the demo's
starting balances), fx_desk (the bank's currency exchange), transit:CNY, world:spending (shops, rent), world:income
(employer, scholarship), world:atm_cash.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

ZERO = Decimal("0")


@dataclass(frozen=True)
class Posting:
    account: str
    currency: str
    amount: Decimal  # + into the account, − out of it

    def to_dict(self) -> dict:
        return {"account": self.account, "currency": self.currency, "amount": str(self.amount)}


@dataclass
class JournalEntry:
    id: str
    at: str  # simulated time
    event: str
    ref: str | None  # the draft, transfer or source this belongs to
    postings: tuple[Posting, ...]

    def to_dict(self) -> dict:
        return {"id": self.id, "at": self.at, "event": self.event, "ref": self.ref,
                "postings": [p.to_dict() for p in self.postings]}


class UnbalancedEntry(ValueError):
    """An entry whose legs do not sum to zero in some currency: refused, nothing is booked."""


@dataclass
class Ledger:
    entries: list[JournalEntry] = field(default_factory=list)
    balances: dict[tuple[str, str], Decimal] = field(default_factory=dict)  # (account, currency) → balance

    def post(self, at: str, event: str, ref: str | None, legs: list[tuple[str, str, Decimal]]) -> JournalEntry:
        postings = tuple(Posting(a, c, Decimal(x)) for a, c, x in legs if Decimal(x) != 0)
        if len(postings) < 2:
            raise UnbalancedEntry(f"{event}: an entry needs at least two legs")
        for cur in {p.currency for p in postings}:
            total = sum((p.amount for p in postings if p.currency == cur), ZERO)
            if total != 0:
                raise UnbalancedEntry(f"{event}: {cur} legs sum to {total}, not zero")
        entry = JournalEntry(f"je-{len(self.entries) + 1:05d}", at, event, ref, postings)
        self.entries.append(entry)
        for p in postings:
            key = (p.account, p.currency)
            self.balances[key] = self.balances.get(key, ZERO) + p.amount
        return entry

    def balance(self, account: str, currency: str) -> Decimal:
        return self.balances.get((account, currency), ZERO)

    def trial_balance(self) -> dict[str, Decimal]:
        """Per currency, the sum over every account. Always zero in correct books."""
        out: dict[str, Decimal] = {}
        for (_, cur), v in self.balances.items():
            out[cur] = out.get(cur, ZERO) + v
        return out

    def refs_of(self, event: str) -> list[str]:
        return [e.ref for e in self.entries if e.event == event and e.ref]
