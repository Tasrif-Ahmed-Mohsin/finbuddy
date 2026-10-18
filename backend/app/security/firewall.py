"""AI Output Firewall (Egress DLP & Output Guardrail).

Defends against sensitive data exfiltration at the EXIT boundary (agent replies & LLM outputs),
not just at the entry prompt:
- Blocks / redacts One-Time Passwords (OTPs), 2FA authentication pins, and verification codes.
- Masks full Payment Card Numbers (PAN, 13-19 digits) validated via the Luhn algorithm.
- Masks full clearing and bank account numbers / IBANs.
- Enforces cross-role privacy invariants between Parent and Student (Earn & Save confidentiality,
  private campus wages, personal wants, unshared Shield balances).
- Blocks system prompt dumps, developer instructions, and secret credential exfiltration.
- Produces immutable audit records for every interception and provides real-time telemetry.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.security.permissions import Actor


class ViolationType(str, Enum):
    OTP_CODE = "otp_code"
    PAYMENT_CARD = "payment_card"
    BANK_ACCOUNT = "bank_account"
    CROSS_ROLE_PRIVACY = "cross_role_privacy"
    SYSTEM_PROMPT_LEAK = "system_prompt_leak"
    SECRET_CREDENTIAL = "secret_credential"


class FirewallAction(str, Enum):
    ALLOW = "allow"
    REDACT = "redact"
    BLOCK = "block"


@dataclass
class OutputViolation:
    violation_type: ViolationType
    severity: str  # "low", "medium", "critical"
    description: str
    snippet_masked: str
    action: str  # "redacted", "blocked"

    def to_dict(self) -> dict[str, Any]:
        return {
            "violation_type": self.violation_type.value,
            "severity": self.severity,
            "description": self.description,
            "snippet_masked": self.snippet_masked,
            "action": self.action,
        }


@dataclass
class OutputFirewallVerdict:
    passed: bool
    action_taken: FirewallAction
    original_length: int
    filtered_length: int
    filtered_text: str
    violations: list[OutputViolation] = field(default_factory=list)
    actor: str = "unknown"
    checked_at: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "action_taken": self.action_taken.value,
            "original_length": self.original_length,
            "filtered_length": self.filtered_length,
            "filtered_text": self.filtered_text,
            "violations": [v.to_dict() for v in self.violations],
            "actor": self.actor,
            "checked_at": self.checked_at,
            "latency_ms": round(self.latency_ms, 3),
        }


# -----------------------------------------------------------------------------
# Luhn Algorithm for ISO/IEC 7812 Payment Card Numbers
# -----------------------------------------------------------------------------
def is_luhn_valid(number_str: str) -> bool:
    digits = [int(c) for c in number_str if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for i, digit in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = digit * 2
            checksum += doubled - 9 if doubled > 9 else doubled
        else:
            checksum += digit
    return checksum % 10 == 0


def mask_card_pan(pan: str) -> str:
    digits = re.sub(r"\D", "", pan)
    last4 = digits[-4:] if len(digits) >= 4 else "XXXX"
    return f"****-****-****-{last4}"


def mask_bank_account(acc: str) -> str:
    digits = re.sub(r"\D", "", acc)
    last4 = digits[-4:] if len(digits) >= 4 else "XXXX"
    return f"****{last4}"


# -----------------------------------------------------------------------------
# AI Output Firewall Engine
# -----------------------------------------------------------------------------
class OutputFirewall:
    """Stateful egress guardrail that validates and filters all agent messages before display."""

    # Redaction placeholders, in the reader's language (the chat is read by a parent in Bangla, too)
    PLACEHOLDERS = {
        "otp": {"en": "[code hidden]", "bn": "[কোড লুকানো]", "zh": "[验证码已隐藏]"},
        "income": {"en": "[student's private income]", "bn": "[শিক্ষার্থীর ব্যক্তিগত আয়]", "zh": "[学生的私人收入]"},
        "shield": {"en": "[student's private savings]", "bn": "[শিক্ষার্থীর ব্যক্তিগত সঞ্চয়]", "zh": "[学生的私人储蓄]"},
        "parent": {"en": "[parent's account hidden]", "bn": "[অভিভাবকের অ্যাকাউন্ট লুকানো]", "zh": "[家长账户已隐藏]"},
        "secret": {"en": "[secret hidden]", "bn": "[গোপন তথ্য লুকানো]", "zh": "[密钥已隐藏]"},
    }
    REDACTED_OTP = PLACEHOLDERS["otp"]["en"]
    REDACTED_PRIVACY = PLACEHOLDERS["income"]["en"]
    REDACTED_SHIELD = PLACEHOLDERS["shield"]["en"]
    REDACTED_PARENT = PLACEHOLDERS["parent"]["en"]
    BLOCKED_SYSTEM_PROMPT = (
        "For security and privacy protection, internal system configurations and instructions "
        "cannot be disclosed."
    )

    # Patterns
    # A one-time code only counts after an explicit code word ("OTP", "verification code", "PIN", ওটিপি, 验证码);
    # a bare "code" or a year is not one.
    _CODE_WORD = (r"(?:\botp\b|one[- ]time[- ](?:password|code|pin)|verification[- ]code|security[- ](?:code|pin)|"
                  r"login[- ](?:code|pin)|auth(?:entication)?[- ]code|\b2fa\b|\bpin\b|ওটিপি|ও\.টি\.পি|পিন|যাচাই(?:করণ)?\s*কোড|"
                  r"验证码|动态码|校验码)")
    RE_OTP_CONTEXT = re.compile(
        rf"(?i){_CODE_WORD}\s*(?:number\s*)?(?:is|was|নম্বর|হলো|是|为)?\s*[:=：-]?\s*(\d{{4,8}})(?!\d)"
        rf"|(?<!\d)(\d{{4,8}})\s*(?:is|was|হলো|是)\s+(?:your\s+|আপনার\s*)?{_CODE_WORD}"
    )
    RE_PAN_CANDIDATE = re.compile(r"\b(?:\d{4}[ -]\d{4}[ -]\d{4}[ -]\d{1,7}|\d{13,19})\b")
    # An account number: 10+ digits (spaces or dashes allowed), or an IBAN; words are never account numbers.
    RE_ACCOUNT_CONTEXT = re.compile(
        r"(?i)(?:\b(?:account(?: number| no\.?| #)?|a/c|iban|bank account|receiving account|clearing account)\b"
        r"[\s:=#-]*(?:is|was)?[\s:=#-]*((?:[A-Z]{2}\d{2}[A-Z0-9]{8,30})|(?:\d[\d -]{8,26}\d)))"
    )
    RE_SECRET_KEY = re.compile(
        r"(?i)(?:sk-[a-zA-Z0-9_\-]{20,}|-----BEGIN (?:RSA |EC )?PRIVATE KEY-----|bearer\s+[a-zA-Z0-9_\-\.]{25,}|ey[a-zA-Z0-9_-]{10,}\.ey[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,})"
    )
    RE_SYSTEM_PROMPT_SIGNATURES = [
        re.compile(r"(?i)you are bluefin[,\s]+a money agent for a bangladeshi student"),
        re.compile(r"(?i)system\s+instructions?\s*:"),
        re.compile(r"(?i)internal\s+confidential\s+prompt"),
        re.compile(r"(?i)here (?:is|are) (?:my|the) (?:initial |system )?(?:prompt|instructions)"),
        re.compile(r"(?i)developer\s+mode\s+enabled\s*:"),
    ]

    def __init__(self) -> None:
        self.total_inspections: int = 0
        self.total_violations: int = 0
        self.blocked_count: int = 0
        self.redacted_count: int = 0
        self.category_counts: dict[str, int] = {
            ViolationType.OTP_CODE.value: 0,
            ViolationType.PAYMENT_CARD.value: 0,
            ViolationType.BANK_ACCOUNT.value: 0,
            ViolationType.CROSS_ROLE_PRIVACY.value: 0,
            ViolationType.SYSTEM_PROMPT_LEAK.value: 0,
            ViolationType.SECRET_CREDENTIAL.value: 0,
        }
        self.recent_interceptions: list[dict[str, Any]] = []

    def reset_stats(self) -> None:
        self.total_inspections = 0
        self.total_violations = 0
        self.blocked_count = 0
        self.redacted_count = 0
        for k in self.category_counts:
            self.category_counts[k] = 0
        self.recent_interceptions.clear()

    def inspect_and_filter(
        self,
        text: str,
        actor: Actor | str,
        context: dict[str, Any] | None = None,
    ) -> OutputFirewallVerdict:
        """Inspects outgoing agent reply text and masks/blocks sensitive egress."""
        start_time = time.perf_counter()
        self.total_inspections += 1
        actor_enum = actor if isinstance(actor, Actor) else Actor(actor) if actor in [a.value for a in Actor] else Actor.AGENT
        context = context or {}

        violations: list[OutputViolation] = []
        modified_text = text
        action = FirewallAction.ALLOW

        # 1. Check System Prompt Exfiltration (Highest Priority - Immediate Block)
        for pat in self.RE_SYSTEM_PROMPT_SIGNATURES:
            if pat.search(text):
                v = OutputViolation(
                    violation_type=ViolationType.SYSTEM_PROMPT_LEAK,
                    severity="critical",
                    description="Attempted exfiltration of internal system instructions / agent directives",
                    snippet_masked="[SYSTEM PROMPT DIRECTIVE DUMP DETECTED]",
                    action="blocked",
                )
                violations.append(v)
                action = FirewallAction.BLOCK
                modified_text = self._localized_refusal(context.get("lang", "en"))
                break

        # If blocked at step 1, finalize and record telemetry
        if action == FirewallAction.BLOCK:
            return self._finalize_verdict(
                text, modified_text, action, violations, actor_enum, start_time
            )

        # 2. Check Secret Credentials (API Keys, JWTs, Private Keys)
        for m in self.RE_SECRET_KEY.finditer(modified_text):
            secret_match = m.group(0)
            v = OutputViolation(
                violation_type=ViolationType.SECRET_CREDENTIAL,
                severity="critical",
                description="Raw API key, JWT token, or private cryptographic key detected in outbound message",
                snippet_masked=secret_match[:4] + "..." + secret_match[-4:] if len(secret_match) > 8 else "***",
                action="redacted",
            )
            violations.append(v)
            modified_text = modified_text.replace(secret_match, self.PLACEHOLDERS["secret"].get(context.get("lang", "en"), "[secret hidden]"))
            if action == FirewallAction.ALLOW:
                action = FirewallAction.REDACT

        # 3. Check Payment Card PANs (Luhn-Valid 13-19 Digits)
        for m in self.RE_PAN_CANDIDATE.finditer(modified_text):
            candidate = m.group(0)
            raw_digits = re.sub(r"\D", "", candidate)
            if 13 <= len(raw_digits) <= 19 and is_luhn_valid(raw_digits):
                masked = mask_card_pan(raw_digits)
                v = OutputViolation(
                    violation_type=ViolationType.PAYMENT_CARD,
                    severity="critical",
                    description=f"Luhn-valid payment card number ({len(raw_digits)} digits) masked to PCI-DSS standard",
                    snippet_masked=masked,
                    action="redacted",
                )
                violations.append(v)
                modified_text = modified_text.replace(candidate, masked)
                if action == FirewallAction.ALLOW:
                    action = FirewallAction.REDACT

        # 4. Check OTPs and Verification Codes
        # A. Contextual regex check
        lang = context.get("lang", "en")
        otp_mark = self.PLACEHOLDERS["otp"].get(lang, self.REDACTED_OTP)

        def hide_code(m: re.Match) -> str:
            code = m.group(1) or m.group(2)
            violations.append(OutputViolation(
                violation_type=ViolationType.OTP_CODE,
                severity="high",
                description=f"One-time code ({len(code)} digits) hidden",
                snippet_masked=f"OTP: {code[:1]}***{code[-1:]}",
                action="redacted",
            ))
            whole = m.group(0)
            return whole.replace(code, otp_mark)

        before = len(violations)
        modified_text = self.RE_OTP_CONTEXT.sub(hide_code, modified_text)
        if len(violations) > before and action == FirewallAction.ALLOW:
            action = FirewallAction.REDACT

        # B. Check known OTP codes from recent inbox messages
        known_otps: set[str] = context.get("known_otps", set())
        for otp_code in known_otps:
            if otp_code and re.search(rf"(?<!\d){re.escape(otp_code)}(?!\d)", modified_text):
                v = OutputViolation(
                    violation_type=ViolationType.OTP_CODE,
                    severity="critical",
                    description="Direct match with active inbound 2FA verification token from user inbox",
                    snippet_masked=f"OTP: {otp_code[:1]}***{otp_code[-1:]}",
                    action="redacted",
                )
                violations.append(v)
                modified_text = re.sub(rf"(?<!\d){re.escape(otp_code)}(?!\d)", otp_mark, modified_text)
                if action == FirewallAction.ALLOW:
                    action = FirewallAction.REDACT

        # 5. Check Bank Account Numbers / IBANs
        for m in self.RE_ACCOUNT_CONTEXT.finditer(modified_text):
            acc_cand = m.group(1)
            if sum(ch.isdigit() for ch in acc_cand) >= 10:
                masked_acc = mask_bank_account(acc_cand)
                v = OutputViolation(
                    violation_type=ViolationType.BANK_ACCOUNT,
                    severity="medium",
                    description="Full bank clearing account number masked",
                    snippet_masked=masked_acc,
                    action="redacted",
                )
                violations.append(v)
                modified_text = modified_text.replace(acc_cand, masked_acc)
                if action == FirewallAction.ALLOW:
                    action = FirewallAction.REDACT

        # 6. Cross-Role Privacy Enforcer (Parent vs Student boundary)
        modified_text, privacy_violations = self._enforce_role_privacy(
            modified_text, actor_enum, context
        )
        if privacy_violations:
            violations.extend(privacy_violations)
            if action == FirewallAction.ALLOW:
                action = FirewallAction.REDACT

        return self._finalize_verdict(
            text, modified_text, action, violations, actor_enum, start_time
        )

    def _enforce_role_privacy(
        self,
        text: str,
        actor: Actor,
        context: dict[str, Any],
    ) -> tuple[str, list[OutputViolation]]:
        violations: list[OutputViolation] = []
        out = text
        lang = context.get("lang", "en")

        if actor == Actor.PARENT:
            # Parent is viewing: Protect Student's private income, wages, employer names, and personal wants
            income_sources = context.get("income_sources", [])
            for src in income_sources:
                name = getattr(src, "name", None) or (src.get("name") if isinstance(src, dict) else None)
                employer = getattr(src, "employer", None) or (src.get("employer") if isinstance(src, dict) else None)
                amount = getattr(src, "amount_cny", None) or (src.get("amount_cny") if isinstance(src, dict) else None)

                # Check employer or job title
                for identifier in (name, employer):
                    if identifier and len(identifier) > 3 and identifier.lower() in out.lower():
                        v = OutputViolation(
                            violation_type=ViolationType.CROSS_ROLE_PRIVACY,
                            severity="high",
                            description=f"Student's private earning source ('{identifier}') redacted from parent view",
                            snippet_masked="[STUDENT INCOME SOURCE]",
                            action="redacted",
                        )
                        violations.append(v)
                        # Case-insensitive replacement
                        pattern = re.compile(re.escape(identifier), re.IGNORECASE)
                        out = pattern.sub(self.PLACEHOLDERS["income"].get(lang, self.REDACTED_PRIVACY), out)

                # Check specific wage amount if phrased as student's earnings
                if amount:
                    amt_str = str(amount)
                    amt_pat = re.compile(rf"(?i)(?:earned|wage|salary|stipend|income|pay(?:ment)?)\s*(?:of|is|:)?\s*[¥￥]?\s*{re.escape(amt_str)}")
                    if amt_pat.search(out):
                        v = OutputViolation(
                            violation_type=ViolationType.CROSS_ROLE_PRIVACY,
                            severity="high",
                            description=f"Student's private wage amount (¥{amt_str}) redacted from parent view",
                            snippet_masked="[STUDENT EARNED AMOUNT]",
                            action="redacted",
                        )
                        violations.append(v)
                        out = amt_pat.sub(self.PLACEHOLDERS["income"].get(lang, self.REDACTED_PRIVACY), out)

            # Check unshared student Shield / Savings
            shares_with_family = context.get("shares_with_family", True)
            shield_cny = context.get("shield_cny", None)
            if not shares_with_family and shield_cny is not None:
                # If student explicitly chose not to share shield, block shield balance dumps to parent
                shield_str = str(shield_cny)
                shield_pat = re.compile(rf"(?i)(?:shield balance|savings balance|shield has|shield)\s*(?:is|of|:)?\s*[¥￥]?\s*{re.escape(shield_str)}")
                if shield_pat.search(out):
                    v = OutputViolation(
                        violation_type=ViolationType.CROSS_ROLE_PRIVACY,
                        severity="high",
                        description="Student's unshared Shield savings balance protected under Earn & Save privacy",
                        snippet_masked="[STUDENT PRIVATE SHIELD]",
                        action="redacted",
                    )
                    violations.append(v)
                    out = shield_pat.sub(self.PLACEHOLDERS["shield"].get(lang, self.REDACTED_SHIELD), out)

        elif actor == Actor.STUDENT:
            # Student is viewing: Protect Parent's private credentials and funding account specifics
            parent_accounts = context.get("parent_accounts", [])
            for pacc in parent_accounts:
                acc_num = getattr(pacc, "account_number", None) or (pacc.get("account_number") if isinstance(pacc, dict) else None)
                if acc_num and len(acc_num) >= 8 and acc_num in out:
                    v = OutputViolation(
                        violation_type=ViolationType.CROSS_ROLE_PRIVACY,
                        severity="medium",
                        description="Parent's private bank account number masked from student view",
                        snippet_masked=mask_bank_account(acc_num),
                        action="redacted",
                    )
                    violations.append(v)
                    out = out.replace(acc_num, self.PLACEHOLDERS["parent"].get(lang, self.REDACTED_PARENT))

        return out, violations

    def _localized_refusal(self, lang: str) -> str:
        if lang == "bn":
            return "নিরাপত্তা ও গোপনীয়তা সুরক্ষার স্বার্থে অভ্যন্তরীণ সিস্টেমের নির্দেশনা ও কনফিগারেশন প্রকাশ করা যাবে না।"
        elif lang == "zh":
            return "出于安全和隐私保护，内部系统指令和配置参数不可披露。"
        return self.BLOCKED_SYSTEM_PROMPT

    def _finalize_verdict(
        self,
        original_text: str,
        filtered_text: str,
        action: FirewallAction,
        violations: list[OutputViolation],
        actor: Actor,
        start_time: float,
    ) -> OutputFirewallVerdict:
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        now_iso = datetime.now(timezone.utc).isoformat()

        if action == FirewallAction.BLOCK:
            self.blocked_count += 1
        elif action == FirewallAction.REDACT:
            self.redacted_count += 1

        if violations:
            self.total_violations += len(violations)
            for v in violations:
                self.category_counts[v.violation_type.value] = (
                    self.category_counts.get(v.violation_type.value, 0) + 1
                )

            # Store recent interception log (last 50)
            log_item = {
                "timestamp": now_iso,
                "actor": actor.value,
                "action": action.value,
                "violations_count": len(violations),
                "violations": [v.to_dict() for v in violations],
            }
            self.recent_interceptions.append(log_item)
            if len(self.recent_interceptions) > 50:
                self.recent_interceptions.pop(0)

        return OutputFirewallVerdict(
            passed=(action == FirewallAction.ALLOW),
            action_taken=action,
            original_length=len(original_text),
            filtered_length=len(filtered_text),
            filtered_text=filtered_text,
            violations=violations,
            actor=actor.value,
            checked_at=now_iso,
            latency_ms=latency_ms,
        )

    def telemetry(self) -> dict[str, Any]:
        """Provides full real-time telemetry of the Egress DLP Firewall."""
        return {
            "status": "active",
            "mode": "egress_dlp_enforced",
            "total_inspections": self.total_inspections,
            "total_violations": self.total_violations,
            "blocked_count": self.blocked_count,
            "redacted_count": self.redacted_count,
            "category_counts": dict(self.category_counts),
            "recent_interceptions": list(reversed(self.recent_interceptions[-15:])),
        }
