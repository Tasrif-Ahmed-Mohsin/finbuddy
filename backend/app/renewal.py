"""Renewal assistant (task T3, problem N-05: the friend's #1 pain).

Students' card endorsements are short (e.g. September → December) and the Student File must be renewed
every year, so the money pipeline from home keeps breaking. This module turns a renewal into a plan:

  1. work BACKWARDS from the expiry date: bank visit → documents to the parent → ask the university
  2. draft the messages: email to the university (English + Chinese), task list for the parent
     (Bengali + English). Bluefin never sends them; the user copies or shares them.
  3. track each step until the user confirms the new expiry date.

Card endorsement (Interview #1 follow-up, 2026-10-13): renewing it needs the STUDENT in person at the bank,
because it needs the passport. A student living in China therefore cannot renew it before the next visit
home, and the card stops working abroad on the expiry date. The plan then switches living money to bank
transfers from the Student File to the student's own Chinese account (which do not need the card) before
that date, and schedules the renewal for the next visit home.

Document lists come from Bangladeshi banks' Student File pages (secondary sources) and our interview.
Exact requirements differ by bank, so every list ends with "confirm with your bank".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from app.corridors.loader import Corridor

ITEMS = {
    "endorsement_expiry": {"en": "Card endorsement", "bn": "কার্ড এনডোর্সমেন্ট", "zh": "银行卡外汇签注"},
    "student_file_expiry": {"en": "Student File", "bn": "স্টুডেন্ট ফাইল", "zh": "留学档案（Student File）"},
}

# What the university must provide (Chinese names help at the international office counter).
UNIVERSITY_DOCS = [
    {"key": "enrolment", "en": "Enrolment certificate (proof that you are a current student)", "zh": "在读证明",
     "bn": "এনরোলমেন্ট সার্টিফিকেট (বর্তমান ছাত্র হওয়ার প্রমাণ)", "confidence": "secondary",
     "source": "Bangladeshi banks' Student File renewal requirements"},
    {"key": "transcript", "en": "Transcript / progress report", "zh": "成绩单",
     "bn": "ট্রান্সক্রিপ্ট / অগ্রগতি প্রতিবেদন", "confidence": "secondary",
     "source": "Bangladeshi banks' Student File renewal requirements"},
    {"key": "fee_notice", "en": "Fee notice / invoice for the coming semester or year", "zh": "下学期（学年）缴费通知单",
     "bn": "আগামী সেমিস্টার বা বছরের ফি নোটিশ / ইনভয়েস", "confidence": "secondary",
     "source": "Bangladeshi banks' Student File renewal requirements"},
]
# What the parent brings to the bank in addition.
BANK_DOCS = [
    {"key": "passport", "en": "Copy of the student's passport (photo page, visa and residence permit pages)",
     "bn": "শিক্ষার্থীর পাসপোর্টের কপি (ছবির পাতা, ভিসা ও রেসিডেন্স পারমিটের পাতা)", "confidence": "assumption",
     "source": "Typical bank KYC; confirm with your bank"},
    {"key": "file_number", "en": "Student File number / account details", "bn": "স্টুডেন্ট ফাইল নম্বর / অ্যাকাউন্টের তথ্য",
     "confidence": "assumption", "source": "Typical bank practice; confirm with your bank"},
]


@dataclass
class RenewalStep:
    id: str
    owner: str  # student | parent | bank
    due: date
    title: str
    detail: str
    status: str = "todo"  # todo | done

    def to_dict(self, today: date) -> dict:
        days = (self.due - today).days
        return {"id": self.id, "owner": self.owner, "due": self.due.isoformat(), "days_left": days, "title": self.title,
                "detail": self.detail, "status": self.status,
                "state": "done" if self.status == "done" else "overdue" if days < 0 else "due_soon" if days <= 2 else "upcoming"}


@dataclass
class RenewalCase:
    id: str
    item: str
    expiry: date
    created: date
    steps: list[RenewalStep]
    late: bool
    status: str = "open"  # open | completed
    new_expiry: date | None = None
    messages: dict = field(default_factory=dict)

    def next_step(self) -> RenewalStep | None:
        return next((s for s in self.steps if s.status != "done"), None)

    def to_dict(self, today: date) -> dict:
        nxt = self.next_step()
        return {"id": self.id, "item": self.item, "label": ITEMS[self.item], "expiry": self.expiry.isoformat(),
                "days_to_expiry": (self.expiry - today).days, "status": self.status, "late": self.late,
                "new_expiry": self.new_expiry.isoformat() if self.new_expiry else None,
                "next_step": nxt.id if nxt else None,
                "steps": [s.to_dict(today) for s in self.steps],
                "documents": {"university": UNIVERSITY_DOCS, "bank": BANK_DOCS},
                "messages": self.messages,
                "note": "Requirements differ by bank. Confirm the exact list with your bank before the visit."}


def plan_renewal(case_id: str, item: str, expiry: date, today: date, corridor: Corridor, profile: dict) -> RenewalCase:
    if item not in ITEMS:
        raise ValueError(f"unknown renewal item '{item}'")
    if (item == "endorsement_expiry" and corridor.i("endorsement_renewal_in_person") == 1
            and profile.get("student_location", "CN") != "BD"):
        return plan_endorsement_from_abroad(case_id, expiry, today, corridor, profile)
    buffer = corridor.i("renewal_buffer_days")
    processing = corridor.i("renewal_bank_processing_days")
    scan = corridor.i("renewal_scan_send_days")
    univ = corridor.i("renewal_university_doc_days")

    bank_visit = expiry - timedelta(days=buffer + processing)
    docs_to_parent = bank_visit - timedelta(days=scan)
    request_docs = docs_to_parent - timedelta(days=univ)
    late = today > request_docs

    def due(d: date) -> date:
        return max(d, today)  # if we are already late, everything is due as soon as possible

    label = ITEMS[item]["en"]
    bank = profile.get("home_bank", "your bank")
    steps = [
        RenewalStep("request_docs", "student", due(request_docs), "Ask the international office for documents",
                    "Send the prepared email (English + Chinese) asking for: enrolment certificate (在读证明), transcript "
                    "(成绩单) and the next fee notice (缴费通知单)." + (" You are late: ask for express processing." if late else "")),
        RenewalStep("collect_docs", "student", due(docs_to_parent - timedelta(days=1)), "Collect the stamped documents",
                    "Pick up the documents with the university stamp (公章) and scan them clearly (PDF or photos)."),
        RenewalStep("send_to_parent", "student", due(docs_to_parent), "Send the scans to your parent",
                    "Share the prepared message with the scans so your parent knows exactly what to bring to the bank."),
        RenewalStep("bank_visit", "parent", due(bank_visit), f"Renew at {bank}",
                    f"Visit the branch that holds the Student File with the documents. Ask for the {label} to cover the whole "
                    "invoice period (until the next fee is due), not only a few months."),
        RenewalStep("confirm_new_expiry", "parent", due(expiry - timedelta(days=buffer)), "Confirm the new expiry date in Bluefin",
                    "Enter the new expiry date the bank gives you, so Bluefin can track it and unblock payments."),
    ]
    case = RenewalCase(case_id, item, expiry, today, steps, late)
    case.messages = draft_messages(case, profile)
    return case


def plan_endorsement_from_abroad(case_id: str, expiry: date, today: date, corridor: Corridor, profile: dict) -> RenewalCase:
    """The student is in China and must renew in person: keep the money coming without the card."""
    lead = corridor.i("bd_tt_transfer_days") + corridor.i("living_safety_days")
    switch = expiry - timedelta(days=lead)  # the first transfer must land before the card stops
    check = switch - timedelta(days=7)
    late = today > switch

    def due(d: date) -> date:
        return max(d, today)

    bank = profile.get("home_bank", "your bank")
    steps = [
        RenewalStep("check_cn_account", "student", due(check), "Check your Chinese bank account can receive money",
                    "Make sure the account is active and your current passport number is on file (an outdated passport is a "
                    "common reason banks freeze foreigners' accounts). Transfers will now arrive there."),
        RenewalStep("switch_living_money", "parent", due(switch), "Switch living money to bank transfers",
                    "Sign the family mandate in Bluefin (Family tab) so living money goes from the Student File to the student's "
                    "own Chinese account. Transfers do not need the card, so nothing stops on "
                    f"{expiry.isoformat()}." + (" You are late: sign it today." if late else "")),
        RenewalStep("renew_in_person", "student", due(expiry), "Renew the endorsement on your next visit home",
                    f"The bank needs you in person with your passport. On your next visit to Bangladesh, go to the {bank} branch "
                    "that holds your Student File with the documents below, and ask for the endorsement to cover the whole "
                    "study period, not only a few months."),
        RenewalStep("confirm_new_expiry", "student", due(expiry), "Confirm the new expiry date in Bluefin",
                    "Enter the new expiry date the bank gives you, so Bluefin can use the card again where it is cheaper."),
    ]
    case = RenewalCase(case_id, "endorsement_expiry", expiry, today, steps, late)
    case.messages = draft_messages(case, profile)
    return case


def draft_messages(case: RenewalCase, profile: dict) -> dict:
    """Deterministic templates (work offline, no invented facts). The user fills the [brackets]."""
    name = profile.get("student_name", "[your name]")
    univ = profile.get("university", "[university]")
    bank = profile.get("home_bank", "your bank")
    steps = {s.id: s for s in case.steps}
    in_person = "renew_in_person" in steps
    need_by = (steps["collect_docs"].due if "collect_docs" in steps else steps["renew_in_person"].due).isoformat()
    visit_by = (steps["bank_visit"].due if "bank_visit" in steps else steps["switch_living_money"].due).isoformat()
    label = ITEMS[case.item]

    email_en = (
        f"Subject: Request for enrolment certificate, transcript and fee notice – {name}, [student ID]\n\n"
        f"Dear International Student Office,\n\n"
        f"I am {name} ([student ID], [programme]) at {univ}. My bank in Bangladesh needs the following documents to renew "
        f"my study-abroad remittance file ({label['en']}), which expires on {case.expiry.isoformat()}:\n"
        "1. Enrolment certificate (stamped)\n2. Transcript / progress report\n3. Fee notice for the next semester\n\n"
        f"Could you please prepare them by {need_by}? I can collect them in person. Thank you very much.\n\n"
        f"Best regards,\n{name}\n[phone] · [email]"
    )
    email_zh = (
        f"主题：申请在读证明、成绩单和缴费通知单 – {name}，学号[学号]\n\n"
        "国际学生办公室老师您好：\n\n"
        f"我是{univ}的留学生{name}（学号：[学号]，专业：[专业]）。我在孟加拉国的银行需要以下材料，"
        f"用于续办我的留学汇款档案（{label['zh']}），该档案将于{case.expiry.isoformat()}到期：\n"
        "1. 在读证明（加盖公章）\n2. 成绩单\n3. 下学期缴费通知单\n\n"
        f"请问能否在{need_by}之前帮我准备好？我可以本人前来领取。非常感谢！\n\n"
        f"此致\n敬礼\n{name}\n[电话] · [邮箱]"
    )
    bank_bn = "আপনার ব্যাংক" if bank == "your bank" else bank
    docs_bn = "\n".join(f"• {d['bn']}" for d in UNIVERSITY_DOCS + BANK_DOCS)
    docs_en = "\n".join(f"• {d['en']}" for d in UNIVERSITY_DOCS + BANK_DOCS)
    if in_person:
        parent_bn = (
            f"আসসালামু আলাইকুম। আমার {label['bn']} এর মেয়াদ {case.expiry.isoformat()} তারিখে শেষ হবে। এরপর আমার কার্ড "
            "বিদেশে কাজ করবে না, আর নবায়ন করতে আমাকে নিজে পাসপোর্ট নিয়ে ব্যাংকে যেতে হবে, যা দেশে আসার আগে সম্ভব নয়।\n\n"
            f"তাই অনুগ্রহ করে {visit_by} তারিখের মধ্যে ব্লুফিন অ্যাপের 'পরিবার' পাতায় পারিবারিক ম্যান্ডেটে সই করবেন। তাহলে মাসিক খরচ "
            "স্টুডেন্ট ফাইল থেকে সরাসরি আমার চীনের ব্যাংক অ্যাকাউন্টে যাবে, কার্ড লাগবে না। প্রতিবার আপনি জানতে পারবেন।\n\n"
            "দেশে এলে আমি নিজে ব্যাংকে গিয়ে এনডোর্সমেন্ট নবায়ন করব, এবং শুধু কয়েক মাস নয়, পুরো পড়াশোনার সময়ের জন্য চাইব।"
        )
        parent_en = (
            f"My {label['en']} expires on {case.expiry.isoformat()}. After that my card stops working abroad, and renewing it "
            "needs me in person at the bank with my passport, which I can only do when I visit home.\n\n"
            f"So please sign the family mandate in the Bluefin app (Family tab) by {visit_by}. Then living money goes from the "
            "Student File straight to my Chinese bank account, without the card, and you are told every time.\n\n"
            "When I visit home I will renew the endorsement myself, and ask for the whole study period, not only a few months."
        )
        return {"university_email": {"en": email_en, "zh": email_zh}, "parent_message": {"bn": parent_bn, "en": parent_en}}
    parent_bn = (
        f"আসসালামু আলাইকুম। আমার {label['bn']} এর মেয়াদ {case.expiry.isoformat()} তারিখে শেষ হবে। "
        f"মেয়াদ শেষ হলে আমার কার্ড বিদেশে কাজ করবে না।\n\n"
        f"অনুগ্রহ করে {visit_by} তারিখের মধ্যে {bank_bn}-এর যে শাখায় স্টুডেন্ট ফাইল আছে, সেখানে এই কাগজগুলো নিয়ে যাবেন "
        f"(স্ক্যান কপি আমি পাঠাচ্ছি):\n{docs_bn}\n\n"
        "ব্যাংককে অনুরোধ করবেন যেন মেয়াদ শুধু কয়েক মাস নয়, পরের ফি জমা দেওয়ার সময় পর্যন্ত দেয়। "
        "যাওয়ার আগে ব্যাংকে ফোন করে কাগজের তালিকা মিলিয়ে নেবেন। নতুন মেয়াদের তারিখটা আমাকে জানাবেন।"
    )
    parent_en = (
        f"My {label['en']} expires on {case.expiry.isoformat()}; after that my card stops working abroad.\n\n"
        f"Please visit the {bank} branch that holds my Student File by {visit_by} with these documents "
        f"(I am sending the scans):\n{docs_en}\n\n"
        "Please ask the bank to give the new period until the next fee is due, not only a few months. "
        "Call the bank first to confirm the list. Please tell me the new expiry date."
    )
    return {"university_email": {"en": email_en, "zh": email_zh}, "parent_message": {"bn": parent_bn, "en": parent_en}}
