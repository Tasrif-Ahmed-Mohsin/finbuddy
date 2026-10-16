"""Application service: the single place where drafts are created, approved and executed.

Every path re-runs compliance checks and permission checks server-side, and writes the audit log.
The API (main.py) and, later, the agent orchestrator both go through this class; neither can
bypass it.
"""
from __future__ import annotations

import hmac
import os
import secrets
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta
from decimal import ROUND_FLOOR, Decimal
from pathlib import Path

from app.agent.autopilot import Autopilot
from app.agent.chat import ChatAgent
from app.agent.mandate_compiler import MandatePolicy, MandateProposal, compile_mandate
from app.agent.explain import Translator
from app.agent.llm import DeepSeekClient
from app.audit.log import AuditLog
from app.config import Settings, load_settings
from app.corridors.loader import load_corridor
from app.engines.cost import atm_cost, tt_cost
from app.engines.cost_truth import field_payment_truth
from app.emergency import SafetyCheck, fastest_money, guide, render_plan
from app.engines.earnings import (CATEGORY_KIND, CATEGORY_LABELS, EVERY, KINDS, SUGGESTED_PCT, IncomeSource, SavingsRule,
                                  ShieldRelease, categorize, compile_savings_rule, income_schedule, monthly_income, paydays,
                                  shield_share, taka_lens, wants_allowance_week, work_checks)
from app.engines.hundi import compare as hundi_compare
from app.engines.hundi import default_planned
from app.engines.rate_watch import rate_watch
from app.engines.stress import dollar_crisis, stress_test, what_if
from app.engines.year_plan import (Policy, Saving, Situation, _per_withdrawal_cap, load_calendar, plan_year, project,
                                   runs_out_on, simulate, spending_pace, topup_decision)
from app.engines.living_planner import ATM_NOTE, LivingRequest, best_quote_for, plan_living
from app.documents import read_document as read_document_photo
from app.engines.tuition_planner import TuitionRequest, plan_tuition
from app.inbox.service import Inbox
from app.integrations.whatsapp import WhatsAppNotifier, mask, normalise_number
from app.fx import FxProvider
from app.bank_rates import BankRateStore
from app.market import BankQuote, Market, build_market, load_quote_config, student_file_fees
from app.money import D, ceil_div, q2
from app.notify import Feed, cny, draft_summaries, num, role_name
from app.passport import issue as issue_passport_doc
from app.passport import verify as verify_passport_doc
from app.renewal import RenewalCase, plan_renewal
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
from app.security.scam import has_high_risk, scan_text

DEMO_START = datetime(2026, 10, 12, 9, 0)


@dataclass
class DraftSpec:
    from_account: str
    withdrawals: list[Decimal]
    purpose: str
    origin_message: str | None
    deadline: date | None = None  # tuition: the university deadline the payment must arrive by


class AppState:
    def __init__(self, audit_path: Path | None = None, start: datetime = DEMO_START,
                 llm: DeepSeekClient | None = None, settings: Settings | None = None):
        self.settings = settings or load_settings()
        self.llm = llm
        self.corridor = load_corridor("bd_cn")
        self.fx = FxProvider()  # real mid-market rate (live → saved history → fixture in tests)
        self.quote_cfg = load_quote_config()
        self.bank_rates = BankRateStore()  # banks' own published daily rate sheets (saved + live)
        self.real_quotes: list[BankQuote] = []
        self._stress_cache: tuple | None = None
        self.audit = AuditLog(audit_path)
        # The audit file persists across restarts but sandbox state (drafts, ids) does not:
        # anything that interprets the log (e.g. the payment passport) only reads this session.
        self.session_start_seq = len(self.audit.entries)
        self.bank = seed_demo_bank(self.corridor, self.audit, start, self.market.mid.cny_per_usd)
        self.bank.payees["student_cash_self"] = Payee(
            "student_cash_self", "Your own cash (ATM withdrawal)", "-", "-", "CNY", True, "Self", "student_cash"
        )
        self.calendar = load_calendar()  # bank days in both countries (sending in BD, crediting in CN)
        self.bank.calendar = self.calendar
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
            "home_bank": "your bank",
            # Interview #1 follow-up: both parent and student handle money; the student lives in China, and
            # renewing the card endorsement needs the student in person at the bank (passport).
            "student_location": "CN",
        }
        self.bank.daily_spend_cny = self.policy.daily_spend_cny
        self.proposals: dict[str, MandateProposal] = {}
        self.execution_auth: dict[str, dict] = {}  # draft id -> who/what authorised the payment (receipts)
        self.feed = Feed()
        self.safety_checks: dict[str, SafetyCheck] = {}
        # WhatsApp alerts for the family: notifications only, to the family's own number, mode set by the server env.
        self.whatsapp = WhatsAppNotifier.from_settings(self.settings)
        self.profile["parent_whatsapp"] = None
        self.profile["parent_lang"] = "bn"
        if self.settings.whatsapp_demo_to:
            try:
                self.profile["parent_whatsapp"] = normalise_number(self.settings.whatsapp_demo_to)
            except ValueError:
                pass
        self._wa_batch: list | None = None  # collects notes while simulated time is fast-forwarded
        self.feed.listeners.append(self._on_note)
        self.renewals: dict[str, RenewalCase] = {}
        # Payment passports (credit building). The signing key should come from the environment in production.
        env_secret = os.environ.get("SATHI_PASSPORT_SECRET")
        self.passport_secret = env_secret.encode() if env_secret else secrets.token_bytes(32)
        self.passports: dict[str, dict] = {}
        self.revoked_passports: set[str] = set()
        # Earn & Save: the student's own money abroad (stipend / approved campus job) and the Shield.
        self.income_sources: dict[str, IncomeSource] = {}
        self.savings_rules: dict[str, SavingsRule] = {}  # proposals and rules, by id
        self.savings_rule_id: str | None = None  # the active rule
        self.savings_terms_id: str | None = None  # the last rule that was ever active: its terms keep covering the Shield
        self.shield_releases: dict[str, ShieldRelease] = {}
        self._crisis_cache: dict | None = None
        self._n = 0
        self.inbox = Inbox(self)
        self.agent = ChatAgent(self)
        self.autopilot = Autopilot(self)
        self.translator = Translator(llm)

    # ---- utilities --------------------------------------------------------
    @property
    def now(self) -> datetime:
        return self.bank.clock

    @property
    def market(self) -> Market:
        return build_market(self.fx.latest(), self.quote_cfg, self.real_quotes, self.bank_rates)

    @property
    def estimates(self) -> bool:
        """True while any figure relies on estimated bank quotes or fixture rates."""
        m = self.market
        return m.mid.sample or m.quotes_estimated

    @property
    def data_quality(self) -> dict:
        m = self.market
        return {"mid": self.fx.status, "mid_as_of": m.mid.as_of, "mid_source": m.mid.source,
                "bdt_per_cny": str(round(m.mid.bdt_per_cny, 4)), "bank_quotes": m.quality,
                "quotes": [{"bank": q.bank, "basis": q.basis, "as_of": q.as_of, "fees_assumed": q.fees_assumed}
                           for q in m.quotes]}

    def bank_prices(self) -> dict:
        """Where every bank price comes from: published sheets and fee schedules, real payments, estimates."""
        m = self.market
        principal = Decimal(100000)
        return {
            "quotes": [{"quote_id": q.quote_id, "bank": q.bank, "basis": q.basis, "bdt_per_cny": str(q.bdt_per_cny),
                        "markup_pct": str(q.markup_pct), "as_of": q.as_of, "rate_source": q.source,
                        "fees": q.fees.to_dict() if q.fees else None, "fees_assumed": q.fees_assumed,
                        "fee_example": {"for_bdt": str(principal), "total_bdt": str(q2(q.fee_total(principal))),
                                        "lines": [{"label": lbl, "bdt": str(q2(a))} for lbl, a in q.fee_lines(principal)]}}
                       for q in m.quotes],
            "student_file_fees": student_file_fees(self.quote_cfg.get("fees", {})),
            "published_history": [{"date": r.date, "bank_id": r.bank_id, "cny_tt_selling": str(r.cny_tt_selling),
                                   "cny_bank_mid": str(r.cny_bank_mid)} for r in self.bank_rates.history("ebl", 400)],
            "rate_watch": rate_watch(self.bank_rates.rates, self.fx.history, "ebl", self.now.date()),
            "notes": m.notes,
            "quality": m.quality,
            "fees_reviewed": self.quote_cfg.get("fees", {}).get("reviewed"),
        }

    @property
    def student_card(self):
        return self.bank.cards[self.profile["student_card_last4"]]

    @property
    def policy(self) -> Policy:
        return Policy.from_corridor(self.corridor, self.profile["monthly_living_cny"])

    @property
    def planning_policy(self) -> Policy:
        """The plan, at the student's real spending pace when that is faster (same rule as the year plan)."""
        pol = self.policy
        pace = spending_pace(pol.daily_spend_cny, self.bank.spend_log)
        return pol if pace == pol.daily_spend_cny else replace(pol, daily_spend_cny=pace)

    def card_usable(self, d: date) -> bool:
        """The Bangladeshi card works abroad only while it is active AND the endorsement is valid."""
        return self.student_card.status == "active" and d <= self.profile["endorsement_expiry"]

    def student_money(self) -> tuple[Decimal, list[tuple[date, Decimal]]]:
        """The student's money in China now, and living-money transfers on the way (arrival day, amount)."""
        transit = sorted((t.arrives_at.date(), t.amount) for t in self.bank.pending if t.to_account_id == "student_cn")
        return self.bank.student_cny(), transit

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
            card_status=self.student_card.status,
        )

    # ---- read-only (L0) ---------------------------------------------------
    def plan_tuition(self, actor: Actor, amount_cny: Decimal, deadline: date, current_quote_id: str | None = None) -> dict:
        self._require(actor, "compare_tuition")
        send_by = deadline - timedelta(days=self.corridor.i("bd_tt_transfer_days") + self.corridor.i("tuition_buffer_days"))
        horizon = (send_by - self.now.date()).days
        fx = self.fx.range(horizon) if horizon >= 1 else None  # "how far could the rate move if we wait?"
        plan = plan_tuition(TuitionRequest(D(amount_cny), deadline, self.now.date(), current_quote_id), self.corridor,
                            self.market, fx)
        if fx is not None and plan["wait_risk"] is not None:
            plan["wait_risk"]["backtest"] = self.fx.backtest(min(horizon, 30))
        plan["data_is_sample"] = self.estimates
        plan["data_quality"] = self.data_quality
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
        plan["data_is_sample"] = self.estimates
        plan["data_quality"] = self.data_quality
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
            payer, spec = Actor.PARENT, DraftSpec("parent_bd", [], "tuition" if kind == "tt_tuition" else "living", origin_message,
                                                  self.profile["tuition_deadline"] if kind == "tt_tuition" else None)
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

    def cancel_draft(self, actor: Actor, draft_id: str, reason: str = "") -> dict:
        """Drop a prepared payment. Its approvals stop working at once (their nonces are consumed)."""
        self._require(actor, "cancel_draft")
        d = self.drafts[draft_id]
        if d.status == "executed":
            raise ValueError("this payment was already sent; it cannot be cancelled here")
        if d.status != "cancelled":
            d.status = "cancelled"
            self.approvals.consume(self.tokens[draft_id])
            self.tokens[draft_id] = []
            self._log("draft_cancelled", actor, "cancel_draft", {"draft_id": draft_id, "reason": reason[:80]})
        return self.draft_view(draft_id)

    def draft_view(self, draft_id: str) -> dict:
        d = self.drafts[draft_id]
        needed = required_approvers(d, self.corridor.v("two_person_threshold_bdt"))
        have = sorted({t["approver"] for t in self.tokens[draft_id]})
        return {
            **d.binding_fields(), "status": d.status, "checks": d.checks, "created_by": d.created_by.value,
            "required_approvers": sorted(a.value for a in needed), "approved_by": have,
            "withdrawals": [str(w) for w in self.specs[draft_id].withdrawals],
            "payee_name": self.bank.payees[d.payee_id].name if d.payee_id in self.bank.payees else "Unknown payee",
            "summary": draft_summaries(d, self.bank.payees.get(d.payee_id), self.specs[draft_id].withdrawals),
            "draft_hash": d.hash(),
        }

    # ---- approvals and execution (L2) -------------------------------------
    def approve(self, actor: Actor, draft_id: str) -> dict:
        if actor == Actor.AGENT:
            self._log("permission_denied", actor, "execute_draft", {"draft_id": draft_id, "reason": "agent cannot approve"})
            raise PermissionError("the agent can never approve a payment")
        d = self.drafts[draft_id]
        if d.status in ("blocked", "executed", "cancelled"):
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
        if d.status in ("executed", "cancelled"):
            raise ValueError(f"draft is {d.status}")
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
        self.execution_auth[draft_id] = {"type": "approvals", "level": "EXECUTE", "executed_by": actor.value,
                                         "approved_by": sorted(t["approver"] for t in self.tokens[draft_id]),
                                         "draft_hash": d.hash()}
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
        if actor != Actor.PARENT:  # mandated transfers are paid from the parent's account
            raise PermissionError("only the parent, who pays, can create a mandate")
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
        if m.auto_topup:
            self.feed.add(self.now, "both", "info", "mandate_revoked", {}, {"screen": "family"})
        return self._mandate_view(m)

    def execute_under_mandate(self, actor: Actor, draft_id: str, mandate_id: str) -> dict:
        self._require(actor, "execute_under_mandate")
        d, spec, m = self.drafts[draft_id], self.specs[draft_id], self.mandates[mandate_id]
        checks = run_draft_checks(d, self._ctx(spec.origin_message))
        decision = check_mandate(m, d, self.now)
        if is_blocked(checks) or not decision.allowed or d.status in ("executed", "cancelled"):
            reason = decision.reason if not decision.allowed else (
                f"draft is {d.status}" if d.status in ("executed", "cancelled") else "blocked by compliance checks")
            self._log("mandate_execution_denied", actor, "execute_under_mandate", {"draft_id": draft_id, "mandate_id": mandate_id, "reason": reason})
            raise PermissionError(reason)
        result = self._run(d, spec, actor.value, Level.MANDATE.name)
        m.spent.append((self.now, d.total_bdt))
        d.status = "executed"
        self.execution_auth[draft_id] = {"type": "mandate", "level": "MANDATE", "executed_by": actor.value,
                                         "mandate_id": m.id, "signed_by": list(m.signed_by) or [m.created_by.value],
                                         "proposal_hash": m.proposal_hash, "draft_hash": d.hash()}
        return {"draft": self.draft_view(draft_id), "bank_event": result, "mandate": self._mandate_view(m)}

    def _mandate_view(self, m: Mandate) -> dict:
        spent = m.spent_in_period(self.now)
        prop = self.proposals.get(m.proposal_id) if m.proposal_id else None
        return {"id": m.id, "payee_id": m.payee_id, "max_bdt_per_payment": str(m.max_bdt_per_payment),
                "max_bdt_per_period": str(m.max_bdt_per_period), "period": m.period, "period_days": m.period_days,
                "expires_at": m.expires_at.isoformat(), "revoked": m.revoked,
                "active": not m.revoked and self.now <= m.expires_at,
                "spent_in_period_bdt": str(q2(spent)),
                "left_in_period_bdt": str(q2(max(m.max_bdt_per_period - spent, Decimal(0)))),
                "payments": len(m.spent), "kinds": list(m.kinds), "auto_topup": m.auto_topup, "signed_by": list(m.signed_by),
                "proposal_id": m.proposal_id, "proposal_hash": m.proposal_hash,
                "summary": prop.summary() if prop else None}

    def mandates_view(self) -> list[dict]:
        return [self._mandate_view(m) for m in reversed(list(self.mandates.values()))]

    # ---- family mandates from the parent's own words (L3) ---------------------------------------
    def _mandate_policy(self) -> MandatePolicy:
        payee = self.bank.payees["student_own_cn"]
        # Bangladesh's living-money limit (USD/month) in taka, with ~3% room for the bank's fee and rate.
        cap = self.corridor.v("bd_living_remit_cap_usd_per_month") * self.market.mid.bdt_per_usd * Decimal("1.03")
        return MandatePolicy("student_own_cn", f"{payee.bank} {payee.account_masked}",
                             (cap / 1000).quantize(Decimal(1), rounding=ROUND_FLOOR) * 1000,
                             self.corridor.v("two_person_threshold_bdt"), self.profile["student_file_expiry"])

    def propose_mandate(self, actor: Actor, text: str, lang: str = "en") -> dict:
        """Turn a standing instruction ("up to ৳1,20,000 a month") into a proposal. Nothing is active yet."""
        self._require(actor, "propose_mandate")
        prop = compile_mandate(self._id("proposal"), text, lang, self.now, actor.value, self._mandate_policy(), self.llm)
        flags = scan_text(text)
        if has_high_risk(flags):
            prop.errors.append("This text contains scam or prompt-injection signals ("
                               + ", ".join(sorted({f.category.replace("_", " ") for f in flags}))
                               + "), so Sathi will not turn it into a mandate.")
            prop.status = "needs_changes"
        self.proposals[prop.id] = prop
        self._log("mandate_proposed", actor, "propose_mandate", {
            "proposal_id": prop.id, "parser": prop.parser, "text_length": len(prop.text), "status": prop.status,
            "max_per_payment_bdt": str(prop.max_bdt_per_payment), "max_per_period_bdt": str(prop.max_bdt_per_period),
            "period_days": prop.period_days, "valid_until": prop.valid_until.isoformat(),
            "required_signers": list(prop.required_signers), "errors": len(prop.errors), "hash": prop.hash()[:16]})
        return prop.to_dict()

    def sign_mandate(self, actor: Actor, proposal_id: str, proposal_hash: str) -> dict:
        """A user signs EXACTLY the proposal they read (its hash). Once everyone required has signed, it is active."""
        self._require(actor, "sign_mandate")
        if actor == Actor.AGENT:
            raise PermissionError("the agent can never sign a mandate")
        prop = self.proposals[proposal_id]
        if prop.status != "proposed":
            raise ValueError(f"this proposal is {prop.status.replace('_', ' ')} and cannot be signed")
        if actor.value not in prop.required_signers:
            raise PermissionError(f"the {actor.value} does not sign this mandate")
        if not hmac.compare_digest(str(proposal_hash), prop.hash()):
            self._log("mandate_sign_denied", actor, "sign_mandate", {"proposal_id": proposal_id, "reason": "hash mismatch"})
            raise PermissionError("the mandate is not the one you read; open it again before signing")
        if self.now - prop.created_at > timedelta(days=2):
            prop.status = "superseded"
            raise ValueError("this proposal is more than 2 days old; write the instruction again")
        prop.signatures[actor.value] = self.now.isoformat()
        self._log("mandate_signed", actor, "sign_mandate", {"proposal_id": proposal_id, "hash": prop.hash()[:16]})
        missing = [x for x in prop.required_signers if x not in prop.signatures]
        if missing:
            summary = prop.summary()
            params = {}
            for lang in ("en", "bn", "zh"):
                params[f"signed_{lang}"] = role_name(actor.value, lang)
                params[f"missing_{lang}"] = role_name(missing[0], lang)
                params[f"summary_{lang}"] = summary[lang]
            self.feed.add(self.now, missing[0], "needs_you", "mandate_needs_signature", params,
                          {"screen": "family", "proposal_id": prop.id})
            return prop.to_dict()
        for old in self.mandates.values():  # one family mandate at a time
            if old.auto_topup and not old.revoked:
                old.revoked = True
                self._log("mandate_superseded", actor, "sign_mandate", {"mandate_id": old.id, "by": prop.id})
        m = Mandate(self._id("mandate"), Actor.PARENT, prop.payee_id, prop.max_bdt_per_payment, prop.max_bdt_per_period,
                    prop.period_days, datetime.combine(prop.valid_until, time(23, 59)), kinds=prop.kinds, auto_topup=True,
                    signed_by=tuple(sorted(prop.signatures)), proposal_id=prop.id, proposal_hash=prop.hash(),
                    period=prop.period)
        self.mandates[m.id] = m
        prop.status, prop.mandate_id = "active", m.id
        self._log("mandate_created", actor, "execute_under_mandate", {
            "mandate_id": m.id, "payee": m.payee_id, "max_per_payment_bdt": str(m.max_bdt_per_payment),
            "max_per_period_bdt": str(m.max_bdt_per_period), "period": m.period, "period_days": m.period_days,
            "expires_at": m.expires_at.isoformat(), "kinds": list(m.kinds), "auto_topup": True,
            "signed_by": list(m.signed_by), "proposal_hash": m.proposal_hash})
        summary = prop.summary()
        self.feed.add(self.now, "both", "info", "mandate_active", {f"summary_{lang}": summary[lang] for lang in ("en", "bn", "zh")},
                      {"screen": "family", "mandate_id": m.id})
        actions = self.autopilot.tick()  # act right away if the money is already low
        return {**prop.to_dict(), "mandate": self._mandate_view(m), "autopilot": actions}

    # ---- year plan, runway, feed, receipts ---------------------------------------------------
    def _year_situation(self) -> Situation:
        p, today = self.profile, self.now.date()
        bal, transit = self.student_money()
        send_by = p["tuition_deadline"] - timedelta(days=self.corridor.i("bd_tt_transfer_days") + self.corridor.i("tuition_buffer_days"))
        end = min(p["student_file_expiry"], today + timedelta(days=260))
        usage = self.bank.card_usage()
        return Situation(today, end, bal, transit, p["endorsement_expiry"], self.student_card.status == "active",
                         p["student_file_expiry"], usage.tx_count, usage.bdt_charged,
                         (send_by, p["tuition_deadline"], p["tuition_invoice_cny"]))

    def stress_test(self, actor: Actor, runs: int = 200) -> dict:
        """Is the year plan robust? The same year re-run with messy spending, late transfers and moved holidays."""
        self._require(actor, "plan_year")
        sit, market = self._year_situation(), self.market
        student_money = self._may_see_student_money(actor)
        key = (sit.start, sit.balance_cny, tuple(sit.in_transit), sit.card_active, market.mid.as_of,
               self.profile["monthly_living_cny"], runs, self._earnings_key(), student_money)
        if self._stress_cache is None or self._stress_cache[0] != key:
            out = stress_test(sit, self.policy, self.calendar, self.corridor, market, runs=runs)
            out["what_if"] = what_if(sit, self.policy, self.calendar, self.corridor, market,
                                     lambda mid: build_market(mid, self.quote_cfg, self.real_quotes, self.bank_rates))
            crisis = self._crisis(sit, with_student_money=student_money)
            w, med = crisis["worst"], crisis["median_stuck"]
            sathi = simulate("sathi", sit, self.policy, self.calendar, self.corridor, market,
                             blocked=(date.fromisoformat(w["from"]), date.fromisoformat(w["to"])))
            # One line in the what-if list: the TYPICAL crisis (median over every start week). The worst start is
            # reported next to it and in full in `crisis` (chosen against Sathi, so it is the honest worst case).
            out["what_if"].append({"key": "dollar_crisis", "weeks": crisis["weeks"], "basis": "median_start",
                                   "stuck_days_sathi": med["sathi"], "stuck_days_today": med["today"],
                                   "stuck_days_sathi_shield": med["sathi_shield"],
                                   "worst": {"from": w["from"], "stuck_today": w["stuck_today"], "stuck_sathi": w["stuck_sathi"],
                                             "stuck_sathi_shield": w["stuck_sathi_shield"]},
                                   "shield_needed_cny": w["shield_needed_cny"],
                                   "family_pays_bdt": str(q2(sum((c.total_bdt for c in sathi.costs), Decimal(0)))),
                                   "change_bdt": "0.00", "overhead_pct": sathi.cost_summary()["overhead_pct"],
                                   "overhead_pct_today": sathi.cost_summary()["overhead_pct"],
                                   "transfers": len(sathi.transfers), "atm_bridges": len(sathi.atm)})
            out["crisis"] = crisis
            out["period"] = {"from": sit.start.isoformat(), "to": sit.end.isoformat()}
            self._stress_cache = (key, out)
        out = self._stress_cache[1]
        self._log("stress_tested", actor, "plan_year", {"runs": runs, "median_stuck_sathi": str(out["stuck_days"]["sathi"]["median"]),
                                                         "worst_stuck_sathi": out["stuck_days"]["sathi"]["worst"]})
        return out

    def year_plan(self, actor: Actor) -> dict:
        self._require(actor, "plan_year")
        p, today = self.profile, self.now.date()
        sit = self._year_situation()
        end = sit.end
        plan = plan_year(sit, self.policy, self.calendar, self.corridor, self.market)
        plan["cost_truth"] = [field_payment_truth(fp, self.fx.history, self.bank_rates.rates)
                              for fp in self.quote_cfg.get("field_payments", [])]
        plan["student_file_fees"] = student_file_fees(self.quote_cfg.get("fees", {}))
        plan["calendar"] = {"reviewed": self.calendar.reviewed,
                            "closures": [c.to_dict() for c in self.calendar.closures_in(today, end)]}
        plan["assumptions"] = [{"name": k, **self.corridor.meta(k)} for k in (
            "bd_tt_transfer_days", "endorsement_renewal_in_person", "living_safety_days", "living_target_days",
            "baseline_reorder_days", "atm_low_cash_days", "bd_card_atm_fixed_fee_bdt", "bd_card_non_usd_factor_pct",
            "bd_living_remit_cap_usd_per_month")]
        m = self.autopilot.active_mandate()
        plan["mandate"] = self._mandate_view(m) if m else None
        plan["shield"] = self._year_shield(sit) if self._may_see_student_money(actor) else None
        if plan["shield"] is not None and actor == Actor.PARENT:
            plan["shield"].pop("income_month_cny", None)  # the student's pay stays private even when the Shield is shared
        plan["data_is_sample"], plan["data_quality"] = self.estimates, self.data_quality
        self._log("year_planned", actor, "plan_year",
                  {k: plan["headline"][k] for k in ("stuck_days_today", "stuck_days_sathi", "saved_bdt")})
        return plan

    def runway(self) -> dict:
        pol, today = self.planning_policy, self.now.date()
        bal, transit = self.student_money()
        m = self.autopilot.active_mandate()
        dec = topup_decision(today, bal, transit, pol, self.calendar)
        out = runs_out_on(bal, transit, today, pol.daily_spend_cny)
        return {"balance_cny": str(q2(bal)), "daily_spend_cny": str(pol.daily_spend_cny),
                "days_left": int(bal // pol.daily_spend_cny) if pol.daily_spend_cny > 0 else None,
                "runs_out_on": out.isoformat() if out else None,
                "in_transit": [{"arrives": d.isoformat(), "amount_cny": str(q2(a))} for d, a in transit],
                "card_works_until": self.profile["endorsement_expiry"].isoformat(), "card_usable": self.card_usable(today),
                "send_today": dec.to_dict() if dec else None, "mandate": self._mandate_view(m) if m else None,
                "stuck_days": len(self.bank.stuck_days),
                "bank_open_today": {"BD": self.calendar.is_open("BD", today), "CN": self.calendar.is_open("CN", today)}}

    def family_feed(self, actor: Actor, lang: str = "en") -> dict:
        who = actor.value
        needs: list[dict] = []
        for d in reversed(list(self.drafts.values())):
            if d.status not in ("draft", "approved") or self.now > d.expires_at:
                continue
            v = self.draft_view(d.id)
            item = {"draft_id": d.id, "kind": d.kind, "amount_cny": str(d.amount_cny), "total_bdt": str(d.total_bdt),
                    "payee_name": v["payee_name"]}
            if who in v["required_approvers"] and who not in v["approved_by"]:
                needs.append({"type": "approve_draft", **item})
            elif d.status == "approved" and who == d.payer.value:
                needs.append({"type": "send_draft", **item})
        if who == "student":
            needs += [{"type": "confirm_safe", "check_id": c.id, "asked_at": c.asked_at.isoformat()}
                      for c in self.safety_checks.values() if c.status == "open"]
        for prop in reversed(list(self.proposals.values())):
            if prop.status == "proposed" and prop.signatures and who in prop.required_signers and who not in prop.signatures:
                needs.append({"type": "sign_mandate", "proposal_id": prop.id, "summary": prop.summary().get(lang, "")})
        if who == "parent":  # only when the student chose to lock their Shield with the family's approval
            needs += [{"type": "approve_release", "release_id": r.id, "amount_cny": str(q2(r.amount_cny)),
                       "available_at": r.available_at.isoformat()}
                      for r in self.shield_releases.values() if r.status == "waiting" and r.needs_family
                      and r.family_approved_at is None]
        return {"now": self.now.isoformat(), "runway": self.runway(), "needs_you": needs,
                "notes": self.feed.for_actor(who, lang), "shield": self.shield_summary(actor)}

    def receipts(self) -> list[dict]:
        """Proof for every executed payment: what was checked, who or what authorised it, and its log entries."""
        entries = [e for e in self.audit.entries if e["seq"] > self.session_start_seq]
        out = []
        for d in self.drafts.values():
            if d.status != "executed":
                continue
            sent = next((e for e in entries if e["event"] in ("transfer_sent", "atm_withdrawals")
                         and e["data"].get("draft_id") == d.id), None)
            landed = next((e for e in entries if e["event"] == "transfer_arrived" and e["data"].get("draft_id") == d.id), None)
            out.append({"draft": self.draft_view(d.id), "authority": self.execution_auth.get(d.id),
                        "sent": ({k: sent[k] for k in ("seq", "hash", "sim_time", "permission_level")}
                                 | {"arrives_at": sent["data"].get("arrives_at")}) if sent else None,
                        "landed": {k: landed[k] for k in ("seq", "hash", "sim_time")} if landed else None})
        return list(reversed(out))

    # ---- emergency mode ----------------------------------------------------------------------
    def _fastest(self) -> dict:
        today = self.now.date()
        bal, transit = self.student_money()
        per_wd, _ = _per_withdrawal_cap(self.corridor, self.market.mid.cny_per_usd)
        return fastest_money(today, bal, transit, self.planning_policy, self.calendar, self.card_usable(today), per_wd,
                             self.shield_cny - self._shield_waiting())

    def emergency(self, actor: Actor, lang: str = "en") -> dict:
        self._require(actor, "emergency_plan")
        plan = self._fastest()
        return {"plan": plan, "text": render_plan(plan, lang, self.calendar.names()),
                "guides": {k: guide(k, lang) for k in ("scam_call", "family_call", "card_lost")},
                "card": {"last4": self.profile["student_card_last4"], "status": self.student_card.status},
                "safety_checks": [c.to_dict() for c in reversed(list(self.safety_checks.values()))][:5]}

    def emergency_no_money(self, actor: Actor, lang: str = "en") -> dict:
        """The student is (almost) out of money: act inside the mandate if it allows, else prepare an urgent
        transfer for the parent to approve and alert the family. Never more than that."""
        self._require(actor, "ask_family_for_money")
        sent = self.autopilot.tick()  # the mandate may already allow it (same rule as every day)
        plan = self._fastest()
        shield_used = None
        if Decimal(plan["from_shield_cny"]) > 0 and (actor == Actor.STUDENT or self._savings_rule() is not None):
            # The student's own Shield first: instant, free, already in China. Only to the student's own spending account,
            # and only because the numbers show the money cannot cover the days until a transfer lands.
            shield_used = self._release_now(Decimal(plan["from_shield_cny"]), "emergency", actor)
            plan = self._fastest()
        today, pol = self.now.date(), self.planning_policy
        lands = date.fromisoformat(plan["urgent_lands_on"])
        bal, transit = self.student_money()
        at_landing = project(bal, transit, today, lands - timedelta(days=1), pol.daily_spend_cny)
        amount = max(pol.min_transfer_cny, ATM_NOTE * ceil_div(
            pol.daily_spend_cny * (pol.target_days + pol.safety_days) - max(at_landing, Decimal(0)), ATM_NOTE))
        draft = None
        if not any(a.get("type") in ("autopilot_sent", "sent") for a in sent) and not transit:
            open_living = next((d for d in self.drafts.values() if d.kind == "tt_living" and d.status in ("draft", "approved")
                                and self.now <= d.expires_at), None)
            draft = self.draft_view(open_living.id) if open_living else self.create_draft(
                actor, "tt_living", amount, "student_own_cn", memo="Emergency: urgent living money")
            covered = ({"en": "the student's own Shield covers the days until then.",
                        "bn": "শিক্ষার্থীর নিজের সুরক্ষা তহবিল ততদিনের খরচ চালাবে।",
                        "zh": "学生自己的应急储备可以支撑到那时。"} if shield_used else
                       {"en": "the money in China lasts until then.", "bn": "চীনে থাকা টাকায় ততদিন চলবে।",
                        "zh": "在中国的钱可以支撑到那时。"})
            texts = {lg: next((o["text"] for o in render_plan(plan, lg, self.calendar.names())["options"]
                               if o["kind"] in ("card_atm", "local_bridge")), covered[lg]) for lg in ("en", "bn", "zh")}
            self.feed.add(self.now, "both", "needs_you", "emergency_no_money",
                          {"balance_cny": str(q2(bal)), "amount_cny": draft["amount_cny"], "lands_date": plan["urgent_lands_on"],
                           "bridge_en": texts["en"], "bridge_bn": texts["bn"], "bridge_zh": texts["zh"]},
                          {"screen": "draft", "draft_id": draft["id"]}, once=f"emergency:{today.isoformat()}")
        self._log("emergency_no_money", actor, "ask_family_for_money",
                  {"balance_cny": plan["balance_cny"], "draft_id": draft["id"] if draft else None,
                   "autopilot": [a.get("type") for a in sent],
                   "shield_used_cny": shield_used["amount_cny"] if shield_used else None})
        return {**self.emergency(actor, lang), "draft": draft, "autopilot": sent, "shield_used": shield_used}

    def emergency_card_lost(self, actor: Actor, lang: str = "en") -> dict:
        last4 = self.profile["student_card_last4"]
        if self.student_card.status == "active":
            self.freeze_card(actor, last4, "emergency: card lost or stolen")
        self._log("emergency_card_lost", actor, "freeze_card", {"card": last4, "status": self.student_card.status})
        return self.emergency(actor, lang)

    def ask_safety_check(self, actor: Actor) -> dict:
        self._require(actor, "ask_safety_check")
        if actor != Actor.PARENT:
            raise PermissionError("only the parent asks the student whether they are safe")
        check = next((c for c in self.safety_checks.values() if c.status == "open"), None)
        if check is None:
            check = SafetyCheck(self._id("safe"), actor.value, self.now)
            self.safety_checks[check.id] = check
            self.feed.add(self.now, "student", "needs_you", "safety_check_asked", {}, {"screen": "emergency"})
        self._log("safety_check_asked", actor, "ask_safety_check", {"check_id": check.id})
        return check.to_dict()

    def confirm_safe(self, actor: Actor, check_id: str | None = None) -> dict:
        """The student says they are safe: answers the parent's open check, or tells the family first (for example
        right after a fake-police call, before the scammers phone the parents)."""
        self._require(actor, "confirm_safe")
        if actor != Actor.STUDENT:
            raise PermissionError("only the student can say they are safe")
        if check_id is None:
            check = next((c for c in self.safety_checks.values() if c.status == "open"), None)
            if check is None:
                check = SafetyCheck(self._id("safe"), actor.value, self.now)
                self.safety_checks[check.id] = check
        else:
            check = self.safety_checks[check_id]
        if check.status != "open":
            raise ValueError("this check was already answered")
        check.status, check.answered_at = "safe", self.now
        self.feed.add(self.now, "parent", "info", "safety_confirmed", {"time": self.now.strftime("%Y-%m-%d %H:%M")},
                      {"screen": "emergency"})
        self._log("safety_confirmed", actor, "confirm_safe", {"check_id": check.id})
        return check.to_dict()

    def surprise_expense(self, actor: Actor, amount_cny: Decimal, memo: str) -> dict:
        if actor != Actor.STUDENT:
            raise PermissionError("only the student spends the student's money")
        amount = D(amount_cny)
        if not Decimal(0) < amount <= Decimal(20000):
            raise ValueError("amount must be between ¥0 and ¥20,000")
        return self.bank.surprise_expense(amount, memo, actor.value)

    # ---- WhatsApp alerts ----------------------------------------------------------------------
    WA_KINDS = ("did", "needs_you", "warning")
    WA_ALWAYS = ("safety_confirmed",)
    WA_FOOTER = {"bn": "অনুমোদন শুধু সাথী অ্যাপে, আঙুলের ছাপ দিয়ে। এই মেসেজের উত্তরে কিছু অনুমোদন হয় না, আর সাথী কখনো কোড বা পিন চায় না।",
                 "en": "Approvals happen only in the Sathi app, with your fingerprint. Replying here approves nothing, and Sathi never asks for codes or PINs.",
                 "zh": "只能在 Sathi 应用中用指纹批准。回复此消息不会批准任何操作，Sathi 也从不索要验证码或密码。"}

    def _on_note(self, note) -> None:
        if not self.whatsapp.enabled or not self.profile.get("parent_whatsapp"):
            return
        if note.audience not in ("parent", "both") or (note.kind not in self.WA_KINDS and note.key not in self.WA_ALWAYS):
            return
        if self._wa_batch is not None:
            self._wa_batch.append(note)
            return
        lang = self.profile.get("parent_lang", "bn")
        r = note.render(lang)
        brand = "সাথী" if lang == "bn" else "Sathi"
        self._wa_send(f"{brand} · {r['title']}\n\n{r['body']}", "note", note.key)

    def _wa_send(self, text: str, kind: str, key: str):
        lang = self.profile.get("parent_lang", "bn")
        to = self.profile["parent_whatsapp"]
        entry = self.whatsapp.send(to, f"{text}\n\n{self.WA_FOOTER.get(lang, self.WA_FOOTER['en'])}", kind, key, self.now)
        self.bank.log("whatsapp_notified", "system", "SYSTEM", {"kind": kind, "key": key, "mode": entry.mode,
                      "status": entry.status, "to": mask(to)})  # never the text or the token
        return entry

    def _wa_digest(self, notes: list, days: int) -> None:
        lang = self.profile.get("parent_lang", "bn")
        rendered = [n.render(lang) for n in notes]
        did = sum(1 for n in notes if n.kind == "did")
        need = sum(1 for n in notes if n.kind == "needs_you")
        warn = sum(1 for n in notes if n.kind == "warning")
        tr = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
        if lang == "bn":
            head = (f"সাথী · গত {str(days).translate(tr)} দিনের সারসংক্ষেপ: {str(did).translate(tr)}টি কাজ করেছে, "
                    f"{str(need).translate(tr)}টিতে আপনার অনুমোদন দরকার, {str(warn).translate(tr)}টি সতর্কতা।")
        else:
            head = f"Sathi · last {days} days: {did} done, {need} need you, {warn} warnings."
        lines = "\n".join(f"• {r['title']}" for r in rendered[-6:])
        self._wa_send(f"{head}\n{lines}", "digest", f"digest:{days}d")

    def whatsapp_status(self) -> dict:
        return {**self.whatsapp.status(), "recipient": mask(self.profile.get("parent_whatsapp")),
                "lang": self.profile.get("parent_lang", "bn"),
                "rules": ["Notifications only: nothing can be approved by replying on WhatsApp.",
                          "Only to the family's own number, set by a user (never by the agent).",
                          "Only the server can switch real sending on (WHATSAPP_MODE=live)."]}

    def set_whatsapp_recipient(self, actor: Actor, number: str | None, lang: str = "bn") -> dict:
        if actor == Actor.AGENT:
            raise PermissionError("only the student or parent can choose who gets WhatsApp alerts")
        self.profile["parent_whatsapp"] = normalise_number(number) if number else None
        self.profile["parent_lang"] = lang if lang in ("bn", "en", "zh") else "bn"
        self._log("whatsapp_recipient_set", actor, None, {"to": mask(self.profile["parent_whatsapp"]),
                                                          "lang": self.profile["parent_lang"]})
        return self.whatsapp_status()

    def whatsapp_test(self, actor: Actor) -> dict:
        if actor == Actor.AGENT:
            raise PermissionError("only the student or parent can send a WhatsApp test")
        if not self.whatsapp.enabled:
            raise ValueError("WhatsApp is off on this server (set WHATSAPP_MODE=dry_run or live)")
        if not self.profile.get("parent_whatsapp"):
            raise ValueError("add the family's WhatsApp number first")
        lang = self.profile.get("parent_lang", "bn")
        text = {"bn": "সাথী · টেস্ট মেসেজ। এখান থেকে আপনি জানতে পারবেন সাথী কী পাঠিয়েছে আর কোথায় আপনার অনুমোদন দরকার।",
                "en": "Sathi · test message. You will get updates here on what Sathi sent and what needs your approval.",
                "zh": "Sathi · 测试消息。你会在这里收到 Sathi 汇款和需要你批准的通知。"}[lang]
        return self._wa_send(text, "test", "test").to_dict()

    # ---- simulated time ----------------------------------------------------------------------
    def advance(self, actor: Actor, days: int) -> dict:
        """Fast-forward the sandbox one day at a time: the student spends, transfers land, the autopilot runs."""
        if days < 0 or days > 365:
            raise ValueError("days must be between 0 and 365")
        events, actions = [], []
        spent_total, stuck_n = Decimal(0), 0
        self._wa_batch = [] if days > 1 else None  # a fast-forward sends one summary, not one message per note
        for _ in range(days):
            covered = self._shield_cover()  # the student's Shield, if today's money is not enough (savings rule)
            if covered:
                actions.append({"type": "shield_cover", "amount_cny": covered["amount_cny"]})
            spent, stuck = self.bank.spend_day()
            spent_total += spent
            if stuck:
                stuck_n += 1
                today = self.now.date()
                if (today - timedelta(days=1)).isoformat() not in self.bank.stuck_days:  # first day of a stuck spell
                    on = self.autopilot.active_mandate() is not None
                    self.feed.add(self.now, "both", "warning", "stuck", {
                        "date_date": today.isoformat(),
                        "fix_en": "Check the payments waiting for approval." if on
                        else "Sign a family mandate so Sathi sends living money before it runs out.",
                        "fix_bn": "অনুমোদনের অপেক্ষায় থাকা পেমেন্টগুলো দেখুন।" if on
                        else "পারিবারিক ম্যান্ডেটে সই করুন, যাতে টাকা শেষ হওয়ার আগেই সাথী মাসিক খরচ পাঠায়।",
                        "fix_zh": "请查看待批准的付款。" if on else "签署家庭授权，让 Sathi 在钱用完之前汇生活费。",
                    }, {"screen": "family"})
            arrived = self.bank.next_day(actor.value)
            for e in arrived:
                if e["data"]["to"] == "student_cn":
                    self.feed.add(self.now, "both", "info", "transfer_arrived", {
                        "amount_cny": e["data"]["amount_cny"], "balance_cny": str(q2(self.bank.student_cny()))})
            events += arrived
            actions += self._pay_incomes()  # pay days: the student's own money lands, the savings rule keeps its share
            actions += self._process_releases()  # Shield releases whose waiting time is over
            self._daily_notes()
            self._weekly_savings_notes()
            actions += self.autopilot.tick()
        batch, self._wa_batch = self._wa_batch, None
        if batch:
            self._wa_digest(batch, days)
        self.bank.log("clock_advanced", actor.value, "SYSTEM", {"days": days, "now": self.now.isoformat(),
                      "student_spent_cny": str(q2(spent_total)), "stuck_days": stuck_n})
        return {"now": self.now.isoformat(), "events": events, "autopilot": actions, "stuck_days": stuck_n}

    def _daily_notes(self) -> None:
        expiry = self.profile["endorsement_expiry"]
        if 0 <= (expiry - self.now.date()).days <= 21:
            on = self.autopilot.active_mandate() is not None
            plan = {
                "en": "Sathi already sends living money by bank transfer to the Chinese account, so the card is not needed."
                if on else "Sign a family mandate before then, so living money comes by bank transfer instead of the card.",
                "bn": "সাথী ইতিমধ্যে ব্যাংক ট্রান্সফারে চীনের অ্যাকাউন্টে মাসিক খরচ পাঠাচ্ছে, তাই কার্ড লাগবে না।"
                if on else "তার আগেই পারিবারিক ম্যান্ডেটে সই করুন, যাতে কার্ডের বদলে ব্যাংক ট্রান্সফারে মাসিক খরচ আসে।",
                "zh": "Sathi 已通过银行汇款把生活费汇到中国账户，不再需要这张卡。"
                if on else "请在此之前签署家庭授权，让生活费改为银行汇款，而不是用卡取现。",
            }
            self.feed.add(self.now, "both", "info" if on else "warning", "card_stops",
                          {"card_date": expiry.isoformat(), "plan_en": plan["en"], "plan_bn": plan["bn"], "plan_zh": plan["zh"]},
                          {"screen": "renewal", "item": "endorsement_expiry"}, once=f"card_stops:{expiry.isoformat()}")

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
            "data_is_sample": self.estimates,
            "data_quality": self.data_quality,
            "card": self.student_card.to_dict(),
        }

    # ---- market data -----------------------------------------------------------
    def add_real_quote(self, actor: Actor, bank: str, bdt_per_cny: Decimal, fixed_fee_bdt: Decimal) -> dict:
        if actor == Actor.AGENT:
            raise PermissionError("only a user can enter a real bank quote")
        rate, fee = D(bdt_per_cny), D(fixed_fee_bdt)
        mid = self.market.mid.bdt_per_cny
        if not (mid * Decimal("0.9") <= rate <= mid * Decimal("1.2")) or fee < 0:
            raise ValueError(f"that rate looks wrong: the market rate is about {round(mid, 2)} BDT per CNY")
        q = BankQuote(f"real-{len(self.real_quotes) + 1}", bank[:40], rate, fee, self.now.date().isoformat(),
                      f"Real quote entered by {actor.value}", False, basis="user_quote")
        self.real_quotes.append(q)
        self._log("real_quote_added", actor, None, {"quote_id": q.quote_id, "bank": q.bank, "bdt_per_cny": str(rate),
                                                    "fixed_fee_bdt": str(fee)})
        return {"quote_id": q.quote_id, "bank": q.bank, "bdt_per_cny": str(rate), "fixed_fee_bdt": str(fee)}

    def fx_overview(self) -> dict:
        m = self.market
        horizons = {}
        for h in (7, 14, 30):
            rr = self.fx.range(h)
            horizons[str(h)] = {"range": rr.to_dict() if rr else None, "backtest": self.fx.backtest(h)}
        return {"mid": {"bdt_per_usd": str(m.mid.bdt_per_usd), "cny_per_usd": str(m.mid.cny_per_usd),
                        "bdt_per_cny": str(round(m.mid.bdt_per_cny, 4)), "as_of": m.mid.as_of, "source": m.mid.source},
                "status": self.fx.status, "history_days": len(self.fx.history),
                "change_pct": {"90d": self.fx.change_pct(90), "365d": self.fx.change_pct(365)},
                "horizons": horizons,
                "method": "Empirical ranges of past h-day moves (window 250 days), centred on today's rate. "
                          "No direction is predicted; the backtest shows how often past ranges were right.",
                "caveat": "Daily data can lag official Bangladesh Bank changes by 1–2 days."}

    def fx_history(self, days: int = 180) -> list[dict]:
        pts = self.fx.history[-max(2, min(days, 1000)):]
        step = max(1, -(-len(pts) // 180))  # ceil: at most ~180 points for a phone chart
        out = [{"date": p.date, "bdt_per_cny": round(p.bdt_per_cny, 4)} for p in pts[::step]]
        if pts and out[-1]["date"] != pts[-1].date:
            out.append({"date": pts[-1].date, "bdt_per_cny": round(pts[-1].bdt_per_cny, 4)})
        return out

    # ---- renewals (T3) ------------------------------------------------------------
    def start_renewal(self, actor: Actor, item: str) -> dict:
        self._require(actor, "plan_renewal")
        existing = next((c for c in self.renewals.values() if c.item == item and c.status == "open"), None)
        if existing:
            return existing.to_dict(self.now.date())
        if item not in ("endorsement_expiry", "student_file_expiry"):
            raise ValueError(f"unknown renewal item '{item}'")
        case = plan_renewal(self._id("renewal"), item, self.profile[item], self.now.date(), self.corridor, self.profile)
        self.renewals[case.id] = case
        self._log("renewal_planned", actor, "plan_renewal", {"case_id": case.id, "item": item, "expiry": case.expiry.isoformat(),
                  "late": case.late, "steps": [(s.id, s.due.isoformat()) for s in case.steps]})
        return case.to_dict(self.now.date())

    def renewal_for(self, item: str) -> dict | None:
        case = next((c for c in reversed(list(self.renewals.values())) if c.item == item), None)
        return case.to_dict(self.now.date()) if case else None

    def update_renewal_step(self, actor: Actor, case_id: str, step_id: str, status: str) -> dict:
        self._require(actor, "update_renewal")
        if actor == Actor.AGENT:
            raise PermissionError("only the student or parent can mark renewal steps")
        if status not in ("todo", "done"):
            raise ValueError("status must be 'todo' or 'done'")
        case = self.renewals[case_id]
        step = next(s for s in case.steps if s.id == step_id)
        step.status = status
        self._log("renewal_step", actor, "update_renewal", {"case_id": case_id, "step": step_id, "status": status})
        return case.to_dict(self.now.date())

    def complete_renewal(self, actor: Actor, case_id: str, new_expiry: date) -> dict:
        self._require(actor, "update_renewal")
        if actor == Actor.AGENT:
            raise PermissionError("only the student or parent can confirm a renewal")
        case = self.renewals[case_id]
        if not (case.expiry < new_expiry <= case.expiry + timedelta(days=800)):
            raise ValueError("the new expiry must be after the old one (and within about two years)")
        case.new_expiry, case.status = new_expiry, "completed"
        for s in case.steps:
            s.status = "done"
        old = self.profile[case.item]
        self.profile[case.item] = new_expiry
        self._log("renewal_completed", actor, "update_renewal", {"case_id": case_id, "item": case.item,
                  "old_expiry": old.isoformat(), "new_expiry": new_expiry.isoformat()})
        return case.to_dict(self.now.date())

    # ---- photo document reader -----------------------------------------------------------
    def read_document(self, actor: Actor, image_base64: str, lang: str = "en") -> dict:
        self._require(actor, "read_document")
        if actor == Actor.AGENT:
            raise PermissionError("only the student or parent can upload a document")
        if self.llm is None:
            raise RuntimeError("reading photos needs the AI service, which is not available right now")
        result = read_document_photo(self.llm, image_base64, lang)
        self._log("document_read", actor, "read_document", {"doc_type": result["doc_type"], "amounts": len(result["amounts"]),
                  "amounts_dropped": result["amounts_dropped"], "deadlines": len(result["deadlines"]),
                  "flags": [f["category"] for f in result["flags"]], "stored_image": False})
        return result

    def apply_fee_notice(self, actor: Actor, amount_cny: Decimal, deadline: date) -> dict:
        self._require(actor, "apply_document")
        if actor == Actor.AGENT:
            raise PermissionError("only the student or parent can confirm a fee notice")
        amount = D(amount_cny)
        if amount <= 0 or amount > Decimal("1000000"):
            raise ValueError("that amount does not look like a tuition fee")
        if deadline < self.now.date():
            raise ValueError("the deadline is in the past")
        old = {"amount": str(self.profile["tuition_invoice_cny"]), "deadline": self.profile["tuition_deadline"].isoformat()}
        self.profile["tuition_invoice_cny"], self.profile["tuition_deadline"] = amount, deadline
        self._log("fee_notice_applied", actor, "apply_document", {"old": old, "new": {"amount": str(amount), "deadline": deadline.isoformat()}})
        return {"tuition_invoice_cny": str(amount), "tuition_deadline": deadline.isoformat()}

    # ---- payment passport (credit building) ------------------------------------------
    def issue_passport(self, actor: Actor, include_amounts: bool) -> dict:
        self._require(actor, "share_passport")
        if actor == Actor.AGENT:
            raise PermissionError("only the student or parent can share a payment passport")
        doc = issue_passport_doc(self, self.passport_secret, self._id("passport"), include_amounts)
        self.passports[doc["id"]] = doc
        self._log("passport_issued", actor, "share_passport", {"passport_id": doc["id"], "entries": len(doc["entries"]),
                  "include_amounts": include_amounts, "valid_until": doc["valid_until"]})
        return doc

    def verify_passport(self, passport: dict) -> dict:
        return verify_passport_doc(self, self.passport_secret, passport, self.revoked_passports)

    def revoke_passport(self, actor: Actor, passport_id: str) -> dict:
        self._require(actor, "share_passport")
        if actor == Actor.AGENT:
            raise PermissionError("only the student or parent can revoke a payment passport")
        if passport_id not in self.passports:
            raise KeyError(passport_id)
        self.revoked_passports.add(passport_id)
        self._log("passport_revoked", actor, "share_passport", {"passport_id": passport_id})
        return {"id": passport_id, "revoked": True}

    # ---- card controls -----------------------------------------------------------
    def freeze_card(self, actor: Actor, last4: str, reason: str = "") -> dict:
        self._require(actor, "freeze_card")
        return self.bank.set_card_status(last4, "frozen", actor.value, "DRAFT", reason[:120] or None)

    def unfreeze_card(self, actor: Actor, last4: str) -> dict:
        self._require(actor, "unfreeze_card")
        if self.bank.cards[last4].status == "active":
            raise ValueError("card is already active")
        return self.bank.set_card_status(last4, "active", actor.value, "EXECUTE", "unfrozen by the cardholder's family")

    def report_card_lost(self, actor: Actor, last4: str) -> dict:
        self._require(actor, "report_card_lost")
        return self.bank.set_card_status(last4, "lost", actor.value, "EXECUTE", "reported lost or stolen")

    # ---- Earn & Save: the student's own money abroad (Interview #2, docs N-11 … N-14) -------------
    # The student's income (stipend or approved campus job) is already in yuan: it never meets Bangladesh's dollar
    # shortage, the bank's fixed fees or hundi. A savings rule the STUDENT signs keeps a share of each income in the
    # Shield, a pocket of their own Chinese account that covers the days money from home cannot arrive. Money only ever
    # moves between the student's own pockets; the parent sees the Shield level (if the student shares it), never
    # purchases; the agent can propose a rule and act inside it, never sign it or take money out for anything else.
    SHIELD_EVENTS = ("shield_saved", "shield_cover", "shield_released", "savings_rule_active", "savings_rule_revoked",
                     "shield_release_requested", "shield_release_cancelled", "shield_release_approved")
    DEFAULT_INCOME_LABEL = {"stipend": "Scholarship stipend", "work_study": "Campus job (approved work-study)",
                            "other": "Other income"}

    @property
    def shield_cny(self) -> Decimal:
        return self.bank.accounts["student_shield"].balance

    def _shield_waiting(self) -> Decimal:
        return sum((r.amount_cny for r in self.shield_releases.values() if r.status == "waiting"), Decimal(0))

    def _savings_rule(self) -> SavingsRule | None:
        r = self.savings_rules.get(self.savings_rule_id) if self.savings_rule_id else None
        if r is None or r.status != "active":
            return None
        if self.now.date() > r.valid_until:
            r.status, self.savings_rule_id = "expired", None
            self._log("savings_rule_expired", "system", None, {"rule_id": r.id})
            return None
        return r

    def _savings_terms(self) -> SavingsRule | None:
        """The terms covering money already in the Shield: the active rule, or the last one that was ever active."""
        return self._savings_rule() or (self.savings_rules.get(self.savings_terms_id) if self.savings_terms_id else None)

    def _shares_with_family(self) -> bool:
        t = self._savings_terms()
        return bool(t and t.share_with_family)

    def family_bdt_per_cny(self) -> Decimal:
        """What one yuan costs the family to send: the cheapest legal bank for a month of living money, fees included."""
        monthly = D(self.profile["monthly_living_cny"])
        _, cost = best_quote_for(monthly, self.market)
        return (cost.total_bdt / monthly).quantize(Decimal("0.0001"))

    def _default_shield_target(self) -> Decimal:
        return ATM_NOTE * ceil_div(self.policy.daily_spend_cny * self.corridor.i("shield_target_days"), ATM_NOTE)

    def _earnings_key(self) -> tuple:
        rule = self._savings_rule()
        return (tuple((s.id, s.amount_cny, s.every, s.pay_day, s.status) for s in self.income_sources.values()),
                (rule.id, rule.shield_pct, rule.target_cny) if rule else None, self.shield_cny)

    def _saving_for_plans(self) -> tuple[Saving | None, bool]:
        """The savings rule simulations use: the student's active rule, else Sathi's suggestion when there is income."""
        rule = self._savings_rule()
        if rule:
            return Saving(rule.shield_pct, rule.target_cny, self.shield_cny), False
        if any(s.status == "ok" for s in self.income_sources.values()):
            return Saving(SUGGESTED_PCT, self._default_shield_target(), self.shield_cny), True
        return None, False

    def _income_plan(self, sit: Situation) -> list[tuple[date, Decimal]]:
        return income_schedule(list(self.income_sources.values()), sit.start + timedelta(days=1), sit.end)

    def _may_see_student_money(self, actor: Actor) -> bool:
        """The student and Sathi (for the student) see it; the parent only if the student shares the Shield."""
        return actor != Actor.PARENT or self._shares_with_family()

    def _crisis(self, sit: Situation, weeks: int | None = None, with_student_money: bool = True) -> dict:
        weeks = weeks or self.corridor.i("crisis_weeks")
        saving, suggested = self._saving_for_plans() if with_student_money else (None, False)
        income = self._income_plan(sit) if with_student_money else None
        market = self.market
        key = (sit.start, sit.balance_cny, tuple(sit.in_transit), sit.card_active, market.mid.as_of,
               self.profile["monthly_living_cny"], weeks, self._earnings_key(), with_student_money)
        cache = self._crisis_cache or {}
        if key not in cache:
            out = dollar_crisis(sit, self.policy, self.calendar, self.corridor, market, income, saving, weeks)
            out["rule_is_suggestion"] = suggested
            out["student_money_shown"] = with_student_money
            cache = {k: v for k, v in cache.items() if k[:-1] == key[:-1]}  # keep only the other view of the same state
            cache[key] = out
            self._crisis_cache = cache
        return cache[key]

    def _year_shield(self, sit: Situation) -> dict:
        saving, suggested = self._saving_for_plans()
        out = {"income_month_cny": str(monthly_income(list(self.income_sources.values()))),
               "shield_cny": str(q2(self.shield_cny)), "rule_is_suggestion": suggested,
               "saving": {"pct": saving.pct, "target_cny": str(q2(saving.target))} if saving else None,
               "end_cny": None, "used_cny": None}
        if saving:
            res = simulate("sathi", sit, self.policy, self.calendar, self.corridor, self.market,
                           income=self._income_plan(sit), saving=saving)
            out.update(end_cny=str(q2(res.shield_end)), used_cny=str(q2(res.shield_used)), saved_cny=str(q2(res.shield_saved)))
        return out

    def _shield_projection(self, pct: int, target: Decimal) -> dict:
        """When the Shield reaches its target from planned income alone (no spending assumed from it)."""
        today, shield = self.now.date(), self.shield_cny
        points, reaches = [], None if self.shield_cny < target else today
        for d, amt in income_schedule(list(self.income_sources.values()), today + timedelta(days=1), today + timedelta(days=365)):
            shield += shield_share(amt, pct, shield, target)
            if len(points) < 12:
                points.append({"date": d.isoformat(), "shield_cny": str(q2(shield))})
            if reaches is None and shield >= target:
                reaches = d
        return {"pct": pct, "target_cny": str(q2(target)), "reaches_target_on": reaches.isoformat() if reaches else None,
                "points": points}

    def _wants_between(self, start: date, end: date, lang: str = "en") -> dict:
        rows = [(amt, cat, kind) for ts, amt, cat, kind in self.bank.wants_log if start <= ts.date() <= end]
        wants = sum((a for a, _, k in rows if k == "want"), Decimal(0))
        needs = sum((a for a, _, k in rows if k == "need"), Decimal(0))
        by_cat: dict[str, Decimal] = {}
        for a, c, k in rows:
            if k == "want":
                by_cat[c] = by_cat.get(c, Decimal(0)) + a
        return {"from": start.isoformat(), "to": end.isoformat(), "wants_cny": str(q2(wants)), "needs_cny": str(q2(needs)),
                "count": len(rows),
                "by_category": [{"category": c, "label": CATEGORY_LABELS[c][lang], "cny": str(q2(v))}
                                for c, v in sorted(by_cat.items(), key=lambda x: -x[1])]}

    def _wants_week_view(self, lang: str = "en") -> dict:
        """This week's wants through the taka lens, against what the student's own pay leaves for wants."""
        today = self.now.date()
        w = self._wants_between(today - timedelta(days=today.weekday()), today, lang)
        rule = self._savings_rule()
        allowance = wants_allowance_week(monthly_income(list(self.income_sources.values())), rule.shield_pct if rule else 0)
        spent = D(w["wants_cny"])
        over = max(spent - allowance, Decimal(0))
        rate, daily = self.family_bdt_per_cny(), self.policy.daily_spend_cny
        return {**w, "allowance_cny": str(allowance), "left_cny": str(q2(max(allowance - spent, Decimal(0)))),
                "over_cny": str(q2(over)), "lens": taka_lens(spent, rate, daily), "over_lens": taka_lens(over, rate, daily)}

    def _shield_history(self, limit: int = 12) -> list[dict]:
        rows = [e for e in self.audit.entries if e["seq"] > self.session_start_seq and e["event"] in self.SHIELD_EVENTS]
        return [{"seq": e["seq"], "hash": e["hash"][:12], "event": e["event"], "sim_time": e["sim_time"],
                 "actor": e["actor"], "level": e["permission_level"], "amount_cny": e["data"].get("amount_cny")}
                for e in rows[-limit:][::-1]]

    def shield_summary(self, actor: Actor) -> dict | None:
        """The Shield in one line for Today / the family feed: None for the parent when the student does not share it."""
        terms = self._savings_terms()
        if actor == Actor.PARENT and not self._shares_with_family():
            return None
        if terms is None and self.shield_cny == 0 and not self.income_sources:
            return None
        target = terms.target_cny if terms else self._default_shield_target()
        return {"balance_cny": str(q2(self.shield_cny)), "target_cny": str(q2(target)),
                "pct_of_target": int(min(self.shield_cny / target, Decimal(1)) * 100) if target > 0 else 0,
                "days_of_living": str((self.shield_cny / self.policy.daily_spend_cny).quantize(Decimal("0.1"))),
                "rule_on": self._savings_rule() is not None}

    PRIVATE_EVENTS = ("income_received", "income_source_added", "income_source_removed", "spending_logged")

    def visible_accounts(self, actor: Actor) -> list[dict]:
        """Sandbox accounts as this person may see them: the Shield is hidden from the parent unless shared."""
        hide = actor == Actor.PARENT and not self._shares_with_family()
        return [a.to_dict() for a in self.bank.accounts.values() if not (hide and a.id == "student_shield")]

    def audit_view(self, actor: Actor, entries: list[dict]) -> list[dict]:
        """The log as the parent may read it: the student's pay and purchases (and the Shield, unless shared) show as
        private. Hashes stay, so the chain is still checked on the server and every entry is still accounted for."""
        if actor != Actor.PARENT:
            return entries
        private = self.PRIVATE_EVENTS + (() if self._shares_with_family() else self.SHIELD_EVENTS + (
            "shield_cover", "savings_rule_proposed", "savings_rule_sign_denied", "savings_rule_superseded"))
        return [{**e, "data": {"private": True}} if e["event"] in private else e for e in entries]

    def savings_view(self, actor: Actor, lang: str = "en") -> dict:
        self._require(actor, "plan_savings")
        lang = lang if lang in ("en", "bn", "zh") else "en"
        today, rule, terms = self.now.date(), self._savings_rule(), self._savings_terms()
        target = terms.target_cny if terms else self._default_shield_target()
        share = actor != Actor.PARENT or self._shares_with_family()
        waiting = [r.to_dict() for r in reversed(list(self.shield_releases.values())) if r.status == "waiting"]
        base = {
            "now": self.now.isoformat(), "role": actor.value, "shared_with_family": self._shares_with_family(),
            "shield": ({"balance_cny": str(q2(self.shield_cny)), "target_cny": str(q2(target)),
                        "free_cny": str(q2(self.shield_cny - self._shield_waiting())),
                        "pct_of_target": int(min(self.shield_cny / target, Decimal(1)) * 100) if target > 0 else 0,
                        "days_of_living": str((self.shield_cny / self.policy.daily_spend_cny).quantize(Decimal("0.1"))),
                        "full": self.shield_cny >= target} if share else None),
            "rule": rule.to_dict() if rule else None,
            "terms": ({"rule_id": terms.id, "cooling_off_hours": terms.cooling_off_hours, "family_lock": terms.family_lock,
                       "share_with_family": terms.share_with_family, "status": terms.status} if terms else None),
            "history": self._shield_history() if share else [],
            "family_rate": {"bdt_per_cny": str(self.family_bdt_per_cny()),
                            "basis": "What ¥1 costs the family to send: the cheapest legal bank for a month of living "
                                     "money, fees included."},
        }
        if actor == Actor.PARENT:  # the Shield level and what needs the parent; never income or purchases
            base["releases"] = [r for r in waiting if r["needs_family"] and r["family_approved_at"] is None]
            return base
        sources = list(self.income_sources.values())
        planned = [(d, s) for s in sources if s.status == "ok"
                   for d in paydays(s, today + timedelta(days=1), today + timedelta(days=40))]
        nxt = min(planned, key=lambda x: x[0]) if planned else None
        proposal = next((p for p in reversed(list(self.savings_rules.values())) if p.status in ("proposed", "needs_changes")), None)
        suggested = None
        if rule is None:
            suggested = {"pct": SUGGESTED_PCT, "target_cny": str(q2(self._default_shield_target())),
                         "cooling_off_hours": self.corridor.i("shield_cooling_off_hours"),
                         "projection": self._shield_projection(SUGGESTED_PCT, self._default_shield_target())}
        return {**base, "releases": waiting,
                "income": {"sources": [s.to_dict() for s in sources], "monthly_cny": str(monthly_income(sources)),
                           "next_pay": {"date": nxt[0].isoformat(), "amount_cny": str(q2(nxt[1].amount_cny)),
                                        "label": nxt[1].label} if nxt else None},
                "wants": self._wants_week_view(lang),
                "projection": self._shield_projection(rule.shield_pct, rule.target_cny) if rule else None,
                "proposal": proposal.to_dict() if proposal else None, "suggested": suggested,
                "categories": [{"key": k, "label": v[lang], "kind": "want" if k in ("delivery", "eating_out", "shopping",
                                "fun", "travel", "other_want") else "need"} for k, v in CATEGORY_LABELS.items()],
                "work_rules": [{"name": k, **self.corridor.meta(k)} for k in (
                    "cn_work_permission_required", "cn_work_hours_week_term", "cn_illegal_work_fine_cny_min",
                    "cn_illegal_work_fine_cny_max")]}

    # -- income ----------------------------------------------------------------------------------------
    def add_income_source(self, actor: Actor, kind: str, label: str, amount_cny: Decimal, every: str = "month",
                          pay_day: int = 10, hours_per_week: Decimal | None = None, permission: bool = False) -> dict:
        self._require(actor, "add_income")
        if actor != Actor.STUDENT:
            raise PermissionError("only the student adds their own income")
        if kind not in KINDS:
            raise ValueError(f"kind must be one of {', '.join(KINDS)}")
        if every not in EVERY:
            raise ValueError("pay must come every month or every week")
        amount = D(amount_cny)
        if not Decimal(0) < amount <= Decimal(50000):
            raise ValueError("amount must be between ¥0 and ¥50,000 per pay")
        if every == "month" and not 1 <= pay_day <= 28:
            raise ValueError("a monthly pay day must be between 1 and 28")
        if every == "week" and not 0 <= pay_day <= 6:
            raise ValueError("a weekly pay day must be a weekday number from 0 (Monday) to 6")
        hours = D(hours_per_week) if hours_per_week is not None and kind == "work_study" else None
        if hours is not None and not Decimal(0) <= hours <= Decimal(60):
            raise ValueError("hours per week must be between 0 and 60")
        perm = bool(permission) if kind == "work_study" else True
        src = IncomeSource(self._id("income"), kind, (label or self.DEFAULT_INCOME_LABEL[kind]).strip()[:40], amount, every,
                           pay_day, hours, perm, self.now.date(), work_checks(kind, hours, perm, self.corridor))
        self.income_sources[src.id] = src
        self._log("income_source_added", actor, "add_income", {
            "source_id": src.id, "kind": kind, "amount_cny": str(q2(amount)), "every": every, "status": src.status,
            "failed_checks": [c["id"] for c in src.checks if not c["passed"]]})
        if src.status == "at_risk":
            self.feed.add(self.now, "student", "warning", "work_permission",
                          {"lo_cny": str(self.corridor.v("cn_illegal_work_fine_cny_min")),
                           "hi_cny": str(self.corridor.v("cn_illegal_work_fine_cny_max"))},
                          {"screen": "save"}, once=f"work_permission:{src.id}")
        return src.to_dict()

    def remove_income_source(self, actor: Actor, source_id: str) -> dict:
        self._require(actor, "add_income")
        if actor != Actor.STUDENT:
            raise PermissionError("only the student changes their own income")
        src = self.income_sources.pop(source_id)
        self._log("income_source_removed", actor, "add_income", {"source_id": src.id})
        return {"removed": src.id}

    def log_income(self, actor: Actor, amount_cny: Decimal, source_id: str | None = None) -> dict:
        """A pay or stipend arrived today. In the sandbox the bank credits it; in real life the bank alert shows it."""
        self._require(actor, "add_income")
        if actor != Actor.STUDENT:
            raise PermissionError("only the student logs their own income")
        amount = D(amount_cny)
        if not Decimal(0) < amount <= Decimal(50000):
            raise ValueError("amount must be between ¥0 and ¥50,000")
        src = self.income_sources[source_id] if source_id else None
        return self._income_arrived(src.id if src else None, src.kind if src else "other", amount, actor.value)

    def _income_arrived(self, source_id: str | None, kind: str, amount: Decimal, actor_label: str) -> dict:
        self.bank.credit_income(source_id, kind, amount, actor_label)
        saved = self._apply_savings_rule(amount)
        return {"type": "income", "source_id": source_id, "amount_cny": str(q2(amount)), "saved": saved,
                "balance_cny": str(q2(self.bank.student_cny())), "shield_cny": str(q2(self.shield_cny))}

    def _pay_incomes(self) -> list[dict]:
        """Sandbox pay days: approved income lands on its day (unauthorised work is never simulated)."""
        today = self.now.date()
        return [self._income_arrived(s.id, s.kind, s.amount_cny, "system") for s in list(self.income_sources.values())
                if s.status == "ok" and s.added_on < today and paydays(s, today, today)]

    def _apply_savings_rule(self, amount: Decimal) -> dict | None:
        """Pay yourself first: the agent moves the rule's share of an income into the Shield (L3, inside the rule)."""
        rule = self._savings_rule()
        if rule is None:
            return None
        keep = min(shield_share(amount, rule.shield_pct, self.shield_cny, rule.target_cny),
                   self.bank.accounts["student_cn"].balance)
        if keep <= 0:
            return None
        self._require(Actor.AGENT, "save_under_rule")
        self.bank.move_cny("student_cn", "student_shield", keep, Actor.AGENT.value, Level.MANDATE.name, "shield_saved",
                           {"rule_id": rule.id, "rule_hash": rule.hash()[:16], "income_cny": str(q2(amount)),
                            "pct": rule.shield_pct})
        monthly = monthly_income(list(self.income_sources.values()))
        free = amount - keep
        week = wants_allowance_week(monthly, rule.shield_pct) if monthly > 0 else q2(free * 7 / 30)
        self.feed.add(self.now, "student", "did", "income_saved",
                      {"saved_cny": str(keep), "amount_cny": str(q2(amount)), "shield_cny": str(q2(self.shield_cny)),
                       "target_cny": str(rule.target_cny), "free_cny": str(q2(free)), "week_cny": str(week)}, {"screen": "save"})
        if rule.share_with_family:
            self.feed.add(self.now, "parent", "info", "family_shield",
                          {"saved_cny": str(keep), "shield_cny": str(q2(self.shield_cny)), "target_cny": str(rule.target_cny)},
                          {"screen": "save"})
        if self.shield_cny >= rule.target_cny:
            self.feed.add(self.now, "both" if rule.share_with_family else "student", "info", "shield_full",
                          {"target_cny": str(rule.target_cny), "days_n": int(rule.target_cny // self.policy.daily_spend_cny)},
                          {"screen": "save"}, once=f"shield_full:{rule.id}")
        return {"saved_cny": str(q2(keep)), "shield_cny": str(q2(self.shield_cny)), "rule_id": rule.id}

    # -- spending (the taka lens) --------------------------------------------------------------------------
    def log_spending(self, actor: Actor, amount_cny: Decimal, merchant: str = "", kind: str | None = None,
                     category: str | None = None, lang: str = "en") -> dict:
        self._require(actor, "log_spending")
        if actor != Actor.STUDENT:
            raise PermissionError("only the student logs their own spending")
        amount = D(amount_cny)
        if not Decimal(0) < amount <= Decimal(20000):
            raise ValueError("amount must be between ¥0 and ¥20,000")
        if category is not None and category not in CATEGORY_KIND:
            raise ValueError("unknown category")
        if kind is not None and kind not in ("need", "want"):
            raise ValueError("kind must be 'need' or 'want'")
        guess = categorize(merchant)
        if category is not None:
            kind = CATEGORY_KIND[category]
        elif kind is not None:
            category = guess[0] if guess and guess[1] == kind else f"other_{kind}"
        else:
            category, kind = guess or ("other_want", "want")
        res = self.bank.spend_logged(amount, category, kind, actor.value)
        lang = lang if lang in ("en", "bn", "zh") else "en"
        return {**res, "category": category, "kind": kind, "label": CATEGORY_LABELS[category][lang],
                "lens": taka_lens(amount, self.family_bdt_per_cny(), self.policy.daily_spend_cny),
                "week": self._wants_week_view(lang)}

    def _weekly_savings_notes(self) -> None:
        """Monday morning: last week's wants through the taka lens (student) and what was saved (family, if shared)."""
        today = self.now.date()
        if today.weekday() != 0:
            return
        start, end = today - timedelta(days=7), today - timedelta(days=1)
        w = self._wants_between(start, end)
        saved = sum((D(e["data"]["amount_cny"]) for e in self.audit.entries if e["seq"] > self.session_start_seq
                     and e["event"] == "shield_saved" and e["sim_time"] and start.isoformat() <= e["sim_time"][:10] <= end.isoformat()),
                    Decimal(0))
        wants = D(w["wants_cny"])
        if wants == 0 and saved == 0:
            return
        terms, rule = self._savings_terms(), self._savings_rule()
        target = terms.target_cny if terms else self._default_shield_target()
        lens = taka_lens(wants, self.family_bdt_per_cny(), self.policy.daily_spend_cny)
        over = max(wants - wants_allowance_week(monthly_income(list(self.income_sources.values())),
                                                rule.shield_pct if rule else 0), Decimal(0))
        o = cny(over, "en")
        over_t = ({"over_en": f" {o} of it was more than your own pay leaves for wants, so it came out of living money from home.",
                   "over_bn": f" এর মধ্যে {cny(over, 'bn')} আপনার নিজের আয়ের শখের অংশের বেশি, তাই তা দেশ থেকে আসা মাসিক খরচ থেকে গেছে।",
                   "over_zh": f"其中 {cny(over, 'zh')} 超出了你自己收入中可用于想要的部分，用的是家里寄来的生活费。"}
                  if over > 0 else {"over_en": "", "over_bn": "", "over_zh": ""})
        self.feed.add(self.now, "student", "info", "week_summary",
                      {"wants_cny": str(q2(wants)), "wants_bdt": lens["bdt"], "days_n": lens["days_of_living"],
                       "saved_cny": str(q2(saved)), "shield_cny": str(q2(self.shield_cny)), "target_cny": str(q2(target)),
                       **over_t}, {"screen": "save"}, once=f"week:{today.isoformat()}")
        if saved > 0 and self._shares_with_family():
            self.feed.add(self.now, "parent", "info", "family_week",
                          {"saved_cny": str(q2(saved)), "shield_cny": str(q2(self.shield_cny)), "target_cny": str(q2(target))},
                          {"screen": "save"}, once=f"family_week:{today.isoformat()}")

    # -- the savings rule (the student's own mandate) -------------------------------------------------------
    def propose_savings_rule(self, actor: Actor, text: str = "", lang: str = "en", pct: int | None = None,
                             target_cny: Decimal | None = None, cooling_off_hours: int | None = None,
                             family_lock: bool | None = None, share_with_family: bool = True) -> dict:
        """The student's words or form → a rule PROPOSAL. Nothing moves until the student signs its exact hash."""
        self._require(actor, "propose_savings_rule")
        if actor == Actor.PARENT:
            raise PermissionError("a savings rule is the student's own choice: only the student (or Sathi for them) writes it")
        rule = compile_savings_rule(self._id("saving"), self.now, actor.value, lang, self._default_shield_target(),
                                    self.corridor.i("shield_cooling_off_hours"), text, pct,
                                    D(target_cny) if target_cny is not None else None, cooling_off_hours, family_lock,
                                    share_with_family)
        flags = scan_text(text) if text else []
        if has_high_risk(flags):
            rule.errors.append("This text contains scam or prompt-injection signals ("
                               + ", ".join(sorted({f.category.replace("_", " ") for f in flags}))
                               + "), so Sathi will not turn it into a rule.")
            rule.status = "needs_changes"
        for old in self.savings_rules.values():  # one proposal at a time
            if old.status in ("proposed", "needs_changes"):
                old.status = "superseded"
        self.savings_rules[rule.id] = rule
        self._log("savings_rule_proposed", actor, "propose_savings_rule", {
            "rule_id": rule.id, "status": rule.status, "pct": rule.shield_pct, "target_cny": str(rule.target_cny),
            "cooling_off_hours": rule.cooling_off_hours, "family_lock": rule.family_lock,
            "share_with_family": rule.share_with_family, "errors": len(rule.errors), "hash": rule.hash()[:16]})
        out = rule.to_dict()
        out["projection"] = self._shield_projection(rule.shield_pct, rule.target_cny) if not rule.errors else None
        return out

    def sign_savings_rule(self, actor: Actor, rule_id: str, rule_hash: str) -> dict:
        self._require(actor, "sign_savings_rule")
        if actor != Actor.STUDENT:
            raise PermissionError("only the student signs their own savings rule")
        rule = self.savings_rules[rule_id]
        if rule.status != "proposed":
            raise ValueError(f"this rule is {rule.status.replace('_', ' ')} and cannot be signed")
        if not hmac.compare_digest(str(rule_hash), rule.hash()):
            self._log("savings_rule_sign_denied", actor, "sign_savings_rule", {"rule_id": rule_id, "reason": "hash mismatch"})
            raise PermissionError("the rule is not the one you read; open it again before signing")
        if self.now - rule.created_at > timedelta(days=2):
            rule.status = "superseded"
            raise ValueError("this proposal is more than 2 days old; write it again")
        old = self._savings_rule()
        if old is not None:
            old.status = "superseded"
            self._log("savings_rule_superseded", actor, "sign_savings_rule", {"rule_id": old.id, "by": rule.id})
        rule.signatures["student"] = self.now.isoformat()
        rule.status, rule.activated_at = "active", self.now
        self.savings_rule_id = self.savings_terms_id = rule.id
        self._log("savings_rule_active", actor, "sign_savings_rule", {
            "rule_id": rule.id, "pct": rule.shield_pct, "target_cny": str(rule.target_cny),
            "cooling_off_hours": rule.cooling_off_hours, "family_lock": rule.family_lock,
            "share_with_family": rule.share_with_family, "valid_until": rule.valid_until.isoformat(), "hash": rule.hash()})
        summary = rule.summary()
        self.feed.add(self.now, "both" if rule.share_with_family else "student", "info", "savings_rule_active",
                      {f"summary_{lg}": summary[lg] for lg in ("en", "bn", "zh")}, {"screen": "save"})
        out = rule.to_dict()
        out["projection"] = self._shield_projection(rule.shield_pct, rule.target_cny)
        return out

    def revoke_savings_rule(self, actor: Actor) -> dict:
        self._require(actor, "revoke_savings_rule")
        if actor != Actor.STUDENT:
            raise PermissionError("only the student can stop their savings rule")
        rule = self._savings_rule()
        if rule is None:
            raise ValueError("no savings rule is on")
        rule.status, self.savings_rule_id = "revoked", None  # the terms keep covering money already saved
        self._log("savings_rule_revoked", actor, "revoke_savings_rule", {"rule_id": rule.id})
        self.feed.add(self.now, "both" if rule.share_with_family else "student", "info", "savings_rule_revoked", {},
                      {"screen": "save"})
        return rule.to_dict()

    # -- taking money out of the Shield ------------------------------------------------------------------
    def _release_now(self, amount: Decimal, reason: str, actor: Actor) -> dict:
        """Move Shield money to the student's own spending account now (an emergency, or a release that may go now)."""
        amount = min(D(amount), self.shield_cny - self._shield_waiting())
        if amount <= 0:
            raise ValueError("there is no free money in the Shield")
        mover = actor if actor == Actor.STUDENT else Actor.AGENT  # only the student, or Sathi inside the student's rule
        if mover == Actor.AGENT:
            self._require(Actor.AGENT, "shield_emergency_cover")
        terms = self._savings_terms()
        rel = ShieldRelease(self._id("release"), amount, reason, actor.value, self.now, self.now, False, status="released",
                            released_at=self.now)
        self.shield_releases[rel.id] = rel
        event = "shield_cover" if reason == "emergency" else "shield_released"
        self.bank.move_cny("student_shield", "student_cn", amount, mover.value,
                           Level.MANDATE.name if mover == Actor.AGENT else Level.EXECUTE.name, event,
                           {"release_id": rel.id, "reason": reason, "rule_id": terms.id if terms else None,
                            "asked_by": actor.value})
        who = "both" if self._shares_with_family() else "student"
        if reason == "emergency":
            self.feed.add(self.now, who, "did", "shield_used",
                          {"amount_cny": str(q2(amount)), "shield_cny": str(q2(self.shield_cny))}, {"screen": "save"})
        else:
            self.feed.add(self.now, who, "info", "shield_released",
                          {"amount_cny": str(q2(amount)), "shield_cny": str(q2(self.shield_cny))}, {"screen": "save"})
        return rel.to_dict()

    def _shortfall(self) -> Decimal:
        """Yuan the student needs, from today until the next money can land, beyond what is in China now (¥100 steps).
        0 when today is covered: that is what makes a withdrawal an emergency."""
        need, bal = self.bank.daily_spend_cny, self.bank.student_cny()
        if need <= 0 or bal >= need:
            return Decimal(0)
        today = self.now.date()
        _, transit = self.student_money()
        until = transit[0][0] if transit else self.calendar.arrival(self.calendar.next_open("BD", today),
                                                                   self.corridor.i("bd_tt_transfer_days"))
        worst = min((project(bal, transit, today, today + timedelta(days=k), need)
                     for k in range(max((until - today).days, 1))), default=bal - need)
        return ATM_NOTE * ceil_div(max(-worst, need - bal), ATM_NOTE)

    def _shield_cover(self) -> dict | None:
        """Before the day's spending: if the money in China cannot cover today, the Shield does (inside the rule).
        It brings enough to last until the next money lands, so a crisis is one move, not one a day."""
        free = self.shield_cny - self._shield_waiting()
        short = self._shortfall()
        if self._savings_rule() is None or short <= 0 or free <= 0:
            return None
        return self._release_now(min(free, short), "emergency", Actor.AGENT)

    def request_shield_release(self, actor: Actor, amount_cny: Decimal, note: str = "") -> dict:
        """The student takes money out. With no money for today it is an emergency (instant); otherwise the waiting time
        and family approval the student chose when signing apply. Either way it only goes to the student's own account."""
        self._require(actor, "release_shield")
        if actor != Actor.STUDENT:
            raise PermissionError("only the student can take money out of their Shield")
        amount = D(amount_cny)
        free = self.shield_cny - self._shield_waiting()
        if amount <= 0 or amount > free:
            raise ValueError(f"the Shield has {cny(free, 'en')} free to take out")
        terms = self._savings_terms()
        # An emergency (no money for today) releases at once only what the student needs until money can land; the
        # rest of the request waits like any other, so spending down first cannot skip the cooling-off.
        instant = min(amount, self._shortfall())
        rest = amount - instant
        hours = 0 if terms is None else terms.cooling_off_hours
        needs_family = bool(terms and terms.family_lock)
        self._log("shield_release_requested", actor, "release_shield", {
            "amount_cny": str(q2(amount)), "emergency_cny": str(q2(instant)), "cooling_off_hours": hours,
            "needs_family": needs_family})
        if instant > 0:
            now_rel = self._release_now(instant, "emergency", actor)
            if rest <= 0:
                return now_rel
            amount = rest
        if hours == 0 and not needs_family:
            return self._release_now(amount, "planned", actor)
        rel = ShieldRelease(self._id("release"), amount, "planned", actor.value, self.now, self.now + timedelta(hours=hours),
                            needs_family, note=note[:80])
        self.shield_releases[rel.id] = rel
        released_now = instant
        wait = {
            "en": (f"You chose to wait {hours} hours before taking Shield money out" if hours else "You chose")
                  + (" and to ask your family first." if needs_family else "."),
            "bn": (f"তহবিলের টাকা তোলার আগে আপনি {num(hours, 'bn')} ঘণ্টা অপেক্ষা বেছে নিয়েছেন" if hours else "আপনি বেছে নিয়েছেন")
                  + (", আর আগে পরিবারকে জিজ্ঞেস করবেন।" if needs_family else "।"),
            "zh": (f"你选择了取出储备前等待 {hours} 小时" if hours else "你选择了") + ("，并先征得家人同意。" if needs_family else "。"),
        }
        self.feed.add(self.now, "student", "info", "shield_release_waiting",
                      {"amount_cny": str(q2(amount)), "available_date": rel.available_at.isoformat(),
                       "wait_en": wait["en"], "wait_bn": wait["bn"], "wait_zh": wait["zh"]}, {"screen": "save"})
        if needs_family:
            self.feed.add(self.now, "parent", "needs_you", "shield_release_needs_family", {"amount_cny": str(q2(amount))},
                          {"screen": "save", "release_id": rel.id})
        return {**rel.to_dict(), "released_now_cny": str(q2(released_now))}

    def approve_shield_release(self, actor: Actor, release_id: str) -> dict:
        self._require(actor, "approve_shield_release")
        if actor != Actor.PARENT:
            raise PermissionError("only the parent approves, and only when the student chose a family lock")
        rel = self.shield_releases[release_id]
        if not rel.needs_family or rel.status != "waiting" or rel.family_approved_at is not None:
            raise ValueError("this release does not need your approval")
        rel.family_approved_at = self.now
        self._log("shield_release_approved", actor, "approve_shield_release", {"release_id": rel.id,
                  "amount_cny": str(q2(rel.amount_cny))})
        self._process_releases()
        return rel.to_dict()

    def cancel_shield_release(self, actor: Actor, release_id: str) -> dict:
        self._require(actor, "cancel_shield_release")
        if actor != Actor.STUDENT:
            raise PermissionError("only the student can cancel their own release")
        rel = self.shield_releases[release_id]
        if rel.status != "waiting":
            raise ValueError(f"this release is already {rel.status}")
        rel.status = "cancelled"
        self._log("shield_release_cancelled", actor, "cancel_shield_release", {"release_id": rel.id,
                  "amount_cny": str(q2(rel.amount_cny))})
        return rel.to_dict()

    def _process_releases(self) -> list[dict]:
        out = []
        for rel in list(self.shield_releases.values()):
            if rel.status != "waiting" or self.now < rel.available_at or (rel.needs_family and rel.family_approved_at is None):
                continue
            amount = min(rel.amount_cny, self.shield_cny)
            rel.status = "released" if amount > 0 else "cancelled"
            if amount <= 0:
                continue
            rel.released_at = self.now
            self.bank.move_cny("student_shield", "student_cn", amount, rel.requested_by, Level.EXECUTE.name, "shield_released",
                               {"release_id": rel.id, "reason": "planned", "waited_until": rel.available_at.isoformat(),
                                "family_approved": rel.family_approved_at is not None})
            self.feed.add(self.now, "both" if self._shares_with_family() else "student", "info", "shield_released",
                          {"amount_cny": str(q2(amount)), "shield_cny": str(q2(self.shield_cny))}, {"screen": "save"})
            out.append({"type": "shield_released", "release_id": rel.id, "amount_cny": str(q2(amount))})
        return out

    # -- hundi vs the legal way; the dollar-crisis test ---------------------------------------------------
    def hundi_check(self, actor: Actor, amount: Decimal, currency: str = "USD", offered_bdt_per_usd: Decimal | None = None,
                    premium_bdt_per_usd: Decimal | None = None, lang: str = "en") -> dict:
        self._require(actor, "plan_savings")
        amt, cur = D(amount), (currency or "USD").upper()
        if cur not in ("USD", "CNY", "BDT"):
            raise ValueError("currency must be USD, CNY or BDT")
        if amt <= 0:
            raise ValueError("amount must be positive")
        mid = self.market.mid
        amount_cny = q2(amt if cur == "CNY" else amt * mid.cny_per_usd if cur == "USD" else amt / mid.bdt_per_cny)
        if amount_cny > Decimal(500000):
            raise ValueError("that is more than a year of study costs; check the amount")
        today = self.now.date()
        planned = None
        if self.autopilot.active_mandate() is not None:
            bal, transit = self.student_money()
            dec = topup_decision(today, bal, transit, self.planning_policy, self.calendar)
            planned = default_planned(dec.to_dict() if dec else None, today)
        r = hundi_compare(amount_cny, self.market, self.corridor, self.calendar, today, self.shield_cny - self._shield_waiting(),
                          offered_bdt_per_usd, premium_bdt_per_usd, planned, lang)
        r["input"] = {"amount": str(amt), "currency": cur}
        self._log("hundi_checked", actor, "plan_savings", {"amount_cny": str(amount_cny), "verdict": r["verdict"],
                  "premium_bdt_per_usd": r["options"][0]["premium_bdt_per_usd"]})
        return r

    def crisis_test(self, actor: Actor, weeks: int | None = None) -> dict:
        self._require(actor, "plan_savings")
        if weeks is not None and not 1 <= weeks <= 12:
            raise ValueError("weeks must be between 1 and 12")
        out = self._crisis(self._year_situation(), weeks, with_student_money=self._may_see_student_money(actor))
        w = out["worst"]
        self._log("crisis_tested", actor, "plan_savings", {"weeks": out["weeks"], "worst_from": w["from"],
                  "stuck_today": w["stuck_today"], "stuck_sathi": w["stuck_sathi"], "stuck_sathi_shield": w["stuck_sathi_shield"]})
        return out
