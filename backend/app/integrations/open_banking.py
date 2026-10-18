"""Open-banking connectors (read-only), with the person's consent: Bluefin reads balances only while it is allowed to.

The flow follows the account-information (AIS) model of UK Open Banking and the Berlin Group NextGenPSD2 standard
that most open-banking rules copy, including PSD2's 90-day limit before the person must confirm again:

1. Bluefin asks for a consent: which bank, which data (balances, and optionally transactions), for how long (≤ 90 days).
2. The account holder authorises it with their passkey, signed over the consent's hash, so they approve exactly
   these permissions for exactly this period. (A real bank does this step on its own site or app.)
3. While the consent is active, Bluefin may read; every read names the consent and is written to the log.
4. The holder can revoke it at any time: reads stop at once. An expired consent stops too.

Read-only by design: no permission here can move money (payments go through drafts, passkeys and the engine).
The connectors are simulated: BRAC Bank (Bangladesh) for the parent's account and Bank of China for the student's
account, answering from the sandbox bank. Bangladesh Bank and China do not yet have a public open-banking API for
these accounts, so the adapters show the shape a bank would plug into, not a live connection.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from app.money import q2

if TYPE_CHECKING:
    from app.sandbox.bank import SandboxBank

MAX_DAYS = 90
PERMISSIONS = {
    "ReadAccountsBasic": "Which accounts you have (name and last 4 digits)",
    "ReadBalances": "How much money is in them",
    "ReadTransactionsBasic": "Money in and out (amounts and dates, no shop names)",
}


@dataclass(frozen=True)
class Connector:
    id: str
    bank: str
    country: str
    standard: str
    holder: str  # who owns the account and must consent: parent | student
    account_ids: tuple[str, ...]


CONNECTORS = {
    "brac_bd": Connector("brac_bd", "BRAC Bank (sandbox)", "BD", "Berlin Group NextGenPSD2 AIS shape", "parent", ("parent_bd",)),
    "boc_cn": Connector("boc_cn", "Bank of China (sandbox)", "CN", "UK Open Banking AIS v3.1 shape", "student", ("student_cn",)),
}


@dataclass
class Consent:
    id: str
    connector_id: str
    holder: str
    permissions: tuple[str, ...]
    days: int
    created_at: datetime
    expires_at: datetime
    status: str = "AwaitingAuthorisation"  # → Authorised → Revoked | Expired
    authorised_at: datetime | None = None
    revoked_at: datetime | None = None
    reads: list[str] = field(default_factory=list)  # when Bluefin read through it

    def hash(self) -> str:
        """What the holder signs: these permissions, this bank, this period."""
        body = {"id": self.id, "connector": self.connector_id, "holder": self.holder,
                "permissions": sorted(self.permissions), "expires_at": self.expires_at.isoformat()}
        return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()

    def state(self, now: datetime) -> str:
        if self.status == "Authorised" and now > self.expires_at:
            return "Expired"
        return self.status

    def to_dict(self, now: datetime) -> dict:
        c = CONNECTORS[self.connector_id]
        return {"id": self.id, "connector": self.connector_id, "bank": c.bank, "country": c.country, "standard": c.standard,
                "holder": self.holder, "permissions": [{"id": p, "text": PERMISSIONS[p]} for p in self.permissions],
                "days": self.days, "created_at": self.created_at.isoformat(), "expires_at": self.expires_at.isoformat(),
                "days_left": max((self.expires_at.date() - now.date()).days, 0), "status": self.state(now),
                "authorised_at": self.authorised_at.isoformat() if self.authorised_at else None,
                "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
                "reads": len(self.reads), "last_read": self.reads[-1] if self.reads else None, "hash": self.hash(),
                "can_move_money": False}


class OpenBanking:
    def __init__(self):
        self.consents: dict[str, Consent] = {}
        self._n = 0

    def request(self, holder: str, connector_id: str, permissions: list[str], days: int, now: datetime) -> Consent:
        c = CONNECTORS.get(connector_id)
        if c is None:
            raise KeyError(connector_id)
        if c.holder != holder:
            raise PermissionError(f"only the account holder (the {c.holder}) can connect {c.bank}")
        perms = tuple(p for p in PERMISSIONS if p in set(permissions))
        if "ReadAccountsBasic" not in perms:
            perms = ("ReadAccountsBasic",) + perms
        if not 1 <= days <= MAX_DAYS:
            raise ValueError(f"a bank connection lasts at most {MAX_DAYS} days, then you confirm it again")
        self._n += 1
        consent = Consent(f"obc-{self._n:04d}", connector_id, holder, perms, days, now, now + timedelta(days=days))
        self.consents[consent.id] = consent
        return consent

    def authorise(self, consent_id: str, now: datetime) -> Consent:
        consent = self.consents[consent_id]
        if consent.status != "AwaitingAuthorisation":
            raise ValueError(f"this connection is {consent.state(now).lower()}")
        consent.status, consent.authorised_at = "Authorised", now
        return consent

    def revoke(self, consent_id: str, holder: str, now: datetime) -> Consent:
        consent = self.consents[consent_id]
        if consent.holder != holder:
            raise PermissionError("only the account holder can revoke this connection")
        if consent.status in ("Authorised", "AwaitingAuthorisation"):
            consent.status, consent.revoked_at = "Revoked", now
        return consent

    def active(self, connector_id: str, now: datetime) -> Consent | None:
        return next((c for c in reversed(list(self.consents.values()))
                     if c.connector_id == connector_id and c.state(now) == "Authorised"), None)

    def read(self, connector_id: str, bank: "SandboxBank", now: datetime) -> dict:
        """Read through an active consent only, and only what it allows. Raises PermissionError otherwise."""
        consent = self.active(connector_id, now)
        if consent is None:
            raise PermissionError("no active consent for this bank: Bluefin cannot read it")
        c = CONNECTORS[connector_id]
        consent.reads.append(now.isoformat())
        accounts = []
        for acct_id in c.account_ids:
            a = bank.accounts[acct_id]
            item = {"AccountId": f"{c.id}-{acct_id}", "Nickname": a.label.split(" [")[0], "Currency": a.currency}
            if "ReadBalances" in consent.permissions:
                item["Balance"] = {"Amount": {"Amount": str(q2(a.balance)), "Currency": a.currency},
                                   "CreditDebitIndicator": "Credit", "Type": "InterimAvailable", "DateTime": now.isoformat()}
            if "ReadTransactionsBasic" in consent.permissions:
                item["Transactions"] = [
                    {"Amount": {"Amount": str(abs(p.amount)), "Currency": p.currency},
                     "CreditDebitIndicator": "Credit" if p.amount > 0 else "Debit", "BookingDateTime": e.at,
                     "Reference": e.ref or e.event}
                    for e in bank.ledger.entries[-200:] for p in e.postings if p.account == acct_id][-20:]
            accounts.append(item)
        return {"consent_id": consent.id, "bank": c.bank, "standard": c.standard, "Data": {"Account": accounts}}

    def for_holder(self, holder: str, now: datetime) -> list[dict]:
        return [c.to_dict(now) for c in self.consents.values() if c.holder == holder]
