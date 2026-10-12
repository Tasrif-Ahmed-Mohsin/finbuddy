"""Data minimisation: keep only messages that are about money.

Everything else (personal chats, promotions) is dropped immediately and never stored. Messages with
scam signals are kept even from unknown senders, so the user can be warned.
"""
from __future__ import annotations

from app.security.scam import contains_term

KNOWN_SENDERS = [
    # Bangladesh banks and mobile wallets
    "brac", "bracbank", "dbbl", "dutch-bangla", "citybank", "city bank", "sonali", "ebl", "eastern bank", "prime bank",
    "mtb", "dhaka bank", "standard chartered", "scb", "islami bank", "bkash", "nagad", "rocket", "upay",
    # China banks and wallets (short codes are the banks' official SMS numbers)
    "icbc", "bank of china", "boc", "ccb", "abc", "cmb", "95588", "95566", "95533", "95599", "95555",
    "alipay", "支付宝", "wechat pay", "微信支付", "工商银行", "中国银行", "建设银行", "农业银行", "招商银行",
    # Education
    "university", "finance office", "bursar", "大学", "财务处",
]

MONEY_TERMS = [
    "debited", "credited", "withdrawal", "withdrawn", "a/c", "card ending", "account", "balance", "avl bal",
    "transaction", "txn", "remittance", "tuition", "invoice", "payment", "transfer", "deposit", "fee", "refund",
    "bdt", "cny", "rmb", "usd", "tk", "otp", "card", "kyc",
    "余额", "尾号", "交易", "支出", "收入", "取款", "消费", "转账", "汇款", "学费", "验证码", "元",
    "টাকা", "জমা", "উত্তোলন", "ব্যালেন্স", "লেনদেন", "৳",
]


def is_financial(sender: str, text: str) -> bool:
    s = (sender or "").lower()
    if any(k in s for k in KNOWN_SENDERS):
        return True
    return sum(1 for t in MONEY_TERMS if contains_term(text, t)) >= 2
