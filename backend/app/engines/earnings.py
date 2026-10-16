"""Earn & Save: the student's own money abroad (problems N-11 … N-14, Interview #2).

The cheapest and safest yuan is the one that never has to cross the border. A student's income abroad (a scholarship
stipend or an approved campus job) is already in the host currency: it sidesteps Bangladesh's dollar shortages, the
bank's fixed transfer fees and hundi. Without a plan it leaks into "wants" (field: "luxury korte giye taka noshto kore
fele"), helped by two documented biases: prices in a stronger currency look small (the face-value effect, Raghubir &
Srivastava 2002) and phone payments hide the pain of paying (Prelec & Simester 2001). A commitment rule chosen in
advance is what works against both (Ashraf, Karlan & Yin 2006; Thaler & Benartzi 2004).

Pure functions only (like the other engines), so every number can be unit-tested:
  * work_checks: is this income legal under the corridor's rules (permission, weekly hours)?
  * paydays / income_schedule: when planned income lands;
  * shield_share: "pay yourself first": a share of each income goes to the Shield until its target;
  * compile_savings_rule: the student's own words (or the form) → a strict, signable rule with a template read-back;
  * taka_lens: a purchase in taka and in days of living money;
  * categorize: need or want, from merchant words (EN / ZH / BN).
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import ROUND_FLOOR, Decimal

from app.corridors.loader import Corridor
from app.money import D, q2
from app.notify import cny, day, num
from app.security.scam import contains_term

KINDS = ("stipend", "work_study", "other")
EVERY = ("month", "week")
COOLING_CHOICES = (0, 24, 72)
PCT_MIN, PCT_MAX = 5, 80
TARGET_MIN, TARGET_MAX = Decimal(500), Decimal(100000)
RULE_MONTHS = 12
# Suggested share of each pay for the Shield when the family already pays for living costs, so the student's pay is
# mostly extra money (product choice; the student picks the share and signs it). In the year plan a ¥1,500/month campus
# job at 50% makes 94% of possible 4-week dollar crises stuck-day free (docs: TECHNICAL_DOCUMENTATION.md, Earn & Save).
SUGGESTED_PCT = 50


# ---- income and the corridor's work rules ------------------------------------------------------
@dataclass
class IncomeSource:
    id: str
    kind: str  # stipend | work_study | other
    label: str
    amount_cny: Decimal  # per pay
    every: str  # month | week
    pay_day: int  # day of the month (1–28) for monthly pay; weekday (0 = Monday) for weekly pay
    hours_per_week: Decimal | None
    permission: bool  # university approval + work-study annotation on the residence permit (jobs only)
    added_on: date
    checks: list[dict] = field(default_factory=list)

    @property
    def status(self) -> str:
        """ok = counted in plans · at_risk = not counted (unauthorised work can end any day, and it is illegal)."""
        return "at_risk" if any(c["severity"] == "block" and not c["passed"] for c in self.checks) else "ok"

    @property
    def monthly_cny(self) -> Decimal:
        return self.amount_cny if self.every == "month" else q2(self.amount_cny * 52 / 12)

    def to_dict(self) -> dict:
        return {"id": self.id, "kind": self.kind, "label": self.label, "amount_cny": str(q2(self.amount_cny)),
                "every": self.every, "pay_day": self.pay_day,
                "hours_per_week": str(self.hours_per_week) if self.hours_per_week is not None else None,
                "permission": self.permission, "added_on": self.added_on.isoformat(), "status": self.status,
                "monthly_cny": str(q2(self.monthly_cny)), "checks": self.checks}


def work_checks(kind: str, hours_per_week: Decimal | None, permission: bool, corridor: Corridor) -> list[dict]:
    """The host country's rules for student income. Sathi cannot see the job: it warns, explains the legal route,
    and leaves unauthorised income out of every plan (it is illegal, and it can stop on any day)."""
    if kind == "stipend":
        return [{"id": "income_legal", "passed": True, "severity": "info",
                 "message": "Scholarship stipend: no work permission is needed.", "source": "Scholarship terms"}]
    if kind != "work_study":
        return [{"id": "income_legal", "passed": True, "severity": "info",
                 "message": "Other income (gift, prize, refund): no work rules apply.", "source": ""}]
    checks = []
    perm = corridor.params["cn_work_permission_required"]
    fine_lo, fine_hi = corridor.i("cn_illegal_work_fine_cny_min"), corridor.i("cn_illegal_work_fine_cny_max")
    if corridor.i("cn_work_permission_required") and not permission:
        checks.append({"id": "work_permission", "passed": False, "severity": "block",
                       "message": ("Working without your university's approval and a work-study annotation on your residence "
                                   f"permit is illegal work in China: a fine of ¥{fine_lo:,}–{fine_hi:,}, detention in serious "
                                   "cases, and the visa can be cancelled. Ask your international student office to apply for "
                                   "the annotation first. Sathi leaves this income out of every plan until then."),
                       "source": perm.source})
    else:
        checks.append({"id": "work_permission", "passed": True, "severity": "info",
                       "message": "Approved work-study (university approval + residence-permit annotation).",
                       "source": perm.source})
    cap = corridor.v("cn_work_hours_week_term")
    if hours_per_week is not None and D(hours_per_week) > cap:
        checks.append({"id": "work_hours", "passed": False, "severity": "warn",
                       "message": (f"{q2(D(hours_per_week)).normalize()} hours a week in term time is above the stricter "
                                   f"reported limit of {cap.normalize()} hours (sources differ). Working beyond the hours in "
                                   "your approval also counts as illegal work: check your approval letter."),
                       "source": corridor.params["cn_work_hours_week_term"].source})
    return checks


def paydays(src: IncomeSource, start: date, end: date) -> list[date]:
    """Pay dates in [start, end]."""
    out: list[date] = []
    if start > end:
        return out
    if src.every == "month":
        y, m = start.year, start.month
        while True:
            d = date(y, m, min(max(src.pay_day, 1), 28))
            if d > end:
                break
            if d >= start:
                out.append(d)
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    else:
        d = start + timedelta(days=(src.pay_day - start.weekday()) % 7)
        while d <= end:
            out.append(d)
            d += timedelta(days=7)
    return out


def income_schedule(sources: list[IncomeSource], start: date, end: date) -> list[tuple[date, Decimal]]:
    """Planned income in [start, end] from sources that pass the work rules (status ok)."""
    return sorted((d, s.amount_cny) for s in sources if s.status == "ok" for d in paydays(s, start, end))


def monthly_income(sources: list[IncomeSource]) -> Decimal:
    return q2(sum((s.monthly_cny for s in sources if s.status == "ok"), Decimal(0)))


# ---- pay yourself first ---------------------------------------------------------------------------
def shield_share(amount: Decimal, pct: int, shield: Decimal, target: Decimal) -> Decimal:
    """The part of one income that goes to the Shield: pct of it in whole yuan, never past the target."""
    want = (D(amount) * pct / 100).quantize(Decimal(1), rounding=ROUND_FLOOR)
    return max(min(want, D(target) - D(shield)), Decimal(0))


def wants_allowance_week(monthly_cny: Decimal, pct: int) -> Decimal:
    """What is left of the pay after saving, per week (the student's own money for wants)."""
    return q2(D(monthly_cny) * (100 - pct) / 100 * 7 / 30)


# ---- the taka lens ----------------------------------------------------------------------------------
def taka_lens(amount_cny: Decimal, family_bdt_per_cny: Decimal, daily_living_cny: Decimal) -> dict:
    """A purchase in the currency the family earns in. `family_bdt_per_cny` is what one yuan costs the family to send
    (cheapest legal bank, fees included), so the number is what the purchase really costs at home."""
    amount = D(amount_cny)
    days_ = (amount / daily_living_cny).quantize(Decimal("0.1")) if daily_living_cny > 0 else Decimal(0)
    return {"amount_cny": str(q2(amount)), "bdt": str(q2(amount * family_bdt_per_cny)), "days_of_living": str(days_)}


# ---- need or want ------------------------------------------------------------------------------------
CATEGORIES: list[tuple[str, str, list[str]]] = [
    ("delivery", "want", ["meituan", "美团", "eleme", "ele.me", "饿了么", "food delivery", "外卖", "ফুড ডেলিভারি"]),
    ("eating_out", "want", ["restaurant", "cafe", "café", "coffee", "starbucks", "星巴克", "luckin", "瑞幸", "kfc", "肯德基",
                            "mcdonald", "麦当劳", "pizza", "burger", "bubble tea", "milk tea", "奶茶", "heytea", "喜茶",
                            "mixue", "蜜雪", "bar", "酒吧", "hotpot", "火锅", "bbq", "烧烤", "রেস্টুরেন্ট", "রেস্তোরাঁ", "কফি"]),
    ("shopping", "want", ["taobao", "淘宝", "tmall", "天猫", "jd.com", "京东", "pinduoduo", "拼多多", "shein", "uniqlo",
                          "apple store", "mall", "商场", "clothes", "服装", "sneakers", "perfume", "শপিং", "কেনাকাটা", "জামা"]),
    ("fun", "want", ["cinema", "movie", "电影", "ktv", "game", "游戏", "steam", "concert", "演唱会", "netflix", "spotify",
                     "সিনেমা", "গেম"]),
    ("travel", "want", ["trip", "ctrip", "携程", "hotel", "酒店", "flight", "机票", "travel", "旅游", "ভ্রমণ"]),
    ("groceries", "need", ["supermarket", "超市", "grocery", "groceries", "菜市场", "walmart", "沃尔玛", "carrefour", "家乐福",
                           "canteen", "食堂", "বাজার", "মুদি"]),
    ("rent_bills", "need", ["rent", "房租", "dorm", "宿舍", "electricity", "电费", "water bill", "水费", "internet", "网费",
                            "phone bill", "话费", "ভাড়া", "বিল"]),
    ("transport", "need", ["metro", "subway", "地铁", "bus", "公交", "didi", "滴滴", "train", "高铁", "火车", "taxi", "出租车",
                           "মেট্রো", "বাস"]),
    ("health", "need", ["hospital", "医院", "pharmacy", "药店", "clinic", "doctor", "medicine", "হাসপাতাল", "ওষুধ"]),
    ("study", "need", ["book", "书店", "textbook", "教材", "printing", "打印", "stationery", "文具", "বই"]),
]
CATEGORY_KIND = {cat: kind for cat, kind, _ in CATEGORIES} | {"other_want": "want", "other_need": "need"}
CATEGORY_LABELS = {
    "delivery": {"en": "Food delivery", "bn": "খাবার ডেলিভারি", "zh": "外卖"},
    "eating_out": {"en": "Eating out", "bn": "বাইরে খাওয়া", "zh": "外出就餐"},
    "shopping": {"en": "Shopping", "bn": "কেনাকাটা", "zh": "购物"},
    "fun": {"en": "Fun", "bn": "বিনোদন", "zh": "娱乐"},
    "travel": {"en": "Travel", "bn": "ভ্রমণ", "zh": "旅行"},
    "groceries": {"en": "Groceries", "bn": "বাজার", "zh": "日用食品"},
    "rent_bills": {"en": "Rent and bills", "bn": "ভাড়া ও বিল", "zh": "房租和账单"},
    "transport": {"en": "Transport", "bn": "যাতায়াত", "zh": "交通"},
    "health": {"en": "Health", "bn": "স্বাস্থ্য", "zh": "医疗"},
    "study": {"en": "Study", "bn": "পড়াশোনা", "zh": "学习"},
    "other_want": {"en": "Other wants", "bn": "অন্যান্য শখ", "zh": "其他想要的"},
    "other_need": {"en": "Other needs", "bn": "অন্যান্য প্রয়োজন", "zh": "其他必需"},
}


def categorize(text: str) -> tuple[str, str] | None:
    """(category, need|want) from the merchant or note, or None when unknown (then the student chooses)."""
    for cat, kind, words in CATEGORIES:
        if any(contains_term(text or "", w) for w in words):
            return cat, kind
    return None


# ---- the savings rule: the student's own words → a strict, signable rule ------------------------
DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯０１２３４５６７８９", "01234567890123456789")
PCT = re.compile(r"(\d+(?:\.\d+)?)\s*(?:%|％|percent\b|per cent\b|শতাংশ|পার্সেন্ট|পারসেন্ট)", re.IGNORECASE)
PCT_ZH = re.compile(r"百分之\s*(\d+(?:\.\d+)?)")
HALF = re.compile(r"\bhalf\b|অর্ধেক|一半", re.IGNORECASE)
HOURS = re.compile(r"(\d+)\s*(?:hours?|hrs?\b|ঘণ্টা|ঘন্টা|小时)", re.IGNORECASE)
NO_WAIT = re.compile(r"no (?:wait|waiting|cooling)|without (?:a )?(?:wait|cooling)|অপেক্ষা ছাড়া|অপেক্ষা ছাড়াই|不用等|无需等待",
                     re.IGNORECASE)
TAKA = re.compile(r"৳|টাকা|taka|\btk\b|bdt|塔卡", re.IGNORECASE)
UNTIL = re.compile(r"until|till|up to|reach|পর্যন্ত|直到|存到|达到|攒到", re.IGNORECASE)
FAMILY_LOCK = re.compile(r"(?:family|parents?|abbu|ammu|বাবা|মা|পরিবার|家人|父母)[^.。!?]{0,40}?"
                         r"(?:approv|lock|agree|allow|অনুমোদন|সম্মতি|同意|批准)", re.IGNORECASE)


@dataclass
class ParsedSavings:
    pct: Decimal | None
    target_cny: Decimal | None
    target_in_taka: bool
    cooling_off_hours: int | None
    family_lock: bool


def parse_savings(text: str) -> ParsedSavings:
    from app.agent.mandate_compiler import AMOUNT, MULT  # lakh / হাজার / 千 / 万 / k, shared with the mandate parser

    t = re.sub(r"(?<=\d),(?=\d)", "", (text or "").translate(DIGITS))
    pct = None
    m = PCT.search(t) or PCT_ZH.search(t)
    if m:
        pct = D(m.group(1))
    elif HALF.search(t):
        pct = Decimal(50)
    hours = HOURS.search(t)
    cooling = 0 if NO_WAIT.search(t) else int(hours.group(1)) if hours else None
    masked = t
    for rx in (PCT, PCT_ZH, HOURS):
        masked = rx.sub(lambda x: " " * len(x.group(0)), masked)  # same length: positions stay comparable
    amounts: list[tuple[int, Decimal]] = []
    for a in AMOUNT.finditer(masked):
        value = D(a.group(1)) * MULT.get((a.group(2) or "").lower(), 1)
        if value >= 100:  # small numbers are counts or days, not a savings target
            amounts.append((a.start(), value))
    target = None
    if amounts:
        u = UNTIL.search(masked)
        if u and u.group(0) == "পর্যন্ত":  # Bengali puts the number before "পর্যন্ত"
            before = [x for x in amounts if x[0] < u.start()]
            target = (before[-1] if before else max(amounts, key=lambda x: x[1]))[1]
        elif u:
            after = [x for x in amounts if x[0] > u.start()]
            target = (after[0] if after else max(amounts, key=lambda x: x[1]))[1]
        else:
            target = max(v for _, v in amounts)
    return ParsedSavings(pct, target, bool(TAKA.search(t)) and target is not None, cooling, bool(FAMILY_LOCK.search(t)))


@dataclass
class SavingsRule:
    id: str
    created_at: datetime
    created_by: str
    lang: str
    text: str
    shield_pct: int
    target_cny: Decimal
    cooling_off_hours: int
    family_lock: bool
    share_with_family: bool
    valid_until: date
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    signatures: dict[str, str] = field(default_factory=dict)
    status: str = "proposed"  # proposed | needs_changes | active | revoked | superseded
    activated_at: datetime | None = None

    def binding_fields(self) -> dict:
        """Everything the student's signature covers (what you read is what you sign)."""
        return {"id": self.id, "owner": "student", "shield_pct": self.shield_pct, "target_cny": str(q2(self.target_cny)),
                "cooling_off_hours": self.cooling_off_hours, "family_lock": self.family_lock,
                "share_with_family": self.share_with_family, "valid_until": self.valid_until.isoformat(),
                "emergency_release": True, "to_account": "student_shield"}

    def hash(self) -> str:
        return hashlib.sha256(json.dumps(self.binding_fields(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def summary(self) -> dict[str, str]:
        if self.errors:
            return {"en": "", "bn": "", "zh": ""}
        return savings_summaries(self.shield_pct, self.target_cny, self.cooling_off_hours, self.family_lock,
                                 self.share_with_family, self.valid_until)

    def to_dict(self) -> dict:
        return {**self.binding_fields(), "created_at": self.created_at.isoformat(), "created_by": self.created_by,
                "lang": self.lang, "text": self.text, "errors": self.errors, "notes": self.notes,
                "signatures": self.signatures, "status": self.status, "required_signers": ["student"],
                "activated_at": self.activated_at.isoformat() if self.activated_at else None,
                "summary": self.summary(), "hash": self.hash()}


def compile_savings_rule(rule_id: str, now: datetime, actor: str, lang: str, default_target: Decimal,
                         default_cooling: int, text: str = "", pct: int | None = None, target_cny: Decimal | None = None,
                         cooling_off_hours: int | None = None, family_lock: bool | None = None,
                         share_with_family: bool = True) -> SavingsRule:
    """Form fields win over words; words win over defaults. Only the rules decide (no AI here)."""
    text = (text or "").strip()[:500]
    parsed = parse_savings(text) if text else ParsedSavings(None, None, False, None, False)
    errors: list[str] = []
    notes: list[str] = []
    p = D(pct) if pct is not None else parsed.pct
    if p is None or p <= 0:
        errors.append("Say how much of each pay to keep, for example: \"keep 30% of every pay until ¥6,000\".")
        p_int = 0
    else:
        p_int = int(p.quantize(Decimal(1), rounding=ROUND_FLOOR))
        if p_int < PCT_MIN:
            notes.append(f"The smallest share is {PCT_MIN}%, so it was raised to {PCT_MIN}%.")
            p_int = PCT_MIN
        elif p_int > PCT_MAX:
            notes.append(f"At most {PCT_MAX}% of each pay goes to the Shield: you still need money to live on.")
            p_int = PCT_MAX
    if target_cny is None and parsed.target_in_taka:
        errors.append("Write the Shield target in yuan (it is kept in your Chinese account), for example ¥6,000.")
    target = D(target_cny) if target_cny is not None else (parsed.target_cny if not parsed.target_in_taka else None)
    if target is None:
        target = D(default_target)
        notes.append(f"No target given: Sathi suggests {cny(target, 'en')}, about a month of living money.")
    target = q2(target)
    if target < TARGET_MIN:
        notes.append(f"The smallest Shield is {cny(TARGET_MIN, 'en')}.")
        target = TARGET_MIN
    elif target > TARGET_MAX:
        notes.append(f"The largest Shield is {cny(TARGET_MAX, 'en')}.")
        target = TARGET_MAX
    cool = cooling_off_hours if cooling_off_hours is not None else parsed.cooling_off_hours
    if cool is None:
        cool = default_cooling
    if cool not in COOLING_CHOICES:
        nearest = min(COOLING_CHOICES, key=lambda c: abs(c - cool))
        notes.append(f"Waiting time can be 0, 24 or 72 hours, so {cool} hours became {nearest}.")
        cool = nearest
    lock = family_lock if family_lock is not None else parsed.family_lock
    return SavingsRule(id=rule_id, created_at=now, created_by=actor, lang=lang, text=text, shield_pct=p_int, target_cny=target,
                       cooling_off_hours=cool, family_lock=bool(lock), share_with_family=bool(share_with_family),
                       valid_until=now.date() + timedelta(days=30 * RULE_MONTHS), errors=errors, notes=notes,
                       status="needs_changes" if errors else "proposed")


def savings_summaries(pct: int, target: Decimal, hours: int, lock: bool, share: bool, valid_until: date) -> dict[str, str]:
    """The read-back the student signs. Templates only: an LLM never writes what people sign."""
    out = {}
    for lang in ("en", "bn", "zh"):
        p, t, h, until = num(pct, lang), cny(target, lang), num(hours, lang), day(valid_until.isoformat(), lang)
        if lang == "en":
            wait = ("Taking money out for anything else is possible at once" if hours == 0
                    else f"Taking money out for anything else waits {h} hours")
            out[lang] = (f"Every time money comes in (your pay or stipend), Sathi moves {p}% of it to your Shield, until "
                         f"the Shield holds {t}. The Shield stays in your own Chinese account. If you cannot cover a day's "
                         f"spending, Sathi uses the Shield at once. {wait}"
                         + (" and needs your family's approval" if lock else "") + ". "
                         + ("Your family sees how much is in the Shield, never what you buy. " if share
                            else "Your family does not see your Shield. ")
                         + f"Valid until {until}. You can stop the rule at any time; money already saved stays under these terms.")
        elif lang == "bn":
            wait = ("অন্য কাজে টাকা তোলা যাবে সঙ্গে সঙ্গে" if hours == 0 else f"অন্য কাজে টাকা তুলতে {h} ঘণ্টা অপেক্ষা করতে হবে")
            out[lang] = (f"যখনই টাকা আসবে (বেতন বা বৃত্তি), সাথী তার {p}% আপনার সুরক্ষা তহবিলে রাখবে, যতক্ষণ না তহবিলে {t} হয়। "
                         "তহবিলটি আপনার নিজের চীনা অ্যাকাউন্টেই থাকবে। কোনো দিন খরচ চালানোর টাকা না থাকলে সাথী সঙ্গে সঙ্গে "
                         f"তহবিল থেকে দেবে। {wait}" + (", আর পরিবারের অনুমোদন লাগবে" if lock else "") + "। "
                         + ("পরিবার দেখবে তহবিলে কত আছে, আপনি কী কিনছেন তা কখনো নয়। " if share
                            else "পরিবার আপনার তহবিল দেখবে না। ")
                         + f"{until} পর্যন্ত বৈধ। যেকোনো সময় নিয়মটি বন্ধ করতে পারবেন; যা জমেছে তা এই শর্তেই থাকবে।")
        else:
            wait = "其他用途可随时取出" if hours == 0 else f"其他用途取出需要等待 {h} 小时"
            out[lang] = (f"每次有钱进账（工资或奖学金），Sathi 会把其中的 {p}% 存入你的应急储备，直到储备达到 {t}。"
                         "储备一直在你本人的中国账户里。如果哪天钱不够当天开销，Sathi 会立即动用储备。"
                         f"{wait}" + ("，并需家人批准" if lock else "") + "。"
                         + ("家人可以看到储备里有多少钱，但永远看不到你买了什么。" if share else "家人看不到你的储备。")
                         + f"有效期至 {until}。你可以随时停止这条规则；已存的钱仍按这些条款保管。")
    return out


# ---- releases ---------------------------------------------------------------------------------------
@dataclass
class ShieldRelease:
    id: str
    amount_cny: Decimal
    reason: str  # emergency | planned
    requested_by: str
    requested_at: datetime
    available_at: datetime
    needs_family: bool
    family_approved_at: datetime | None = None
    status: str = "waiting"  # waiting | released | cancelled
    released_at: datetime | None = None
    note: str = ""

    def to_dict(self) -> dict:
        return {"id": self.id, "amount_cny": str(q2(self.amount_cny)), "reason": self.reason,
                "requested_by": self.requested_by, "requested_at": self.requested_at.isoformat(),
                "available_at": self.available_at.isoformat(), "needs_family": self.needs_family,
                "family_approved_at": self.family_approved_at.isoformat() if self.family_approved_at else None,
                "status": self.status, "released_at": self.released_at.isoformat() if self.released_at else None,
                "note": self.note}
