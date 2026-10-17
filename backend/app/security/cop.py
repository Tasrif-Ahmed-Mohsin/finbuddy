"""Confirmation of Payee (CoP) Engine.

Modeled on the UK Payment Systems Regulator (PSR) Specific Direction 10/17 and the
EU Instant Payments Regulation (VoP - Verification of Payee, 2024/886):
- Queries receiving bank account records before payment execution.
- Compares the intended payee name against the official legal account holder name.
- Categorizes outcomes into MATCH, CLOSE_MATCH, NO_MATCH, or OPTED_OUT.
- Protects against Authorised Push Payment (APP) scams, invoice redirection, and accidental misrouting.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class CopStatus(str, Enum):
    MATCH = "match"                # Full or exact legal match
    CLOSE_MATCH = "close_match"    # Minor variation, typo, or alias
    NO_MATCH = "no_match"          # Name does not match registered account (APP Scam Warning)
    OPTED_OUT = "opted_out"        # Account holder opted out
    UNAVAILABLE = "unavailable"    # Receiving bank responder unavailable


class AccountType(str, Enum):
    BUSINESS = "business"
    PERSONAL = "personal"


@dataclass
class CopRecord:
    """Official account registration record held by the receiving clearing bank."""
    account_id: str
    account_number_masked: str
    registered_name: str
    account_type: AccountType
    bank_name: str
    bic: str
    aliases: list[str] = field(default_factory=list)
    cop_enabled: bool = True


@dataclass
class CopVerification:
    """Outcome of a real-time Confirmation of Payee verification check."""
    status: CopStatus
    intended_name: str
    registered_name: str
    account_type: AccountType
    match_score: float
    bank_name: str
    bic: str
    app_scam_risk: str  # "low", "medium", "critical"
    reason: str
    advice: str
    verified_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "intended_name": self.intended_name,
            "registered_name": self.registered_name,
            "account_type": self.account_type.value,
            "match_score": round(self.match_score, 3),
            "bank_name": self.bank_name,
            "bic": self.bic,
            "app_scam_risk": self.app_scam_risk,
            "reason": self.reason,
            "advice": self.advice,
            "verified_at": self.verified_at,
        }


def _normalize_name(name: str) -> str:
    """Normalizes company / institutional / personal names for CoP token comparison."""
    n = name.lower()
    # Strip common legal suffixes and noise words
    noise = [
        r"\bltd\b", r"\blimited\b", r"\binc\b", r"\bcorp\b", r"\bco\b",
        r"\bllc\b", r"\boffice\b", r"\bfinance\b", r"\bdepartment\b",
        r"\buniversity\b", r"\buniv\b", r"\bthe\b", r"\bof\b", r"\band\b",
        r"[-_.,/()'\"]",
    ]
    for pattern in noise:
        n = re.sub(pattern, " ", n)
    return " ".join(n.split())


class ConfirmationOfPayeeService:
    """Receiving Bank Confirmation of Payee (CoP) Simulator."""

    def __init__(self):
        # Receiving bank registered legal accounts
        self.directory: dict[str, CopRecord] = {
            "univ_demo": CopRecord(
                account_id="univ_demo",
                account_number_masked="****6021",
                registered_name="Demo University Finance Office",
                account_type=AccountType.BUSINESS,
                bank_name="Sandbox Bank of China (Beijing Branch)",
                bic="BKCHCNBJXXX",
                aliases=["Demo University", "Demo Univ", "Demo University Tuition"],
            ),
            "student_own_cn": CopRecord(
                account_id="student_own_cn",
                account_number_masked="****3317",
                registered_name="Demo Student",
                account_type=AccountType.PERSONAL,
                bank_name="Sandbox Bank of China (Beijing Branch)",
                bic="BKCHCNBJXXX",
                aliases=["Demo Student Account"],
            ),
            "agent_x": CopRecord(
                account_id="agent_x",
                account_number_masked="****9999",
                registered_name="Shenzhen Apex Trading Co. Ltd",
                account_type=AccountType.BUSINESS,
                bank_name="Sandbox Unknown Bank",
                bic="UNKNCNXXXXX",
                aliases=[],  # Rogue account pretending to be 'Fast Tuition Agency'
            ),
        }

    def verify_payee(
        self,
        payee_id: str,
        intended_name: str | None = None,
    ) -> CopVerification:
        """Executes a Confirmation of Payee inquiry against the receiving bank directory."""
        now_str = datetime.now(timezone.utc).isoformat()
        rec = self.directory.get(payee_id)

        if rec is None:
            return CopVerification(
                status=CopStatus.UNAVAILABLE,
                intended_name=intended_name or "Unknown",
                registered_name="Not Found in Receiving Bank Directory",
                account_type=AccountType.BUSINESS,
                match_score=0.0,
                bank_name="Unknown Clearing Bank",
                bic="UNKNOWN",
                app_scam_risk="critical",
                reason="The destination account was not found in the receiving bank's directory.",
                advice="Do not proceed. The account details could not be verified by the receiving bank.",
                verified_at=now_str,
            )

        target_name = (intended_name or rec.registered_name).strip()

        # Check for exact case-insensitive match or known official alias
        if target_name.lower() == rec.registered_name.lower() or any(
            target_name.lower() == a.lower() for a in rec.aliases
        ):
            return CopVerification(
                status=CopStatus.MATCH,
                intended_name=target_name,
                registered_name=rec.registered_name,
                account_type=rec.account_type,
                match_score=1.0,
                bank_name=rec.bank_name,
                bic=rec.bic,
                app_scam_risk="low",
                reason=f"Account name verified: matched '{rec.registered_name}' with receiving bank records.",
                advice="Safe to proceed: the account holder matches the intended recipient.",
                verified_at=now_str,
            )

        # Compute token-based and sequence similarity
        norm_intended = _normalize_name(target_name)
        norm_registered = _normalize_name(rec.registered_name)

        seq_score = difflib.SequenceMatcher(None, norm_intended, norm_registered).ratio()

        # Check aliases
        best_alias_score = 0.0
        for alias in rec.aliases:
            score = difflib.SequenceMatcher(None, norm_intended, _normalize_name(alias)).ratio()
            if score > best_alias_score:
                best_alias_score = score

        final_score = max(seq_score, best_alias_score)

        if final_score >= 0.82:
            return CopVerification(
                status=CopStatus.MATCH,
                intended_name=target_name,
                registered_name=rec.registered_name,
                account_type=rec.account_type,
                match_score=final_score,
                bank_name=rec.bank_name,
                bic=rec.bic,
                app_scam_risk="low",
                reason=f"Account name matched '{rec.registered_name}' (Score: {final_score:.2f}).",
                advice="Safe to proceed: name matches official bank records.",
                verified_at=now_str,
            )

        if final_score >= 0.50:
            return CopVerification(
                status=CopStatus.CLOSE_MATCH,
                intended_name=target_name,
                registered_name=rec.registered_name,
                account_type=rec.account_type,
                match_score=final_score,
                bank_name=rec.bank_name,
                bic=rec.bic,
                app_scam_risk="medium",
                reason=(
                    f"Close match: the name registered on this account is '{rec.registered_name}', "
                    f"which differs slightly from '{target_name}'."
                ),
                advice=(
                    f"Check carefully: did you mean '{rec.registered_name}'? If someone asked you to "
                    f"type a different name, stop and verify directly."
                ),
                verified_at=now_str,
            )

        # No Match: Significant discrepancy (Authorised Push Payment scam indicator)
        return CopVerification(
            status=CopStatus.NO_MATCH,
            intended_name=target_name,
            registered_name=rec.registered_name,
            account_type=rec.account_type,
            match_score=final_score,
            bank_name=rec.bank_name,
            bic=rec.bic,
            app_scam_risk="critical",
            reason=(
                f"Confirmation of Payee FAILED: Account belongs to '{rec.registered_name}', "
                f"NOT '{target_name}'. Authorised Push Payment (APP) fraud detected."
            ),
            advice=(
                f"DO NOT SEND MONEY: Fraudsters often instruct victims to enter a university or friend's name, "
                f"while giving the bank account of a shell company ({rec.registered_name})."
            ),
            verified_at=now_str,
        )
