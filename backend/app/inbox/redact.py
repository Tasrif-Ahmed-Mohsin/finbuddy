"""Privacy first: redact a message BEFORE it is stored or sent to any LLM.

  * One-time codes (OTP / 验证码 / ওটিপি): the code itself is removed. Sathi never stores, shows or
    forwards an OTP, and never asks for one.
  * Long numbers (account, card, phone: 9–19 digits) are masked to their last 4 digits.
  * Email addresses are masked.
Amounts (with decimals or thousands separators) are left intact so transactions can be tracked.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.security.scam import contains_term

OTP_TERMS = [
    "otp", "one time password", "one-time password", "verification code", "security code", "passcode", "pin code",
    "验证码", "动态码", "校验码", "动态密码", "ওটিপি", "ভেরিফিকেশন কোড", "গোপন কোড",
]

LONG_NUMBER = re.compile(r"(?<![\d.,])\d{9,19}(?![\d.,]\d)")
SHORT_CODE = re.compile(r"(?<![\d.,])\d{4,8}(?![\d.,]\d)")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


@dataclass
class Redaction:
    text: str
    otp: bool
    masked: int


def redact(text: str) -> Redaction:
    otp = any(contains_term(text, t) for t in OTP_TERMS)
    masked = 0

    def mask(m: re.Match) -> str:
        nonlocal masked
        masked += 1
        return "••••" + m.group()[-4:]

    out = LONG_NUMBER.sub(mask, text)
    out = EMAIL.sub("[email]", out)
    if otp:
        out = SHORT_CODE.sub("[code removed]", out)
    return Redaction(out, otp, masked)
