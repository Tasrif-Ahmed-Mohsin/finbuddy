"""Application service: the single place where drafts are created, approved and executed.

Every path re-runs compliance checks and permission checks server-side, and writes the audit log.
The API (main.py) and, later, the agent orchestrator both go through this class; neither can
bypass it.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from app.agent.chat import ChatAgent
from app.agent.explain import Translator
from app.agent.llm import DeepSeekClient
from app.audit.log import AuditLog
from app.config import Settings, load_settings
from app.corridors.loader import load_corridor
from app.engines.cost import atm_cost, tt_cost
from app.engines.living_planner import LivingRequest, plan_living
from app.engines.tuition_planner import TuitionRequest, plan_tuition
from app.inbox.service import Inbox
from app.market import load_market
from app.money import D, q2
from app.sandbox.bank import seed_demo_bank
from app.security.compliance import ComplianceContext, Payee, is_blocked, run_draft_checks
from app.security.permissions import (
    ACTION_LEVELS,
    Actor,
    ApprovalService,
    Draft,
    Level,
    Mandate,
    can_actor_perform,
    check_mandate,
    required_approvers,
)
from app.security.scam import scan_text

DEMO_START = datetime(2026, 10, 12, 9, 0)


@dataclass
class DraftSpec:
    from_account: str
    withdrawals: list[Decimal]
    purpose: str
    origin_message: str | None


class AppState:
    def __init__(self, audit_path: Path | None = None, start: datetime = DEMO_START,
                 llm: DeepSeekClient | None = None, settings: Settings | None = None):
        self.settings = settings or load_settings()
        self.llm = llm
        self.corridor = load_corridor("bd_cn")
        self.market = load_market("market_sample")
        self.audit = AuditLog(audit_path)
        self.bank = seed_demo_bank(self.corridor, self.audit, start, self.market.mid.cny_per_usd)
        self.bank.payees["student_cash_self"] = Payee(
            "student_cash_self", "Your own cash (ATM withdrawal)", "-", "-", "CNY", True, "Self", "student_cash"
        )
        self.approvals = ApprovalService()
        self.drafts: dict[str, Draft] = {}
        self.specs: dict[str, DraftSpec] = {}
        self.tokens: dict[str, list[dict]] = {}
        self.mandates: dict[str, Mandate] = {}
        # Demo profile (fictional). Endorsement until December mirrors Interview #1 (N-05).
        self.profile = {
            "student_name": "Demo Student",
            "parent_name": "Demo Parent",
            "university": "Demo University (sandbox)",
            "corridor": self.corridor.id,
            "tuition_invoice_cny": Decimal("35200"),
            "tuition_deadline": date(2026, 11, 15),
            "endorsement_expiry": date(2026, 12, 31),
            "student_file_expiry": date(2027, 9, 15),
            "monthly_living_cny": Decimal("6000"),
            # Last 4 digits only, used to match bank alerts to accounts (demo values).
            "student_card_last4": "4821",
            "parent_account_last4": "7730",
            "student_cn_last4": "3317",
        }
        self._n = 0
        self.inbox = Inbox(self)
        self.agent = ChatAgent(self)
        self.translator = Translator(llm)

    # ---- utilities --------------------------------------------------------
    @property
    def now(self) -> datetime:
        return self.bank.clock

    def _id(self, prefix: str) -> str:
        self._n += 1
        return f"{prefix}-{self._n:04d}"

    def _log(self, event: str, actor: Actor | str, action: str | None, data: dict) -> dict:
        level = ACTION_LEVELS[action].name if action in ACTION_LEVELS else "SYSTEM"
        actor_s = actor.value if isinstance(actor, Actor) else actor
        return self.bank.log(event, actor_s, level, data)

    def _require(self, actor: Actor, action: str) -> None:
        decision = can_actor_perform(actor, action)
        if not decision.allowed:
            self._log("permission_denied", actor, action, {"action": action, "reason": decision.reason})
            raise PermissionError(decision.reason)

    def _ctx(self, origin_message: str | None) -> ComplianceContext:
        return ComplianceContext(
            corridor=self.corridor,
            payees=self.bank.payees,
            now=self.now,
            invoice_amount_cny=self.profile["tuition_invoice_cny"],
            living_remitted_usd_this_month=self.bank.living_remitted_usd.get(self.bank.month, Decimal(0)),
            cny_per_usd=self.market.mid.cny_per_usd,
            endorsement_expiry=self.profile["endorsement_expiry"],
            student_file_expiry=self.profile["student_file_expiry"],
            origin_flags=scan_text(origin_message) if origin_message else None,
        )

    # ---- read-only (L0) ---------------------------------------------------
    def plan_tuition(self, actor: Actor, amount_cny: Decimal, deadline: date, current_quote_id: str | None = None) -> dict:
        self._require(actor, "compare_tuition")
        plan = plan_tuition(TuitionRequest(D(amount_cny), deadline, self.now.date(), current_quote_id), self.corridor, self.market)
        plan["data_is_sample"] = self.market.mid.sample
        self._log("plan_tuition", actor, "compare_tuition", {"amount_cny": str(amount_cny), "deadline": deadline.isoformat(),
                                                              "best": plan["best_quote_id"], "status": plan["status"]})
        return plan

    def plan_living(self, actor: Actor, need_cny: Decimal, bridge_cny: Decimal = Decimal(0),
                    reserved_card_tx: int = 0, days_available: int = 30) -> dict:
        self._require(actor, "plan_living")
        usage = self.bank.card_usage()
        req = LivingRequest(
            need_cny=D(need_cny), bridge_cny=D(bridge_cny), card_spent_bdt=usage.bdt_charged, card_tx_used=usage.tx_count,
            reserved_card_tx=reserved_card_tx,
            living_remitted_usd=self.bank.living_remitted_usd.get(self.bank.month, Decimal(0)),
            days_available=days_available,
        )
        plan = plan_living(req, self.corridor, self.market).to_dict()
        plan["data_is_sample"] = self.market.mid.sample
        self._log("plan_living", actor, "plan_living", {"need_cny": str(need_cny), "feasible": plan["feasible"],
                                                        "savings_vs_all_atm_bdt": plan["savings_vs_all_atm_bdt"]})
        return plan

    def check_message(self, actor: Actor, text: str) -> dict:
        self._require(actor, "check_message")
        flags = [f.to_dict() for f in scan_text(text)]
        self._log("message_checked", actor, "check_message", {"flags": [f["category"] for f in flags], "length": len(text)})
        return {"flags": flags, "high_risk": any(f["severity"] == "high" for f in flags)}

    # ---- drafts (L1) ------------------------------------------------------
    def create_draft(self, actor: Actor, kind: str, amount_cny: Decimal, payee_id: str, quote_id: str | None = None,
                     memo: str = "", origin_message: str | None = None, withdrawals: list[Decimal] | None = None) -> dict:
        self._require(actor, "create_draft")
        amount = D(amount_cny)
        if amount <= 0:
            raise ValueError("amount must be positive")
        mid = self.market.mid.bdt_per_cny
        rate = None
        if kind in ("tt_tuition", "tt_living"):
            quote = self.market.quote(quote_id) if quote_id else min(
                self.market.quotes, key=lambda q: tt_cost(amount, q, mid).total_bdt)
            quote_id, rate = quote.quote_id, quote.bdt_per_cny
            total = tt_cost(amount, quote, mid).total_bdt  # computed by the engine, never by the LLM
            payer, spec = Actor.PARENT, DraftSpec("parent_bd", [], "tuition" if kind == "tt_tuition" else "living", origin_message)
        elif kind == "atm_plan":
            ws = [D(w) for w in (withdrawals or [])]
            if not ws or sum(ws, Decimal(0)) != amount:
                raise ValueError("atm_plan needs withdrawals that add up to the amount")
            total = atm_cost(ws, self.corridor, mid).total_bdt
            payer, payee_id = Actor.STUDENT, "student_cash_self"
            spec = DraftSpec("student_bd_card", ws, "living_cash", origin_message)
        else:
            raise ValueError(f"unknown draft kind '{kind}'")

        draft = Draft(
            id=self._id("draft"), kind=kind, payer=payer, amount_cny=amount, total_bdt=q2(total),
            payee_id=payee_id, quote_id=quote_id, rate_bdt_per_cny=rate, memo=memo, created_at=self.now,
            expires_at=self.now + timedelta(minutes=self.corridor.i("quote_max_age_minutes")), created_by=actor,
        )
        checks = run_draft_checks(draft, self._ctx(origin_message))
        draft.checks = [c.to_dict() for c in checks]
        draft.status = "blocked" if is_blocked(checks) else "draft"
        self.drafts[draft.id], self.specs[draft.id], self.tokens[draft.id] = draft, spec, []
        self._log("draft_created", actor, "create_draft", {
            "draft_id": draft.id, "kind": kind, "amount_cny": str(amount), "total_bdt": str(draft.total_bdt),
            "payee": payee_id, "status": draft.status,
            "failed_checks": [c.id for c in checks if not c.passed],
        })
        return self.draft_view(draft.id)

    def draft_view(self, draft_id: str) -> dict:
        d = self.drafts[draft_id]
        needed = required_approvers(d, self.corridor.v("two_person_threshold_bdt"))
        have = sorted({t["approver"] for t in self.tokens[draft_id]})
        return {
            **d.binding_fields(), "status": d.status, "checks": d.checks, "created_by": d.created_by.value,
            "required_approvers": sorted(a.value for a in needed), "approved_by": have,
            "withdrawals": [str(w) for w in self.specs[draft_id].withdrawals],
            "payee_name": self.bank.payees[d.payee_id].name if d.payee_id in self.bank.payees else "Unknown payee",
        }

    # ---- approvals and execution (L2) -------------------------------------
    def approve(self, actor: Actor, draft_id: str) -> dict:
        if actor == Actor.AGENT:
            self._log("permission_denied", actor, "execute_draft", {"draft_id": draft_id, "reason": "agent cannot approve"})
            raise PermissionError("the agent can never approve a payment")
        d = self.drafts[draft_id]
        if d.status in ("blocked", "executed"):
            raise ValueError(f"draft is {d.status} and cannot be approved")
        token = self.approvals.issue(d, actor, self.now)
        self.tokens[draft_id] = [t for t in self.tokens[draft_id] if t["approver"] != actor.value] + [token]
        decision = self.approvals.verify(d, self.tokens[draft_id], self.now, self.corridor.v("two_person_threshold_bdt"))
        if decision.allowed:
            d.status = "approved"
        self._log("draft_approved", actor, "execute_draft", {
            "draft_id": draft_id, "approver": actor.value, "fully_approved": decision.allowed,
            "missing": decision.missing_approvers, "draft_hash": d.hash()[:16],
        })
        return self.draft_view(draft_id)

    def execute(self, actor: Actor, draft_id: str) -> dict:
        self._require(actor, "execute_draft")
        d = self.drafts[draft_id]
        spec = self.specs[draft_id]
        if d.status == "executed":
            raise ValueError("draft already executed")
        checks = run_draft_checks(d, self._ctx(spec.origin_message))  # re-check at execution time
        if is_blocked(checks):
            d.status, d.checks = "blocked", [c.to_dict() for c in checks]
            self._log("execution_blocked", actor, "execute_draft", {"draft_id": draft_id,
                      "failed_checks": [c.id for c in checks if not c.passed and c.severity == "block"]})
            raise PermissionError("blocked by compliance checks: " + ", ".join(c.id for c in checks if not c.passed and c.severity == "block"))
        decision = self.approvals.verify(d, self.tokens[draft_id], self.now, self.corridor.v("two_person_threshold_bdt"))
        if not decision.allowed:
            self._log("execution_denied", actor, "execute_draft", {"draft_id": draft_id, **decision.to_dict()})
            raise PermissionError(decision.reason + (f": {', '.join(decision.missing_approvers)}" if decision.missing_approvers else ""))
        result = self._run(d, spec, actor.value, Level.EXECUTE.name)
        self.approvals.consume(self.tokens[draft_id])
        d.status = "executed"
        return {"draft": self.draft_view(draft_id), "bank_event": result}

    def _run(self, d: Draft, spec: DraftSpec, actor: str, level: str) -> dict:
        if d.kind in ("tt_tuition", "tt_living"):
            return self.bank.execute_tt(d.id, spec.from_account, d.payee_id, d.amount_cny, d.total_bdt, actor, level, spec.purpose)
        return self.bank.execute_atm_withdrawals(d.id, spec.from_account, "student_cash", spec.withdrawals, d.total_bdt, actor, level)

    # ---- mandates (L3) ----------------------------------------------------
    def create_mandate(self, actor: Actor, payee_id: str, max_bdt_per_payment: Decimal, max_bdt_per_period: Decimal,
                       period_days: int, valid_days: int) -> dict:
        if actor == Actor.AGENT:
            raise PermissionError("only a user can create a mandate")
        if payee_id not in self.bank.payees or not self.bank.payees[payee_id].verified:
            raise ValueError("mandates are only allowed for verified payees")
        m = Mandate(self._id("mandate"), actor, payee_id, D(max_bdt_per_payment), D(max_bdt_per_period), period_days,
                    self.now + timedelta(days=valid_days))
        self.mandates[m.id] = m
        self._log("mandate_created", actor, "execute_under_mandate", {"mandate_id": m.id, "payee": payee_id,
                  "max_per_payment_bdt": str(m.max_bdt_per_payment), "max_per_period_bdt": str(m.max_bdt_per_period),
                  "period_days": period_days, "expires_at": m.expires_at.isoformat()})
        return self._mandate_view(m)

    def revoke_mandate(self, actor: Actor, mandate_id: str) -> dict:
        if actor == Actor.AGENT:
            raise PermissionError("only a user can revoke a mandate")
        m = self.mandates[mandate_id]
        m.revoked = True
        self._log("mandate_revoked", actor, "execute_under_mandate", {"mandate_id": mandate_id})
        return self._mandate_view(m)

    def execute_under_mandate(self, actor: Actor, draft_id: str, mandate_id: str) -> dict:
        self._require(actor, "execute_under_mandate")
        d, spec, m = self.drafts[draft_id], self.specs[draft_id], self.mandates[mandate_id]
        checks = run_draft_checks(d, self._ctx(spec.origin_message))
        decision = check_mandate(m, d, self.now)
        if is_blocked(checks) or not decision.allowed or d.status == "executed":
            reason = decision.reason if not decision.allowed else ("already executed" if d.status == "executed" else "blocked by compliance checks")
            self._log("mandate_execution_denied", actor, "execute_under_mandate", {"draft_id": draft_id, "mandate_id": mandate_id, "reason": reason})
            raise PermissionError(reason)
        result = self._run(d, spec, actor.value, Level.MANDATE.name)
        m.spent.append((self.now, d.total_bdt))
        d.status = "executed"
        return {"draft": self.draft_view(draft_id), "bank_event": result, "mandate": self._mandate_view(m)}

    def _mandate_view(self, m: Mandate) -> dict:
        return {"id": m.id, "payee_id": m.payee_id, "max_bdt_per_payment": str(m.max_bdt_per_payment),
                "max_bdt_per_period": str(m.max_bdt_per_period), "period_days": m.period_days,
                "expires_at": m.expires_at.isoformat(), "revoked": m.revoked,
                "spent_in_period_bdt": str(q2(m.spent_in_period(self.now)))}

    # ---- overview ---------------------------------------------------------
    def timeline(self) -> dict:
        p, today = self.profile, self.now.date()
        transfer_days = self.corridor.i("bd_tt_transfer_days")
        buffer_days = self.corridor.i("tuition_buffer_days")
        send_by = p["tuition_deadline"] - timedelta(days=transfer_days + buffer_days)
        usage = self.bank.card_usage()
        warn = self.corridor.i("bd_endorsement_warn_days")
        items = [
            {"type": "tuition_due", "title": "Tuition payment", "amount_cny": str(p["tuition_invoice_cny"]),
             "due": p["tuition_deadline"].isoformat(), "send_by": send_by.isoformat(), "days_to_send_by": (send_by - today).days},
            {"type": "endorsement_expiry", "title": "Card endorsement expires", "due": p["endorsement_expiry"].isoformat(),
             "days_left": (p["endorsement_expiry"] - today).days, "warn": (p["endorsement_expiry"] - today).days <= warn},
            {"type": "student_file_renewal", "title": "Student File renewal", "due": p["student_file_expiry"].isoformat(),
             "days_left": (p["student_file_expiry"] - today).days, "warn": (p["student_file_expiry"] - today).days <= warn},
            {"type": "living_money", "title": "Monthly living money", "amount_cny": str(p["monthly_living_cny"])},
        ]
        return {
            "today": today.isoformat(),
            "items": sorted(items, key=lambda i: i.get("due", "9999")),
            "card_usage": {"month": usage.month, "tx_used": usage.tx_count,
                           "tx_cap": self.corridor.i("bd_student_card_tx_cap_per_month"),
                           "bdt_used": str(q2(usage.bdt_charged)),
                           "bdt_cap": str(self.corridor.v("bd_student_card_cap_bdt_per_month"))},
            "data_is_sample": self.market.mid.sample,
        }
