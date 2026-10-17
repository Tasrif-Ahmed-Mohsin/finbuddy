"""Taint tracking for payment values: money amounts that came from outside text cannot reach a payment the AI drafts.

Idea from Google DeepMind's CaMeL (2025): label where data came from, and let the policy at the "sink" (here: the AI
drafting a payment) decide by provenance, not by spotting attack words.

* Outside text (forwarded SMS, emails, webhook messages, photo reading) is untrusted. The money amounts and account
  numbers in it are recorded with where they came from (source, sender, a hash of the text).
* Trusted values: what the person typed in this chat (they said it), the tuition amount the person confirmed in the app,
  and values a person endorsed.
* Sink rule: when the AI drafts a payment whose amount appears only in untrusted text (never typed or confirmed by a
  person), the draft is blocked, however the text was phrased. Drafts a person makes in the app are not checked here:
  the person chose the amount.

Honest limits: values are matched by amount, not tracked through the model's reasoning (the model is a black box
here, unlike CaMeL's interpreter), so an outside amount the person also typed counts as theirs. Payees are already
an allow-list, so an account number from a message can never become a payee anyway.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any

from app.security.permissions import Actor


class TaintLevel(str, Enum):
    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"


class TaintSource(str, Enum):
    # High-integrity sources
    SYSTEM_CONFIG = "system_config"
    VERIFIED_PROFILE = "verified_profile"
    OFFICIAL_REGISTRY = "official_registry"
    USER_AUTHENTICATED = "user_authenticated"  # User typed or confirmed directly in authenticated UI
    PASSPHRASE_OR_BIOMETRIC = "passphrase_or_biometric"

    # Untrusted external sources (Potential Prompt Injection vectors)
    UNTRUSTED_SMS = "untrusted_sms"
    UNTRUSTED_EMAIL = "untrusted_email"
    UNTRUSTED_WEBHOOK = "untrusted_webhook"
    UNTRUSTED_PHOTO_OCR = "untrusted_photo_ocr"
    UNTRUSTED_EXTERNAL_CHAT = "untrusted_external_chat"


@dataclass
class Provenance:
    """Cryptographic provenance trail for any data entity entering the agent boundary."""
    source: TaintSource
    source_id: str
    sender: str
    snippet: str
    sha256: str
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source.value,
            "source_id": self.source_id,
            "sender": self.sender,
            "snippet": self.snippet[:40],
            "sha256": self.sha256,
            "timestamp": self.timestamp,
        }


@dataclass
class TaintedEntity:
    """An individual entity (monetary amount, account number, payee name) carrying taint status."""
    id: str
    entity_type: str  # "amount", "account_number", "payee_id", "deadline", "command"
    raw_value: str
    normalized_value: Decimal | str
    provenance: Provenance
    taint_level: TaintLevel = TaintLevel.UNTRUSTED
    endorsed: bool = False
    endorsed_by: Actor | None = None
    endorsed_at: str | None = None
    endorsement_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "raw_value": self.raw_value,
            "normalized_value": str(self.normalized_value),
            "taint_level": self.taint_level.value,
            "endorsed": self.endorsed,
            "endorsed_by": self.endorsed_by.value if self.endorsed_by else None,
            "endorsed_at": self.endorsed_at,
            "endorsement_reason": self.endorsement_reason,
            "provenance": self.provenance.to_dict(),
        }


@dataclass
class TaintVerdict:
    """The outcome of an Information Flow Control sink policy check."""
    allowed: bool
    sink: str
    violating_parameter: str | None = None
    violating_entity: TaintedEntity | None = None
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "sink": self.sink,
            "violating_parameter": self.violating_parameter,
            "violating_entity": self.violating_entity.to_dict() if self.violating_entity else None,
            "reason": self.reason,
        }


# Money in outside text: a number next to a currency mark (before or after it). Bare numbers (dates, times, codes,
# counts) are not money. Indian grouping (1,20,000) and Bangla digits are understood.
DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
_CUR = r"(?:¥|￥|৳|\$|cny|rmb|yuan|usd|bdt|tk\.?|taka|টাকা|ইউয়ান|元|块)"
_NUM = r"(\d{1,3}(?:,\d{2,3})+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)"
MONEY_RE = re.compile(rf"{_CUR}\s*{_NUM}|{_NUM}\s*(?:{_CUR}|lakh|লাখ|হাজার|万)", re.IGNORECASE)
ACCOUNT_RE = re.compile(r"\b([0-9]{12,24}|[0-9]{4}[-\s][0-9]{4}[-\s][0-9]{4}(?:[-\s][0-9]{4})?)\b")
SWIFT_BIC_RE = re.compile(r"\b([A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)\b")


class TaintLedger:
    """Lattice-based Information Flow Control engine for Sathi.
    
    Tracks untrusted entities from external inputs (SMS, email, OCR),
    enforces non-interference sink policies, and manages formal human declassification.
    """

    def __init__(self):
        self._entities: dict[str, TaintedEntity] = {}
        self._blocked_events: list[dict[str, Any]] = []
        self._counter: int = 0

    def _next_id(self, prefix: str = "tnt") -> str:
        self._counter += 1
        return f"{prefix}-{self._counter:05d}"

    def register_untrusted_text(
        self,
        source: TaintSource,
        source_id: str,
        sender: str,
        text: str,
        timestamp: datetime | None = None,
    ) -> list[TaintedEntity]:
        """Scans untrusted outside text and immutably tags extracted financial parameters."""
        if not text:
            return []

        ts = (timestamp or datetime.now(timezone.utc)).isoformat()
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        prov = Provenance(
            source=source,
            source_id=source_id,
            sender=sender[:60],
            snippet=text[:120],
            sha256=digest,
            timestamp=ts,
        )

        extracted: list[TaintedEntity] = []

        # 1. Extract monetary amounts
        text = text.translate(DIGITS)
        for match in MONEY_RE.finditer(text):
            raw_num = (match.group(1) or match.group(2)).replace(",", "")
            try:
                dec = Decimal(raw_num)
                if dec > 0:
                    ent = TaintedEntity(
                        id=self._next_id("tnt-amt"),
                        entity_type="amount",
                        raw_value=match.group(0).strip(),
                        normalized_value=dec,
                        provenance=prov,
                        taint_level=TaintLevel.UNTRUSTED,
                    )
                    self._entities[ent.id] = ent
                    extracted.append(ent)
            except Exception:
                pass

        # 2. Extract bank account candidates
        for match in ACCOUNT_RE.finditer(text):
            clean_acct = re.sub(r"[-\s]", "", match.group(1))
            if len(clean_acct) >= 10:
                ent = TaintedEntity(
                    id=self._next_id("tnt-acct"),
                    entity_type="account_number",
                    raw_value=match.group(0).strip(),
                    normalized_value=clean_acct,
                    provenance=prov,
                    taint_level=TaintLevel.UNTRUSTED,
                )
                self._entities[ent.id] = ent
                extracted.append(ent)

        return extracted

    def register_trusted_baseline(
        self,
        entity_type: str,
        value: Decimal | str,
        label: str = "official_tuition_baseline",
    ) -> TaintedEntity:
        """Registers a verified trusted value (e.g. from the student's official university enrollment)."""
        prov = Provenance(
            source=TaintSource.OFFICIAL_REGISTRY,
            source_id=f"registry-{label}",
            sender="official_portal",
            snippet=f"Verified authoritative record: {value}",
            sha256=hashlib.sha256(str(value).encode()).hexdigest(),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        ent = TaintedEntity(
            id=self._next_id("tnt-trust"),
            entity_type=entity_type,
            raw_value=str(value),
            normalized_value=Decimal(str(value)) if isinstance(value, (int, float, Decimal)) else str(value),
            provenance=prov,
            taint_level=TaintLevel.TRUSTED,
            endorsed=True,
            endorsement_reason=label,
        )
        self._entities[ent.id] = ent
        return ent

    def endorse(
        self,
        value: Decimal | str,
        entity_type: str,
        actor: Actor,
        reason: str = "human_user_confirmed",
    ) -> list[TaintedEntity]:
        """Formal declassification operation: human user explicitly endorses a previously untrusted entity."""
        endorsed: list[TaintedEntity] = []
        val_str = str(value)
        val_dec = None
        try:
            val_dec = Decimal(val_str)
        except Exception:
            pass

        now_str = datetime.now(timezone.utc).isoformat()

        for ent in self._entities.values():
            if ent.entity_type != entity_type:
                continue
            matches = False
            if val_dec is not None and isinstance(ent.normalized_value, Decimal):
                matches = (ent.normalized_value == val_dec)
            else:
                matches = (str(ent.normalized_value) == val_str)

            if matches:
                ent.taint_level = TaintLevel.TRUSTED
                ent.endorsed = True
                ent.endorsed_by = actor
                ent.endorsed_at = now_str
                ent.endorsement_reason = reason
                endorsed.append(ent)

        # If entity wasn't in ledger, register it directly as a trusted user input
        if not endorsed:
            prov = Provenance(
                source=TaintSource.USER_AUTHENTICATED,
                source_id=f"user-{actor.value}",
                sender=actor.value,
                snippet=f"Explicit authenticated human input: {value}",
                sha256=hashlib.sha256(val_str.encode()).hexdigest(),
                timestamp=now_str,
            )
            ent = TaintedEntity(
                id=self._next_id("tnt-user"),
                entity_type=entity_type,
                raw_value=val_str,
                normalized_value=val_dec if val_dec is not None else val_str,
                provenance=prov,
                taint_level=TaintLevel.TRUSTED,
                endorsed=True,
                endorsed_by=actor,
                endorsed_at=now_str,
                endorsement_reason=reason,
            )
            self._entities[ent.id] = ent
            endorsed.append(ent)

        return endorsed

    def is_tainted(
        self,
        value: Decimal | str,
        entity_type: str = "amount",
    ) -> tuple[bool, TaintedEntity | None]:
        """Checks if a given value matches an un-endorsed, untrusted entity."""
        val_str = str(value)
        val_dec = None
        try:
            val_dec = Decimal(val_str)
        except Exception:
            pass

        # Check if there is an explicit TRUSTED record matching this value
        for ent in self._entities.values():
            if ent.entity_type == entity_type and ent.taint_level == TaintLevel.TRUSTED:
                if val_dec is not None and isinstance(ent.normalized_value, Decimal):
                    if ent.normalized_value == val_dec:
                        return False, None
                elif str(ent.normalized_value) == val_str:
                    return False, None

        # Check if there is an UNTRUSTED entity matching this value
        for ent in self._entities.values():
            if ent.entity_type == entity_type and ent.taint_level == TaintLevel.UNTRUSTED and not ent.endorsed:
                if val_dec is not None and isinstance(ent.normalized_value, Decimal):
                    if ent.normalized_value == val_dec:
                        return True, ent
                elif str(ent.normalized_value) == val_str:
                    return True, ent

        return False, None

    def endorse_user_text(self, text: str, actor: Actor) -> list[TaintedEntity]:
        """What the person typed in the chat is theirs: the money amounts in it become trusted values."""
        out: list[TaintedEntity] = []
        t = (text or "").translate(DIGITS)
        nums = {m.group(1) or m.group(2) for m in MONEY_RE.finditer(t)}
        nums |= set(re.findall(r"(?<![\d.,])(\d{3,}(?:\.\d{1,2})?)(?![\d.,])", t))  # "send 2000 living money"
        for n in nums:
            try:
                value = Decimal(n.replace(",", ""))
            except Exception:  # noqa: BLE001
                continue
            if value > 0:
                out += self.endorse(value, "amount", actor, "typed_by_the_person")
        return out

    def check_sink(
        self,
        sink_name: str,
        amount_cny: Decimal | None = None,
        payee_id: str | None = None,
        account_number: str | None = None,
        memo: str | None = None,
        trusted_amounts: set[Decimal] | frozenset[Decimal] = frozenset(),
    ) -> TaintVerdict:
        """The sink rule for a payment the AI drafts: refuse an amount (or account) that came only from outside text.
        `trusted_amounts` are values the system already holds from a person (the confirmed tuition amount)."""
        # 1. Check Amount parameter
        if amount_cny is not None and amount_cny not in trusted_amounts:
            tainted, ent = self.is_tainted(amount_cny, entity_type="amount")
            if tainted and ent is not None:
                verdict = TaintVerdict(
                    allowed=False,
                    sink=sink_name,
                    violating_parameter="amount_cny",
                    violating_entity=ent,
                    reason=(
                        f"Refused amount ¥{amount_cny}: it came from outside text ({ent.provenance.source.value}, "
                        f"{ent.provenance.source_id}) and the person never typed or confirmed it. "
                        f"Taint tracking (CaMeL-style provenance) stopped a possible prompt injection."
                    ),
                )
                self._record_block(verdict)
                return verdict

        # 2. Check Payee/Account parameter
        if account_number is not None:
            tainted, ent = self.is_tainted(account_number, entity_type="account_number")
            if tainted and ent is not None:
                verdict = TaintVerdict(
                    allowed=False,
                    sink=sink_name,
                    violating_parameter="account_number",
                    violating_entity=ent,
                    reason=(
                        f"Refused bank account {account_number}: originated from {ent.provenance.source.value} "
                        f"({ent.provenance.source_id}). Only pre-verified registry accounts are permitted."
                    ),
                )
                self._record_block(verdict)
                return verdict

        return TaintVerdict(allowed=True, sink=sink_name)

    def _record_block(self, verdict: TaintVerdict):
        self._blocked_events.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sink": verdict.sink,
            "parameter": verdict.violating_parameter,
            "reason": verdict.reason,
            "violating_entity": verdict.violating_entity.to_dict() if verdict.violating_entity else None,
        })

    def scrub_text(self) -> int:
        """After the person deletes their messages: keep the amounts (the safety check needs them), drop the text."""
        n = 0
        for e in self._entities.values():
            p = e.provenance
            if p.source not in (TaintSource.USER_AUTHENTICATED, TaintSource.OFFICIAL_REGISTRY) and p.snippet:
                p.snippet, p.sender, e.raw_value = "", "deleted", str(e.normalized_value)
                n += 1
        for b in self._blocked_events:
            if b.get("violating_entity"):
                b["violating_entity"]["provenance"]["snippet"] = ""
                b["violating_entity"]["provenance"]["sender"] = "deleted"
        return n

    def get_status(self) -> dict[str, Any]:
        """Telemetry report of the Taint Tracking Engine."""
        untrusted_count = sum(1 for e in self._entities.values() if e.taint_level == TaintLevel.UNTRUSTED and not e.endorsed)
        trusted_count = sum(1 for e in self._entities.values() if e.taint_level == TaintLevel.TRUSTED or e.endorsed)
        return {
            "taint_tracking_active": True,
            "defense_standard": "provenance labels at the payment sink (after Google DeepMind's CaMeL, 2025)",
            "enforcement_mode": "ai_drafted_payments",
            "total_entities_tracked": len(self._entities),
            "untrusted_entities": untrusted_count,
            "endorsed_entities": trusted_count,
            "total_injections_blocked": len(self._blocked_events),
            "recent_blocks": self._blocked_events[-10:],
        }


def wrap_untrusted_context(
    source_name: str,
    source_id: str,
    sender: str,
    content: str,
) -> str:
    """CaMeL Environment Isolation: encapsulates outside text in non-escapable boundary tags."""
    content_clean = content.replace("</untrusted_input>", "&lt;/untrusted_input&gt;")
    digest = hashlib.sha256(content.encode()).hexdigest()[:16]
    return (
        f'<untrusted_input source="{source_name}" id="{source_id}" sender="{sender}" integrity="{digest}">\n'
        f'{content_clean}\n'
        f'</untrusted_input>'
    )
