# Sathi: cross-border student finance agent

**FinTechathon 2026 · International Track · Topic C (Cross-border & Student Finance Assistant)**

Sathi (সাথী, "companion") **keeps an international student funded all year through the legal bank channel,
and acts on its own only inside a limit the family has signed**, in Bengali, English and Chinese.
Hero corridor: **Bangladesh → China**.

> ⚠️ Sandbox only. No real money moves. The **mid-market exchange rate is real** (live, with 953 days of saved
> history from [fawazahmed0/exchange-api](https://github.com/fawazahmed0/exchange-api), CC0). **Bank prices are real or
> published:**
> - Eastern Bank's own daily CNY rate sheets: 139 sheets, March–October 2026, refreshed by `scripts/fetch_bank_rates.py`.
> - Fees from banks' published 2026 schedules of charges.
> - One real BRAC payment.
>
> Anything not published is labelled as an assumption in the app.

## The problem in one paragraph

Money leaving Bangladesh for study can only go through a bank **Student File**: there is no Wise for outbound
BDT. That legal channel breaks on predictable days:
- the student's card endorsement ends (Sep → Dec), and **renewing it needs the student in person** in Bangladesh;
- transfers take a week, and Bangladeshi branches close Fri–Sat and for about a week at each Eid;
- Chinese banks close for Spring Festival.

With today's habits our demo student is **without money for 20 days a year**. And it isn't the exchange rate that
costs families most: a real BRAC tuition payment was only 0.22% above the market rate, while its ৳8,000 charge was
**5.5× that markup**. When the legal channel breaks, families are pushed to hundi. **Sathi makes the legal way easier than hundi.**

## One loop: Sense → Plan → Act → Prove

| | What happens | App |
|---|---|---|
| **Sense** | Money in China, transfers on the way, card status; shared bank SMS/email (OTP removed, numbers masked); photographed documents; the real exchange rate | **Today**, **Sathi** |
| **Plan** | **"Never stuck" year plan**: a day-by-day simulation across both countries' bank calendars, the endorsement end and card limits; today's habits vs Sathi (stuck days, fees vs rate markup); tuition send-by and living-money optimisers | **Plan → Year / Tuition / Living** |
| **Act** | The parent writes a **family mandate in their own words** ("প্রতি মাসে ১ লাখ ২০ হাজার টাকা পর্যন্ত…", up to 1.2 lakh taka a month) → a strict proposal → read aloud → signed with fingerprint (both people for large caps). The **autopilot** then sends living money to the student's own account **before** it runs out, counting Eid, Spring Festival and weekends, and **asks** whenever a limit would be exceeded. Card freeze, renewal plan for a student abroad, scam blocking | **Family** |
| **Prove** | A receipt for every payment: approved by people (EXECUTE) or by the autopilot under the signed mandate (MANDATE, with the proposal hash). Hash-chained log, payment passport | **Proof** |

**Results** (saved real rates):
- **Year plan:** stuck days **20 → 0**; fees + markup **4.39% → 3.88%** (৳5,126 saved for the same money). **89%** of what families lose today is fees, not the exchange rate.
- **Published data:** Eastern Bank's CNY transfer rate averaged **+0.96%** above the market (138 days). Its fees on a ৳1 lakh transfer are **৳3,565**, more than the rate markup.
- **Stress test:** the same year re-run 200 times with messy spending, late transfers and moved holidays. Typical year: **30 → 0** stuck days; **64%** of messy years with none (today: 0%). What if the taka weakens 10%, spending rises 30%, every transfer is 3 days late, or all at once: still **0** stuck days.
- **Live sandbox run:** 12 Oct 2026 → 21 Feb 2027, through the card stop and Spring Festival: **0 stuck days**.
- See [docs/evidence/scenario_summary.md](docs/evidence/scenario_summary.md).

**Security** (details in the [security self-assessment](docs/SECURITY_SELF_ASSESSMENT.md)):
- Permission levels L0–L3; the AI can never approve, sign, unfreeze or widen a limit.
- Signatures and approvals are bound to the exact proposal or draft. What people read and hear is generated from those exact fields, never by the AI.
- Numbers from the AI must appear in the user's text.
- Two-person rule from ৳1 lakh; hash-chained audit log; 203 tests, including the red-team cases.

## Run it

**Backend** (Python 3.12):
```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # macOS/Linux: .venv/bin/python
.venv/Scripts/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
API docs: http://localhost:8000/docs

**AI (optional):** put `DEEPSEEK_API_KEY=...` in `backend/.env`. This file is git-ignored; never put the key in the mobile app. Without a key, Sathi uses rule-based answers. Optional email: `SATHI_IMAP_HOST`, `SATHI_IMAP_USER`, `SATHI_IMAP_PASSWORD` (an app password).

**Mobile app** (Node 22, Expo SDK 57):
```bash
cd mobile
npm install
npx expo start          # scan the QR code with Expo Go on your phone
npx expo start --web    # or open in a browser
```
On a phone, the app looks for the backend on the same computer at port 8000 (the phone and computer must be on the same Wi-Fi, and the firewall must allow port 8000). Change the address in **Settings** if needed, or set `EXPO_PUBLIC_API_URL`.

## Test it
```bash
cd backend && .venv/Scripts/python -m pytest -q        # 203 tests: bank prices, year plan, mandates + autopilot, security, engines, agent, inbox, FX, cards, renewals, passport, documents
cd mobile && npx tsc --noEmit && npx expo lint
```

## Submission documents
- [Technical documentation](docs/TECHNICAL_DOCUMENTATION.md): architecture, core algorithms, security design, data, API, deployment, tests
- [Security self-assessment](docs/SECURITY_SELF_ASSESSMENT.md): permission-tier implementation, threat model, red-team results, known-risk list
- [Execution evidence](docs/evidence/scenario_summary.md): hash-chained sandbox operation log from a full end-to-end run

## Repository map
```
docs/00_project_brief.md     competition rules, decisions, concept, plan
docs/01_problem_research.md  34 problems + field interview, with sources and confidence labels
docs/02_build_plan.md        organiser expectations → scope → architecture → schedule
backend/app/corridors/       rule pack (every number has a source + confidence)
backend/app/engines/         year plan (bank calendars, look-ahead rule), cost + cost truth, living optimiser, tuition planner, FX ranges
backend/app/agent/           autopilot, mandate compiler, chat agent (DeepSeek) + offline fallback
backend/app/data/            bank holidays (BD + CN), bank quotes + real payment, FX history, demo messages
backend/app/security/        permissions, compliance checks, scam/injection detection
backend/app/sandbox/         simulated bank with clock, delays and fees
backend/app/audit/           hash-chained operation log (execution evidence)
mobile/src/app/              Expo Router screens (Today, Plan, Family, Sathi, Proof, payment approval, renewal, passport, settings)
```
