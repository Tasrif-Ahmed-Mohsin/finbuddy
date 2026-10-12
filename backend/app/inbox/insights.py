"""Insight engine: deterministic rules that turn tracked transactions into advice and alerts.

The rules decide WHAT to say and compute every number; the LLM may later rephrase or translate the
text (with a number-grounding check), but never changes the facts.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal

from app.corridors.loader import Corridor
from app.engines.living_planner import LivingRequest, plan_living
from app.market import Market
from app.money import q2

URL = re.compile(r"(https?://\S+|www\.\S+|bit\.ly/\S+|tinyurl\.com/\S+)", re.IGNORECASE)
URGENCY = ["verify", "suspend", "blocked", "block", "kyc", "update your", "click", "login", "confirm your",
           "验证", "冻结", "点击", "登录", "যাচাই", "ব্লক", "আপডেট"]


@dataclass
class Insight:
    id: str
    type: str
    severity: str  # info | warn | alert
    title: str
    body: str
    savings_bdt: Decimal | None = None
    action: dict | None = None
    txn_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"id": self.id, "type": self.type, "severity": self.severity, "title": self.title, "body": self.body,
                "savings_bdt": str(self.savings_bdt) if self.savings_bdt is not None else None,
                "action": self.action, "txn_ids": self.txn_ids}


@dataclass
class InsightContext:
    corridor: Corridor
    market: Market
    now: datetime
    profile: dict
    txns: list  # inbox Txn objects
    messages: list  # inbox StoredMessage objects
    card_tx_used: int
    card_bdt_used: Decimal
    executed_amounts_cny: list[Decimal]
    card_status: str = "active"


def fmt_bdt(x: Decimal) -> str:
    return f"৳{int(q2(x)):,}"


def fmt_cny(x: Decimal) -> str:
    v = q2(x)
    return f"¥{int(v):,}" if v == int(v) else f"¥{v:,}"


def generate(ctx: InsightContext) -> list[Insight]:
    c, out = ctx.corridor, []
    month = ctx.now.strftime("%Y-%m")
    card_last4 = ctx.profile.get("student_card_last4")
    mine = [t for t in ctx.txns if t.received_at.strftime("%Y-%m") == month]

    def freeze_action(t) -> dict | None:
        if t.owner == "student_card" and ctx.card_status == "active":
            return {"screen": "card", "op": "freeze", "last4": card_last4}
        return None

    # 0. A charge on a card that is frozen or reported lost: the card may be compromised.
    for t in mine:
        if t.owner == "student_card" and t.direction == "debit" and t.card_status in ("frozen", "lost"):
            out.append(Insight(f"used_while_{t.card_status}:{t.id}", "card_used_while_blocked", "alert",
                               f"Card used while {t.card_status}!",
                               f"A charge of {fmt_cny(t.amount) if t.currency == 'CNY' else fmt_bdt(t.amount)} arrived for card "
                               f"ending {card_last4} while it was {t.card_status}. Call your bank's 24-hour hotline now and "
                               "report the card lost so it is cancelled.",
                               action={"screen": "card", "op": "report_lost", "last4": card_last4}, txn_ids=[t.id]))

    # 1. ATM fee leakage (N-01/N-02): many withdrawals with a fixed fee each.
    atms = [t for t in mine if t.kind == "atm" and t.direction == "debit" and t.account_last4 == card_last4]
    if len(atms) >= 2:
        fees = sum((t.fee if t.fee is not None else c.v("bd_card_atm_fixed_fee_bdt") for t in atms), Decimal(0))
        atm_cny = sum((t.amount for t in atms if t.currency == "CNY"), Decimal(0))
        savings = None
        if atm_cny > 0:
            plan = plan_living(LivingRequest(need_cny=atm_cny), c, ctx.market)
            savings = plan.savings_vs_baseline_bdt if plan.best and plan.best.tt_cny > 0 else None
        body = (f"You made {len(atms)} ATM withdrawals this month ({fmt_cny(atm_cny)}) and paid about {fmt_bdt(fees)} "
                f"in fixed Bangladeshi bank fees.")
        if savings and savings > 0:
            body += f" Sending living money to your own Chinese account instead could save about {fmt_bdt(savings)} a month."
        out.append(Insight(f"atm_fee_leak:{month}", "atm_fee_leak", "warn", "ATM fees are adding up", body, savings,
                           {"screen": "plan", "mode": "living", "need_cny": str(q2(atm_cny))}, [t.id for t in atms]))

    # 2. Card limits (N-06): warn at 80%.
    tx_cap = c.i("bd_student_card_tx_cap_per_month")
    bdt_cap = c.v("bd_student_card_cap_bdt_per_month")
    if ctx.card_tx_used >= 0.8 * tx_cap or ctx.card_bdt_used >= Decimal("0.8") * bdt_cap:
        sev = "alert" if ctx.card_tx_used >= tx_cap or ctx.card_bdt_used >= bdt_cap else "warn"
        out.append(Insight(f"card_limit:{month}", "card_limit", sev, "Card limit almost reached",
                           f"This month you have used {ctx.card_tx_used} of {tx_cap} card transactions and "
                           f"{fmt_bdt(ctx.card_bdt_used)} of {fmt_bdt(bdt_cap)}. Plan bigger, fewer withdrawals or a transfer.",
                           action={"screen": "plan", "mode": "living"}))

    # 3. Large debit not initiated through Sathi: "Was this you?"
    threshold = c.v("large_debit_alert_bdt")
    for t in mine:
        if t.direction == "debit" and t.bdt_value >= threshold:
            known = t.currency == "CNY" and any(abs(t.amount - a) <= 1 for a in ctx.executed_amounts_cny)
            if not known:
                out.append(Insight(f"large_debit:{t.id}", "large_debit", "alert", "Large payment: was this you?",
                                   f"{fmt_cny(t.amount) if t.currency == 'CNY' else fmt_bdt(t.amount)} was debited"
                                   f"{' at ' + t.counterparty if t.counterparty else ''} (about {fmt_bdt(t.bdt_value)}). "
                                   "If you did not make it, freeze the card now and call your bank's hotline.",
                                   action=freeze_action(t), txn_ids=[t.id]))

    # 4. Duplicate charge: same amount + merchant within 10 minutes.
    debits = sorted((t for t in mine if t.direction == "debit"), key=lambda t: t.received_at)
    for a, b in zip(debits, debits[1:]):
        if (a.amount == b.amount and a.currency == b.currency and (a.counterparty or "") == (b.counterparty or "")
                and b.received_at - a.received_at <= timedelta(minutes=10)):
            out.append(Insight(f"duplicate:{b.id}", "duplicate_charge", "alert", "Possible double charge",
                               f"{fmt_cny(b.amount) if b.currency == 'CNY' else fmt_bdt(b.amount)} was charged twice"
                               f"{' at ' + b.counterparty if b.counterparty else ''} within minutes. Check with the merchant or your bank.",
                               action=freeze_action(b), txn_ids=[a.id, b.id]))

    # 5–7. Message-level security signals.
    otp_seen = False
    for m in sorted(ctx.messages, key=lambda m: m.received_at, reverse=True):
        cats = {f["category"] for f in m.flags if f["severity"] == "high"}
        if URL.search(m.text) and ("phishing" in cats or any(w in m.text.lower() for w in URGENCY)):
            out.append(Insight(f"phishing:{m.id}", "phishing_link", "alert", "Do not click this link",
                               f"A message from {m.sender} asks you to act through a link. Banks never ask you to verify "
                               "your card or KYC by SMS link. Open your bank app or call the number on your card instead.",
                               action={"screen": "message", "id": m.id}))
        elif cats:
            label = ", ".join(sorted(x.replace("_", " ") for x in cats))
            advice = next(f["advice"] for f in m.flags if f["severity"] == "high")
            out.append(Insight(f"suspicious:{m.id}", "suspicious_message", "alert", "Suspicious message",
                               f"A message from {m.sender} looks like a scam ({label}). Do not reply, pay or share codes. " + advice,
                               action={"screen": "message", "id": m.id}))
        if m.otp and not otp_seen:
            otp_seen = True
            out.append(Insight(f"otp:{m.id}", "otp_received", "info", "One-time code received",
                               f"You received a one-time code from {m.sender}. Sathi removed it and will never ask for it. "
                               "Never share it, not even with someone claiming to be bank staff."))

    # 8. Renewals (N-05).
    warn_days = c.i("bd_endorsement_warn_days")
    for key, label in (("endorsement_expiry", "Card endorsement"), ("student_file_expiry", "Student File")):
        expiry = ctx.profile.get(key)
        if expiry is None:
            continue
        days = (expiry - ctx.now.date()).days
        if days <= warn_days:
            out.append(Insight(f"{key}:{expiry}", "renewal_due", "alert" if days < 0 else "warn",
                               f"{label} {'expired' if days < 0 else 'expires soon'}",
                               f"{label} {'expired' if days < 0 else 'expires'} on {expiry} "
                               f"({'' if days < 0 else 'in '}{abs(days)} days{' ago' if days < 0 else ''}). Without it the card "
                               "stops working abroad. Start the renewal: enrolment certificate, transcript and invoice.",
                               action={"screen": "renewal", "item": key}))

    # 9. Hidden exchange-rate markup on a card transaction that shows both CNY and BDT.
    mid = ctx.market.mid.bdt_per_cny
    for t in mine:
        if t.currency == "CNY" and t.home_bdt and t.amount > 0:
            effective = t.home_bdt / t.amount
            markup = (effective / mid - 1) * 100
            if markup >= Decimal("1.5"):
                extra = t.home_bdt - t.amount * mid
                out.append(Insight(f"fx_markup:{t.id}", "fx_markup", "info", "Hidden exchange-rate cost",
                                   f"On {fmt_cny(t.amount)} you were charged {fmt_bdt(t.home_bdt)}: about {q2(markup)}% "
                                   f"({fmt_bdt(extra)}) above the market rate. For large amounts, compare banks first.",
                                   q2(extra), {"screen": "plan", "mode": "tuition"}, [t.id]))

    order = {"alert": 0, "warn": 1, "info": 2}
    return sorted(out, key=lambda i: order[i.severity])
