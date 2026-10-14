"""Conversation skills the judges score: clarification, correction, refusal and fallback.

The DeepSeek agent follows the same rules through its system prompt and tools; this module is the
deterministic version used offline (and the source of truth for what "vague" or "a correction" means):

  * Clarify: a payment request without an amount or a purpose gets ONE short question with the real options
    (tuition to the university, or living money to the student's own account) instead of a guessed draft.
  * Correct: "no, I meant ¥2,500" changes the draft prepared in this chat (the old one is cancelled), and
    "cancel" drops it. Nothing is ever sent from the chat: people approve in the app with a fingerprint.
  * Refuse: requests to approve, bypass limits or change who gets paid (privilege escalation), and requests for
    codes, PINs or full card numbers (data extraction), get a plain refusal that explains why.
"""
from __future__ import annotations

import re
from decimal import ROUND_FLOOR, Decimal

DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
CNY_MARK = r"(?:¥|cny|rmb|yuan|ইউয়ান|ইউআন|元|块)"
NUM = r"(\d+(?:\.\d+)?)"
BDT_MARK = re.compile(r"৳|টাকা|taka|\btk\b|bdt|lakh|লাখ|লক্ষ|হাজার", re.IGNORECASE)

TUITION = ("tuition", "semester fee", "university fee", "টিউশন", "সেমিস্টার ফি", "বিশ্ববিদ্যালয়ের ফি", "学费")
LIVING = ("living", "own account", "my account", "chinese account", "allowance", "rent", "pocket money", "মাসিক খরচ",
          "হাত খরচ", "খরচের টাকা", "চীনের অ্যাকাউন্ট", "নিজের অ্যাকাউন্ট", "生活费", "我的账户", "房租")
SEND = ("send", "pay ", "pay my", "pay the", "transfer", "remit", "prepare a payment", "prepare the payment", "পাঠাও",
        "পাঠান", "পাঠাতে", "পাঠিয়ে", "পেমেন্ট করো", "পেমেন্ট করুন", "দিয়ে দাও", "汇款", "汇", "转账", "付款", "支付", "打钱")
QUESTION = ("?", "？", "when ", "how ", "what ", "which ", "should i", "কবে", "কখন", "কিভাবে", "কীভাবে", "কেমন", "কত ",
            "什么", "怎么", "何时", "多少", "吗")
CORRECTION = ("no,", "no ", "not ", "actually", "i meant", "i mean", "change it", "make it", "instead", "wrong", "না,", "না ",
              "আসলে", "বদলে", "ভুল", "না, ", "不是", "改成", "其实", "错了", "改为")
CANCEL = ("cancel", "don't send", "do not send", "stop the payment", "বাতিল", "পাঠাবেন না", "পাঠিও না", "পাঠাবে না", "取消",
          "不要汇", "别汇")
CONFIRM = ("yes", "ok", "okay", "sure", "go ahead", "please do", "হ্যাঁ", "হ্যা", "জি", "ঠিক আছে", "আচ্ছা", "是", "好", "可以",
           "对", "行")
ESCALATE = ("approve it", "approve the", "approve this", "approve my", "you approve", "execute", "send it now",
            "send it yourself", "do it yourself", "without approval", "without my approval", "skip approval",
            "skip the approval", "bypass", "override", "raise the limit", "increase the limit", "raise my limit",
            "remove the limit", "change the mandate", "change the payee", "you are admin", "admin mode", "developer mode",
            "god mode", "অনুমোদন করে দাও", "অনুমোদন দিয়ে দাও", "তুমি অনুমোদন", "আপনি অনুমোদন", "নিজে পাঠাও", "নিজেই পাঠাও",
            "সীমা বাড়াও", "批准", "直接汇", "跳过", "管理员", "提高限额")
SECRET_WORDS = ("one-time code", "one time code", "verification code", "password", "card number", "account number",
                "full number", "api key", "secret key", "system prompt", "your instructions", "your rules", "ওটিপি", "পিন",
                "পাসওয়ার্ড", "কার্ড নম্বর", "কার্ডের নম্বর", "অ্যাকাউন্ট নম্বর", "验证码", "密码", "卡号", "账号", "提示词",
                "系统指令")
SECRET_SHORT = re.compile(r"\b(otp|pin|cvv|cvc|token)\b", re.IGNORECASE)


def normalise(text: str) -> str:
    t = (text or "").translate(DIGITS)
    return re.sub(r"(?<=\d),(?=\d)", "", t)


def has_any(text: str, words) -> bool:
    t = text.lower()
    return any(w in t for w in words)


def find_amount(text: str) -> tuple[Decimal | None, str | None]:
    """(amount, currency): CNY when marked as yuan, BDT when written in taka/lakh, None when unmarked."""
    t = normalise(text).lower()
    m = re.search(CNY_MARK + r"\s*" + NUM, t) or re.search(NUM + r"\s*" + CNY_MARK, t)
    if m:
        return Decimal(m.group(1)), "CNY"
    if BDT_MARK.search(t):
        from app.agent.mandate_compiler import parse_rules  # lakh / হাজার / compound amounts
        amounts = parse_rules(text).amounts
        if amounts:
            return max(amounts), "BDT"
    m = re.search(r"(?<![\d.])" + NUM + r"(?![\d.])", t)
    if m and Decimal(m.group(1)) >= 100:  # small numbers are days, counts or dates, not payments
        return Decimal(m.group(1)), None
    return None, None


def find_purpose(text: str) -> str | None:
    if has_any(text, TUITION):
        return "tt_tuition"
    if has_any(text, LIVING):
        return "tt_living"
    return None


def is_send_intent(text: str) -> bool:
    return has_any(text, SEND) and not has_any(text, QUESTION)


def is_confirmation(text: str) -> bool:
    t = text.strip().lower().rstrip("!.। ")
    return any(t == w or t.startswith(w + " ") or t.startswith(w + ",") for w in CONFIRM)


def asks_for_secrets(text: str) -> bool:
    return has_any(text, SECRET_WORDS) or bool(SECRET_SHORT.search(text))


def bdt_to_cny(bdt: Decimal, bdt_per_cny: Decimal) -> Decimal:
    """Round DOWN to ¥100 so the payment never costs more taka than the user named (fees are extra)."""
    return (bdt / bdt_per_cny / 100).quantize(Decimal(1), rounding=ROUND_FLOOR) * 100


PURPOSE = {"tt_tuition": {"en": "tuition", "bn": "টিউশন", "zh": "学费"},
           "tt_living": {"en": "living money", "bn": "মাসিক খরচ", "zh": "生活费"}}
WHO = {("parent",): {"en": "the parent", "bn": "অভিভাবক", "zh": "家长"},
       ("parent", "student"): {"en": "the parent and the student", "bn": "অভিভাবক ও শিক্ষার্থী", "zh": "家长和学生"},
       ("student",): {"en": "the student", "bn": "শিক্ষার্থী", "zh": "学生"}}

NO_MONEY = ("no money", "out of money", "ran out of money", "run out of money", "have no money", "money is finished",
            "টাকা শেষ", "টাকা নেই", "হাতে টাকা নেই", "没钱", "钱用完", "没有钱了")
TEXT = {
    "en": {
        "clarify_both": "Sure. How much, and for what?\n• Tuition to {univ} (fee notice {tuition}, send by {send_by})\n"
                        "• Living money to your own Chinese account (about {living} a month)\nFor example: \"send ¥3,000 living money\".",
        "clarify_purpose": "Is {amount} for tuition (to {univ}) or living money (to your own Chinese account)?",
        "confirm_tuition": "Prepare the full tuition from the fee notice, {amount}, to {univ}? Say \"yes\" or give another amount.",
        "confirm_living": "Prepare one month of living money, {amount}, to your own Chinese account? Say \"yes\" or give another amount.",
        "confirm_bdt": "Payments are prepared in yuan: {bdt} is about {amount} at today's market rate (bank fees come on top). "
                       "Prepare {amount} as {purpose}? Say \"yes\" or give the amount in yuan.",
        "drafted": "📝 Prepared, not sent: {amount} {purpose} to {payee}, about {total} in total. {who} must approve it in the app "
                   "with a fingerprint. Say \"no, I meant ¥…\" to change it or \"cancel\" to drop it.",
        "drafted_blocked": "⛔ I prepared it, but the safety checks blocked it: {why}",
        "revised": "✏️ Changed: the {old} draft is cancelled and a new one is ready, {amount} {purpose}, about {total}. "
                   "Approve the new one in the app.",
        "cancelled": "🗑️ Cancelled the {amount} draft. Nothing was sent.",
        "emergency_more": "Open Emergency in the app to ask the family with one tap (the parent approves with fingerprint).",
        "nothing_to_change": "There is no payment draft from this chat to change. Tell me the amount and purpose, for example "
                             "\"send ¥3,000 living money\".",
        "cannot_approve": "I can't approve or send money, raise limits or change who gets paid, whoever asks. Only you can approve, "
                          "in the app with your fingerprint (Family → Payments waiting). That keeps your money safe even if "
                          "someone tricks me.",
        "no_secrets": "I never show or ask for codes, PINs, passwords or full card and account numbers, and I don't reveal my "
                      "internal settings. I only ever see the last 4 digits, like ****3317. If anyone asks you for a code, "
                      "it is a scam: don't share it.",
        "mandate_cancel": "To cancel the family mandate, open Family and tap \"Cancel the mandate\". Either of you can do it in one tap.",
    },
    "bn": {
        "clarify_both": "অবশ্যই। কত টাকা, আর কিসের জন্য?\n• {univ}-এ টিউশন (ফি নোটিশ {tuition}, পাঠানোর শেষ দিন {send_by})\n"
                        "• আপনার নিজের চীনের অ্যাকাউন্টে মাসিক খরচ (মাসে প্রায় {living})\nযেমন: \"৩০০০ ইউয়ান মাসিক খরচ পাঠাও\"।",
        "clarify_purpose": "{amount} কি টিউশনের জন্য ({univ}-এ), নাকি মাসিক খরচ (আপনার নিজের চীনের অ্যাকাউন্টে)?",
        "confirm_tuition": "ফি নোটিশ অনুযায়ী পুরো টিউশন {amount} {univ}-এ পাঠানোর খসড়া করব? \"হ্যাঁ\" বলুন, অথবা অন্য পরিমাণ লিখুন।",
        "confirm_living": "এক মাসের খরচ {amount} আপনার নিজের চীনের অ্যাকাউন্টে পাঠানোর খসড়া করব? \"হ্যাঁ\" বলুন, অথবা অন্য পরিমাণ লিখুন।",
        "confirm_bdt": "পেমেন্ট ইউয়ানে তৈরি হয়: আজকের বাজার দরে {bdt} প্রায় {amount} (ব্যাংকের ফি আলাদা)। {purpose} হিসেবে {amount} "
                       "এর খসড়া করব? \"হ্যাঁ\" বলুন, অথবা ইউয়ানে পরিমাণ লিখুন।",
        "drafted": "📝 খসড়া তৈরি, পাঠানো হয়নি: {amount} {purpose}, {payee}-এ, মোট প্রায় {total}। {who} অ্যাপে আঙুলের ছাপ দিয়ে "
                   "অনুমোদন করবেন। বদলাতে বলুন \"না, ¥… হবে\", বাদ দিতে বলুন \"বাতিল\"।",
        "drafted_blocked": "⛔ খসড়া করেছি, কিন্তু নিরাপত্তা যাচাইয়ে আটকে গেছে: {why}",
        "revised": "✏️ বদলানো হয়েছে: আগের {old} খসড়া বাতিল, নতুন খসড়া {amount} {purpose}, মোট প্রায় {total}। নতুনটি অ্যাপে অনুমোদন করুন।",
        "cancelled": "🗑️ {amount} এর খসড়া বাতিল করেছি। কিছুই পাঠানো হয়নি।",
        "emergency_more": "এক চাপে পরিবারকে জানাতে অ্যাপে জরুরি পাতা খুলুন (অভিভাবক আঙুলের ছাপ দিয়ে অনুমোদন দেবেন)।",
        "nothing_to_change": "এই চ্যাটে বদলানোর মতো কোনো পেমেন্টের খসড়া নেই। পরিমাণ আর উদ্দেশ্য বলুন, যেমন \"৩০০০ ইউয়ান মাসিক খরচ পাঠাও\"।",
        "cannot_approve": "যে-ই বলুক, আমি টাকা অনুমোদন করতে বা পাঠাতে পারি না, সীমা বাড়াতে পারি না, প্রাপকও বদলাতে পারি না। "
                          "অনুমোদন শুধু আপনি দিতে পারেন, অ্যাপে আঙুলের ছাপ দিয়ে (পরিবার → অপেক্ষমাণ পেমেন্ট)। তাই কেউ আমাকে "
                          "ধোঁকা দিলেও আপনার টাকা নিরাপদ।",
        "no_secrets": "আমি কখনো কোড, পিন, পাসওয়ার্ড বা পুরো কার্ড/অ্যাকাউন্ট নম্বর দেখাই না বা চাই না, আর আমার ভেতরের সেটিংসও জানাই না। "
                      "আমি শুধু শেষ ৪টি সংখ্যা দেখি, যেমন ****3317। কেউ কোড চাইলে সেটা প্রতারণা: কাউকে দেবেন না।",
        "mandate_cancel": "পারিবারিক ম্যান্ডেট বাতিল করতে 'পরিবার' পাতায় \"ম্যান্ডেট বাতিল করুন\" চাপুন। আপনাদের যে কেউ এক চাপে করতে পারেন।",
    },
    "zh": {
        "clarify_both": "好的。要汇多少、用途是什么？\n• 学费，汇给{univ}（缴费通知 {tuition}，最晚 {send_by} 汇出）\n"
                        "• 生活费，汇到你本人的中国账户（每月约 {living}）\n例如：“汇 ¥3,000 生活费”。",
        "clarify_purpose": "{amount} 是学费（汇给{univ}）还是生活费（汇到你本人的中国账户）？",
        "confirm_tuition": "按缴费通知准备全额学费 {amount}，汇给{univ}吗？回复“是”，或告诉我其他金额。",
        "confirm_living": "准备一个月生活费 {amount}，汇到你本人的中国账户吗？回复“是”，或告诉我其他金额。",
        "confirm_bdt": "付款以人民币准备：按今天的市场汇率 {bdt} 约合 {amount}（银行费用另计）。按{purpose}准备 {amount} 吗？回复“是”，"
                       "或直接告诉我人民币金额。",
        "drafted": "📝 已准备（尚未汇出）：{amount} {purpose}，收款方 {payee}，总计约 {total}。需要{who}在应用中用指纹批准。"
                   "说“不是，是 ¥…”可修改，说“取消”可放弃。",
        "drafted_blocked": "⛔ 已准备，但被安全检查拦截：{why}",
        "revised": "✏️ 已修改：原来 {old} 的草稿已取消，新草稿为 {amount} {purpose}，总计约 {total}。请在应用中批准新的草稿。",
        "cancelled": "🗑️ 已取消 {amount} 的草稿，没有汇出任何款项。",
        "emergency_more": "打开应用中的“紧急”页面，一键通知家人（由家长用指纹批准）。",
        "nothing_to_change": "这次对话中没有可以修改的付款草稿。请告诉我金额和用途，例如“汇 ¥3,000 生活费”。",
        "cannot_approve": "无论谁这么要求，我都不能批准或汇出款项、提高限额或更改收款人。只有你本人可以在应用中用指纹批准"
                          "（家庭 → 待处理付款）。这样即使有人诱导我，你的钱也是安全的。",
        "no_secrets": "我从不显示或索要验证码、密码或完整的卡号和账号，也不会透露我的内部设置。我只能看到后4位，例如 ****3317。"
                      "如果有人向你索要验证码，那就是诈骗：不要告诉任何人。",
        "mandate_cancel": "要取消家庭授权，请打开“家庭”页面，点击“取消授权”。你们任何一方都可以一键取消。",
    },
}
