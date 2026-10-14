"""Scam, informal-channel and prompt-injection detection for messages and documents.

Messages and uploaded documents are DATA, never instructions. This module flags patterns from the
research (P-09 discount agents, P-24 impersonation, P-25 money mules, N-08 hundi) and common
prompt-injection phrasing, in English, Bengali (script + romanised) and Chinese.
Rule-based on purpose: transparent, testable, and it works even when the LLM is unavailable.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

PATTERNS: dict[str, list[str]] = {
    "informal_channel": ["hundi", "hundee", "হুন্ডি", "হুণ্ডি", "地下钱庄"],
    "crypto": ["bitcoin", "usdt", "tether", "crypto", "gift card", "比特币", "泰达币", "虚拟货币", "ক্রিপ্টো"],
    "discount_agent": [
        "discount on tuition", "tuition discount", "cheaper tuition", "pay through me", "pay through my agency",
        "pay your fees for you", "% cheaper", "% off tuition", "ছাড়ে টিউশন", "কম খরচে টিউশন", "代缴学费", "学费优惠",
    ],
    "impersonation": [
        "supervisory account", "safe account", "your id was used", "your passport was used", "police case",
        "安全账户", "监管账户", "公安局", "涉嫌洗钱", "পুলিশ কেস",
        "parcel contains", "illegal items in your parcel", "arrest warrant", "包裹里有", "逮捕令", "গ্রেপ্তারি পরোয়ানা",
    ],
    "fake_emergency": [
        "has been arrested", "been kidnapped", "kidnapped", "ransom", "in police custody", "accident and needs money",
        "অপহরণ", "অপহৃত", "গ্রেপ্তার হয়েছে", "মুক্তিপণ", "绑架", "赎金", "被拘留", "被警察抓",
    ],
    "money_mule": [
        "rent your bank card", "lend your card", "use your account", "easy money", "receive money for me",
        "借卡", "租卡", "出租银行卡", "কার্ড ভাড়া", "অ্যাকাউন্ট ভাড়া",
    ],
    "secrecy_pressure": ["don't tell anyone", "do not tell your parents", "keep this secret", "保密", "কাউকে বলবেন না"],
    "phishing": [
        "verify your kyc", "update your kyc", "kyc", "is blocked", "will be blocked", "account suspended",
        "verify your account", "verify your card", "click the link", "账户冻结", "账户异常", "点击链接",
        "কেওয়াইসি", "অ্যাকাউন্ট ব্লক",
    ],
    "prompt_injection": [
        "ignore previous instructions", "ignore all previous", "disregard your instructions", "you are now",
        "system prompt", "approve this transfer", "execute the transfer", "skip the approval", "change the payee",
        "忽略之前的指令", "আগের নির্দেশ উপেক্ষা",
    ],
}

SEVERITY = {
    "informal_channel": "high",
    "crypto": "high",
    "discount_agent": "high",
    "impersonation": "high",
    "fake_emergency": "high",
    "money_mule": "high",
    "secrecy_pressure": "medium",
    "phishing": "high",
    "prompt_injection": "high",
}

ADVICE = {
    "informal_channel": "Hundi is illegal and unprotected, and it forfeits Bangladesh's 2.5% formal-channel incentive. Use a bank transfer.",
    "crypto": "Crypto transfers are restricted in both Bangladesh and China, and the words alone can freeze a bank account.",
    "discount_agent": "'Discount tuition' agents often pay with stolen cards; the payment bounces and you still owe the full fee. Pay only the university's official account.",
    "impersonation": "Real police, banks and embassies never ask you to move money to a 'safe' or 'supervisory' account. Hang up and check yourself: in China call 110 or the anti-fraud line 96110. See Emergency in the app.",
    "fake_emergency": "Scammers tell families a student was arrested, kidnapped or hurt and demand money fast. Do not pay. Call the student directly and use 'Are you safe?' in the app's Emergency screen.",
    "money_mule": "Letting others use your card or account is a crime and gets your account frozen by police.",
    "secrecy_pressure": "Pressure to act fast or in secret is a classic scam sign. Talk to your family or the international office first.",
    "prompt_injection": "This content tries to give instructions to the assistant. Documents are treated as data only; nothing was executed.",
    "phishing": "Banks never ask you to verify your card or KYC through an SMS link. Do not click; open your bank app or call the number on your card.",
}


@dataclass
class Flag:
    category: str
    term: str
    severity: str

    def to_dict(self) -> dict:
        return {"category": self.category, "term": self.term, "severity": self.severity, "advice": ADVICE[self.category]}


def contains_term(text: str, term: str) -> bool:
    """Whole-word match for ASCII terms (so 'eth' does not match 'method'); substring otherwise."""
    if term.isascii():
        t = term.lower()
        left = r"(?<![a-z0-9])" if t[0].isalnum() else ""
        right = r"(?![a-z0-9])" if t[-1].isalnum() else ""
        return re.search(left + re.escape(t) + right, text.lower()) is not None
    return term in text


def scan_text(text: str) -> list[Flag]:
    flags: list[Flag] = []
    for category, terms in PATTERNS.items():
        for term in terms:
            if contains_term(text, term):
                flags.append(Flag(category, term, SEVERITY[category]))
                break  # one flag per category is enough
    return flags


def has_high_risk(flags: list[Flag]) -> bool:
    return any(f.severity == "high" for f in flags)
