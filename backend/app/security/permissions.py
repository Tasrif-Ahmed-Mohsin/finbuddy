"""Permission engine: levels L0–L3, approval tokens, two-person rule, mandates.

Principles (see docs/02_build_plan.md §4):
  * The agent may READ (L0) and DRAFT (L1) freely. Nothing moves at those levels.
  * EXECUTE (L2) needs an approval token from the payer, bound to the exact draft. Changing the
    amount, payee, rate quote or expiry changes the draft hash, so the token no longer verifies.
  * Payments at or above the two-person threshold need BOTH student and parent.
  * MANDATE (L3): the agent may execute repeat payments only inside an active, user-created mandate.
  * Tokens are single-use (nonce) and expire.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum, IntEnum


class Level(IntEnum):
    READ = 0
    DRAFT = 1
    EXECUTE = 2
    MANDATE = 3


class Actor(str, Enum):
    AGENT = "agent"
    STUDENT = "student"
    PARENT = "parent"


# Which level each action needs. Anything not listed is denied.
ACTION_LEVELS: dict[str, Level] = {
    "get_rates": Level.READ,
    "compare_tuition": Level.READ,
    "plan_living": Level.READ,
    "explain": Level.READ,
    "check_message": Level.READ,
    "create_draft": Level.DRAFT,
    "set_reminder": Level.DRAFT,
    "plan_renewal": Level.DRAFT,  # make a renewal plan + draft messages (nothing is sent)
    "update_renewal": Level.DRAFT,  # tick steps / confirm the new expiry: the user only
    "share_passport": Level.DRAFT,  # issue / revoke a payment passport (shares personal data): the user only
    # Protective and reversible, moves no money: low friction, the agent may do it in an emergency.
    "freeze_card": Level.DRAFT,
    # Re-enables spending or is irreversible: the user only, with fingerprint/PIN on the phone.
    "unfreeze_card": Level.EXECUTE,
    "report_card_lost": Level.EXECUTE,
    "execute_draft": Level.EXECUTE,
    "execute_under_mandate": Level.MANDATE,
}

# The agent's ceiling. It can never EXECUTE on its own; only MANDATE within user-set caps.
# Asymmetric by design: making things SAFER is easy, making them riskier needs a human.
AGENT_ALLOWED = {"get_rates", "compare_tuition", "plan_living", "explain", "check_message", "create_draft",
                 "set_reminder", "plan_renewal", "freeze_card", "execute_under_mandate"}


@dataclass
class Draft:
    id: str
    kind: str  # tt_tuition | tt_living | atm_plan
    payer: Actor
    amount_cny: Decimal
    total_bdt: Decimal
    payee_id: str
    quote_id: str | None
    rate_bdt_per_cny: Decimal | None
    memo: str
    created_at: datetime
    expires_at: datetime
    created_by: Actor
    status: str = "draft"  # draft | blocked | approved | executed | expired
    checks: list[dict] = field(default_factory=list)

    def binding_fields(self) -> dict:
        """Everything an approval is bound to."""
        return {
            "id": self.id,
            "kind": self.kind,
            "payer": self.payer.value,
            "amount_cny": str(self.amount_cny),
            "total_bdt": str(self.total_bdt),
            "payee_id": self.payee_id,
            "quote_id": self.quote_id,
            "rate_bdt_per_cny": str(self.rate_bdt_per_cny) if self.rate_bdt_per_cny is not None else None,
            "memo": self.memo,
            "expires_at": self.expires_at.isoformat(),
        }

    def hash(self) -> str:
        canonical = json.dumps(self.binding_fields(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class Decision:
    allowed: bool
    reason: str
    missing_approvers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"allowed": self.allowed, "reason": self.reason, "missing_approvers": self.missing_approvers}


@dataclass
class Mandate:
    id: str
    created_by: Actor
    payee_id: str
    max_bdt_per_payment: Decimal
    max_bdt_per_period: Decimal
    period_days: int
    expires_at: datetime
    revoked: bool = False
    spent: list[tuple[datetime, Decimal]] = field(default_factory=list)

    def spent_in_period(self, now: datetime) -> Decimal:
        since = now - timedelta(days=self.period_days)
        return sum((amt for ts, amt in self.spent if ts >= since), Decimal(0))


def can_actor_perform(actor: Actor, action: str) -> Decision:
    if action not in ACTION_LEVELS:
        return Decision(False, f"unknown action '{action}' is denied by default")
    if actor == Actor.AGENT and action not in AGENT_ALLOWED:
        return Decision(False, f"the agent may not perform '{action}' (level {ACTION_LEVELS[action].name})")
    return Decision(True, "ok")


def required_approvers(draft: Draft, two_person_threshold_bdt: Decimal) -> set[Actor]:
    needed = {draft.payer}
    if draft.total_bdt >= two_person_threshold_bdt:
        needed |= {Actor.STUDENT, Actor.PARENT}
    return needed


class ApprovalService:
    """Issues and verifies single-use approval tokens bound to a draft hash.

    Hackathon note: the phone proves the user is present with biometrics/PIN, then calls the approve
    endpoint with the user's session. In production the token would be signed by a device-bound key
    (Android Keystore / Secure Enclave) so even the server could not forge an approval.
    """

    def __init__(self, secret: bytes | None = None, ttl_minutes: int = 15):
        self.secret = secret or secrets.token_bytes(32)
        self.ttl = timedelta(minutes=ttl_minutes)
        self.used_nonces: set[str] = set()

    def _sign(self, draft_hash: str, approver: str, nonce: str, exp: str) -> str:
        msg = f"{draft_hash}|{approver}|{nonce}|{exp}".encode("utf-8")
        return hmac.new(self.secret, msg, hashlib.sha256).hexdigest()

    def issue(self, draft: Draft, approver: Actor, now: datetime) -> dict:
        if approver == Actor.AGENT:
            raise PermissionError("the agent can never approve a payment")
        nonce = secrets.token_hex(8)
        exp = (now + self.ttl).isoformat()
        return {
            "draft_id": draft.id,
            "approver": approver.value,
            "nonce": nonce,
            "exp": exp,
            "sig": self._sign(draft.hash(), approver.value, nonce, exp),
        }

    def verify(self, draft: Draft, tokens: list[dict], now: datetime, two_person_threshold_bdt: Decimal) -> Decision:
        needed = required_approvers(draft, two_person_threshold_bdt)
        valid_by: set[Actor] = set()
        draft_hash = draft.hash()
        for tok in tokens:
            try:
                approver = Actor(tok["approver"])
                exp = datetime.fromisoformat(tok["exp"])
            except (KeyError, ValueError):
                return Decision(False, "malformed approval token")
            if approver == Actor.AGENT:
                return Decision(False, "agent approvals are never valid")
            if tok.get("nonce") in self.used_nonces:
                return Decision(False, "approval token already used (replay blocked)")
            if now > exp:
                return Decision(False, f"approval from {approver.value} expired")
            expected = self._sign(draft_hash, approver.value, tok.get("nonce", ""), tok["exp"])
            if not hmac.compare_digest(expected, tok.get("sig", "")):
                return Decision(False, "approval does not match this draft (amount, payee, rate or expiry changed)")
            valid_by.add(approver)
        missing = sorted(a.value for a in needed - valid_by)
        if missing:
            return Decision(False, "approval missing", missing)
        return Decision(True, "all required approvals valid")

    def consume(self, tokens: list[dict]) -> None:
        for tok in tokens:
            self.used_nonces.add(tok["nonce"])


def check_mandate(mandate: Mandate, draft: Draft, now: datetime) -> Decision:
    if mandate.revoked:
        return Decision(False, "mandate revoked")
    if now > mandate.expires_at:
        return Decision(False, "mandate expired")
    if draft.payee_id != mandate.payee_id:
        return Decision(False, "payee is not covered by the mandate")
    if draft.total_bdt > mandate.max_bdt_per_payment:
        return Decision(False, "amount exceeds the mandate's per-payment cap")
    if mandate.spent_in_period(now) + draft.total_bdt > mandate.max_bdt_per_period:
        return Decision(False, "amount exceeds the mandate's period cap")
    return Decision(True, "within mandate")
