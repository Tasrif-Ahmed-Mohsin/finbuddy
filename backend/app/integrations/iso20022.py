"""ISO 20022 Customer Credit Transfer Initiation (pain.001.001.09) + SWIFT gpi UETR Engine.

Conforms to SWIFT CBPR+ (Cross-Border Payments and Reporting Plus) and ISO 20022 Level 3 standards.
Generates compliant XML instructions for cross-border student remittances (Bangladesh -> China),
including:
- SWIFT gpi Unique End-to-end Transaction Reference (UETR) under RFC 4122 UUID v4.
- Originating Bank BIC (BRAC Bank, Eastern Bank) -> Destination Bank BIC (Bank of China, ICBC).
- Remittance and regulatory information (Bangladesh Bank FE Circular No. 37 Student File).
"""
from __future__ import annotations

import re
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

ISO20022_PAIN001_NS = "urn:iso:std:iso:20022:tech:xsd:pain.001.001.09"

# Bank Identifier Codes (SWIFT BIC, head offices) for the corridor. Public codes; the sandbox never contacts them.
CORRIDOR_BICS = {
    # Bangladeshi Originating Banks
    "brac": {"bic": "BRAKBDDHXXX", "name": "BRAC Bank PLC", "country": "BD", "city": "Dhaka"},
    "ebl": {"bic": "EBLDBDDHXXX", "name": "Eastern Bank PLC", "country": "BD", "city": "Dhaka"},
    "scb_bd": {"bic": "SCBLBDDXXXX", "name": "Standard Chartered Bank Bangladesh", "country": "BD", "city": "Dhaka"},
    "default_bd": {"bic": "BRAKBDDHXXX", "name": "BRAC Bank PLC", "country": "BD", "city": "Dhaka"},
    # Chinese Beneficiary Banks
    "boc": {"bic": "BKCHCNBJXXX", "name": "Bank of China", "country": "CN", "city": "Beijing"},
    "icbc": {"bic": "ICBKCNBJXXX", "name": "Industrial and Commercial Bank of China", "country": "CN", "city": "Beijing"},
    "ccb": {"bic": "PCBCCNBJXXX", "name": "China Construction Bank", "country": "CN", "city": "Beijing"},
    "default_cn": {"bic": "BKCHCNBJXXX", "name": "Bank of China", "country": "CN", "city": "Beijing"},
}
BIC_RE = re.compile(r"^[A-Z0-9]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$")
# Limits and code lists from the pain.001.001.09 schema that this message uses
MAX35 = ("MsgId", "PmtInfId", "EndToEndId", "Inf")
MAX140 = ("Nm", "Ustrd")
CHARGE_BEARER = {"DEBT", "CRED", "SHAR", "SLEV"}  # ChargeBearerType1Code
PURPOSE = {"tt_tuition": "EDUC", "tt_living": "FAMI"}  # ExternalPurpose1Code: education fees / family maintenance

UETR_REGEX = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)


def generate_uetr(seed_str: str | None = None) -> str:
    """Generates an RFC 4122 UUID version 4 compliant SWIFT gpi UETR."""
    if seed_str:
        # Deterministic UUID v4 for sandbox and test reproducibility
        ns = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
        raw = uuid.uuid5(ns, seed_str)
        # Force version 4 bits: 0100 for version, 10 for variant
        hex_str = raw.hex
        v4_hex = hex_str[:12] + "4" + hex_str[13:16] + "a" + hex_str[17:]
        return str(uuid.UUID(v4_hex)).lower()
    return str(uuid.uuid4()).lower()


def is_valid_uetr(uetr_str: str) -> bool:
    """Validates that a string is a valid SWIFT gpi UETR (UUID v4 canonical format)."""
    if not uetr_str or not isinstance(uetr_str, str):
        return False
    return bool(UETR_REGEX.match(uetr_str.strip()))


def resolve_origin_bic(bank_name_or_quote: str | None) -> dict[str, str]:
    if not bank_name_or_quote:
        return CORRIDOR_BICS["default_bd"]
    s = bank_name_or_quote.lower()
    if "eastern" in s or "ebl" in s:
        return CORRIDOR_BICS["ebl"]
    if "standard" in s or "scb" in s:
        return CORRIDOR_BICS["scb_bd"]
    return CORRIDOR_BICS["brac"]


def resolve_dest_bic(payee_bank: str | None) -> dict[str, str]:
    if not payee_bank:
        return CORRIDOR_BICS["default_cn"]
    s = payee_bank.lower()
    if "icbc" in s or "commercial" in s:
        return CORRIDOR_BICS["icbc"]
    if "construction" in s or "ccb" in s:
        return CORRIDOR_BICS["ccb"]
    return CORRIDOR_BICS["boc"]


def build_pain001_xml(
    draft_id: str,
    kind: str,
    amount_cny: Decimal,
    total_bdt: Decimal,
    rate_bdt_per_cny: Decimal | None,
    payer_name: str,
    payee_name: str,
    payee_account: str,
    memo: str,
    timestamp: datetime,
    origin_bank: str | None = None,
    dest_bank: str | None = None,
    uetr: str | None = None,
    student_file_ref: str = "BD-STUDENT-FILE-2026",
) -> tuple[str, str, str]:
    """Constructs a compliant ISO 20022 pain.001.001.09 customer credit transfer message.

    Returns:
        tuple[str, str, str]: (msg_id, uetr, xml_string)
    """
    the_uetr = uetr or generate_uetr(f"{draft_id}-{timestamp.isoformat()}")
    date_str = timestamp.strftime("%Y%m%d")
    msg_id = f"SATHI-{date_str}-{draft_id.upper()}"[:35]
    cre_dt_tm = timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
    req_exec_dt = timestamp.strftime("%Y-%m-%d")

    orig_bic_info = resolve_origin_bic(origin_bank)
    dest_bic_info = resolve_dest_bic(dest_bank)

    # Register default namespace for pain.001.001.09
    ET.register_namespace("", ISO20022_PAIN001_NS)
    doc = ET.Element(f"{{{ISO20022_PAIN001_NS}}}Document")
    cstmr = ET.SubElement(doc, f"{{{ISO20022_PAIN001_NS}}}CstmrCdtTrfInitn")

    # 1. Group Header (GrpHdr)
    grp_hdr = ET.SubElement(cstmr, f"{{{ISO20022_PAIN001_NS}}}GrpHdr")
    m_id = ET.SubElement(grp_hdr, f"{{{ISO20022_PAIN001_NS}}}MsgId")
    m_id.text = msg_id
    c_dt = ET.SubElement(grp_hdr, f"{{{ISO20022_PAIN001_NS}}}CreDtTm")
    c_dt.text = cre_dt_tm
    nb_tx = ET.SubElement(grp_hdr, f"{{{ISO20022_PAIN001_NS}}}NbOfTxs")
    nb_tx.text = "1"
    ctrl_sum = ET.SubElement(grp_hdr, f"{{{ISO20022_PAIN001_NS}}}CtrlSum")
    ctrl_sum.text = f"{amount_cny:.2f}"

    initg_pty = ET.SubElement(grp_hdr, f"{{{ISO20022_PAIN001_NS}}}InitgPty")
    initg_nm = ET.SubElement(initg_pty, f"{{{ISO20022_PAIN001_NS}}}Nm")
    initg_nm.text = "Sathi Autonomous Student Finance Gateway"
    initg_id = ET.SubElement(initg_pty, f"{{{ISO20022_PAIN001_NS}}}Id")
    initg_org = ET.SubElement(initg_id, f"{{{ISO20022_PAIN001_NS}}}OrgId")
    initg_othr = ET.SubElement(initg_org, f"{{{ISO20022_PAIN001_NS}}}Othr")
    initg_othr_id = ET.SubElement(initg_othr, f"{{{ISO20022_PAIN001_NS}}}Id")
    initg_othr_id.text = "SATHI-BD-CN-CORRIDOR"

    # 2. Payment Information (PmtInf)
    pmt_inf = ET.SubElement(cstmr, f"{{{ISO20022_PAIN001_NS}}}PmtInf")
    pmt_inf_id = ET.SubElement(pmt_inf, f"{{{ISO20022_PAIN001_NS}}}PmtInfId")
    pmt_inf_id.text = f"PMT-{draft_id}"[:35]
    pmt_mtd = ET.SubElement(pmt_inf, f"{{{ISO20022_PAIN001_NS}}}PmtMtd")
    pmt_mtd.text = "TRF"  # Credit Transfer
    nb_of_txs = ET.SubElement(pmt_inf, f"{{{ISO20022_PAIN001_NS}}}NbOfTxs")
    nb_of_txs.text = "1"

    pmt_tp_inf = ET.SubElement(pmt_inf, f"{{{ISO20022_PAIN001_NS}}}PmtTpInf")
    svc_lvl = ET.SubElement(pmt_tp_inf, f"{{{ISO20022_PAIN001_NS}}}SvcLvl")
    svc_cd = ET.SubElement(svc_lvl, f"{{{ISO20022_PAIN001_NS}}}Cd")
    svc_cd.text = "G001"  # SWIFT gpi standard service level

    reqd_dt = ET.SubElement(pmt_inf, f"{{{ISO20022_PAIN001_NS}}}ReqdExctnDt")
    dt = ET.SubElement(reqd_dt, f"{{{ISO20022_PAIN001_NS}}}Dt")
    dt.text = req_exec_dt

    # Debtor (Dbtr)
    dbtr = ET.SubElement(pmt_inf, f"{{{ISO20022_PAIN001_NS}}}Dbtr")
    dbtr_nm = ET.SubElement(dbtr, f"{{{ISO20022_PAIN001_NS}}}Nm")
    dbtr_nm.text = payer_name
    dbtr_adr = ET.SubElement(dbtr, f"{{{ISO20022_PAIN001_NS}}}PstlAdr")
    dbtr_ctry = ET.SubElement(dbtr_adr, f"{{{ISO20022_PAIN001_NS}}}Ctry")
    dbtr_ctry.text = "BD"
    dbtr_line = ET.SubElement(dbtr_adr, f"{{{ISO20022_PAIN001_NS}}}AdrLine")
    dbtr_line.text = f"{orig_bic_info['city']}, Bangladesh"

    # Debtor Account (DbtrAcct)
    dbtr_acct = ET.SubElement(pmt_inf, f"{{{ISO20022_PAIN001_NS}}}DbtrAcct")
    dbtr_acct_id = ET.SubElement(dbtr_acct, f"{{{ISO20022_PAIN001_NS}}}Id")
    dbtr_acct_othr = ET.SubElement(dbtr_acct_id, f"{{{ISO20022_PAIN001_NS}}}Othr")
    dbtr_acct_othr_id = ET.SubElement(dbtr_acct_othr, f"{{{ISO20022_PAIN001_NS}}}Id")
    dbtr_acct_othr_id.text = student_file_ref
    dbtr_ccy = ET.SubElement(dbtr_acct, f"{{{ISO20022_PAIN001_NS}}}Ccy")
    dbtr_ccy.text = "BDT"

    # Debtor Agent (DbtrAgt)
    dbtr_agt = ET.SubElement(pmt_inf, f"{{{ISO20022_PAIN001_NS}}}DbtrAgt")
    dbtr_agt_fi = ET.SubElement(dbtr_agt, f"{{{ISO20022_PAIN001_NS}}}FinInstnId")
    dbtr_bic = ET.SubElement(dbtr_agt_fi, f"{{{ISO20022_PAIN001_NS}}}BICFI")
    dbtr_bic.text = orig_bic_info["bic"]
    dbtr_bnk_nm = ET.SubElement(dbtr_agt_fi, f"{{{ISO20022_PAIN001_NS}}}Nm")
    dbtr_bnk_nm.text = orig_bic_info["name"]

    # 3. Credit Transfer Transaction Information (CdtTrfTxInf)
    tx_inf = ET.SubElement(pmt_inf, f"{{{ISO20022_PAIN001_NS}}}CdtTrfTxInf")

    # Payment ID with EndToEndId and SWIFT UETR
    pmt_id = ET.SubElement(tx_inf, f"{{{ISO20022_PAIN001_NS}}}PmtId")
    e2e_id = ET.SubElement(pmt_id, f"{{{ISO20022_PAIN001_NS}}}EndToEndId")
    e2e_id.text = draft_id[:35]
    uetr_el = ET.SubElement(pmt_id, f"{{{ISO20022_PAIN001_NS}}}UETR")
    uetr_el.text = the_uetr

    # Amount
    amt = ET.SubElement(tx_inf, f"{{{ISO20022_PAIN001_NS}}}Amt")
    instd_amt = ET.SubElement(amt, f"{{{ISO20022_PAIN001_NS}}}InstdAmt", {"Ccy": "CNY"})
    instd_amt.text = f"{amount_cny:.2f}"

    # FX Rate Information
    if rate_bdt_per_cny and rate_bdt_per_cny > 0:
        fx_inf = ET.SubElement(tx_inf, f"{{{ISO20022_PAIN001_NS}}}XchgRateInf")
        unit_ccy = ET.SubElement(fx_inf, f"{{{ISO20022_PAIN001_NS}}}UnitCcy")
        unit_ccy.text = "CNY"
        xchg_rate = ET.SubElement(fx_inf, f"{{{ISO20022_PAIN001_NS}}}XchgRate")
        xchg_rate.text = f"{rate_bdt_per_cny:.4f}"

    # Charge bearer: tuition goes "OUR" (DEBT: the sender pays every fee, so the university gets the full amount);
    # living money is shared (SHAR).
    chrg_br = ET.SubElement(tx_inf, f"{{{ISO20022_PAIN001_NS}}}ChrgBr")
    chrg_br.text = "DEBT" if kind == "tt_tuition" else "SHAR"

    # Creditor Agent (CdtrAgt - Beneficiary Bank in China)
    cdtr_agt = ET.SubElement(tx_inf, f"{{{ISO20022_PAIN001_NS}}}CdtrAgt")
    cdtr_agt_fi = ET.SubElement(cdtr_agt, f"{{{ISO20022_PAIN001_NS}}}FinInstnId")
    cdtr_bic = ET.SubElement(cdtr_agt_fi, f"{{{ISO20022_PAIN001_NS}}}BICFI")
    cdtr_bic.text = dest_bic_info["bic"]
    cdtr_bnk_nm = ET.SubElement(cdtr_agt_fi, f"{{{ISO20022_PAIN001_NS}}}Nm")
    cdtr_bnk_nm.text = dest_bic_info["name"]

    # Creditor (Cdtr)
    cdtr = ET.SubElement(tx_inf, f"{{{ISO20022_PAIN001_NS}}}Cdtr")
    cdtr_nm = ET.SubElement(cdtr, f"{{{ISO20022_PAIN001_NS}}}Nm")
    cdtr_nm.text = payee_name
    cdtr_adr = ET.SubElement(cdtr, f"{{{ISO20022_PAIN001_NS}}}PstlAdr")
    cdtr_ctry = ET.SubElement(cdtr_adr, f"{{{ISO20022_PAIN001_NS}}}Ctry")
    cdtr_ctry.text = "CN"
    cdtr_line = ET.SubElement(cdtr_adr, f"{{{ISO20022_PAIN001_NS}}}AdrLine")
    cdtr_line.text = f"{dest_bic_info['city']}, China"

    # Creditor Account (CdtrAcct)
    cdtr_acct = ET.SubElement(tx_inf, f"{{{ISO20022_PAIN001_NS}}}CdtrAcct")
    cdtr_acct_id = ET.SubElement(cdtr_acct, f"{{{ISO20022_PAIN001_NS}}}Id")
    cdtr_acct_othr = ET.SubElement(cdtr_acct_id, f"{{{ISO20022_PAIN001_NS}}}Othr")
    cdtr_acct_othr_id = ET.SubElement(cdtr_acct_othr, f"{{{ISO20022_PAIN001_NS}}}Id")
    cdtr_acct_othr_id.text = payee_account or "CN-STUDENT-ACCOUNT"
    cdtr_ccy = ET.SubElement(cdtr_acct, f"{{{ISO20022_PAIN001_NS}}}Ccy")
    cdtr_ccy.text = "CNY"

    # Purpose (ExternalPurpose1Code): EDUC = education fees, FAMI = family maintenance (living money)
    purp = ET.SubElement(tx_inf, f"{{{ISO20022_PAIN001_NS}}}Purp")
    purp_cd = ET.SubElement(purp, f"{{{ISO20022_PAIN001_NS}}}Cd")
    purp_cd.text = PURPOSE.get(kind, "EDUC")

    # Regulatory reporting for Bangladesh Bank: an outward student remittance under the Student File
    reg_rptg = ET.SubElement(tx_inf, f"{{{ISO20022_PAIN001_NS}}}RgltryRptg")
    reg_ind = ET.SubElement(reg_rptg, f"{{{ISO20022_PAIN001_NS}}}DbtCdtRptgInd")
    reg_ind.text = "DEBT"
    reg_dtls = ET.SubElement(reg_rptg, f"{{{ISO20022_PAIN001_NS}}}Dtls")
    reg_ctry = ET.SubElement(reg_dtls, f"{{{ISO20022_PAIN001_NS}}}Ctry")
    reg_ctry.text = "BD"
    reg_cd = ET.SubElement(reg_dtls, f"{{{ISO20022_PAIN001_NS}}}Cd")
    reg_cd.text = "STUDTUIT" if kind == "tt_tuition" else "STUDLIVE"  # Max10Text
    reg_inf = ET.SubElement(reg_dtls, f"{{{ISO20022_PAIN001_NS}}}Inf")
    reg_inf.text = f"Student File {student_file_ref}"[:35]

    # Remittance Information (RmtInf)
    rmt_inf = ET.SubElement(tx_inf, f"{{{ISO20022_PAIN001_NS}}}RmtInf")
    ustrd = ET.SubElement(rmt_inf, f"{{{ISO20022_PAIN001_NS}}}Ustrd")
    clean_memo = memo.strip() if memo else ("Tuition Remittance" if kind == "tt_tuition" else "Living Remittance")
    ustrd.text = f"Sathi {draft_id}: {clean_memo}"[:140]

    xml_bytes = ET.tostring(doc, encoding="utf-8", xml_declaration=True)
    xml_str = xml_bytes.decode("utf-8")
    return msg_id, the_uetr, xml_str


def validate_pain001(xml_str: str) -> dict[str, Any]:
    """Validates an ISO 20022 pain.001.001.09 message against banking standards."""
    errors: list[str] = []
    checks: list[str] = []

    try:
        root = ET.fromstring(xml_str.encode("utf-8"))
    except Exception as e:
        return {"valid": False, "schema": "unknown", "errors": [f"Malformed XML: {e}"], "checks_passed": 0}

    # Verify namespace
    expected_root = f"{{{ISO20022_PAIN001_NS}}}Document"
    if root.tag != expected_root:
        errors.append(f"Invalid root element or namespace: expected '{expected_root}', got '{root.tag}'")
    else:
        checks.append("Namespace matches ISO 20022 pain.001.001.09")

    def find_el(parent, tag_name):
        return parent.find(f"{{{ISO20022_PAIN001_NS}}}{tag_name}")

    cstmr = find_el(root, "CstmrCdtTrfInitn")
    if cstmr is None:
        errors.append("Missing <CstmrCdtTrfInitn>")
        return {"valid": False, "schema": "pain.001.001.09", "errors": errors, "checks_passed": len(checks)}
    checks.append("Found <CstmrCdtTrfInitn>")

    # Group Header checks
    grp = find_el(cstmr, "GrpHdr")
    msg_id = ""
    if grp is not None:
        msg_id_el = find_el(grp, "MsgId")
        msg_id = msg_id_el.text if msg_id_el is not None else ""
        if not msg_id:
            errors.append("Missing or empty <GrpHdr><MsgId>")
        else:
            checks.append(f"Valid Message ID: {msg_id}")
    else:
        errors.append("Missing <GrpHdr>")

    # Payment Info checks
    pmt_inf = find_el(cstmr, "PmtInf")
    uetr = ""
    amount = ""
    ccy = ""
    if pmt_inf is not None:
        checks.append("Found <PmtInf>")
        # Debtor Agent BIC
        dbtr_agt = find_el(pmt_inf, "DbtrAgt")
        if dbtr_agt is not None:
            bic_el = dbtr_agt.find(f".//{{{ISO20022_PAIN001_NS}}}BICFI")
            if bic_el is not None and len(bic_el.text or "") in (8, 11):
                checks.append(f"Valid Debtor BIC: {bic_el.text}")
            else:
                errors.append("Invalid or missing Debtor Agent <BICFI>")

        # Transaction Info
        tx_inf = find_el(pmt_inf, "CdtTrfTxInf")
        if tx_inf is not None:
            checks.append("Found <CdtTrfTxInf>")
            # UETR
            uetr_el = tx_inf.find(f".//{{{ISO20022_PAIN001_NS}}}UETR")
            if uetr_el is not None and is_valid_uetr(uetr_el.text or ""):
                uetr = uetr_el.text or ""
                checks.append(f"Valid SWIFT gpi UETR: {uetr}")
            else:
                errors.append(f"Invalid or missing SWIFT gpi <UETR>: got '{getattr(uetr_el, 'text', None)}'")

            # Amount & Currency
            amt_el = tx_inf.find(f".//{{{ISO20022_PAIN001_NS}}}InstdAmt")
            if amt_el is not None:
                amount = amt_el.text or ""
                ccy = amt_el.attrib.get("Ccy", "")
                if ccy in ("CNY", "BDT", "USD") and Decimal(amount or "0") > 0:
                    checks.append(f"Valid Instructed Amount: {ccy} {amount}")
                else:
                    errors.append(f"Invalid amount or currency: {ccy} {amount}")

            # Creditor Agent BIC
            cdtr_agt = find_el(tx_inf, "CdtrAgt")
            if cdtr_agt is not None:
                cbic_el = cdtr_agt.find(f".//{{{ISO20022_PAIN001_NS}}}BICFI")
                if cbic_el is not None and len(cbic_el.text or "") in (8, 11):
                    checks.append(f"Valid Creditor BIC: {cbic_el.text}")
                else:
                    errors.append("Invalid or missing Creditor Agent <BICFI>")

            # Charge bearer and purpose from the schema's code lists
            chrg = find_el(tx_inf, "ChrgBr")
            if chrg is not None and chrg.text not in CHARGE_BEARER:
                errors.append(f"<ChrgBr> '{chrg.text}' is not a ChargeBearerType1Code")
            elif chrg is not None:
                checks.append(f"Charge bearer {chrg.text}")
            purp_el = tx_inf.find(f".//{{{ISO20022_PAIN001_NS}}}Purp/{{{ISO20022_PAIN001_NS}}}Cd")
            if purp_el is not None and re.fullmatch(r"[A-Z]{4}", purp_el.text or ""):
                checks.append(f"Purpose code {purp_el.text}")
            # Regulatory Reporting
            reg_el = tx_inf.find(f".//{{{ISO20022_PAIN001_NS}}}RgltryRptg")
            if reg_el is not None:
                cd = reg_el.find(f".//{{{ISO20022_PAIN001_NS}}}Cd")
                if cd is not None and len(cd.text or "") > 10:
                    errors.append("<RgltryRptg><Dtls><Cd> is longer than 10 characters")
                else:
                    checks.append("Regulatory reporting for Bangladesh Bank present")
    else:
        errors.append("Missing <PmtInf>")

    # Text lengths and BIC format, everywhere in the message
    for el in root.iter():
        tag = el.tag.split("}")[-1]
        if tag in MAX35 and len(el.text or "") > 35:
            errors.append(f"<{tag}> is longer than 35 characters")
        if tag in MAX140 and len(el.text or "") > 140:
            errors.append(f"<{tag}> is longer than 140 characters")
        if tag == "BICFI" and not BIC_RE.match(el.text or ""):
            errors.append(f"<BICFI> '{el.text}' is not a valid BIC")
    if not errors:
        checks.append("Field lengths, code lists and BIC formats follow the pain.001.001.09 schema")

    is_valid = len(errors) == 0
    return {
        "valid": is_valid,
        "schema": "pain.001.001.09",
        "uetr": uetr,
        "msg_id": msg_id,
        "amount": amount,
        "currency": ccy,
        "checks_passed": len(checks),
        "checks": checks,
        "errors": errors,
    }
