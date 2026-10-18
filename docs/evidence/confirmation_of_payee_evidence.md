# Confirmation of Payee (CoP) & Anti-APP Fraud Verification

## 1. Executive Summary

**Authorised Push Payment (APP) fraud** is the fastest-growing financial crime in cross-border education and remittance corridors:
A scammer impersonates a university bursar, student housing agency, or tuition clearing service and instructs a student or parent:
> *"Transfer ¥35,200 to University Tuition Office (Account: 6222-0202-9999-009)"*

The victim willingly authorises the payment because they believe they are paying their university. In reality, the bank account belongs to a criminal syndicate or shell company (`Shenzhen Apex Trading Co. Ltd`).

**Bluefin implements Confirmation of Payee (CoP)**, modeled on:
- **UK Payment Systems Regulator (PSR)** Specific Direction 10 / 17
- **EU Verification of Payee (VoP)** under SEPA Instant Payments Regulation (EU 2024/886)

---

## 2. How Confirmation of Payee Operates

Before any payment draft is approved or executed, the sending engine makes a real-time cryptographic inquiry to the receiving bank's directory simulator:

```
  [ Bluefin Payment Engine ]
             │
             │  Query: payee_id="univ_demo", intended="Demo University"
             ▼
  [ Receiving Bank Directory (Sandbox Bank of China) ]
             │
             │  1. Token normalization & fuzzy sequence matching
             │  2. Entity categorization (Business vs Personal)
             │  3. Score computation: Jaro-Winkler + Token-Set
             ▼
      [ CoP Result: MATCH | CLOSE_MATCH | NO_MATCH ]
             │
             ├──► MATCH (Score ≥ 0.82):
             │    "Account holder MATCHED 'Demo University Finance Office' (BKCHCNBJXXX)"
             │    App Scam Risk: LOW. Safe to proceed.
             │
             ├──► CLOSE_MATCH (Score 0.50 - 0.81):
             │    "Account belongs to 'Demo University Finance Office', differing slightly from input"
             │    App Scam Risk: MEDIUM. Prompts user to confirm spelling.
             │
             └──► NO_MATCH (Score < 0.50 or Wrong Owner):
                  "CRITICAL APP FRAUD WARNING: Account belongs to 'Shenzhen Apex Trading Co', NOT 'Demo University'"
                  App Scam Risk: CRITICAL. Payment BLOCKED by compliance engine.
```

---

## 3. Implementation Across Bluefin

1. **Confirmation of Payee Engine ([`backend/app/security/cop.py`](file:///e:/chinahack/backend/app/security/cop.py))**:
   - `ConfirmationOfPayeeService`: Maintains simulated receiving bank account directories (`univ_demo`, `student_own_cn`, `agent_x`).
   - Normalization: Strips noise words (`Ltd`, `Limited`, `Office`, `Finance`, `Univ`, punctuation).
   - Returns full `CopVerification` record with risk grading, bank BIC, and actionable advice.

2. **Compliance Integration ([`backend/app/security/compliance.py`](file:///e:/chinahack/backend/app/security/compliance.py#L161-L192))**:
   - Check 9: `cop_verification` executed on every payment draft.
   - If `NO_MATCH`: blocks draft creation with `severity="block"`.
   - If `MATCH`: approves with green badge.

3. **REST Endpoint ([`backend/app/main.py`](file:///e:/chinahack/backend/app/main.py#L588-L593))**:
   - `POST /security/cop/verify`: Standalone endpoint for live pre-payment recipient verification.

4. **Mobile UI Component ([`mobile/src/components/cop-card.tsx`](file:///e:/chinahack/mobile/src/components/cop-card.tsx))**:
   - Rendered in [mobile/src/app/draft/[id].tsx](file:///e:/chinahack/mobile/src/app/draft/[id].tsx) before user fingerprint approval.
   - Trilingual support in English, Bengali, and Chinese.

---

## 4. Verification Evidence

Automated tests in [`backend/tests/test_cop.py`](file:///e:/chinahack/backend/tests/test_cop.py):
- `test_cop_exact_match`: Exact legal name verification (Score 1.0, Risk Low).
- `test_cop_alias_match`: University alias verification (Risk Low).
- `test_cop_close_match_with_typo`: Minor misspelling prompt.
- `test_cop_no_match_app_fraud_detection`: Attacker impersonates university using rogue account `agent_x` $\to$ Returns `NO_MATCH` and flags APP Fraud.
- `test_cop_draft_checks_and_endpoint`: Verified draft creation check and `POST /security/cop/verify`.
