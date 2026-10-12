# Problem Research — International Students' Money Problems in China

**Focus corridor:** Bangladesh → China (findings that apply to other South Asian / African corridors are noted).
**Last updated:** 2026-10-12
**Purpose:** Evidence base for the problems Sathi solves. Feeds the pitch deck, the technical doc, and the solution design (next step).

### Confidence labels

| Label | Meaning |
|---|---|
| ✅ | Official / primary source (government, regulator, university page, peer-reviewed paper, major news report) |
| ⚠️ | Secondary source (guide, blog, op-ed, vendor). Probably right, **verify before putting a number on a slide** |
| ❓ | Not found / unverified. **Ask our friend in China, the university, or a Bangladeshi bank** |
| 🗣️ | Field evidence from a real student interview (Interview #1: self-funded Bangladeshi student who arrived in China in Sept 2026; anonymised). One person's experience: strong for "this happens", weak for "how often" |

Severity is our own judgment: **H** = can cost a whole semester's money or block study, **M** = recurring meaningful loss or stress, **L** = annoyance.

---

## A. Before leaving Bangladesh

### P-01 · Banks refuse or delay the "student file" during dollar shortages — H
- For over a year (2023–Feb 2024), thousands of Bangladeshi students could not open the bank "student file" needed to pay fees abroad. Most banks stopped opening them during the dollar crisis; some opened them only through connections. ✅ [Daily Star](https://www.thedailystar.net/business/news/studying-abroad-students-struggle-open-profiles-dollar-crisis-3540301), [UNB](https://unb.com.bd/category/Bangladesh/challenges-to-studying-abroad-banks-not-opening-student-profiles/104628)
- Official higher-education outflows barely moved ($240M vs $235M, Jul–Nov FY24 vs FY23) even though demand grew, because of these restrictions. ✅ (same Daily Star report)
- Families turned to hundi (informal transfer). ⚠️ opinion column, [Financial Express](https://thefinancialexpress.com.bd/views/columns/draining-of-dollar-is-biggest-headache)
- **Who's hurt:** parents and new students. **Hook:** early-warning on bank and dollar-availability stress; a checklist and plan for the student file; never route to hundi.

### P-02 · Bangladesh's outward-remittance rules are complex and change — M
- FE Circular No. 37 (2025): tuition up to the institution's demand note (no fixed cap); living costs up to **USD 2,000/month** (+50% for high-cost locations, with proof); **USD 1,000** one-time incidental allowance for new students. ⚠️ [Legalseba guide](https://legalseba.com/bd-articles/?p=1125)
- Later-semester payments need **proof of academic progression**. ⚠️ [Observer 2026](https://observerbd.com/news/584772)
- The circular was reportedly valid only until **29 Sep 2026**, so it may have been replaced. ❓ Check bb.org.bd / an authorised bank.
- **Hook:** rules stored as versioned data with a "last verified" date; the compliance engine checks every transfer against them.

### P-03 · Funding uncertainty: scholarships are scarce, most students self-fund — M
- The CSC (Chinese Government Scholarship) is competitive; one blog says 55 Bangladeshi students received it in 2023. ⚠️ [blog](https://studentshub.digitalpress.blog/study-in-china-from-bangladesh/)
- One search summary quoted Ministry of Education 2018 figures: 12.81% of international students in China were on Chinese Government Scholarships and 87.19% were self-funded. ⚠️ **Exact source paper still to re-check; don't put this on a slide yet.**
- Roughly 20,000 Bangladeshi students are in China (Chinese ambassador's claim, undated). ⚠️ [SIIS reprint of Daily Star column](https://www.siis.org.cn/mjlsp/17410.jhtml)
- **Hook:** whole-degree cost plan (tuition + housing + insurance + residence permit + living) in BDT, with FX ranges.

### P-04 · Carrying cash because there's no bank account yet — M
- Cash of **≥ RMB 20,000** or foreign currency **≥ USD 5,000 equivalent** must be declared on entry. There is no cap on bringing foreign currency in, only the declaration rule. ✅ [Shanghai customs guide](https://english.shanghai.gov.cn/en-CustomsClearance/20231212/9a3c7f512d464e0798be3fc76c8dd6f2.html)
- Taking out more than USD 5,000 in foreign cash needs a bank-issued permit. ⚠️ [China Highlights](https://chinahighlights.com/travelguide/guidebook/customs.htm)
- Risks: loss or theft, poor airport exchange rates, customs trouble if the student doesn't know the rule.
- **Hook:** an "arrival cash calculator": how much cash covers the days until a bank account opens, below declaration thresholds, with the rule explained in Bengali.

---

## B. Paying tuition and fees

### P-05 · Double conversion: BDT → USD → CNY — M/H
- Bangladesh has no deep direct taka–yuan retail market; payments usually route through USD, so the family pays **two spreads**.
- Since 2018, Bangladeshi banks may hold **CNY clearing accounts** at Bangladesh Bank. ✅ [TBS](https://www.tbsnews.net/node/496930). Whether *students* can get a direct BDT→CNY rate for tuition is **unknown** ❓.
- Bank FX markups are often 2–6% per conversion. ⚠️ [Angel One citing an industry report](https://oga-prod.angelone.in/news/personal-finance/hidden-costs-of-studying-abroad-how-indian-families-lose-1-700-crore)
- The World Bank's global average remittance cost is **6.49%** (Q1 2025, for $200 transfers; large tuition payments are usually cheaper in %, but not free). ✅ [World Bank RPW](https://remittanceprices.worldbank.org/sites/default/files/rpw_main_report_and_annex_q125_1_0.pdf)
- **Hook:** a true-cost engine that multiplies every leg's spread and fee, and compares USD-pay vs CNY-pay vs other routes.
- 🗣️ **Field update (Interview #1):** tuition was paid **directly in CNY** through **BRAC Bank PLC**: 35,200 CNY, arrived in about 1 week, university accepts CNY. So a CNY route exists. The bank's BDT/CNY rate still contains a markup (probably priced via USD internally), and the friend says **each Bangladeshi bank quotes a different rate** (see N-04). For scale: 35,200 CNY ≈ 6.2 lakh BDT at the Feb 2026 mid-market rate (~17.7 BDT/CNY, Wise). The exact BDT debited is still needed to measure the markup.

### P-06 · Fees count as "paid" only when they ARRIVE — H
- Nanjing Medical University: *the date funds reach the Finance Department is the payment date*. All fees are due by the end of the first week of the academic year. A remittance receipt is not proof of payment. ✅ [NJMU](https://intladmission.njmu.edu.cn/17890/list.htm)
- Central China Normal University: self-funded students pay at least one semester before classes, **in person** with passport and student ID. ✅ [CCNU](https://is.ccnu.edu.cn/info/1018/1368.htm)
- **Hook:** plan backwards from the arrival deadline (send-by date = deadline − transfer time − buffer), then track until the university confirms receipt.

### P-07 · Unknown intermediary and receiving-bank deductions — M
- No published data was found on correspondent or receiving fees for SWIFT payments into Chinese university accounts. ❓
- 🗣️ Field: about **8,000 BDT "student file charge"** was deducted on the Bangladesh side. Other banks list Student File renewal at **Tk 4,500–6,000 + VAT per year**, and the file must be **renewed every year** with an enrolment certificate, transcript, and the year's invoice. ⚠️ [City Bank](https://www.banksbd.org/cibl/student-file.html), [Dhaka Bank](https://dhakabank.com.bd/shopno-jatra-student-service/), [UNB](https://unb.com.bd/category/Bangladesh/higher-education-abroad-how-bangladeshis-can-open-student-files/128093)
- Student File money can only go to the institution or to the **student's own account abroad**. ⚠️ (same sources)
- Generic risk: the university receives less than the invoice → "unpaid balance" → late status.
- **Hook:** pick the right fee option (OUR/SHA/BEN), add a fee buffer, and confirm receipt. **Ask our friend what was deducted.**

### P-08 · Many small fee items, each paid a different way — L/M
- Example (NJMU MBBS): tuition **RMB 34,000/yr** (English-taught) or 30,000 (Chinese-taught); accommodation **6,000–12,000**; insurance **600**; residence permit **400**; registration **500**. ✅ [NJMU](https://intladmission.njmu.edu.cn/17890/list.htm)
- Xiamen University: English-taught programmes cost **30% more** than Chinese-taught. ✅ [Xiamen gov](https://www.xm.gov.cn/english/services/life/tipsforlivinginchina/202111/t20211108_2596811.html)
- **Hook:** a document reader turns the fee notice into a payment calendar with each item, deadline, and best channel.

### P-09 · "Discount tuition agent" scam — H
- Pattern seen in Australia and the UK: a fake "agent" offers 10–20% off tuition, pays with a stolen card, the payment bounces, and the student loses the money **and** still owes the full fee. One Adelaide student lost **AU$45,000**. ✅ [UTS](https://www.uts.edu.au/for-students/admissions-entry/fees-costs/payment-information/warning-fraudulent-payment-scams), [Adelaide](https://international.uni.adelaide.edu.au/international-student-support/scam-awareness)
- Prevalence among China-bound students is unknown ❓, but the pattern transfers easily.
- **Hook:** a payee allow-list (only the university's official accounts) plus scam-pattern detection on chat and documents.

---

## C. Arrival: the first 30 days ("financial limbo")

### P-10 · No Chinese bank account until documents are ready — M (downgraded after Interview #1)
- 🗣️ **Field correction:** the friend opened a Chinese bank account **within a few hours with passport only**, and the card was issued the **same day**. This is probably a university-partner branch, so the guides below overstate the gap for at least some universities.
- 🗣️ Residence formalities (friend + university checklist): **register residence at the police station within 24 hours** of arrival; **extend visa / get residence permit within 30 days**. The university's checklist lists the application form, introduction letter, passport bio page, visa page, last entry stamp, old residence permit (if any), JW201/JW202, admission letter, health check report, accommodation registration form, and a photo. Photo saved at [`evidence/residence_permit_documents_checklist.webp`](evidence/residence_permit_documents_checklist.webp), a good bilingual test document for the document reader.
- Desk research (may vary by bank and city):
  - Typical requirements: passport, **residence permit** (most banks), admission letter or student ID, and a **Chinese phone number**, in person at a branch. Banks don't open personal RMB accounts remotely. ⚠️ [WentChina 2026](https://wentchina.com/how-to-open-a-bank-account-in-china-as-a-foreign-student-2026/), ✅ [USTB](https://oia.ustb.edu.cn/InternationalFaculty/WorkingUSTB/CampusServices/index.htm)
  - Some guides say a long-stay visa is enough; others say the residence permit is essential. ⚠️
- **Hook:** a first-30-days plan: the 24-hour and 30-day deadlines, a document checklist (read from the university's Chinese/English sheet), which bank, plus a bridge payment method meanwhile.

### P-11 · Foreign-card mobile payments: limits, fees, risk controls — M
- PBOC (March 2024): foreign-card limits on Alipay/Tenpay raised from **USD 1,000 → 5,000 per transaction** and **USD 10,000 → 50,000 per year**. ✅ [Xinhua via Ukranews](https://ukranews.com/en/news/988846-china-further-streamlines-mobile-payments-for-foreigners), [SCMP](https://scmp.com/tech/big-tech/article/3254710/chinas-alipay-and-wechat-pay-ease-way-foreign-travellers-make-payments-worlds-largest-cashless)
- The higher annual cap needs ID registration; without it, about USD 2,000. ⚠️ [Payments Journal](https://www.paymentsjournal.com/making-payments-in-china-just-got-easier-for-foreign-visitors)
- About **3% fee on payments above RMB 200** with foreign cards, on top of the card issuer's FX markup. ⚠️ [WentChina](https://wentchina.com/how-to-open-a-bank-account-in-china-as-a-foreign-student-2026/), [travelofchina](https://www.travelofchina.com/alipay-wechat-new-5000-limit-for-foreigners-2026/)
- Real limits are set by risk control and can be much lower (often USD 200–500 on the no-ID tier). ⚠️ blog
- **Hook:** the true-cost engine includes the "foreign card + 3%" route; the agent tells students when opening a local account starts paying for itself.

### P-12 · A foreign card can't pay *people* — M
- With foreign cards, students generally **can't transfer to individuals, send red packets, or withdraw to a bank**, so they can't split rent, repay a classmate, or pay a small landlord. WeChat is more restrictive than Alipay. Incomplete real-name verification locks transfers. ⚠️ [wanderinchina](https://www.wanderinchina.com/survival-guide/payment/wechat-pay-vs-alipay/), [chinafortravelers](https://chinafortravelers.com/guides/wechat-pay-for-foreigners/)
- **Hook:** a social-payment workaround guide plus prioritising the bank-account step.

### P-13 · Mandatory health insurance: pay first, claim later — M
- All international students must buy China's comprehensive insurance (**RMB 800/yr or 400/semester**) **before they can register**. Home-country insurance doesn't replace it. ✅ [China Daily Study China](https://studychina.chinadaily.com.cn/s/202509/18/WS68cbca7a498e3685503354d8/medical-insurance-guide-for-international-students-in-china.html)
- Outpatient: **650 RMB deductible**, 85% reimbursed above it, cap RMB 20,000; public hospitals only; pay first, then claim via the international office with receipts. ✅/⚠️ university pages ([BFSU](https://osao.bfsu.edu.cn/info/1048/1959.htm))
- **73%** of 384 international students in Nanjing named financial constraints as a barrier to healthcare, and **89%** named language barriers. ✅ [J. International Students 2026](https://ojed.org/jis/article/view/9852)
- **Hook:** an insurance-claim assistant (what's covered, which receipts to keep, a claim checklist) plus an emergency medical cash buffer in the budget.

### P-14 · e-CNY wallet as a bridge (opportunity, not only a problem) — L
- The e-CNY wallet can be registered with phone numbers from **210+ countries**, no Chinese bank account needed. The anonymous tier is capped at **CNY 2,000/transaction, 5,000/day**; it can be topped up with Visa/Mastercard (with some limits). ⚠️ [China Briefing](https://www.china-briefing.com/news/chinas-digital-yuan-app-gets-a-boost-new-features-enhance-convenience-for-foreign-users/), [registrationchina](https://www.registrationchina.com/articles/china-e-cny-guide-for-foreigners/)
- **Hook:** include it as a route in the first-30-days plan. This is a compliant "digital money" angle, unlike crypto.

### P-15 · Stipend timing gaps and arrears — M
- CSC stipend tiers: **RMB 2,500 / 3,000 / 3,500 per month** (bachelor / master / PhD). ✅ [Nanchang Univ.](https://iec.ncu.edu.cn/english/Scholarships/ChineseGovernments/index.htm)
- Registering after the 15th of a month gets **half** that month's stipend. ✅ (same page)
- Delayed payments ("funds have not arrived") reported in 2015 and 2019. ⚠️ [Chinese-forums](https://chinese-forums.com/forums/topic/47638-raise-in-foreign-student-subsidies)
- Home-government stipends can stop: at least **270 Pakistani students** in a provincial programme in China went unpaid (2018). ✅ [Express Tribune](https://tribune.com.pk/story/1847585/students-china-face-hardship-govt-fails-pay-stipend)
- **Hook:** stipend-aware budget with a gap forecast ("your first stipend lands around X; you need RMB Y until then").

---

## D. Daily life and banking in China

### P-16 · Bank accounts get frozen — H
Three kinds of freeze ⚠️ [TropicalHainan, Mar 2026](https://www.tropicalhainan.com/why-foreigners-lose-access-to-their-chinese-bank-accounts/):
1. **Bank-initiated:** an expired passport number on file after renewal (foreigners' passports expire much sooner than Chinese ID cards), a name mismatch, or dormancy (typically **1–2 years** without activity).
2. **Judicial/administrative:** court or tax orders.
3. **Police:** the account *received* money linked to a fraud network, even unknowingly. Can take weeks or months.

Other details:
- Words like "Bitcoin", "USDT", "DOGE" in a transfer note can trigger restrictions. ⚠️
- Single-day cash of **≥ RMB 50,000** triggers mandatory reporting. ⚠️
- Recourse: Article 39 of the Anti-Money Laundering Law (in force 1 Jan 2025): a formal objection must get a bank response within **15 days**. ⚠️ (as described by the article; verify against the law text)

**Hook:** an account-health monitor (passport/permit expiry reminders, dormancy nudges, transfer-note linting), plus a freeze-response playbook in the student's language.

### P-17 · Anti-fraud transaction limits on new accounts — M
- Under China's anti-telecom-fraud "card-cutting" campaign (断卡行动), banks set **non-counter limits** (ATM, POS, mobile transfers, quick-pay) on some accounts based on occupation, age, and transaction traits; customers can apply at a branch to raise them. ⚠️ [Lanjinger 2023](https://www.lanjinger.com/d/203378)
- Restricted-card complaints rose in 2022; unlocking typically needs proof of residence, work, statements, or social insurance (students may lack most of these). ⚠️ [36Kr](https://www.36kr.com/p/1854053787340423)
- Exact limits for new foreign-student accounts ❓ (ask our friend).
- **Hook:** the planner respects daily caps (e.g., splits a rent payment) and prepares the documents for a limit increase.

### P-18 · Language: Chinese-only counters, forms, and apps — M/H
- Language was the top barrier (**89%**) in the Nanjing study. ✅ [JIS 2026](https://ojed.org/jis/article/view/9852)
- Alipay has better English support than WeChat. ⚠️
- Papers on foreigners' mobile-payment adoption in China note setup, habit, and trust barriers; none isolates language. ⚠️ [Chou (Alipay ethnography)](https://www.informahealthcare.com/doi/full/10.1080/10919392.2024.2340778)
- **Hook:** a three-language document explainer (Chinese document → Bengali for parent, English for student).

### P-19 · Students can't freely work, so income depends on family or stipend — M
- Off-campus work-study requires **university approval plus a residence-permit annotation** from immigration; working without it is illegal and penalised. ✅ [Peking Univ.](https://isd.pku.edu.cn/en/detail.php?id=302), [Beijing gov](https://english.beijing.gov.cn/mostrequested/residencepermit/international/202405/t20240528_3695884.html), [NWPU notice](https://studyat.nwpu.edu.cn/info/1018/1065.htm)
- Typical conditions: age 18+, permit with more than 6 months left, more than 1 year at the university, clean record. ⚠️ [China Daily guide](https://studychina.chinadaily.com.cn/s/202508/28/WS68affdea498e23165e06736c/work-study-management-measures-for-international-students-in-chinese-universities.html)
- Side effect: students are tempted by illegal gigs and **money-mule offers** (see P-25).
- **Hook:** a legal work-study eligibility check plus budgeting that assumes no job income.

### P-20 · Financial anxiety is widespread — M
- **87%** of surveyed international students in mainland China reported financial anxiety. ✅ [Sustainability 2022, 14(7):3743](https://doi.org/10.3390/su14073743)
- Many rely on parents or relatives; even scholarship holders sometimes find funding insufficient. ✅ [PMC 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7398760/)
- Financial strain is a recurring stress theme. ⚠️ [arXiv 2025](https://arxiv.org/pdf/2503.14139)
- **Hook:** clarity reduces anxiety: one screen showing "what's due, what's covered, what's at risk".

---

## E. Two-way money flows (from home, and back home)

### P-21 · Receiving money from home: conversion quota and documents — M
- Non-mainland individuals (foreigners) have an **annual FX settlement/purchase quota of USD 50,000**; within it, ID is enough; above it, supporting documents are needed (e.g., a school receipt for education). ✅ [HSBC China guide](https://www.hsbc.com.cn/content/dam/hsbc/cn/docs/foreign-exchange/personal-foreign-exchange-business-handling-guide-en.pdf), [SAFE 2010 notice](https://www.safe.gov.cn/en/2010/0429/703.html)
- Splitting transactions to dodge the quota is prohibited. ✅ (SAFE)
- Exact inbound rules and fees for foreign students' accounts ❓.
- **Hook:** a quota tracker plus a document vault (tuition receipts, scholarship letter).

### P-22 · Sending money home from China is hard and getting stricter — M
- Outward remittance happens at the bank with ID plus supporting documents; staff often question transfers to oneself. ✅ [Bank of China](https://www.boc.cn/english/individuals/pbk/t_r/202601/t20260105_25639112.html), ⚠️ [expat guides](https://randomwire.com/how-to-transfer-money-out-of-china/)
- **New rules from 1 Jan 2026** (issued 31 Oct 2025 by PBOC and the financial regulators): banks must verify remitter information for single outward transfers of **≥ RMB 5,000 or ≥ USD 1,000**; record retention goes from **5 → 10 years**; stricter KYC. ⚠️ [Sinoblawg](https://www.sinoblawg.com/china-is-tightening-foreign-exchange-control/)
- Informal routes (a Chinese friend, Alipay to a third party, PayPal) are flagged as illegal workarounds. ⚠️
- **Hook:** a guided "send savings home legally" flow with document prep and quota checks.

### P-23 · Informal channels forfeit Bangladesh's 2.5% incentive — M
- Bangladesh pays a **2.5% cash incentive** on remittances through formal channels, kept in the proposed FY2026-27 budget. ✅ [TBS](https://www.tbsnews.net/node/1460256), [Prothom Alo](https://en.prothomalo.com/business/local/mv650guvu4)
- Banks report incentive backlogs (they pay first and are reimbursed later). ⚠️ TBS
- Does a student's stipend savings sent home qualify? ❓ (check eligibility rules)
- **Hook:** show the formal route **plus 2.5%** against hundi: a measurable, compliant saving.

---

## F. Scams, fraud, and money mules

### P-24 · Impersonation scams aimed at international students — H
- Fake police or officials say "your ID was used in a crime" and demand a transfer to a "supervisory account". Other variants: fake landlord with a "new account", parcel-contains-contraband calls, fake lottery fees, crypto "investments". ✅ [Shanghai gov: anti-fraud tips for international students](https://english.shanghai.gov.cn/en-Editor'sPick-StudyinShanghai/20240828/f7b950613be9462e80a8bd94ca2c38de.html)
- China's anti-fraud reporting line **12110** is cited. ⚠️
- The same playbook hits Chinese students in the UK ("virtual kidnapping"). ✅ [Avon & Somerset Police](https://www.avonandsomerset.police.uk/crime-prevention-advice/fraud-prevention-advice-for-chinese-students/), [Lancashire report](https://lep.co.uk/news/national/police-warn-chinese-students-at-lancaster-university-about-scams-after-virtual-kidnaps-for-money-and-telephone-fraud-3960734)
- **Hook:** real-time scam check: the agent refuses to move money to unverified accounts and explains why, in the user's language.

### P-25 · Money mules / renting out bank cards — H
- Students are recruited to "earn easy money" by letting criminals use their accounts. It's a criminal offence, and in China it ties directly into police account freezes (P-16) and the card-cutting campaign (P-17). ✅ [Avon & Somerset Police](https://www.avonandsomerset.police.uk/crime-prevention-advice/fraud-prevention-advice-for-chinese-students/)
- **Hook:** education plus detection of inbound-from-stranger patterns; never let the agent itself act as a pass-through.

### P-26 · Rental and deposit fraud — M
- Fake listings, already-let flats, and "landlord changed account" texts. ✅ (Shanghai gov page above)
- **Hook:** payee-change alert ("this landlord's account changed; confirm by phone first").

---

## G. Shocks

### P-27 · Home-currency crisis makes fees unpayable mid-degree — H
- **Nigeria 2024:** the naira lost about **51.5%** vs USD in months (30% in one day); central-bank FX limits blocked transfers; Teesside University students were **removed from courses and told to leave the UK** after defaulting, including one who had paid 90%. A KCL student was blocked from paying final-year fees. ✅ [The PIE News](https://thepienews.com/nigerian-students-tuition-fees-currency-drop), [Roar News](https://roarnews.co.uk/2024/nigerian-student-forced-to-abandon-kings-degree-due-to-central-bank-forex-restrictions-the-last-thing-i-need-is-kings-sending-me-emails-every-day-about-something-i-cant-fix/), [Gazette NGR](https://gazettengr.com/nigerian-students-in-uk-expelled-forced-to-leave-country-amid-currency-crisis/)
- **Pakistan 2022:** the central bank restricted dollar outflows; third-party instalment vendors were disallowed. ⚠️ op-ed, [Friday Times](https://thefridaytimes.com/10-Dec-2022/as-the-us-rupee-relationship-deteriorates-pakistani-students-suffer-the-most)
- **Bangladesh 2022–24:** the dollar crisis (P-01); the taka went from ~86 to ~110 per USD, with a crawling-peg jump to 117 in May 2024; a market-based regime started May 2025 (~Tk 122–124 since). ✅ [Bloomberg](https://www.bloomberg.com/news/articles/2025-05-15/bangladesh-removes-restrictions-in-currency-movement-in-imf-push), [Dhaka Tribune](https://www.dhakatribune.com/amp/business/416866/taka-outperforms-south-asian-currencies)
- **Hook:** home-currency stress monitor plus whole-degree FX risk plan (convert or prepay earlier when stress rises), shown as ranges, not promises.

### P-28 · Disruptions (COVID-type) and special circulars — M
- During COVID, Bangladeshi students in China studied online from home and needed to pay outstanding tuition to get visas; Bangladesh Bank issued a special circular (Nov 2022) to allow it. ✅ [TBS](https://www.tbsnews.net/node/528626)
- Parents were reluctant to pay full fees for online classes. ✅ [Emerald QEA 2024](https://www.emerald.com/insight/content/doi/10.1108/qea-07-2024-0057/full/html)
- **Hook:** the rules engine supports time-limited exceptions; the agent tracks policy news.

### P-29 · Visa refusal and refunds — H
- **Australia (clear national law, ESOS):** refund within **4 weeks** of a written claim, minus **the lesser of 5% of tuition or AUD 500**; no refund if the refusal was the student's own fault. ✅ (provider policies quoting ESOS: [Ozford](https://ozford.edu.au/documents/134/Refund_Management_Policy_and_Procedure_2025.pdf), [UQ College](https://uqcollege.uq.edu.au/sites/default/files/2026-07/student-refunds-procedure.pdf))
- **China:** refund rules are university-specific ❓.
- **Hook:** a refund-claim agent (letter draft, deadline tracking, convert-back-now vs hold scenario). Our hero story: 14 → 15 lakh BDT.

---

## H. Leaving China / graduation

### P-30 · Money stuck after leaving — M
- Dormant accounts lose online and ATM access; reactivation needs a **branch visit**, which is hard from abroad. ⚠️ [TropicalHainan](https://www.tropicalhainan.com/why-foreigners-lose-access-to-their-chinese-bank-accounts/)
- More than USD 5,000 in foreign cash out needs a permit ⚠️; outward transfers need documents under the 2026 rules (P-22).
- **Hook:** a pre-departure exit checklist: send savings home legally, close or keep the account, get refunds of deposits, final insurance claims.

---

## I. Cross-cutting problems

### P-31 · No credit history, and home credit isn't portable — M
- A credit card in China needs a residence permit valid for more than 1 month **and** positive credit history; most new students have neither. ⚠️ [WentChina](https://wentchina.com/how-to-open-a-bank-account-in-china-as-a-foreign-student-2026/)
- International students face higher financial strain partly due to **limited access to formal credit**. ⚠️ [Theseus thesis](https://www.theseus.fi/handle/10024/905980)
- **Hook (Topic C explicitly names "credit building"):** a verifiable on-time payment record (tuition, rent, transfers from agent logs) the student can share. Honest limit: it's not an official PBOC credit file.

### P-32 · Low financial literacy, family far away — M
- Students who'd normally ask family for advice can't, because their family doesn't know the host country's system; currency fluctuations add risk. ⚠️ [Academic Matters](https://academicmatters.ca/the-importance-of-supporting-international-students-with-financial-literacy-education/)
- Limited access to financial information lowers confidence in digital financial services; FinTech can ease the transition. ⚠️ [Bangor Univ. study](https://research.bangor.ac.uk/en/publications/fintech-and-financial-literacy-an-exploratory-study-of-internatio/)
- **Hook:** explain-every-step design; jargon glossary in Bengali.

### P-33 · The payer is often a parent with a different language — H (our insight)
- A parent in Dhaka (Bengali, branch banking) pays; the student in China (English, mobile) receives; the university and bank speak Chinese. **Needs validation in the friend interview.**
- **Hook:** two-user, three-language workflow with parent approval for big payments.

### P-34 · Information is scattered, inconsistent, and changing — H (meta-problem)
- Bangladesh FE circulars, China's SAFE/PBOC rules (new KYC rules in 2026), university-by-university payment rules, app limits set by risk control: sources disagree (several conflicts noted above).
- **Hook:** a rules knowledge base with citations and a "last verified" date, plus an honest "I'm not sure, verify with X" behaviour.

---

## J. Field evidence: Interview #1 (2026-10-12)

**Profile:** Bangladeshi student, self-funded (no scholarship), arrived in China in Sept 2026. Family sends money through a bank. Tuition paid via BRAC Bank in CNY.
Original problem notes were in Bengali (Banglish); our translations are in quotes.

### N-01 · Every ATM withdrawal with a Bangladeshi card costs ~345 BDT — H
- 🗣️ "Using Bangladeshi bank cards to withdraw CNY here, each time about **345 taka** is cut."
- Our inference: 345 BDT ≈ USD 2.8 at ~122 BDT/USD, consistent with a fixed fee of about USD 2.5 + 15% VAT. **Verify against the bank's schedule of charges.**
- Possible extra layers: Chinese ATM fee for foreign cards **20–30 CNY** ⚠️ [you.co guide](https://www.you.co/sg/blog/china-atm-withdrawal-guide/); BRAC's 2019 card schedule applied a **3% "foreign currency factor"** to non-USD transactions (CNY is non-USD) ⚠️ [BRAC SOC 2019](https://www.bracbank.com/schedule_of_charges/Scehdule%20of%20Charges_Card_2019.pdf), which may be outdated.
- **Hook:** a withdrawal planner (how much per withdrawal, how often) vs remitting to the student's own Chinese account (one transfer instead of many withdrawals).

### N-02 · Can't withdraw much at once, so fees multiply — H
- 🗣️ "Can't withdraw a lot of CNY at once."
- BRAC debit cards abroad were reported at **USD 300/day and USD 1,500/month** ⚠️ ([Financial Express](https://thefinancialexpress.com.bd/home/brac-bank-lifts-bar-on-foreign-atm-cash-withdrawals-with-debit-cards), undated). BRAC once **suspended foreign ATM withdrawals entirely** before restoring them (same report): a single point of failure.
- Chinese big-bank ATMs: roughly **2,500–5,000 CNY per withdrawal**, ~10,000 CNY/day ⚠️ (travel guides, forum reports).
- **Worked example (illustrative; every assumption must be verified):** 6,000 CNY/month of living cost by ATM with a USD 300/day cap (≈ 2,100 CNY at an assumed ~7.1 CNY/USD) → 3 withdrawals × 345 BDT = **1,035 BDT** in fixed fees. Add a possible 3% factor on ~1.06 lakh BDT (≈ 3,200 BDT) and the total is **about 4% of the money**, before the bank's FX markup.
- **Hook:** the cost engine computes this per user; caps feed the planner.

### N-03 · A blocked card means no money for days — H
- 🗣️ "One person's card got blocked the other day; no transactions for **two days**."
- Cause unknown ❓ (Bangladeshi bank fraud rule? endorsement lapse? Chinese ATM?).
- **Hook:** a contingency plan: a second payment method (Chinese account, e-CNY, Alipay foreign card), an emergency buffer, and a step-by-step unblock script with the bank's hotline, in Bengali.

### N-04 · Every Bangladeshi bank quotes a different rate — H (validates our true-cost engine)
- 🗣️ "Each bank gives a different rate; some higher, some lower."
- **Hook:** daily comparison of Bangladeshi banks' CNY/USD selling rates plus fees: "Bank X costs ৳Y more than Bank Z for your 35,200 CNY tuition." Data: banks' published daily rate sheets (scrape).

### N-05 · Short "endorsement" period for students (friend's biggest problem) — H
- 🗣️ "The bigger problem is endorsement tenure. I came in September, but they gave me endorsement only **until December**. Then I have to go to the bank again to endorse. How can it work with such a short period? They do this only for students; others get longer endorsement."
- Corroboration ⚠️: Bangladesh Bank allowed **multi-year** dollar endorsement for travellers (up to USD 12,000/yr) **but excluded people going abroad for study**, employment, and immigration ([New Age](https://www.newagebd.net/article/149926/bb-allows-multiple-years-dollar-endorsement-at-once-based-on-passport-validity), about 5 years old). Student Files must be **renewed yearly** with an enrolment certificate, transcript, and invoice ⚠️ (bank pages, P-07).
- Unknown ❓: the rule behind the short student endorsement, who must visit the bank (student abroad or parent in Bangladesh), and whether it can be done online.
- **Hook (very agent-shaped):** an endorsement and Student File tracker. The agent reminds ahead of expiry, drafts the request to the university for an enrolment certificate (Chinese/English), assembles the renewal pack, and tells the parent in Bengali what to bring to the branch. It's a multi-step task with deadlines, documents, and two users.

### N-06 · Student account transaction limits: 5 lakh BDT and 30 transactions per month — H
- 🗣️ "Student account transaction limit is also an issue." Follow-up answer: about **5 lakh BDT per month** and **30 transactions per month**.
- The limit is in BDT, so it's most likely the **Bangladeshi** student account/card (our inference; confirm).
- For scale: 5 lakh BDT ≈ 28,000 CNY ≈ USD 4,100 (at ~17.7 BDT/CNY, ~122 BDT/USD).
- Tuition (35,200 CNY ≈ 6.2 lakh BDT) is *above* 5 lakh but still went through, so the cap probably applies to **card/account spending, not Student File remittances** (inference; confirm).
- It is also above the reported USD 2,000/month living-cost cap (P-02), so check how the two rules relate.
- **Why 30 transactions hurts:** if every ATM withdrawal *and* every card purchase counts, a student who pays small amounts by card can hit the cap mid-month and be cut off (looks like N-03).
- **The constraints pull in opposite directions:** the per-withdrawal fee (~345 BDT) and the 30-transaction cap push toward fewer, larger withdrawals. Per-withdrawal ATM caps (~2,500–5,000 CNY) and daily caps (~USD 300 reported) push toward more, smaller ones.
- **Hook (core algorithm for the tech doc):** a constrained cost-minimisation planner. Inputs are monthly needs, BDT cap, transaction-count cap, per-withdrawal and daily caps, fixed and % fees, and FX rate. Output is the schedule of withdrawals and transfers. It also warns at 80% of either cap and never plans a transaction that would breach a cap. Remitting living costs to the student's own Chinese account (allowed under the Student File) may bypass the card limits entirely.

### N-07 · Rate volatility worry — M
- 🗣️ "The CNY rate goes up and down."
- This validates the need for the FX planner (M3), but it must stay honest: show ranges and staged plans, not predictions. Both BDT and CNY are managed currencies, and the BDT/CNY rate moves mainly through USD.

### N-08 · Hundi was offered; the family chose the bank — validates P-01/P-23
- 🗣️ "Yes, offered hundi, but chose the banking channel."
- **Pitch angle:** Sathi makes the legal route also the *easy and cheap* route, so families don't need to be heroes to stay formal.

### N-09 · Arrival money via cash and seniors — M
- 🗣️ The student bought **CNY cash at a bank booth at Dhaka airport**, then got it into **Alipay with seniors' help** (likely an informal peer exchange: cash for an Alipay balance; method to confirm ❓). A foreign card was added to Alipay but not used yet.
- Risks: airport rates, cash handling (customs thresholds, P-04), and dependence on informal peer transfers that can be linked to frozen accounts (P-16).
- **Hook:** an arrival plan comparing airport cash vs foreign card on Alipay (3% above RMB 200) vs e-CNY vs a same-day Chinese account (now known to be possible).

### N-10 · "Agency fees" — ❓
- 🗣️ The answer to one question was "Agency fees". Probably education-agent fees as a cost or scam risk. **Clarify.**

---

## Priority shortlist (re-ranked after Interview #1)

Ranked by severity × how often it happens × how well an agent can fix it (our judgment, now backed by field evidence):

| Rank | Problem | Why it matters for scoring |
|---|---|---|
| 1 | **N-04 + N-01 + N-02 + P-05: "What's the cheapest way to get my money to China?"** (bank-rate comparison, withdrawal vs remittance-to-own-account, caps) | **Task completion + measurable value:** real, validated, numbers we can compute |
| 2 | **N-05 endorsement / Student File renewal tracker** | **Task completion + interaction:** the friend's #1 pain; multi-step, deadlines, documents, parent + student |
| 3 | P-06 arrival-deadline tuition payment | **Task completion** |
| 4 | P-09/P-24/P-25/N-08 scams, mules, hundi | **Security & compliance** |
| 5 | N-03 + P-16/P-17/N-06 card blocks, freezes, limits | **Compliance + resilience:** contingency plan |
| 6 | P-33/P-18 + residence checklist: parent ↔ student ↔ Chinese docs | **Interaction:** multilingual done for real |
| 7 | P-21/P-22/P-23 send home legally + 2.5% incentive | **Measurable value** |
| 8 | N-07/P-27 FX ranges and home-currency stress | **FX planner:** our original idea, done honestly |
| 9 | P-29 refund (Australia corridor), P-31 credit record | Pitch story; Topic C names credit building |

Downgraded: P-10 (bank account opened same day with passport only, at least at the friend's university).

---

## Open questions → follow-up with the friend
- **N-04/P-05:** exact BDT debited for the 35,200 CNY tuition, and the date (to compute the markup vs mid-market). Which other banks' rates did they compare?
- **P-07:** was the 8,000 BDT a one-time file-opening fee? Any other charges (SWIFT, VAT, receiving)?
- **N-01/N-02:** which card (BRAC multicurrency/Visa debit?), which Chinese ATM bank, the maximum per withdrawal, and did the Chinese ATM also charge?
- **N-03:** whose card was blocked, why, and how it was fixed.
- **N-05:** what amount and period were endorsed; who must visit the bank to renew (student or parent); which documents; is online renewal possible?
- **N-06 (partly answered: 5 lakh BDT and 30 transactions per month):** confirm it's the Bangladeshi card/account; do card purchases (Alipay, POS) count toward the 30, or only ATM withdrawals? Do Student File remittances count?
- **N-09:** how exactly did seniors convert cash into Alipay balance? At what rate?
- **N-10:** what did "agency fees" mean?
- **P-33 (unanswered):** who handles the money, parent or student, and in what language?
- **P-15/P-17:** n/a (self-funded) / see N-06.
