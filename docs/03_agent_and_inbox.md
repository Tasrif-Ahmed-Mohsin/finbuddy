# Bluefin Agent and Inbox (SMS / email tracking)

**Last updated:** 2026-10-12 · Feeds the technical documentation and the security self-assessment.

## What the agent does
1. **Tracks:** reads bank SMS and email alerts the user shares or forwards, and turns them into transactions. Card limits (5 lakh BDT / 30 transactions) update from real alerts.
2. **Finds the best solution:** a rule engine raises insights with computed savings, e.g. "3 ATM withdrawals cost ৳1,035 in fees; a transfer to your own Chinese account saves ~৳3,300/month".
3. **Protects:** large or duplicate charges ("was this you?"), scam, hundi and phishing messages, OTP warnings, prompt-injection attempts.
4. **Keeps the user updated:** an Updates feed (Home and the Bluefin tab) in English, Bengali or Chinese, plus a chat agent (DeepSeek) that can explain, plan and **draft** payments.

## How messages get in (honest about platform limits)

| Channel | Status | Why |
|---|---|---|
| Share / paste into the app | ✅ works (Expo Go) | No special permission needed; works on Android and iOS |
| Webhook `POST /inbox/webhook` + `X-Ingest-Token` | ✅ works | For Android SMS-forwarding apps or iOS Shortcuts "when a message arrives" automations |
| Email (IMAP, read-only, app password) | ✅ code ready, needs a mailbox | `SATHI_IMAP_HOST/USER/PASSWORD` in `backend/.env`; `POST /inbox/email/sync` |
| Automatic SMS reading | ❌ not used | Google Play only allows `READ_SMS` for default SMS apps; a budgeting app tracking bank SMS was refused an exception. iOS has no API at all |

## Pipeline (`backend/app/inbox/service.py`)

```
message ─► financial filter ─► redaction ─► scam/phishing/injection scan ─► extraction ─► tracking ─► insights
            (drop non-money)   (OTP removed,   (rules, EN/BN/ZH)            (rules first;   (card caps,   (rules decide;
                               numbers masked)                               DeepSeek on     ledger)       DeepSeek only
                                                                             redacted text,                translates,
                                                                             number-grounded)              numbers checked)
```

## AI design (DeepSeek)
- Provider: DeepSeek (OpenAI-compatible API), model `deepseek-flash`, thinking mode disabled (fast, cheap). It is reachable from mainland China, which matters for the Shenzhen final.
- The key lives only in `backend/.env` (git-ignored) on the server, **never in the mobile app**.
- **The AI never decides numbers.** Extraction is accepted only if every number it returns appears in the message. Translations are accepted only if they contain the same numbers. Chat answers use tool results.
- **The AI cannot move money.** Its tools are read-only plus `create_payment_draft`. No approve/execute tool exists, and the permission engine blocks `Actor.AGENT` from executing anyway.
- **Offline fallback:** if DeepSeek is unreachable, rule-based answers in EN/BN/ZH (tested).

## Privacy and security promises (for the security self-assessment)
1. Non-money messages are dropped and never stored (only a counter).
2. One-time codes are removed before storage; Bluefin never asks for or shows an OTP.
3. Account, card and phone numbers are masked to their last 4 digits; emails are masked.
4. Only redacted text is sent to DeepSeek; the original text is never stored.
5. Message content is untrusted data: injection phrases are flagged, and risky messages are never turned into transactions or payments.
6. Reading messages is a READ (L0) capability; it can never move money.
7. Every ingestion and every agent tool call is in the hash-chained audit log (no message content, no OTPs).

**Known risks to list:**
- Data goes to a third-party AI provider (redacted only; get the user's consent; it is a China-based provider, so state data residency).
- The demo ingest token is a shared secret; rotate it in production.
- Parsers are tuned on synthetic samples and need real anonymised alerts.
- The phishing heuristic can flag legitimate "update KYC" messages (this fails safe).

## Photo documents (DeepSeek vision)
- `POST /documents/read` (users only): the photo is processed in memory and never stored. The audit log records the document type and counts only, never the text.
- Amounts are kept only if they appear in the model's own transcription. Long numbers are masked. Injection phrases in the document are flagged.
- A fee notice suggestion (amount + deadline) is applied only after the user confirms it (`POST /documents/apply`). From then on it backs the invoice check, so paying more than the notice is blocked.
- Live test: the friend's real residence-permit checklist (Chinese/English) gave all 11 items and a Bengali summary in 3.6 s. One translation slip ("介绍信" rendered as "ID card" in Bengali) shows why confirmation matters.

## Earn & Save in the inbox and the chat (16 Oct)
- **Inbox:** a credit with pay words (salary, stipend, 工资, 奖学金, বেতন, বৃত্তি) to the student's Chinese account is an `income` transaction → insight "Your pay arrived" (with the savings rule's share, or a suggestion). Debits whose text matches a "want" (Meituan, Taobao, hotpot, cinema…) in the last 7 days → insight "Wants in the last 7 days, in taka". Reading alerts never moves money: in the sandbox, pay days are credited by the sandbox bank; in production a bank API would move the Shield share.
- **Chat tools:** `get_savings` (Shield, rule, income, this week's wants in taka), `propose_savings_rule` (the student's own words → a proposal only the student can sign), `check_hundi_offer` (the legal options with real costs and the honest note). System rules 17–19: talk about pay/saving → `get_savings`; hundi → `check_hundi_offer`, never recommend it; never suggest unauthorised work.
- **Offline router:** savings words in English, Bengali, Banglish ("joma", "noshto", "luxury") and Chinese; a share like "50%" / "অর্ধেক" / "百分之30" makes a proposal. A hundi message is flagged as before, and the reply now adds the legal options with numbers (amount and offered rate read from text such as "$500 lagbe, 124 taka per dollar").

## Tests
`backend/tests/test_inbox.py` (privacy, parsing, grounding, insights, webhook, injection) and `backend/tests/test_agent.py` (tool calling with a fake DeepSeek, no-execute guarantee, bad tools, outage fallback, 3 languages). The suite never calls the real API.

## Next
- Ask the friend for 5–10 **real** anonymised bank SMS samples to tune the parsers.
- Local notifications for alerts (expo-notifications).
- A share-sheet target ("Share to Bluefin") in a development build.
