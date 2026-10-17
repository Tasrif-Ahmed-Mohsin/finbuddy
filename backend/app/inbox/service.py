"""Inbox service: ingest a shared/forwarded SMS or email and keep the user's picture up to date.

Pipeline (each step is logged in the audit log, without message content):
  1. financial filter: non-money messages are dropped, never stored (data minimisation)
  2. redaction: OTP codes removed, account/card/phone numbers masked, emails masked
  3. scam / phishing / prompt-injection scan
  4. extraction: rules first; DeepSeek fallback on the REDACTED text, with number grounding
  5. tracking: Bangladeshi card usage (5 lakh BDT / 30 transactions) updated from real alerts
  6. insights recomputed
Reading messages is a READ (L0) capability only: it can never move money.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from app.engines.cost import card_bdt_per_cny
from app.inbox.extract_llm import llm_extract
from app.inbox.filters import is_financial
from app.inbox.insights import InsightContext, generate
from app.inbox.parsers import ParsedTxn, parse
from app.inbox.redact import redact
from app.money import q2
from app.security.scam import has_high_risk, scan_text
from app.security.taint import TaintSource

if TYPE_CHECKING:
    from app.service import AppState

DEMO_FILE = Path(__file__).resolve().parent.parent / "data" / "demo_messages.yaml"
SOURCES = {"sms", "email", "share", "webhook"}


@dataclass
class StoredMessage:
    id: str
    source: str
    sender: str
    received_at: datetime
    text: str  # REDACTED text only; the original is never stored
    otp: bool
    flags: list[dict]
    txn_id: str | None = None

    def to_dict(self) -> dict:
        return {"id": self.id, "source": self.source, "sender": self.sender, "received_at": self.received_at.isoformat(),
                "text": self.text, "otp": self.otp, "flags": self.flags, "txn_id": self.txn_id}


@dataclass
class Txn:
    id: str
    message_id: str
    received_at: datetime
    sender: str
    amount: Decimal
    currency: str
    direction: str | None
    kind: str
    account_last4: str | None
    owner: str
    balance_after: Decimal | None
    fee: Decimal | None
    home_bdt: Decimal | None
    bdt_value: Decimal
    bdt_is_estimate: bool
    counterparty: str | None
    parser: str
    confidence: float
    counted_on_card: bool = False
    card_status: str | None = None  # status of the student's card when this alert arrived
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {k: (str(v) if isinstance(v, Decimal) else v.isoformat() if isinstance(v, datetime) else v)
                for k, v in self.__dict__.items()}


class Inbox:
    def __init__(self, app: "AppState"):
        self.app = app
        self.messages: list[StoredMessage] = []
        self.txns: list[Txn] = []
        self.dropped = 0
        self._n = 0

    def _id(self, prefix: str) -> str:
        self._n += 1
        return f"{prefix}-{self._n:04d}"

    # ---- ingestion -----------------------------------------------------------
    def ingest(self, actor: str, source: str, sender: str, text: str, received_at: datetime | None = None) -> dict:
        if source not in SOURCES:
            raise ValueError(f"unknown source '{source}'")
        text = (text or "").strip()
        if not text:
            raise ValueError("empty message")
        when = received_at or self.app.now
        # Taint tracking: label the money amounts in ALL outside text at the door, before any filtering, so the
        # defence never depends on how a message was classified (the safety fuzzer found that gap).
        self.app.taint_ledger.register_untrusted_text(
            {"email": TaintSource.UNTRUSTED_EMAIL, "webhook": TaintSource.UNTRUSTED_WEBHOOK}.get(source, TaintSource.UNTRUSTED_SMS),
            f"{source}-{self._n + 1:04d}", sender[:60] or "unknown", text, when)
        flags = scan_text(text)
        risky = has_high_risk(flags)
        if not is_financial(sender, text) and not risky:
            self.dropped += 1
            self.app.bank.log("message_dropped", actor, "READ", {"source": source, "reason": "not financial", "length": len(text)})
            return {"kept": False, "reason": "Not a money message, so it was not stored."}

        red = redact(text)
        msg = StoredMessage(self._id("msg"), source, sender[:60] or "unknown", when, red.text, red.otp,
                            [f.to_dict() for f in flags])
        self.messages.append(msg)

        txn = None
        if not red.otp and not risky:
            parsed = parse(red.text)
            llm = self.app.llm_for(actor) if actor in ("parent", "student") else self.app.llm
            if (parsed is None or parsed.confidence < 0.75) and llm is not None:
                parsed = llm_extract(llm, red.text) or parsed
            if parsed is not None:
                txn = self._track(msg, parsed)
                msg.txn_id = txn.id

        self.app.bank.log("message_ingested", actor, "READ", {
            "message_id": msg.id, "source": source, "sender": msg.sender, "otp_removed": red.otp,
            "numbers_masked": red.masked, "flags": [f.category for f in flags],
            "txn": {"id": txn.id, "amount": str(txn.amount), "currency": txn.currency, "kind": txn.kind,
                    "parser": txn.parser, "counted_on_card": txn.counted_on_card} if txn else None,
        })
        return {"kept": True, "message": msg.to_dict(), "transaction": txn.to_dict() if txn else None,
                "flags": msg.flags, "insights": self.insights()}

    def _track(self, msg: StoredMessage, p: ParsedTxn) -> Txn:
        prof, mid = self.app.profile, self.app.market.mid
        owner = {prof.get("student_card_last4"): "student_card", prof.get("parent_account_last4"): "parent_account",
                 prof.get("student_cn_last4"): "student_cn"}.get(p.account_last4, "unknown")
        if p.currency == "BDT":
            value, estimate = p.amount, False
        elif p.home_bdt is not None:
            value, estimate = p.home_bdt, False
        elif p.currency == "CNY":
            rate = card_bdt_per_cny(self.app.corridor, mid.bdt_per_cny) if owner == "student_card" else mid.bdt_per_cny
            value, estimate = p.amount * rate, True
        else:  # USD
            value, estimate = p.amount * mid.bdt_per_usd, True
        txn = Txn(self._id("txn"), msg.id, msg.received_at, msg.sender, p.amount, p.currency, p.direction, p.kind,
                  p.account_last4, owner, p.balance_after, p.fee, p.home_bdt, q2(value), estimate, p.counterparty,
                  p.parser, p.confidence, notes=list(p.notes))
        if owner == "student_card":
            txn.card_status = self.app.student_card.status
        # Track the Bangladeshi card's monthly limits from real alerts (N-06).
        if owner == "student_card" and p.direction == "debit" and p.kind in ("atm", "pos"):
            usage = self.app.bank.card_usage()
            if msg.received_at.strftime("%Y-%m") == usage.month:
                usage.tx_count += 1
                usage.bdt_charged += txn.bdt_value + (p.fee or Decimal(0))
                txn.counted_on_card = True
        self.txns.append(txn)
        return txn

    def seed_demo(self, actor: str) -> dict:
        raw = yaml.safe_load(DEMO_FILE.read_text(encoding="utf-8"))
        results = [self.ingest(actor, m["source"], m["sender"], m["text"],
                               self.app.now - timedelta(minutes=int(m.get("minutes_ago", 0))))
                   for m in raw["messages"]]
        return {"ingested": len(results), "kept": sum(1 for r in results if r["kept"]), "synthetic": raw.get("synthetic", True)}

    # ---- views -----------------------------------------------------------------
    def insights(self) -> list[dict]:
        usage = self.app.bank.card_usage()
        executed = [d.amount_cny for d in self.app.drafts.values() if d.status == "executed"]
        rule = self.app._savings_rule()
        ctx = InsightContext(self.app.corridor, self.app.market, self.app.now, self.app.profile, self.txns,
                             self.messages, usage.tx_count, usage.bdt_charged, executed, self.app.student_card.status,
                             [c.to_dict(self.app.now.date()) for c in self.app.renewals.values()],
                             savings_pct=rule.shield_pct if rule else None,
                             shield_target_cny=rule.target_cny if rule else None,
                             family_bdt_per_cny=self.app.family_bdt_per_cny(),
                             daily_living_cny=self.app.policy.daily_spend_cny)
        return [i.to_dict() for i in generate(ctx)]

    def summary(self) -> dict:
        month = self.app.now.strftime("%Y-%m")
        mine = [t for t in self.txns if t.received_at.strftime("%Y-%m") == month]
        spent = sum((t.bdt_value for t in mine if t.direction == "debit"), Decimal(0))
        fees = sum((t.fee for t in mine if t.fee), Decimal(0))
        return {"month": month, "messages": len(self.messages), "dropped": self.dropped, "transactions": len(mine),
                "spent_bdt": str(q2(spent)), "fees_bdt": str(q2(fees))}
