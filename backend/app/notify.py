"""Family feed: what Sathi did, what needs you, and what is coming (Today screen).

Notes are written from deterministic templates in English, Bengali and Chinese. Numbers are formatted
here (lakh grouping for taka, Bengali digits in Bengali), never by the LLM, so a translated note
can't change an amount.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from app.money import D, q2

BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
AUDIENCES = {"parent", "student", "both"}
KINDS = {"did", "needs_you", "warning", "info"}


def group_indian(n: int) -> str:
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return ("-" if n < 0 else "") + s


def bdt(x, lang: str) -> str:
    s = "৳" + group_indian(int(q2(D(x)).to_integral_value()))
    return s.translate(BN_DIGITS) if lang == "bn" else s


def cny(x, lang: str) -> str:
    v = q2(D(x))
    s = "¥" + (f"{int(v):,}" if v == v.to_integral_value() else f"{v:,}")
    return s.translate(BN_DIGITS) if lang == "bn" else s


def day(iso: str, lang: str) -> str:
    return iso[:10].translate(BN_DIGITS) if lang == "bn" else iso[:10]


def num(n, lang: str) -> str:
    return str(n).translate(BN_DIGITS) if lang == "bn" else str(n)


# (title, body) per language. Placeholders ending in _bdt / _cny / _date / _n are formatted per language.
TEMPLATES: dict[str, dict[str, tuple[str, str]]] = {
    "autopilot_sent": {
        "en": ("Sathi sent {amount_cny} to the student's Chinese account",
               "Cost {total_bdt} via {bank}. Arrives {lands_date}. Why now: {why_en} Used under the family mandate: "
               "{used_bdt} of {cap_bdt} in this period."),
        "bn": ("সাথী শিক্ষার্থীর চীনের অ্যাকাউন্টে {amount_cny} পাঠিয়েছে",
               "খরচ {total_bdt} ({bank})। পৌঁছাবে {lands_date}। এখন কেন: {why_bn} পারিবারিক ম্যান্ডেটে এই সময়ে ব্যবহার হয়েছে "
               "{cap_bdt} এর মধ্যে {used_bdt}।"),
        "zh": ("Sathi 已向学生的中国账户汇出 {amount_cny}",
               "费用 {total_bdt}（{bank}）。预计 {lands_date} 到账。为什么是现在：{why_zh} 家庭授权本期已使用 {used_bdt} / {cap_bdt}。"),
    },
    "autopilot_needs_approval": {
        "en": ("Approve {amount_cny} of living money",
               "Sathi could not send this alone: {reason_en}. Open the payment and approve it, or change the family mandate."),
        "bn": ("{amount_cny} মাসিক খরচ অনুমোদন করুন",
               "সাথী একা এটি পাঠাতে পারেনি: {reason_bn}। পেমেন্টটি খুলে অনুমোদন দিন, অথবা পারিবারিক ম্যান্ডেট বদলান।"),
        "zh": ("请批准 {amount_cny} 生活费",
               "Sathi 无法自行汇出：{reason_zh}。请打开付款并批准，或修改家庭授权。"),
    },
    "bridge_cash": {
        "en": ("Withdraw about {amount_cny} at an ATM today",
               "The next bank transfer can arrive on {lands_date}; until then the student needs cash. The card works abroad "
               "until {card_date}."),
        "bn": ("আজ এটিএম থেকে প্রায় {amount_cny} তুলুন",
               "পরের ব্যাংক ট্রান্সফার {lands_date} তারিখে পৌঁছাতে পারে; ততদিন নগদ টাকা লাগবে। কার্ড বিদেশে {card_date} পর্যন্ত চলবে।"),
        "zh": ("今天请在ATM取现约 {amount_cny}",
               "下一笔银行汇款最早 {lands_date} 到账；在此之前需要现金。银行卡在境外可用至 {card_date}。"),
    },
    "runway_low": {
        "en": ("Money runs out on {out_date}",
               "The student has {balance_cny} (about {days_n} days) and no transfer is on the way that arrives in time. "
               "Sign a family mandate so Sathi can send living money in time, or prepare a transfer now."),
        "bn": ("টাকা শেষ হবে {out_date} তারিখে",
               "শিক্ষার্থীর কাছে আছে {balance_cny} (প্রায় {days_n} দিনের)। সময়মতো পৌঁছানোর মতো কোনো ট্রান্সফার পথে নেই। "
               "সাথী যেন সময়মতো মাসিক খরচ পাঠাতে পারে, সেজন্য পারিবারিক ম্যান্ডেটে সই করুন, অথবা এখনই ট্রান্সফার প্রস্তুত করুন।"),
        "zh": ("资金将在 {out_date} 用完",
               "学生目前有 {balance_cny}（约 {days_n} 天），没有能及时到账的汇款。签署家庭授权，让 Sathi 按时汇生活费，或现在就准备一笔汇款。"),
    },
    "stuck": {
        "en": ("The student ran out of money",
               "On {date_date} the student could not cover the day's spending. {fix_en}"),
        "bn": ("শিক্ষার্থীর টাকা শেষ হয়ে গেছে",
               "{date_date} তারিখে শিক্ষার্থী দিনের খরচ চালাতে পারেনি। {fix_bn}"),
        "zh": ("学生的钱用完了", "{date_date} 学生无法支付当天开销。{fix_zh}"),
    },
    "transfer_arrived": {
        "en": ("{amount_cny} arrived in the student's Chinese account", "Balance now {balance_cny}."),
        "bn": ("শিক্ষার্থীর চীনের অ্যাকাউন্টে {amount_cny} পৌঁছেছে", "এখন ব্যালান্স {balance_cny}।"),
        "zh": ("{amount_cny} 已到学生的中国账户", "当前余额 {balance_cny}。"),
    },
    "mandate_active": {
        "en": ("Family mandate is active", "{summary_en}"),
        "bn": ("পারিবারিক ম্যান্ডেট চালু হয়েছে", "{summary_bn}"),
        "zh": ("家庭授权已生效", "{summary_zh}"),
    },
    "mandate_needs_signature": {
        "en": ("Sign the family mandate", "{signed_en} signed. Sathi starts only after {missing_en} also signs. {summary_en}"),
        "bn": ("পারিবারিক ম্যান্ডেটে সই করুন", "{signed_bn} সই করেছেন। {missing_bn} সই করলে তবেই সাথী শুরু করবে। {summary_bn}"),
        "zh": ("请签署家庭授权", "{signed_zh} 已签署。{missing_zh} 也签署后 Sathi 才会开始。{summary_zh}"),
    },
    "mandate_revoked": {
        "en": ("Family mandate cancelled", "Sathi will not send money on its own any more."),
        "bn": ("পারিবারিক ম্যান্ডেট বাতিল", "সাথী আর নিজে থেকে টাকা পাঠাবে না।"),
        "zh": ("家庭授权已取消", "Sathi 将不再自行汇款。"),
    },
    "mandate_expiring": {
        "en": ("The family mandate ends on {end_date}",
               "After that Sathi will not send living money on its own. Write a new instruction in Family to continue."),
        "bn": ("পারিবারিক ম্যান্ডেট শেষ হবে {end_date} তারিখে",
               "এরপর সাথী নিজে থেকে মাসিক খরচ পাঠাবে না। চালু রাখতে পরিবার পাতায় নতুন নির্দেশনা লিখুন।"),
        "zh": ("家庭授权将于 {end_date} 到期", "到期后 Sathi 将不再自行汇生活费。如需继续，请在“家庭”页面写下新的指示。"),
    },
    "card_stops": {
        "en": ("The card stops working abroad on {card_date}",
               "Renewing the endorsement needs the student in person at the bank in Bangladesh. {plan_en}"),
        "bn": ("{card_date} থেকে কার্ড বিদেশে চলবে না",
               "এনডোর্সমেন্ট নবায়নে শিক্ষার্থীকে নিজে বাংলাদেশের ব্যাংকে যেতে হবে। {plan_bn}"),
        "zh": ("银行卡将于 {card_date} 起在境外停用", "续签需要学生本人携带护照到孟加拉国的银行办理。{plan_zh}"),
    },
}

ROLE_NAMES = {"parent": {"en": "the parent", "bn": "অভিভাবক", "zh": "家长"},
              "student": {"en": "the student", "bn": "শিক্ষার্থী", "zh": "学生"}}


@dataclass
class Note:
    id: str
    at: datetime
    audience: str
    kind: str
    key: str
    params: dict
    ref: dict = field(default_factory=dict)

    def render(self, lang: str) -> dict:
        lang = lang if lang in ("en", "bn", "zh") else "en"
        title, body = TEMPLATES[self.key][lang]
        values = {}
        for k, v in self.params.items():
            if k.endswith("_bdt"):
                values[k] = bdt(v, lang)
            elif k.endswith("_cny"):
                values[k] = cny(v, lang)
            elif k.endswith("_date"):
                values[k] = day(v, lang)
            elif k.endswith("_n"):
                values[k] = num(v, lang)
            else:
                values[k] = v
        # Language variants of free text fall back to English when a template asks for one that is missing.
        safe = _Fallback(values)
        return {"id": self.id, "at": self.at.isoformat(), "audience": self.audience, "kind": self.kind, "key": self.key,
                "title": title.format_map(safe), "body": body.format_map(safe), "ref": self.ref}


class _Fallback(dict):
    def __missing__(self, key: str) -> str:
        for suffix in ("_bn", "_zh"):
            if key.endswith(suffix) and key[: -len(suffix)] in self:
                return str(self[key[: -len(suffix)]])
            if key.endswith(suffix) and key[: -len(suffix)] + "_en" in self:
                return str(self[key[: -len(suffix)] + "_en"])
        return ""


class Feed:
    def __init__(self) -> None:
        self.notes: list[Note] = []
        self._keys: set[str] = set()
        self._n = 0

    def add(self, at: datetime, audience: str, kind: str, key: str, params: dict, ref: dict | None = None,
            once: str | None = None) -> Note | None:
        """`once`: a dedupe key, so the same warning is not repeated (e.g. one low-money warning per day)."""
        if audience not in AUDIENCES or kind not in KINDS or key not in TEMPLATES:
            raise ValueError("bad note")
        if once is not None:
            if once in self._keys:
                return None
            self._keys.add(once)
        self._n += 1
        note = Note(f"note-{self._n:04d}", at, audience, kind, key, params, ref or {})
        self.notes.append(note)
        return note

    def for_actor(self, actor: str, lang: str, limit: int = 30) -> list[dict]:
        mine = [n for n in self.notes if n.audience in ("both", actor)]
        return [n.render(lang) for n in reversed(mine[-limit:])]


def role_name(role: str, lang: str) -> str:
    return ROLE_NAMES.get(role, {}).get(lang, role)


def why_texts(dec: dict, holiday_names: dict[str, dict[str, str]]) -> dict[str, str]:
    """Explain an autopilot decision (TopupDecision.to_dict()) in three languages."""
    def names(lang: str) -> str:
        sep = "、" if lang == "zh" else ", "
        return sep.join(holiday_names.get(n, {}).get(lang, n) for n in dec["closures"])

    out = {}
    for lang in ("en", "bn", "zh"):
        nxt, wl, lands = day(dec["next_chance"], lang), day(dec["wait_would_land"], lang), day(dec["lands"], lang)
        low_on, safety = day(dec["low_on"], lang), num(dec["safety_days"], lang)
        if dec["closures"]:
            out[lang] = {
                "en": f"banks are closed for {names(lang)}; a transfer sent at the next chance ({nxt}) would land only on {wl}, "
                      "after the money runs low.",
                "bn": f"{names(lang)} এর জন্য ব্যাংক বন্ধ; পরের সুযোগে ({nxt}) পাঠালে টাকা পৌঁছাবে {wl} তারিখে, তখন হাতে টাকা প্রায় শেষ থাকবে।",
                "zh": f"因{names(lang)}银行休息；如果下次（{nxt}）再汇，要到 {wl} 才到账，那时钱已不够用。",
            }[lang]
        elif dec["low_on"] <= dec["send_on"]:
            out[lang] = {
                "en": f"the student has less than {safety} days of money left; a transfer sent today lands on {lands}.",
                "bn": f"শিক্ষার্থীর হাতে {safety} দিনেরও কম টাকা আছে; আজ পাঠালে পৌঁছাবে {lands} তারিখে।",
                "zh": f"学生的钱已不足 {safety} 天；今天汇出将于 {lands} 到账。",
            }[lang]
        else:
            out[lang] = {
                "en": f"money drops below {safety} days on {low_on}; a transfer sent today lands on {lands}.",
                "bn": f"{low_on} তারিখে হাতে {safety} দিনের কম টাকা থাকবে; আজ পাঠালে পৌঁছাবে {lands} তারিখে।",
                "zh": f"{low_on} 余额将不足 {safety} 天；今天汇出将于 {lands} 到账。",
            }[lang]
    return out


# Reasons the permission engine gives (English) → Bengali / Chinese.
REASONS = {
    "amount exceeds the mandate's per-payment cap": {"bn": "পরিমাণটি ম্যান্ডেটের প্রতি-পেমেন্ট সীমার বেশি", "zh": "金额超过授权的单笔上限"},
    "amount exceeds the mandate's period cap": {"bn": "এই সময়ের জন্য ম্যান্ডেটের সীমা শেষ", "zh": "本期授权额度已用完"},
    "mandate expired": {"bn": "ম্যান্ডেটের মেয়াদ শেষ", "zh": "授权已过期"},
    "mandate revoked": {"bn": "ম্যান্ডেট বাতিল করা হয়েছে", "zh": "授权已取消"},
    "blocked by compliance checks": {"bn": "নিরাপত্তা যাচাইয়ে আটকে গেছে", "zh": "未通过合规检查"},
    "payee is not covered by the mandate": {"bn": "এই প্রাপক ম্যান্ডেটে নেই", "zh": "收款人不在授权范围内"},
    "this kind of payment is not covered by the mandate": {"bn": "এই ধরনের পেমেন্ট ম্যান্ডেটে নেই", "zh": "此类付款不在授权范围内"},
    "Bangladesh's monthly living-money limit is reached": {"bn": "বাংলাদেশের মাসিক খরচ পাঠানোর সীমা পূর্ণ", "zh": "已达到孟加拉国每月生活费汇款上限"},
}


PURPOSE = {"tt_tuition": {"en": "tuition", "bn": "টিউশন ফি", "zh": "学费"},
           "tt_living": {"en": "living money", "bn": "মাসিক খরচ", "zh": "生活费"},
           "atm_plan": {"en": "living money", "bn": "মাসিক খরচ", "zh": "生活费"}}


def draft_summaries(d, payee, withdrawals: list) -> dict[str, str]:
    """What the approver hears and reads before the fingerprint step (explain-before-sign).

    Built only from the fields the approval token is bound to (amount, total, payee, rate, expiry), from
    templates, never by the LLM: what you hear is exactly what you approve.
    """
    to = f"{payee.name} ({payee.bank} {payee.account_masked})" if payee else d.payee_id
    until = d.expires_at.strftime("%H:%M")
    out = {}
    for lang in ("en", "bn", "zh"):
        amt, total = cny(d.amount_cny, lang), bdt(d.total_bdt, lang)
        what = PURPOSE.get(d.kind, PURPOSE["tt_living"])[lang]
        rate = f"৳{d.rate_bdt_per_cny}" if d.rate_bdt_per_cny is not None else ""
        if lang == "bn":
            rate, until_l = rate.translate(BN_DIGITS), until.translate(BN_DIGITS)
        else:
            until_l = until
        if d.kind == "atm_plan":
            n = num(len(withdrawals), lang)
            out[lang] = {
                "en": f"You are approving {n} ATM withdrawals of {amt} in total with your Bangladeshi card, costing about "
                      f"{total} with all fees. This approval works only for this exact plan, until {until_l}.",
                "bn": f"আপনি আপনার বাংলাদেশি কার্ড দিয়ে মোট {amt} এর {n}টি এটিএম উত্তোলনের অনুমোদন দিচ্ছেন, সব ফি মিলিয়ে খরচ প্রায় "
                      f"{total}। এই অনুমোদন শুধু এই পরিকল্পনার জন্য, {until_l} পর্যন্ত বৈধ।",
                "zh": f"您正在批准用孟加拉国银行卡在ATM取现 {n} 次，共 {amt}，含全部费用约 {total}。此批准仅对这份计划有效，"
                      f"有效期至 {until_l}。",
            }[lang]
        else:
            out[lang] = {
                "en": f"You are approving a bank transfer of {amt} to {to} for {what}. Total cost {total}, at {rate} per ¥1. "
                      f"This approval works only for this exact payment, until {until_l}.",
                "bn": f"আপনি {to}-কে {what} বাবদ {amt} ব্যাংক ট্রান্সফারের অনুমোদন দিচ্ছেন। মোট খরচ {total}, প্রতি ¥১ = {rate}। "
                      f"এই অনুমোদন শুধু এই পেমেন্টের জন্য, {until_l} পর্যন্ত বৈধ।",
                "zh": f"您正在批准一笔银行汇款：向 {to} 汇出 {amt}，用途：{what}。总费用 {total}，汇率 ¥1 = {rate}。"
                      f"此批准仅对这笔付款有效，有效期至 {until_l}。",
            }[lang]
    return out


def reason_texts(reason: str) -> dict[str, str]:
    r = REASONS.get(reason, {})
    return {"reason_en": reason, "reason_bn": r.get("bn", reason), "reason_zh": r.get("zh", reason)}
