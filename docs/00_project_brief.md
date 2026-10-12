# Project Brief: FinTechathon 2026, International Track, Topic C

**Working name:** Sathi (সাথী, "companion" in Bengali / Hindi / Nepali). Rename freely.
**Last updated:** 2026-10-12
**Companion file:** [`01_problem_research.md`](01_problem_research.md), the evidence base of problems (P-01 … P-34).

---

## 1. Competition facts (from the official rules)

| Item | Detail |
|---|---|
| Competition | 2026 Shenzhen International FinTech Competition, WeBank FinTech University Challenge, **International Track (AI)** |
| Theme | **"AI as a Financial Participant"**: build an AI agent that *completes real tasks* in a financial scenario |
| Our topic | **C · Cross-border & Student Finance Assistant**: "remittances, tuition payments, **credit building**, and multi-currency management" (+ multilingual) |
| Topic labels | A–E are new or expanded topics this year. F (Agent Wallet, on-chain) is the original topic. Pick one; scoring is identical |
| **Scoring** | **Task completion 40% · Security & compliance 30% · Innovation & interaction 30%** · on-chain challenge bonus 0–5 |
| Team | 2–5 full-time students at **non-China** universities; **≥ 60% non-Chinese nationals**; one team per person |
| Language | English for submission, presentation, and review |
| **Deadline** | **20 Oct 2026, 23:59 Beijing (UTC+8) = 21:59 Dhaka.** Registration and submission share this deadline. Updates allowed until then |
| Review | Late Oct online review (WeBank experts + scholars) → finalists by 31 Oct |
| Finals | 20 Nov check-in + WeBank HQ visit; **21–23 Nov Grand Final, Shenzhen**; at least 1 member in person; travel and hotel covered for invited members |
| Prizes (track) | RMB 100k / 80k / 50k + Best Innovation RMB 20k + Excellence awards; WeBank fast-track interviews |
| Contact | info@ican-x.com · site: fintechathon.g-ican.com |

### Registration (do this first; confirmation takes up to 48 h)
- Email the completed **English** form to **fintechathon@ican-x.com**
- Subject: `International Track Registration – Team Name – Team Leader Name`
- Attach for each member: proof of enrollment (scan) and passport bio-page image. The form needs passport/ID number **and** student ID number
- Optional: advisor; **proposal summary of 100–200 words** (draft in §7)
- Members must be 18+ (minors need a guardian consent form)

### Submission checklist (six deliverables)
1. **Technical documentation:** system architecture, core algorithm description, security design
2. **Presentation deck:** final talk ≤ 10 min
3. **Demo video:** optional, ≤ 5 min (do it anyway)
4. **Source code:** GitHub link, README, deployment instructions, **test cases**
5. **Security self-assessment report:** **permission-tier implementation** and a **known-risk list**
6. **Execution evidence:** for non-on-chain topics, **sandbox/simulated-account operation logs** plus the demo video

**How to submit:** not stated in the rules, the registration form, or the website (checked 2026-10-12). The website's participation instructions only say to email the registration form to fintechathon@ican-x.com. "The latest version received prevails" suggests email, but **ask the organisers in the registration email** (draft questions: channel, links vs attachments, size limits, formats, updates, on-chain bonus eligibility). Plan: share links (GitHub repo + cloud folder of PDFs + unlisted video), send a first full version around 18 Oct, then update.

**IP and integrity:** all third-party data, code, and libraries must be properly licensed. We keep IP; the hosts may use entries for non-commercial promotion.

---

## 2. Decisions so far

| Decision | Choice | Why |
|---|---|---|
| Topic | **C** | Real pain we've lived; fits the "AI participant" theme |
| Hero corridor | **Bangladesh → China** | Judges' home context (WeBank, Shenzhen); richer problems (double conversion, first-month limbo, Chinese-only docs, 2026 KYC rules, two-way flows); stronger multilingual case; a friend there as a live user |
| Second corridor | **Bangladesh → Australia (light)** | Hosts our origin story (visa refusal refund) and the clean ESOS refund law; proves "a corridor is just configuration" |
| On-chain bonus | **Skip** | China (2021) treats crypto transactions as illegal financial activity; Bangladesh Bank warns against crypto. Compliance is 30% of the score, which outweighs ≤ 5 bonus points |
| FX prediction | **Ranges, not point forecasts** | See §3; judges include econometricians |
| Safety | **Deterministic rules engine outside the LLM; the LLM never computes money amounts** | 30% of the score is security & compliance |

---

## 3. Key findings from the earlier analysis

### 3.1 Our origin story, explained honestly
- We paid about **14 lakh BDT** tuition (in AUD) to an Australian university. The visa was refused about 3 months later, and the refund arrived as about **15 lakh BDT**.
- That is not luck from a prediction. The money sat in AUD while the **taka weakened**. After the bank's buy/sell spreads and the ESOS deduction (≤ AUD 500), the taka must have fallen roughly **8–13% vs AUD** in those months. Taka episodes like that happened in the 2022–23 dollar crisis and the May 2024 crawling-peg jump (110 → 117 per USD).
- If the taka had strengthened, we'd have **lost** money. Since the May 2025 market-based regime, the taka has been stable (≈ 0.6% move vs USD, Mar 2025 → Mar 2026; ~Tk 122–124), so the same story wouldn't repeat today.
- **Lesson:** the value is in managing risk and costs, not in betting on rates.

### 3.2 Why we don't sell an "FX prediction / hold-vs-send" app
- Meese & Rogoff (1983): a random walk ("tomorrow = today") beats exchange-rate models out of sample. That result has largely held for 40 years ([Fed working paper](https://www.federalreserve.gov/econres/feds/files/2025089r1pap.pdf)).
- ML sometimes wins at 1-month horizons, or on predicting direction, but often fails. In a 2026 CAD/USD study, RF/XGBoost/GBM did **not** beat the random walk ([arXiv](https://arxiv.org/pdf/2606.15058)).
- Deadlines and rules (tuition demand notes, monthly caps) shrink the real "hold" option.
- **Reframe:** *cut certain costs, control FX risk around real deadlines, act safely on the user's behalf.* Forecasts become calibrated ranges that feed a plan.

### 3.3 Where money really leaks (most of the benefit is *certain* savings)

| Leak | Size | Control |
|---|---|---|
| Hidden bank FX markup | ~2–6% per conversion ⚠️; × 2 when routing BDT → USD → CNY | Certain savings |
| Fixed + intermediary SWIFT fees, wrong OUR/SHA/BEN choice | Fixed per transfer | Certain savings |
| Scams ("discount agent", fake police) | Whole tuition | Detection and blocking |
| Rate moves before a deadline | ± several % | Reduce variance, can't predict |
| Visa refusal / refunds | ≤ AUD 500 + spreads + visa fee | Partly |
| Informal channels → missing 2.5% BD incentive, legal risk | 2.5%+ | Certain (route to formal) |
| Money left behind at exit | Varies | Checklist |

### 3.4 Australia vs China (why China won)
China wins on judge relevance, number of China-specific problems, the multilingual requirement, and having a live user (our friend). Australia wins on the FX-volatility story (AUD floats freely) and on clear refund law. Hence: **China deep, Australia light.**
**Watch out:** judges know Chinese rules well, so every China fact must be verified (see the ❓ items in the research file).

---

## 4. Product concept

> **Sathi is an AI agent that plans, checks and (with your approval) carries out every cross-border payment in a student's journey, at the lowest true cost, with FX risk under control, in the family's own language.**

### 4.1 Agent loop → rubric

```
Understand ──► Plan ──► Verify ──► Confirm ──► Execute ──► Monitor
 (intent)     (task      (rules     (user       (sandbox   (measurable
              planning)   engine)    control)    + logs)     value)
```

| Rubric | Weight | What earns it |
|---|---|---|
| Task completion | 40% | 3–4 end-to-end tasks that actually finish in the sandbox, with logs |
| Security & compliance | 30% | Permission levels, rules engine, scam blocking, audit log, known-risk list |
| Innovation & interaction | 30% | Three-language parent ↔ student ↔ Chinese-document flow; honest uncertainty ranges; corridor-as-config |

### 4.2 Core modules
- **M1 · Intent and documents.** Multilingual chat ("ছেলের সেমিস্টার ফি …", i.e. "my son's semester fee …") → structured obligation (amount, currency, deadline, payee, purpose). Read fee notices and offer letters into a **payment calendar**.
- **M2 · True-cost engine.** All-in cost = Σ per-leg (spread vs mid-market + fixed fee + intermediary fee), plus speed and eligibility. Compares bank TT via USD, CNY route, foreign card + Alipay (3% above RMB 200), e-CNY, etc. Output: "Route A costs ৳X more than route B."
- **M3 · FX risk planner.** Forecast **ranges** (quantile models + conformal calibration) benchmarked against the random walk. Staged-conversion plan with a deadline buffer and an optional trigger. **Backtest** lump-sum-now vs lump-sum-at-deadline vs staged → report mean and 95th-percentile cost. Includes a home-currency stress monitor (P-27).
- **M4 · Safety and control.** Deterministic rules engine: payee allow-list from official university pages; BD limits (demand note, USD 2,000/month living cap); China (USD 50k/yr quota, 2026 remitter-verification threshold RMB 5,000 / USD 1,000); scam patterns; daily account limits. The LLM drafts, code computes, the user approves. Every action logged.
- **M5 · Exceptions.** Visa-refusal refund (AU/ESOS), account freeze playbook (P-16), insurance claim helper (P-13).
- **M6 · Multilingual.** Bengali + English + Chinese first; lakh/crore formatting; jargon glossary; voice notes for parents.

### 4.3 China-specific features

**Validated by Interview #1 (2026-10-12), now the top priorities:**
- **g. Money-route optimizer:** compare Bangladeshi banks' daily CNY/USD rates plus fees (N-04), and "ATM withdrawals with a Bangladeshi card" (~345 BDT each, daily caps; N-01/N-02) vs "remit to my own Chinese account" vs foreign card on Alipay. Hard constraints: the student account's **5 lakh BDT/month and 30 transactions/month** (N-06), plus per-withdrawal and daily caps. Output: cheapest plan that never breaks a cap + ৳ saved. This constrained optimiser is a strong "core algorithm" for the technical doc.
- **h. Endorsement & Student File tracker:** short student endorsement periods (Sep → Dec) and yearly file renewal (N-05). Reminders before expiry; drafts the enrolment-certificate request to the university; builds the renewal pack; tells the parent in Bengali what to bring to the branch.
- **i. Card-block contingency:** a backup payment method, an emergency buffer, and an unblock script (N-03).

**Earlier features (still valid):**
- **a. First-30-days plan:** police registration within 24 h, residence permit within 30 days (document checklist read from the university's sheet), a bank account (same day with passport at the friend's university), bridge payment methods (airport cash vs foreign card on Alipay vs e-CNY), arrival cash calculator under customs thresholds (RMB 20,000 / USD 5,000).
- **b. Double-conversion-aware routing:** BDT → USD → CNY vs paying in USD vs a direct CNY route (if available).
- **c. Arrival-date planning:** fees count only when they reach the university's finance office, so send-by date = deadline − transfer time − buffer.
- **d. Three-language document reader:** Chinese bank forms, fee notices, contracts → Bengali (parent) and English (student).
- **e. Stipend budget and send-home flow:** CSC RMB 2,500 / 3,000 / 3,500 per month; legal outward transfer + Bangladesh's 2.5% incentive vs hundi.
- **f. Credit-building record:** a verifiable on-time payment record from the agent's logs (honestly: not an official PBOC credit file).

### 4.4 Permission levels (goes into the security self-assessment)

| Level | Agent may | Control |
|---|---|---|
| **L0 Read** | Show rates, explain, read documents | None |
| **L1 Draft** | Plans and transfer drafts; no money moves | None |
| **L2 Execute** | Each transfer, after showing amount, rate, fee, payee | User confirms each one; above a threshold, a second approver (parent) |
| **L3 Mandate** | Repeat payments within user-set caps (e.g., ≤ RMB 3,000/month to an approved payee) | Revocable any time |
| **Always blocked** | Unapproved payee; breaking BD/CN FX rules; hundi or crypto routes; instructions embedded in uploaded documents | No level overrides |

**Known-risk list (draft):**
- Prompt injection via uploaded PDFs or messages
- Stale rules (all rules dated and versioned)
- FX model error (shown as ranges, benchmarked against the random walk)
- LLM inventing numbers (amounts are computed in code only)
- Fake university or landlord accounts
- Sensitive document storage (passport, receipts): privacy and retention
- Over-reliance: not financial advice; real execution would go through licensed partners

---

## 5. Data pipeline

| Layer | Sources | Notes |
|---|---|---|
| Home official rates | Bangladesh Bank daily rates; banks' TT selling rate sheets (Sonali, BRAC, City, …) | Scrape daily: the rates families actually pay |
| CNY side | PBOC central parity / CFETS reference rates | CNY is managed (daily fixing, trading band) |
| Market mid-rates | Open exchange-rate APIs, yfinance history | **Check BDT coverage.** The ECB/Frankfurter feed has no BDT |
| Provider prices | Wise Comparison API (Wise's hourly scraped estimates, bank-transfer only, may need a token); manual quotes | Wise is an interested party; label it so |
| Macro/events | BB reserves, remittance inflows, policy rates; Fed/PBOC dates; oil | Features for the range model and stress monitor |
| Rules KB | BD FE circulars; SAFE/PBOC rules incl. 2026 KYC; ESOS; university fee pages | Retrieval with citations and a "last verified" date |
| Stack | DuckDB/Postgres → scheduled jobs → models → FastAPI → tool-calling LLM → web chat (+ IM if time) | Keep it simple and reliable |

Licensing: check every data source's terms (rules §8).

---

## 6. Measurable value (metrics for judges)
- **Cost:** ৳ and % saved vs bank TT across N real quotes (aim to use our friend's real receipts, with consent).
- **Risk:** backtested 95th-percentile cost, staged plan vs lump sum.
- **Forecast honesty:** do the 80% ranges contain the actual rate about 80% of the time? Pinball loss vs the random walk, reported even if it's a tie.
- **Safety:** % of planted scam/injection cases blocked; **0** unapproved executions in red-team tests.
- **Language:** task success rate per language (bn / en / zh).
- **Effort:** steps and time to complete a tuition payment, agent vs manual.

---

## 7. Proposal summary (registration form, ~170 words; edit freely)

> Sathi is a multilingual AI agent that helps international students and their families move money across borders safely and at the lowest true cost. Our hero corridor is Bangladesh → China: a Bengali-speaking parent pays tuition from Dhaka, the student lives on a CNY stipend, and university and bank documents are in Chinese. Sathi understands requests in Bengali, English and Chinese, turns fee notices into a payment calendar, and compares routes by all-in cost: FX markups, double conversion via USD, fixed and intermediary fees, and arrival time against deadlines. It plans conversions using calibrated exchange-rate ranges benchmarked against a random walk, not point predictions. Every action passes a deterministic compliance engine (payee allow-list, Bangladesh outward-remittance limits, China FX quotas, scam patterns) and a four-level permission model, from read-only to capped, revocable mandates. Transfers run in a sandbox with full audit logs. Sathi also handles exceptions such as visa-refusal refunds, and builds a verifiable on-time payment record for credit building. Each corridor is a configuration, so the same agent extends to Australia and beyond.

---

## 8. Plan to 20 Oct (mapped to deliverables)

| Date | Work | Deliverable |
|---|---|---|
| **12 Oct** | Send registration; interview friend; freeze scope; repo skeleton | Registration |
| 13–14 Oct | Data ingestion; true-cost engine; rules KB; payee/scam check | Code (#4) |
| 15–16 Oct | FX range model + backtest; staged planner | Core algorithm (#1) |
| 16–17 Oct | Agent orchestration; approval UI; sandbox bank + **operation logs** | Execution evidence (#6) |
| 18 Oct | Bengali/English/Chinese; scenarios (tuition, first-30-days, send-home, AU refund); test cases; red-team | Tests (#4), risks (#5) |
| 19 Oct | Technical doc; security self-assessment; deck; demo video | #1, #2, #3, #5 |
| **20 Oct** | Polish; **submit by midday Beijing time**; resubmit if needed before 23:59 | All |

**Cut order if behind:** Chinese → Bengali + English only; AU refund → scripted; IM channel → web only; batching optimizer → drop.

**Demo storyline (updated after Interview #1):**
1. A Bengali-speaking parent uploads the fee notice → payee verified → Bangladeshi banks' CNY rates compared (saves ৳X) → FX range chart + staged plan → parent approves → sandbox executes (log shown).
2. Student in China: "ATM withdrawals at ~345 BDT each vs remit to my own Chinese account" → cheaper living-cost plan.
3. "Your endorsement expires in 3 weeks" → the agent drafts the enrolment-certificate request to the university, builds the renewal pack, and messages the parent in Bengali.
4. Card-blocked scenario → contingency plan kicks in.
5. A planted hundi / "discount agent" offer is blocked, with an explanation.
6. "Australia mode": visa refused → refund claim + decision.
7. Metrics slide.

---

## 9. Friend interview (Bangladesh → China, arrived Sept 2026)

**Interview #1 done (2026-10-12).** Answers and new problems N-01 … N-10 are in `01_problem_research.md` §J, with follow-up questions at the end of that file. Original questions:
1. How was the first tuition paid? Which Bangladeshi bank, USD or CNY, how many days, total BDT cost?
2. Was anything deducted along the way? Does the university accept USD?
3. Before a Chinese bank account: how did you pay? Foreign card on Alipay or WeChat? Fees? Blocked transfers?
4. How long did the residence permit and bank account take? Which documents? Anything Chinese-only?
5. Any limits on the new account (daily transfer caps)?
6. Scholarship? Stipend amount, which bank, when did the first payment land?
7. How does family send money now? Anyone offering hundi or a "discount agent"?
8. Any scam calls or "easy money with your bank card" offers?
9. Who handles the money: parent or student? In what language?
10. Can we use anonymised receipts to calibrate the cost model, and quote you anonymously?

---

## 10. To verify before it goes on a slide
- ~~Can Bangladeshi students remit tuition directly in CNY?~~ **Yes**: BRAC Bank sent 35,200 CNY directly (Interview #1). Still need the BDT amount debited to measure the markup.
- The rule behind the **short student endorsement** period, and the renewal process (Bangladesh Bank / BRAC)
- BRAC's current schedule of charges: foreign ATM fee (the ~345 BDT), the 3% non-USD factor, daily/monthly caps
- Has **FE Circular 37** been replaced after 29 Sep 2026? (bb.org.bd / bank)
- China rules for foreigners **receiving** remittances; exact app limits and fees (3% > RMB 200)
- China 2026 KYC rule: official title and text (PBOC)
- Does stipend money sent home qualify for Bangladesh's **2.5% incentive**?
- Source of "87.19% self-funded (MoE 2018)" statistic
- Free FX API with **BDT** coverage and licence terms

---

## Sources (earlier analysis)
- [FinTechathon official site](https://fintechathon.g-ican.com/#/en)
- [IEEE CIS Shenzhen announcement](https://r10.ieee.org/shenzhen-cis/blog/2026/06/17/2026-shenzhen-international-fintech-competition-international-track/)
- [World Bank RPW Q1 2025](https://remittanceprices.worldbank.org/sites/default/files/rpw_main_report_and_annex_q125_1_0.pdf)
- [Bloomberg: BD market-based rate](https://www.bloomberg.com/news/articles/2025-05-15/bangladesh-removes-restrictions-in-currency-movement-in-imf-push)
- [Dhaka Tribune: taka stability](https://www.dhakatribune.com/amp/business/416866/taka-outperforms-south-asian-currencies)
- [Ozford refund policy (ESOS)](https://ozford.edu.au/documents/134/Refund_Management_Policy_and_Procedure_2025.pdf)
- [Wise Comparison API](https://docs.wise.com/api-reference/comparison)
- [Fed paper on Meese–Rogoff](https://www.federalreserve.gov/econres/feds/files/2025089r1pap.pdf)
- [arXiv 2026: ML vs random walk](https://arxiv.org/pdf/2606.15058)
- Full problem-evidence sources: see [`01_problem_research.md`](01_problem_research.md)
