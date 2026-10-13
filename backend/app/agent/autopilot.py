"""Autopilot: the agent ACTING as a financial participant, but only inside a family mandate (level L3).

Every simulated day (and right after a mandate is signed) it:
  1. senses: the student's money in China and transfers already on the way (sandbox bank feed; in real
     life the same numbers come from the bank SMS/email alerts the inbox reads);
  2. plans: `topup_decision`, the same look-ahead rule the year plan uses (weekends and holidays in both
     countries, transfer time, a cushion);
  3. acts: fits the amount inside Bangladesh's living-money limit and the mandate's caps, creates a draft
     as the AGENT (all compliance checks run) and executes it under the mandate, or, if anything does not
     fit, leaves a draft for the family to approve and says why;
  4. proves: every step is in the hash-chained audit log, and the family feed explains it in Bengali,
     English and Chinese.
It never approves, never changes a mandate, never pays anyone except the mandate's payee, and never
withdraws cash (an ATM withdrawal is the student's own physical action: Sathi only suggests it).
"""
from __future__ import annotations

from datetime import date
from decimal import ROUND_FLOOR, Decimal
from typing import TYPE_CHECKING

from app.engines.living_planner import ATM_NOTE, best_quote_for
from app.engines.year_plan import runs_out_on, topup_decision
from app.money import q2
from app.notify import reason_texts, why_texts
from app.security.permissions import Actor

if TYPE_CHECKING:
    from app.service import AppState


class Autopilot:
    def __init__(self, app: "AppState"):
        self.app = app
        self.asked: set[str] = set()  # one request to the family per planned landing day

    def active_mandate(self):
        now = self.app.now
        live = [m for m in self.app.mandates.values() if m.auto_topup and not m.revoked and now <= m.expires_at]
        return live[-1] if live else None

    def fit_amount(self, amount: Decimal, room_bdt: Decimal) -> Decimal:
        """Largest multiple of ¥100 (≤ amount) whose cheapest all-in cost fits in `room_bdt`."""
        market = self.app.market
        a = (amount / ATM_NOTE).quantize(Decimal(1), rounding=ROUND_FLOOR) * ATM_NOTE
        while a > 0 and best_quote_for(a, market)[1].total_bdt > room_bdt:
            a -= ATM_NOTE
        return a

    def tick(self) -> list[dict]:
        app = self.app
        today: date = app.now.date()
        policy, cal = app.policy, app.calendar
        bal, transit = app.student_money()
        m = self.active_mandate()
        if today > app.profile["student_file_expiry"]:
            return []
        dec = topup_decision(today, bal, transit, policy, cal)

        if m is not None and (m.expires_at.date() - today).days == 14:
            app.feed.add(app.now, "both", "warning", "mandate_expiring", {"end_date": m.expires_at.date().isoformat()},
                         {"screen": "family"}, once=f"expiring:{m.id}")
        if m is None:
            if bal < policy.daily_spend_cny:
                return []  # already out of money: the 'stuck' warning says so; do not repeat every day
            out = runs_out_on(bal, transit, today, policy.daily_spend_cny)
            if out is not None and (out - today).days <= policy.transfer_days + policy.safety_days:
                days = int(bal // policy.daily_spend_cny) if policy.daily_spend_cny > 0 else 0
                app.feed.add(app.now, "both", "warning", "runway_low",
                             {"out_date": out.isoformat(), "balance_cny": str(q2(bal)), "days_n": days},
                             {"screen": "family"}, once=f"runway:{out.isoformat()}")
            return []
        if dec is None:
            return []

        cny_per_usd = app.market.mid.cny_per_usd
        living_left = (app.corridor.v("bd_living_remit_cap_usd_per_month")
                       - app.bank.living_remitted_usd.get(app.bank.month, Decimal(0))) * cny_per_usd
        room = min(m.max_bdt_per_payment, m.max_bdt_per_period - m.spent_in_period(app.now))
        wanted = dec.amount_cny
        amount = self.fit_amount(min(wanted, living_left), room)
        why = why_texts(dec.to_dict(), cal.names())
        actions: list[dict] = []

        if amount < policy.min_transfer_cny:
            reason = ("Bangladesh's monthly living-money limit is reached" if living_left < policy.min_transfer_cny
                      else "amount exceeds the mandate's period cap" if room < m.max_bdt_per_payment
                      else "amount exceeds the mandate's per-payment cap")
            actions.append(self._ask_family(wanted, reason, dec))
            return actions
        self.asked = {k for k in self.asked if not k.startswith(app.bank.month)}  # a new send clears old requests

        draft = app.create_draft(Actor.AGENT, "tt_living", amount, m.payee_id, memo="Living money")
        if draft["status"] == "blocked":
            actions.append(self._ask_family(amount, "blocked by compliance checks", dec, draft_id=draft["id"]))
            return actions
        try:
            res = app.execute_under_mandate(Actor.AGENT, draft["id"], m.id)
        except (PermissionError, ValueError) as e:
            actions.append(self._ask_family(amount, str(e), dec, draft_id=draft["id"]))
            return actions
        event = res["bank_event"]["data"]
        mv = res["mandate"]
        app.feed.add(app.now, "both", "did", "autopilot_sent", {
            "amount_cny": str(amount), "total_bdt": draft["total_bdt"], "bank": app.market.quote(draft["quote_id"]).bank,
            "lands_date": event["arrives_at"], "used_bdt": mv["spent_in_period_bdt"], "cap_bdt": mv["max_bdt_per_period"],
            "why_en": why["en"], "why_bn": why["bn"], "why_zh": why["zh"],
        }, {"screen": "proof", "draft_id": draft["id"]})
        actions.append({"type": "autopilot_sent", "draft_id": draft["id"], "amount_cny": str(amount), "decision": dec.to_dict()})
        if amount < wanted and wanted - amount >= policy.min_transfer_cny:
            actions.append(self._ask_family(wanted - amount, "amount exceeds the mandate's period cap"
                                            if room < m.max_bdt_per_payment else "amount exceeds the mandate's per-payment cap", dec))
        if dec.bridge_cny > 0 and app.card_usable(today):
            app.feed.add(app.now, "student", "needs_you", "bridge_cash",
                         {"amount_cny": str(dec.bridge_cny), "lands_date": dec.lands.isoformat(),
                          "card_date": app.profile["endorsement_expiry"].isoformat()},
                         {"screen": "plan", "mode": "living"}, once=f"bridge:{today.isoformat()}")
        return actions

    def _ask_family(self, amount: Decimal, reason: str, dec, draft_id: str | None = None) -> dict:
        """Leave a draft for the family to approve (or say why it is blocked) instead of acting alone."""
        app = self.app
        key = f"{app.bank.month}:{reason}"
        if key in self.asked:
            return {"type": "needs_approval", "draft_id": draft_id, "reason": reason, "repeat": True}
        self.asked.add(key)
        # No draft is left waiting (its rate quote would go stale): the family prepares a fresh one with one tap.
        ref = {"screen": "draft", "draft_id": draft_id} if draft_id else {"screen": "topup", "amount_cny": str(q2(amount))}
        app.feed.add(app.now, "parent", "needs_you", "autopilot_needs_approval",
                     {"amount_cny": str(q2(amount)), **reason_texts(reason)}, ref)
        app.bank.log("autopilot_escalated", Actor.AGENT.value, "DRAFT", {"draft_id": draft_id, "reason": reason,
                                                                         "decision": dec.to_dict()})
        return {"type": "needs_approval", "draft_id": draft_id, "reason": reason}
