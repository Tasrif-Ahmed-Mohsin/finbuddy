"""Emergency mode: when something goes wrong, the fastest SAFE way through it.

Three situations from the interviews and the research (P-24 impersonation, N-05 stuck without money):
  * no_money:    the student has (almost) no money. We list every way money can reach them, soonest first, with
                 real dates from both bank calendars: the card (if it still works abroad), money already on the
                 way, an urgent transfer the parent approves, and a short local bridge with the exact amount.
  * card_lost:   freeze first (protective, reversible), then the same plan without the card.
  * scam_call:   someone claims to be police, a court, the embassy, a courier or customs. A fixed guide.
  * family_call: someone tells the PARENT the student was arrested, kidnapped or needs money now. The guide,
                 plus an "Are you safe?" check that only the student can answer, in the app.
Sathi never moves money in an emergency on its own beyond the family mandate, and it can only ever pay the
student's own account and the university: that rule is what makes these scams fail.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.engines.living_planner import ATM_NOTE
from app.engines.year_plan import BankCalendar, Policy, project, runs_out_on
from app.money import ceil_div, q2
from app.notify import cny, day, num

KINDS = ("no_money", "card_lost", "scam_call", "family_call")


@dataclass
class SafetyCheck:
    id: str
    asked_by: str
    asked_at: datetime
    status: str = "open"  # open | safe
    answered_at: datetime | None = None

    def to_dict(self) -> dict:
        return {"id": self.id, "asked_by": self.asked_by, "asked_at": self.asked_at.isoformat(), "status": self.status,
                "answered_at": self.answered_at.isoformat() if self.answered_at else None}


def fastest_money(today: date, balance: Decimal, transit: list[tuple[date, Decimal]], policy: Policy, cal: BankCalendar,
                  card_usable: bool, per_withdrawal_cny: Decimal) -> dict:
    """Every way money can reach the student, soonest first. Facts only; nothing is sent here."""
    daily = policy.daily_spend_cny
    out = runs_out_on(balance, transit, today, daily)
    send_on = today if cal.is_open("BD", today) else cal.next_open("BD", today)
    lands = cal.arrival(send_on, policy.transfer_days)
    closures = list(dict.fromkeys(cal.holidays_between("BD", today, send_on - timedelta(days=1))
                                  + cal.holidays_between("CN", send_on + timedelta(days=policy.transfer_days), lands)))
    on_the_way = [(d, a) for d, a in transit if d <= lands]
    # cash needed to get through, day by day, until the urgent transfer lands (money on the way counts from the
    # day it lands, not before)
    worst = min((project(balance, transit, today, today + timedelta(days=k), daily) for k in range((lands - today).days)),
                default=Decimal(0))
    bridge = ATM_NOTE * ceil_div(-worst, ATM_NOTE) if worst < 0 else Decimal(0)
    options = []
    if card_usable and bridge > 0:
        options.append({"kind": "card_atm", "available_on": today.isoformat(), "amount_cny": str(q2(min(per_withdrawal_cny, max(bridge, ATM_NOTE)))),
                        "who": "student"})
    for d, a in on_the_way:
        options.append({"kind": "on_the_way", "available_on": d.isoformat(), "amount_cny": str(q2(a)), "who": "bank"})
    options.append({"kind": "urgent_transfer", "send_on": send_on.isoformat(), "available_on": lands.isoformat(),
                    "closures": closures, "who": "parent"})
    if bridge > 0 and not card_usable:
        options.append({"kind": "local_bridge", "available_on": today.isoformat(), "amount_cny": str(q2(bridge)),
                        "repay_on": lands.isoformat(), "who": "student"})
    return {"today": today.isoformat(), "balance_cny": str(q2(balance)), "daily_spend_cny": str(daily),
            "days_left": int(balance // daily) if daily > 0 else None, "runs_out_on": out.isoformat() if out else None,
            "card_usable": card_usable, "bridge_needed_cny": str(q2(bridge)), "urgent_lands_on": lands.isoformat(),
            "options": options}


# ---- text (deterministic templates; amounts and dates are formatted here, never by the LLM) --------------
OPTION_TEXT = {
    "card_atm": {
        "en": "Today: withdraw up to {amount_cny} with the Bangladeshi card at a Bank of China or ICBC ATM.",
        "bn": "আজই: ব্যাংক অফ চায়না বা আইসিবিসি এটিএম থেকে বাংলাদেশি কার্ডে {amount_cny} পর্যন্ত তুলুন।",
        "zh": "今天：用孟加拉国银行卡在中国银行或工商银行 ATM 取现，最多 {amount_cny}。"},
    "on_the_way": {
        "en": "{available_on}: {amount_cny} already on the way lands in the Chinese account.",
        "bn": "{available_on}: পথে থাকা {amount_cny} চীনের অ্যাকাউন্টে পৌঁছাবে।",
        "zh": "{available_on}：已在途的 {amount_cny} 到达中国账户。"},
    "urgent_transfer": {
        "en": "{available_on}: an urgent transfer sent on {send_on} (the next Bangladeshi bank day) lands. The parent approves it in the app.{closures_en}",
        "bn": "{available_on}: {send_on} তারিখে (বাংলাদেশে পরের ব্যাংক দিবস) পাঠানো জরুরি ট্রান্সফার পৌঁছাবে। অভিভাবক অ্যাপে অনুমোদন দেবেন।{closures_bn}",
        "zh": "{available_on}：{send_on}（孟加拉国下一个银行工作日）发出的加急汇款到账。由家长在应用中批准。{closures_zh}"},
    "urgent_transfer_today": {
        "en": "{available_on}: an urgent transfer sent today lands, if the parent approves it in the app today.{closures_en}",
        "bn": "{available_on}: আজ পাঠানো জরুরি ট্রান্সফার পৌঁছাবে, যদি অভিভাবক আজই অ্যাপে অনুমোদন দেন।{closures_bn}",
        "zh": "{available_on}：今天发出的加急汇款到账（需家长今天在应用中批准）。{closures_zh}"},
    "local_bridge": {
        "en": "Until then: borrow {amount_cny} from a friend you trust (WeChat Pay or Alipay) or ask the international student office about emergency support; repay after {repay_on}. Never borrow from online lenders or strangers.",
        "bn": "ততদিন: বিশ্বস্ত বন্ধুর কাছ থেকে {amount_cny} ধার নিন (উইচ্যাট পে বা আলিপে), অথবা আন্তর্জাতিক শিক্ষার্থী অফিসে জরুরি সহায়তার কথা জিজ্ঞেস করুন; {repay_on} এর পরে শোধ করুন। অনলাইন ঋণদাতা বা অচেনা কারও কাছ থেকে কখনো ধার নেবেন না।",
        "zh": "在此之前：向信任的朋友借 {amount_cny}（微信支付或支付宝），或询问国际学生办公室是否有紧急援助；{repay_on} 之后归还。切勿向网贷或陌生人借钱。"},
}
CLOSURE_TEXT = {"en": " Banks are closed for {names} in between.", "bn": " মাঝে {names} উপলক্ষে ব্যাংক বন্ধ।",
                "zh": " 期间银行因{names}休息。"}
HEADLINE = {
    "en": "Money left: {balance_cny} ({days_n} {day_word} at {daily_cny} a day).",
    "bn": "হাতে আছে {balance_cny} (দিনে {daily_cny} হিসেবে {days_n} দিন)।",
    "zh": "剩余 {balance_cny}（按每天 {daily_cny} 计，可用 {days_n} 天）。",
}

GUIDES: dict[str, dict[str, dict]] = {
    "scam_call": {
        "en": {"title": "Someone says they are police, a court, the embassy, a courier or customs",
               "steps": ["Hang up. Real police, courts and embassies never ask you to transfer money, keep it secret, or stay on a video call.",
                         "Do not install any app they send, share your screen, or read out a code.",
                         "Check it yourself: call 110 (police) or 96110 (China's anti-fraud line), and tell your university's international student office.",
                         "Tell your family now with \"I'm safe\" below. Scammers often call parents next and say you were arrested or kidnapped.",
                         "Sathi can only pay your own Chinese account and your university. Nobody can add a new payee without both of you."]},
        "bn": {"title": "কেউ বলছে সে পুলিশ, আদালত, দূতাবাস, কুরিয়ার বা কাস্টমস থেকে",
               "steps": ["ফোন কেটে দিন। আসল পুলিশ, আদালত বা দূতাবাস কখনো টাকা পাঠাতে, গোপন রাখতে বা ভিডিও কলে থাকতে বলে না।",
                         "তাদের পাঠানো কোনো অ্যাপ ইনস্টল করবেন না, স্ক্রিন শেয়ার করবেন না, কোনো কোড বলবেন না।",
                         "নিজে যাচাই করুন: ১১০ (পুলিশ) বা ৯৬১১০ (চীনের প্রতারণা-বিরোধী লাইন) নম্বরে ফোন করুন, আর বিশ্ববিদ্যালয়ের আন্তর্জাতিক শিক্ষার্থী অফিসকে জানান।",
                         "নিচের \"আমি নিরাপদ\" দিয়ে এখনই পরিবারকে জানান। প্রতারকেরা প্রায়ই এরপর বাবা-মাকে ফোন করে বলে আপনি গ্রেপ্তার বা অপহৃত।",
                         "সাথী শুধু আপনার নিজের চীনা অ্যাকাউন্ট আর বিশ্ববিদ্যালয়ে টাকা পাঠাতে পারে। আপনাদের দুজনের সম্মতি ছাড়া কেউ নতুন প্রাপক যোগ করতে পারে না।"]},
        "zh": {"title": "有人自称是警察、法院、大使馆、快递或海关",
               "steps": ["立即挂断。真正的警察、法院和大使馆绝不会要求你转账、保密或一直保持视频通话。",
                         "不要安装对方发来的任何应用，不要共享屏幕，不要报出验证码。",
                         "自己核实：拨打 110（报警）或 96110（全国反诈专线），并告知学校国际学生办公室。",
                         "现在就用下面的“我很安全”告诉家人。骗子常会接着给父母打电话，说你被捕或被绑架。",
                         "Sathi 只能向你本人的中国账户和学校付款。没有你们双方同意，任何人都不能添加新的收款人。"]},
    },
    "family_call": {
        "en": {"title": "Someone says your child was arrested, kidnapped, is in hospital or needs money now",
               "steps": ["Do not pay and do not stay on the line. Real police never ask families for money by phone.",
                         "Tap \"Ask: are you safe?\". Your child answers in the Sathi app, which a caller cannot do for them.",
                         "Call your child directly, then the university's international student office.",
                         "If you cannot reach them, call the Bangladesh Embassy in Beijing using the number on its official website, never a number the caller gives you.",
                         "Sathi will not send money to anyone except your child's own account and the university, whatever anyone says."]},
        "bn": {"title": "কেউ বলছে আপনার সন্তান গ্রেপ্তার, অপহৃত, হাসপাতালে বা এখনই টাকা লাগবে",
               "steps": ["টাকা দেবেন না, লাইনে থাকবেন না। আসল পুলিশ কখনো ফোনে পরিবারের কাছে টাকা চায় না।",
                         "\"জিজ্ঞেস করুন: তুমি নিরাপদ?\" চাপুন। আপনার সন্তান সাথী অ্যাপে উত্তর দেবে, যা ফোনকারী তার হয়ে করতে পারে না।",
                         "সরাসরি সন্তানকে ফোন করুন, তারপর বিশ্ববিদ্যালয়ের আন্তর্জাতিক শিক্ষার্থী অফিসে।",
                         "যোগাযোগ না হলে বেইজিংয়ে বাংলাদেশ দূতাবাসে ফোন করুন, দূতাবাসের অফিশিয়াল ওয়েবসাইটের নম্বরে; ফোনকারীর দেওয়া নম্বরে কখনো নয়।",
                         "কেউ যা-ই বলুক, সাথী আপনার সন্তানের নিজের অ্যাকাউন্ট আর বিশ্ববিদ্যালয় ছাড়া কাউকে টাকা পাঠাবে না।"]},
        "zh": {"title": "有人说你的孩子被捕、被绑架、住院或急需用钱",
               "steps": ["不要付钱，也不要一直通话。真正的警察绝不会打电话向家属要钱。",
                         "点击“问一下：你安全吗？”。孩子会在 Sathi 应用里回答，打电话的人无法替他回答。",
                         "直接给孩子打电话，然后联系学校的国际学生办公室。",
                         "如果联系不上，请拨打孟加拉国驻北京大使馆官网上的电话，绝不要用来电者给的号码。",
                         "无论对方怎么说，Sathi 只会向孩子本人的账户和学校付款。"]},
    },
    "card_lost": {
        "en": {"title": "The card is lost or stolen",
               "steps": ["The card is frozen now: no new charges can go through.",
                         "Call your bank's 24-hour number from its official website or the back of another card, not from an SMS.",
                         "If it is really lost, tap \"Report lost\" in the app (only you can do this, with your fingerprint).",
                         "Living money still reaches your Chinese account by transfer. The plan below already leaves out the card."]},
        "bn": {"title": "কার্ড হারিয়ে গেছে বা চুরি হয়েছে",
               "steps": ["কার্ড এখন বন্ধ (ফ্রিজ): নতুন কোনো খরচ হবে না।",
                         "ব্যাংকের অফিশিয়াল ওয়েবসাইট থেকে ২৪ ঘণ্টার নম্বরে ফোন করুন, কোনো এসএমএসের নম্বরে নয়।",
                         "সত্যিই হারিয়ে গেলে অ্যাপে \"হারানো রিপোর্ট\" চাপুন (শুধু আপনি পারবেন, আঙুলের ছাপ দিয়ে)।",
                         "মাসিক খরচের টাকা ট্রান্সফারে চীনের অ্যাকাউন্টে আসতেই থাকবে। নিচের পরিকল্পনায় কার্ড ধরা হয়নি।"]},
        "zh": {"title": "银行卡丢失或被盗",
               "steps": ["卡已冻结：不会再有新的扣款。",
                         "请拨打银行官网上的 24 小时电话，不要用短信里的号码。",
                         "如果确实丢失，请在应用中点击“挂失”（只有你本人可以，用指纹确认）。",
                         "生活费仍会通过汇款到达你的中国账户。下面的计划已不再依赖这张卡。"]},
    },
}


def render_plan(plan: dict, lang: str, holiday_names: dict[str, dict[str, str]]) -> dict:
    lang = lang if lang in ("en", "bn", "zh") else "en"
    lines = []
    for o in plan["options"]:
        vals = {k: (cny(v, lang) if k.endswith("_cny") else day(v, lang) if k in ("available_on", "send_on", "repay_on") else v)
                for k, v in o.items()}
        names = ", ".join(holiday_names.get(n, {}).get(lang, n) for n in o.get("closures", []))
        vals[f"closures_{lang}"] = CLOSURE_TEXT[lang].format(names=names) if names else ""
        key = "urgent_transfer_today" if o["kind"] == "urgent_transfer" and o["send_on"] == plan["today"] else o["kind"]
        lines.append({"kind": o["kind"], "text": OPTION_TEXT[key][lang].format(**vals)})
    days = plan["days_left"] or 0
    head = HEADLINE[lang].format(balance_cny=cny(plan["balance_cny"], lang), days_n=num(days, lang),
                                 day_word="day" if days == 1 else "days", daily_cny=cny(plan["daily_spend_cny"], lang))
    return {"headline": head, "options": lines}


def guide(kind: str, lang: str) -> dict:
    lang = lang if lang in ("en", "bn", "zh") else "en"
    return GUIDES[kind][lang]
