"""Compliance and safety checks run on every draft BEFORE approval and AGAIN before execution.

Each check returns pass/fail, a severity (block | warn | info), a human message and the rule's
source, so the app can explain *why* something was blocked.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.corridors.loader import Corridor
from app.money import q2
from app.security.permissions import Actor, Draft
from app.security.scam import Flag, contains_term, has_high_risk


@dataclass
class Check:
    id: str
    passed: bool
    severity: str  # block | warn | info
    message: str
    source: str = ""

    def to_dict(self) -> dict:
        return {"id": self.id, "passed": self.passed, "severity": self.severity, "message": self.message, "source": self.source}


@dataclass
class Payee:
    id: str
    name: str
    bank: str
    account_masked: str
    currency: str
    verified: bool
    verified_source: str
    credit_account_id: str


@dataclass
class ComplianceContext:
    corridor: Corridor
    payees: dict[str, Payee]
    now: datetime
    invoice_amount_cny: Decimal | None = None
    living_remitted_usd_this_month: Decimal = Decimal(0)
    cny_per_usd: Decimal = Decimal(7)
    endorsement_expiry: date | None = None
    student_file_expiry: date | None = None
    origin_flags: list[Flag] | None = None
    card_status: str | None = None  # status of the Bangladeshi card used for ATM plans
    taint_ledger: Any | None = None
    cop_service: Any | None = None
    trusted_amounts: frozenset = frozenset()  # amounts a person confirmed in the app (the tuition invoice)
    cop_names: dict | None = None  # who should hold each payee account (the student's own account → the student)


def run_draft_checks(draft: Draft, ctx: ComplianceContext) -> list[Check]:
    c = ctx.corridor
    checks: list[Check] = []

    # 1. Payee must be on the verified allow-list (stops fake agents / changed accounts: P-09, P-26).
    payee = ctx.payees.get(draft.payee_id)
    if payee is None or not payee.verified:
        checks.append(Check("payee_allowlisted", False, "block",
                            "This payee is not on the verified list. Only the university's official account or your own account can receive money.",
                            "Product safety rule"))
    else:
        checks.append(Check("payee_allowlisted", True, "info", f"Verified payee: {payee.name} ({payee.verified_source})"))

    # 2. Draft must not be expired (approval only for a fresh rate quote).
    fresh = ctx.now <= draft.expires_at
    checks.append(Check("quote_fresh", fresh, "block" if not fresh else "info",
                        "Rate quote is fresh" if fresh else "Rate quote expired; create a new draft for a current rate",
                        "Product safety rule"))

    # 3. Transfer note must not contain words that trigger bank risk controls (P-16).
    bad = [t for t in c.blocked_memo_terms if contains_term(draft.memo, t)]
    checks.append(Check("memo_clean", not bad, "block" if bad else "info",
                        f"Transfer note contains risky words: {', '.join(bad)}" if bad else "Transfer note is clean",
                        "Bank risk controls (docs P-16)"))

    # 4. Tuition: Bangladesh allows remitting the amount on the institution's demand note (P-02).
    if draft.kind == "tt_tuition":
        if ctx.invoice_amount_cny is None:
            checks.append(Check("invoice_match", False, "warn", "No fee notice on file; upload the university's invoice",
                                "FE Circular 37: tuition up to the demand note"))
        elif draft.amount_cny > ctx.invoice_amount_cny:
            checks.append(Check("invoice_match", False, "block",
                                f"Amount {q2(draft.amount_cny)} CNY is more than the fee notice ({q2(ctx.invoice_amount_cny)} CNY)",
                                "FE Circular 37: tuition up to the demand note"))
        else:
            checks.append(Check("invoice_match", True, "info", "Amount matches the fee notice"))

    # 5. Living money: Bangladesh monthly living-cost cap (P-02).
    if draft.kind == "tt_living":
        cap = c.v("bd_living_remit_cap_usd_per_month")
        after = ctx.living_remitted_usd_this_month + draft.amount_cny / ctx.cny_per_usd
        ok = after <= cap
        checks.append(Check("living_cap", ok, "block" if not ok else "info",
                            f"Living remittance this month would be {q2(after)} USD (cap {cap} USD)",
                            c.params["bd_living_remit_cap_usd_per_month"].source))

    # 5b. A frozen or lost card cannot be used for ATM withdrawals.
    if draft.kind == "atm_plan" and ctx.card_status is not None:
        ok = ctx.card_status == "active"
        checks.append(Check("card_active", ok, "info" if ok else "block",
                            "Card is active" if ok else f"Card is {ctx.card_status}; unfreeze it (or use the replacement card) first",
                            "Card controls"))

    # 6. Endorsement / Student File must be valid; warn ahead of expiry (N-05).
    #    The card endorsement only matters for using the card abroad (ATM). Bank transfers to the student's
    #    own account or the university come from the Student File and keep working after the card stops.
    warn_days = c.i("bd_endorsement_warn_days")
    for check_id, label, expiry in (("endorsement_valid", "Endorsement", ctx.endorsement_expiry),
                                    ("student_file_valid", "Student File", ctx.student_file_expiry)):
        if expiry is None or (check_id == "endorsement_valid" and draft.kind != "atm_plan"):
            continue
        days = (expiry - ctx.now.date()).days
        if days < 0:
            checks.append(Check(check_id, False, "block", f"{label} expired on {expiry}; renew it before sending money", "Bank rule (docs N-05)"))
        elif days <= warn_days:
            checks.append(Check(check_id, True, "warn", f"{label} expires in {days} days ({expiry}); start the renewal now", "Bank rule (docs N-05)"))
        else:
            checks.append(Check(check_id, True, "info", f"{label} valid until {expiry}"))

    # 7. The message that started this draft must not carry scam / injection signals (P-24, P-25, N-08).
    if ctx.origin_flags is not None:
        risky = has_high_risk(ctx.origin_flags)
        cats = ", ".join(sorted({f.category for f in ctx.origin_flags}))
        checks.append(Check("origin_message_safe", not risky, "block" if risky else "info",
                            f"The request contains scam/injection signals ({cats})" if risky else "Request looks safe",
                            "Scam & injection rules (app/security/scam.py)"))

    # 8. Taint tracking (after DeepMind's CaMeL, 2025): when the AI drafts a payment, its amount must not come only
    #    from outside text (SMS, email, photo). A person's own drafts are theirs and are not checked here.
    if ctx.taint_ledger is not None and draft.created_by == Actor.AGENT:
        verdict = ctx.taint_ledger.check_sink(
            sink_name="create_payment_draft",
            amount_cny=draft.amount_cny,
            payee_id=draft.payee_id,
            trusted_amounts=ctx.trusted_amounts,
        )
        if not verdict.allowed:
            checks.append(Check(
                "taint_flow_control",
                False,
                "block",
                verdict.reason,
                "Taint tracking (app/security/taint.py)",
            ))
        else:
            checks.append(Check(
                "taint_flow_control",
                True,
                "info",
                "The amount did not come from outside text",
                "Taint tracking (app/security/taint.py)",
            ))

    # 9. Confirmation of Payee (CoP) verification (UK PSR & EU VoP 2024/886 standard).
    #    Queries the receiving bank simulator to verify that the name on the account matches.
    #    CoP applies to bank account transfers (tt_tuition, tt_living), not ATM card cash withdrawals.
    if ctx.cop_service is not None and draft.payee_id and draft.kind != "atm_plan":
        from app.security.cop import CopStatus
        payee_rec = ctx.payees.get(draft.payee_id)
        intended = (ctx.cop_names or {}).get(draft.payee_id) or (payee_rec.name if payee_rec else draft.payee_id)
        cop = ctx.cop_service.verify_payee(draft.payee_id, intended)
        if cop.status == CopStatus.MATCH:
            checks.append(Check(
                "cop_verification",
                True,
                "info",
                f"Confirmation of Payee: MATCHED '{cop.registered_name}' ({cop.bank_name})",
                "UK PSR / EU VoP Confirmation of Payee",
            ))
        elif cop.status == CopStatus.CLOSE_MATCH:
            checks.append(Check(
                "cop_verification",
                True,
                "warn",
                f"Confirmation of Payee: CLOSE MATCH. Registered legal name: '{cop.registered_name}'",
                "UK PSR / EU VoP Confirmation of Payee",
            ))
        else:
            checks.append(Check(
                "cop_verification",
                False,
                "block",
                f"Confirmation of Payee FAILED: Account belongs to '{cop.registered_name}', NOT '{intended}'. Authorised Push Payment (APP) fraud risk.",
                "UK PSR / EU VoP Confirmation of Payee",
            ))

    return checks


def is_blocked(checks: list[Check]) -> bool:
    return any((not ch.passed) and ch.severity == "block" for ch in checks)
