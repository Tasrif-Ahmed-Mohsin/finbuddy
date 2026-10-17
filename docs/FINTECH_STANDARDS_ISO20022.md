# ISO 20022 payment messages (`pain.001.001.09`) and SWIFT gpi UETR

> Code: `backend/app/integrations/iso20022.py` (message and checks), `backend/app/service.py` (made when a transfer
> is sent), `mobile/src/components/swift-uetr-card.tsx` (shown on the receipt). Tests: `backend/tests/test_iso20022.py`.

## 1. What it does

Every bank transfer Sathi sends in the sandbox also produces the instruction a bank would receive:

1. **ISO 20022 `pain.001.001.09`** (Customer Credit Transfer Initiation), the message format SWIFT's CBPR+ uses for
   cross-border payments.
2. A **SWIFT gpi UETR** (Unique End-to-end Transaction Reference, a version-4 UUID) on the receipt, the ID banks
   use to track a payment end to end.
3. **Purpose and regulatory reporting**: purpose code `EDUC` (education fees) or `FAMI` (family maintenance, living
   money), and a Bangladesh Bank reporting block (`DbtCdtRptgInd = DEBT`, country `BD`, code `STUDTUIT` / `STUDLIVE`,
   the Student File reference).
4. **Charge bearer**: tuition goes `DEBT` (the sender pays every fee, so the university receives the full amount,
   which universities ask for); living money `SHAR`.

The message is made once, when the transfer is sent (never on a page view), and written to the hash-chained log
(`iso20022_generated`, with the UETR).

## 2. How it is checked

`validate_pain001()` checks the rules of the `pain.001.001.09` schema that this message uses:

- namespace and the required blocks (`GrpHdr`, `PmtInf`, `CdtTrfTxInf`), message ID, amount and currency;
- the UETR format (`[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}`);
- code lists: `ChrgBr` must be a ChargeBearerType1Code (`DEBT`, `CRED`, `SHAR`, `SLEV`), purpose a 4-letter code;
- lengths: `MsgId`, `PmtInfId`, `EndToEndId` and regulatory `Inf` at most 35 characters, names and remittance text
  at most 140, regulatory `Cd` at most 10;
- every `BICFI` matches the BIC pattern `[A-Z0-9]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?`.

Honest limit: this is a rule check written from the schema, not a run of the official XSD file. Validating against
the published XSD (from iso20022.org) is the next step before a bank pilot. An earlier version of this module used
values the schema rejects (`ChrgBr = SHA`, a 22-character regulatory code, a 77-character `Inf`) and several wrong
bank codes; the review on 18 Oct fixed them and added `test_message_follows_the_schema_rules`.

## 3. Bank codes (SWIFT BIC, head offices)

| Bank | Country | BIC | Role here |
|---|---|---|---|
| BRAC Bank PLC | BD | `BRAKBDDHXXX` | Default sending bank (Student File) |
| Eastern Bank PLC | BD | `EBLDBDDHXXX` | Sending bank |
| Standard Chartered Bank Bangladesh | BD | `SCBLBDDXXXX` | Sending bank |
| Bank of China | CN | `BKCHCNBJXXX` | Default receiving bank |
| Industrial and Commercial Bank of China | CN | `ICBKCNBJXXX` | Receiving bank |
| China Construction Bank | CN | `PCBCCNBJXXX` | Receiving bank |

These are public head-office codes; the sandbox never contacts the banks.

## 4. Endpoints

| Endpoint | Method | Returns |
|---|---|---|
| `/receipts` | GET | Every payment, with its UETR and a summary of the ISO 20022 message |
| `/receipts/{draft_id}/iso20022` | GET | The whole record: XML, check list, routing BICs (400 before the transfer is sent) |
| `/receipts/{draft_id}/pain001.xml` | GET | The raw `application/xml` message |

## 5. A generated message (tuition, ¥35,200)

```xml
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.09">
  <CstmrCdtTrfInitn>
    <GrpHdr>
      <MsgId>SATHI-20261012-DRAFT-0001</MsgId>
      <CreDtTm>2026-10-12T09:00:00Z</CreDtTm>
      <NbOfTxs>1</NbOfTxs>
      <CtrlSum>35200.00</CtrlSum>
      <InitgPty>
        <Nm>Sathi Autonomous Student Finance Gateway</Nm>
        <Id>
          <OrgId>
            <Othr>
              <Id>SATHI-BD-CN-CORRIDOR</Id>
            </Othr>
          </OrgId>
        </Id>
      </InitgPty>
    </GrpHdr>
    <PmtInf>
      <PmtInfId>PMT-draft-0001</PmtInfId>
      <PmtMtd>TRF</PmtMtd>
      <NbOfTxs>1</NbOfTxs>
      <PmtTpInf>
        <SvcLvl>
          <Cd>G001</Cd>
        </SvcLvl>
      </PmtTpInf>
      <ReqdExctnDt>
        <Dt>2026-10-12</Dt>
      </ReqdExctnDt>
      <Dbtr>
        <Nm>Demo Parent</Nm>
        <PstlAdr>
          <Ctry>BD</Ctry>
          <AdrLine>Dhaka, Bangladesh</AdrLine>
        </PstlAdr>
      </Dbtr>
      <DbtrAcct>
        <Id>
          <Othr>
            <Id>BD-STUDENT-FILE-2026</Id>
          </Othr>
        </Id>
        <Ccy>BDT</Ccy>
      </DbtrAcct>
      <DbtrAgt>
        <FinInstnId>
          <BICFI>BRAKBDDHXXX</BICFI>
          <Nm>BRAC Bank PLC</Nm>
        </FinInstnId>
      </DbtrAgt>
      <CdtTrfTxInf>
        <PmtId>
          <EndToEndId>draft-0001</EndToEndId>
          <UETR>e7ff12b6-17cc-4fe2-a9eb-de5d0ae55040</UETR>
        </PmtId>
        <Amt>
          <InstdAmt Ccy="CNY">35200.00</InstdAmt>
        </Amt>
        <XchgRateInf>
          <UnitCcy>CNY</UnitCcy>
          <XchgRate>17.4000</XchgRate>
        </XchgRateInf>
        <ChrgBr>DEBT</ChrgBr>
        <CdtrAgt>
          <FinInstnId>
            <BICFI>BKCHCNBJXXX</BICFI>
            <Nm>Bank of China</Nm>
          </FinInstnId>
        </CdtrAgt>
        <Cdtr>
          <Nm>Demo University Finance Office</Nm>
          <PstlAdr>
            <Ctry>CN</Ctry>
            <AdrLine>Beijing, China</AdrLine>
          </PstlAdr>
        </Cdtr>
        <CdtrAcct>
          <Id>
            <Othr>
              <Id>university</Id>
            </Othr>
          </Id>
          <Ccy>CNY</Ccy>
        </CdtrAcct>
        <Purp>
          <Cd>EDUC</Cd>
        </Purp>
        <RgltryRptg>
          <DbtCdtRptgInd>DEBT</DbtCdtRptgInd>
          <Dtls>
            <Ctry>BD</Ctry>
            <Cd>STUDTUIT</Cd>
            <Inf>Student File BD-STUDENT-FILE-2026</Inf>
          </Dtls>
        </RgltryRptg>
        <RmtInf>
          <Ustrd>Sathi draft-0001: Tuition 2026-27</Ustrd>
        </RmtInf>
      </CdtTrfTxInf>
    </PmtInf>
  </CstmrCdtTrfInitn>
</Document>
```

It passes all 13 checks of section 2 (`validate_pain001`).
