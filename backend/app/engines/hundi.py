"""Hundi vs the legal way, honestly (problems N-08, N-11, N-12, P-23).

Field (Interview #2): when the dollar is short, families bring money by hundi and "lose 1–2 taka per dollar". Our own
data says the uncomfortable part out loud: one small bank transfer can cost MORE than that on paper, because the bank's
fixed fees (৳3,680 per transfer at EBL) are larger than 1–2 taka per dollar on a few hundred dollars. That gap is why
families choose hundi. Bluefin does not hide it. It shows:
  * the hundi offer's visible cost against the market rate;
  * one legal bank transfer for the same money, with its real fees and the day it lands;
  * the legal ways that beat both: the student's own Shield (money already in China costs ৳0 to "send") and the
    planned transfer that is coming anyway (no extra fee);
  * what the hundi price leaves out, each risk with its source and confidence.
Never a hundi route: Bluefin only ever recommends formal channels (security self-assessment, hard blocks).
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from app.corridors.loader import Corridor
from app.engines.living_planner import best_quote_for
from app.engines.year_plan import BankCalendar
from app.market import Market
from app.money import D, q2

RISKS = [
    {"key": "illegal_bd", "confidence": "secondary",
     "en": "Illegal in Bangladesh: only banks authorised by Bangladesh Bank may deal in foreign exchange, and money moved by "
           "hundi is investigated as money laundering.",
     "bn": "বাংলাদেশে অবৈধ: শুধু বাংলাদেশ ব্যাংকের অনুমোদিত ব্যাংক বৈদেশিক মুদ্রার লেনদেন করতে পারে, আর হুন্ডির টাকা মানি "
           "লন্ডারিং হিসেবে তদন্ত হয়।",
     "zh": "在孟加拉国违法：只有孟加拉国央行授权的银行才能经营外汇，地下汇款按洗钱调查。",
     "source": "Foreign Exchange Regulation Act 1947 (s. 3, authorised dealers); Money Laundering Prevention Act 2012"},
    {"key": "illegal_cn", "confidence": "official",
     "en": "Illegal in China too: underground banks (地下钱庄) that settle cross-border money without moving it are prosecuted "
           "as illegal business operation.",
     "bn": "চীনেও অবৈধ: যে আন্ডারগ্রাউন্ড ব্যাংক (地下钱庄) টাকা না পাঠিয়েই সীমান্তপারের লেনদেন মেটায়, তাদের অবৈধ ব্যবসা "
           "হিসেবে বিচার হয়।",
     "zh": "在中国同样违法：不实际跨境转移资金而进行对冲结算的地下钱庄，按非法经营罪追诉。",
     "source": "PRC Criminal Law Art. 225; SPC/SPP interpretation on illegal payment settlement and foreign exchange trading (2019)"},
    {"key": "account_freeze", "confidence": "secondary",
     "en": "The yuan arrives from a stranger's account. In China, receiving money linked to fraud is a common reason for "
           "police account freezes that last weeks or months.",
     "bn": "ইউয়ান আসে অচেনা কারও অ্যাকাউন্ট থেকে। চীনে প্রতারণার সঙ্গে যুক্ত টাকা পেলে পুলিশ প্রায়ই অ্যাকাউন্ট সপ্তাহ বা মাসের "
           "জন্য ফ্রিজ করে।",
     "zh": "人民币来自陌生人的账户。在中国，收到与诈骗有关的钱，是账户被警方冻结数周甚至数月的常见原因。",
     "source": "Research P-16 (TropicalHainan, Mar 2026)"},
    {"key": "no_recourse", "confidence": "assumption",
     "en": "No recourse: if the agent keeps the money or disappears, no bank, receipt or court can get it back.",
     "bn": "কোনো প্রতিকার নেই: এজেন্ট টাকা রেখে দিলে বা উধাও হলে কোনো ব্যাংক, রসিদ বা আদালত তা ফেরত আনতে পারবে না।",
     "zh": "无法追索：如果中间人扣下钱或消失，没有银行、收据或法院能帮你追回。",
     "source": "Product reasoning: an informal transfer leaves no contract"},
    {"key": "no_record", "confidence": "assumption",
     "en": "No record: it cannot back a Student File renewal, a visa's proof of funds or your payment passport.",
     "bn": "কোনো রেকর্ড নেই: স্টুডেন্ট ফাইল নবায়ন, ভিসার অর্থের প্রমাণ বা আপনার পেমেন্ট পাসপোর্টে এটি দেখানো যায় না।",
     "zh": "没有记录：不能用于学生档案续办、签证资金证明或你的付款护照。",
     "source": "Product reasoning (Student File and visa paperwork need bank records)"},
]

LEGAL_ROUTES = [  # channels outside the student's own account (the Shield is compared above, at ৳0)
    {"key": "student_file", "confidence": "official",
     "en": "Student File transfer from any authorised bank to your own Chinese account (living money) or the university "
           "(tuition). Fewer, larger, planned transfers pay the fixed fee less often.",
     "bn": "যেকোনো অনুমোদিত ব্যাংকের স্টুডেন্ট ফাইল থেকে আপনার নিজের চীনা অ্যাকাউন্টে (মাসিক খরচ) বা বিশ্ববিদ্যালয়ে (টিউশন) "
           "ট্রান্সফার। কম সংখ্যায়, বড় অঙ্কে, পরিকল্পিত ট্রান্সফারে নির্দিষ্ট ফি কম বার দিতে হয়।",
     "zh": "通过任何授权银行的学生档案汇到你本人的中国账户（生活费）或学校（学费）。次数少、金额大、有计划的汇款，固定手续费付得更少。",
     "source": "FE Circular 37 via legalseba.com (secondary); bank fee schedules 2026"},
    {"key": "education_card", "confidence": "secondary",
     "en": "Since 10 Aug 2026, banks may issue an international debit, prepaid or credit card in the student's or the sponsor's "
           "name for tuition and approved education costs, outside the travel quota. Ask your bank about fees and limits.",
     "bn": "১০ আগস্ট ২০২৬ থেকে ব্যাংক শিক্ষার্থী বা অভিভাবকের নামে টিউশন ও অনুমোদিত শিক্ষা খরচের জন্য আন্তর্জাতিক ডেবিট, প্রিপেইড বা "
           "ক্রেডিট কার্ড দিতে পারে, ট্রাভেল কোটার বাইরে। ফি ও সীমা ব্যাংকে জিজ্ঞেস করুন।",
     "zh": "自 2026 年 8 月 10 日起，银行可以以学生或资助人的名义发行国际借记卡、预付卡或信用卡，用于学费和获批的教育费用，不占旅行额度。费用和额度请咨询银行。",
     "source": "Bangladesh Bank circular, 10 Aug 2026 (Dhaka Tribune, TBS, Daily Star reports)"},
]


def _texts(items: list[dict], lang: str) -> list[dict]:
    return [{"key": i["key"], "text": i.get(lang, i["en"]), "confidence": i["confidence"], "source": i["source"]} for i in items]


def compare(amount_cny: Decimal, market: Market, corridor: Corridor, cal: BankCalendar, today: date, shield_cny: Decimal,
            offered_bdt_per_usd: Decimal | None = None, premium_bdt_per_usd: Decimal | None = None,
            planned: dict | None = None, lang: str = "en") -> dict:
    """Same yuan, every way. `planned`: the next living-money transfer the autopilot will send anyway (or None)."""
    amount = D(amount_cny)
    if amount <= 0:
        raise ValueError("amount must be positive")
    lang = lang if lang in ("en", "bn", "zh") else "en"
    mid = market.mid
    usd = amount / mid.cny_per_usd
    mid_bdt = amount * mid.bdt_per_cny
    if offered_bdt_per_usd is not None:
        rate = D(offered_bdt_per_usd)
        if not (mid.bdt_per_usd * Decimal("0.8") <= rate <= mid.bdt_per_usd * Decimal("1.3")):
            raise ValueError(f"that rate looks wrong: the market rate is about ৳{round(mid.bdt_per_usd, 2)} per dollar")
        premium = rate - mid.bdt_per_usd
        premium_source = "the offer you entered"
    else:
        premium = D(premium_bdt_per_usd) if premium_bdt_per_usd is not None else corridor.v("hundi_premium_bdt_per_usd")
        rate = mid.bdt_per_usd + premium
        premium_source = corridor.params["hundi_premium_bdt_per_usd"].source if premium_bdt_per_usd is None else "the premium you entered"
    hundi_bdt = usd * rate

    quote, cost = best_quote_for(amount, market)
    send_on = today if cal.is_open("BD", today) else cal.next_open("BD", today)
    lands = cal.arrival(send_on, corridor.i("bd_tt_transfer_days"))
    bank_overhead = cost.total_bdt - mid_bdt
    shield_use = min(D(shield_cny), amount)
    rest = amount - shield_use

    options = [{"key": "hundi", "legal": False, "total_bdt": str(q2(hundi_bdt)), "extra_bdt": str(q2(hundi_bdt - mid_bdt)),
                "rate_bdt_per_usd": str(q2(rate)), "premium_bdt_per_usd": str(q2(premium)), "premium_source": premium_source,
                "visible_cost_only": True}]
    options.append({"key": "bank_once", "legal": True, "bank": quote.bank, "total_bdt": str(q2(cost.total_bdt)),
                    "extra_bdt": str(q2(bank_overhead)), "fees_bdt": str(q2(cost.by_kind("fee"))),
                    "rate_markup_bdt": str(q2(cost.by_kind("rate"))), "send_on": send_on.isoformat(), "lands": lands.isoformat()})
    if shield_use > 0:
        options.append({"key": "shield", "legal": True, "amount_cny": str(q2(shield_use)), "total_bdt": "0.00",
                        "extra_bdt": "0.00", "available_on": today.isoformat(), "covers_all": rest <= 0})
    if planned:
        options.append({"key": "planned", "legal": True, "send_on": planned["send_on"], "lands": planned["lands"],
                        "amount_cny": planned["amount_cny"], "extra_bdt": "0.00"})

    hundi_extra = hundi_bdt - mid_bdt
    gap = bank_overhead - hundi_extra  # > 0: one bank transfer costs more on paper than this hundi offer
    if rest <= 0:
        verdict = "use_shield"
    elif shield_use > 0:
        verdict = "shield_then_bank"
    elif planned and date.fromisoformat(planned["lands"]) <= lands:
        verdict = "wait_for_planned"
    else:
        verdict = "bank"
    return {
        "amount_cny": str(q2(amount)), "amount_usd": str(q2(usd)), "mid_bdt": str(q2(mid_bdt)),
        "mid_bdt_per_usd": str(q2(mid.bdt_per_usd)), "options": options, "verdict": verdict,
        "bank_costs_more_on_paper_bdt": str(q2(gap)) if gap > 0 else None,
        "shield_saves_vs_hundi_bdt": str(q2(shield_use / amount * hundi_bdt)) if shield_use > 0 else None,
        "risks": _texts(RISKS, lang), "legal_routes": _texts(LEGAL_ROUTES, lang),
        "honest_note": ("On paper this hundi offer costs less than one small bank transfer, because the bank's fixed fees "
                        "are larger than the hundi premium. That gap is real. The legal way to close it is fewer, larger "
                        "planned transfers and your own Shield, never hundi." if gap > 0 else
                        "The legal bank transfer costs no more than this hundi offer, without any of its risks."),
        "data_is_sample": market.quotes_estimated or mid.sample,
    }


def default_planned(decision: dict | None, today: date) -> dict | None:
    """The autopilot's next transfer within 10 days, in the shape `compare` expects."""
    if not decision:
        return None
    if date.fromisoformat(decision["send_on"]) - today > timedelta(days=10):
        return None
    return {"send_on": decision["send_on"], "lands": decision["lands"], "amount_cny": decision["amount_cny"]}
