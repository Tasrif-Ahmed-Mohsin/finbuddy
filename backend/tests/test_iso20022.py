"""Automated tests for ISO 20022 pain.001.001.09 XML generation and SWIFT gpi UETR tracking.

Validates:
1. RFC 4122 UUID v4 compliance for SWIFT gpi UETR.
2. Corridor BIC mapping for Bangladesh -> China banking rails.
3. Element-level CBPR+ compliance for pain.001.001.09 customer credit transfer instructions.
4. Bangladesh Bank Foreign Exchange Circular No. 37 regulatory reporting tag.
5. Hash-chained audit logging and receipt enrichment on execution.
6. API endpoints for ISO 20022 JSON inspection and raw XML download.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.integrations.iso20022 import (
    ISO20022_PAIN001_NS,
    CORRIDOR_BICS,
    build_pain001_xml,
    generate_uetr,
    is_valid_uetr,
    resolve_dest_bic,
    resolve_origin_bic,
    validate_pain001,
)
from app.main import create_app
from app.security.permissions import Actor


HEADERS_PARENT = {"Authorization": "Bearer demo-parent"}
HEADERS_STUDENT = {"Authorization": "Bearer demo-student"}


def test_uetr_generation_and_validation():
    """SWIFT gpi requires RFC 4122 UUID v4 in canonical 36-character format."""
    # Random generation
    uetr = generate_uetr()
    assert is_valid_uetr(uetr)
    assert len(uetr) == 36
    assert uetr[14] == "4"  # Version 4
    assert uetr[19] in ("8", "9", "a", "b")  # Variant 10xx

    # Seeded / deterministic generation
    uetr_seeded1 = generate_uetr("payment-draft-12345")
    uetr_seeded2 = generate_uetr("payment-draft-12345")
    assert uetr_seeded1 == uetr_seeded2
    assert is_valid_uetr(uetr_seeded1)

    # Invalid UETRs
    assert not is_valid_uetr("")
    assert not is_valid_uetr("not-a-uuid")
    assert not is_valid_uetr("12345678-1234-1234-1234-123456789abc")  # Version not 4


def test_corridor_bic_resolution():
    """Originating and beneficiary banks must map to valid SWIFT BICs."""
    # BD Originating Banks
    brac = resolve_origin_bic("BRAC Bank")
    assert brac["bic"] == "BRAKBDDHXXX"
    assert brac["country"] == "BD"

    ebl = resolve_origin_bic("Eastern Bank PLC")
    assert ebl["bic"] == "EBLDBDDHXXX"

    default_bd = resolve_origin_bic(None)
    assert default_bd["country"] == "BD"

    # CN Beneficiary Banks
    boc = resolve_dest_bic("Sandbox Bank of China")
    assert boc["bic"] == "BKCHCNBJXXX"
    assert boc["country"] == "CN"

    icbc = resolve_dest_bic("Industrial and Commercial Bank of China")
    assert icbc["bic"] == "ICBKCNBJXXX"


def test_pain001_xml_generation_tuition():
    """Generates valid pain.001.001.09 message with all 10 CBPR+ checks passing."""
    now = datetime(2026, 10, 18, 12, 0, 0, tzinfo=timezone.utc)
    msg_id, uetr, xml_str = build_pain001_xml(
        draft_id="draft_test_101",
        kind="tt_tuition",
        amount_cny=Decimal("35200.00"),
        total_bdt=Decimal("580000.00"),
        rate_bdt_per_cny=Decimal("16.48"),
        payer_name="Demo Parent",
        payee_name="Demo University Finance Office",
        payee_account="CN04BKCH00006021",
        memo="Tuition Fee Autumn 2026",
        timestamp=now,
        origin_bank="BRAC Bank PLC",
        dest_bank="Bank of China",
    )

    assert "SATHI" in msg_id
    assert is_valid_uetr(uetr)

    # Validate against built-in CBPR+ rules
    report = validate_pain001(xml_str)
    assert report["valid"] is True
    assert report["schema"] == "pain.001.001.09"
    assert report["checks_passed"] == 13
    assert len(report["errors"]) == 0
    assert report["uetr"] == uetr
    assert report["amount"] == "35200.00"
    assert report["currency"] == "CNY"

    # Deep XML node inspection
    root = ET.fromstring(xml_str)
    ns = {"p": ISO20022_PAIN001_NS}

    # Verify SWIFT gpi Service Level
    svc_lvl = root.find(".//p:PmtTpInf/p:SvcLvl/p:Cd", ns)
    assert svc_lvl is not None and svc_lvl.text == "G001"

    # Verify Regulatory Reporting for Bangladesh Bank
    reg_cd = root.find(".//p:RgltryRptg/p:Dtls/p:Cd", ns)
    assert reg_cd is not None and reg_cd.text == "STUDTUIT"

    # Verify Debtor and Creditor BICs
    dbtr_bic = root.find(".//p:DbtrAgt/p:FinInstnId/p:BICFI", ns)
    assert dbtr_bic is not None and dbtr_bic.text == "BRAKBDDHXXX"

    cdtr_bic = root.find(".//p:CdtrAgt/p:FinInstnId/p:BICFI", ns)
    assert cdtr_bic is not None and cdtr_bic.text == "BKCHCNBJXXX"


def test_pain001_xml_generation_living():
    """Living allowance uses STUDLIVE regulatory code."""
    now = datetime(2026, 10, 18, 12, 0, 0, tzinfo=timezone.utc)
    _, _, xml_str = build_pain001_xml(
        draft_id="draft_test_102",
        kind="tt_living",
        amount_cny=Decimal("6000.00"),
        total_bdt=Decimal("99000.00"),
        rate_bdt_per_cny=Decimal("16.50"),
        payer_name="Demo Parent",
        payee_name="Student Personal Account",
        payee_account="CN04BKCH00003317",
        memo="Monthly living support",
        timestamp=now,
    )
    report = validate_pain001(xml_str)
    assert report["valid"] is True

    root = ET.fromstring(xml_str)
    ns = {"p": ISO20022_PAIN001_NS}
    reg_cd = root.find(".//p:RgltryRptg/p:Dtls/p:Cd", ns)
    assert reg_cd is not None and reg_cd.text == "STUDLIVE"


def test_validate_pain001_detects_tampering():
    """Corrupted or non-compliant XML must be flagged by the validator."""
    # Completely broken XML
    bad1 = validate_pain001("<NotEvenXml")
    assert bad1["valid"] is False
    assert any("Malformed XML" in e for e in bad1["errors"])

    # Missing UETR
    xml_without_uetr = f"""<Document xmlns="{ISO20022_PAIN001_NS}">
        <CstmrCdtTrfInitn>
            <GrpHdr><MsgId>M1</MsgId></GrpHdr>
            <PmtInf>
                <DbtrAgt><FinInstnId><BICFI>BRAKBDDHXXX</BICFI></FinInstnId></DbtrAgt>
                <CdtTrfTxInf>
                    <InstdAmt Ccy="CNY">100.00</InstdAmt>
                    <CdtrAgt><FinInstnId><BICFI>BKCHCNBJXXX</BICFI></FinInstnId></CdtrAgt>
                </CdtTrfTxInf>
            </PmtInf>
        </CstmrCdtTrfInitn>
    </Document>"""
    bad2 = validate_pain001(xml_without_uetr)
    assert bad2["valid"] is False
    assert any("UETR" in e for e in bad2["errors"])


def test_end_to_end_receipt_and_iso_api(tmp_path):
    """Executing a draft generates an ISO 20022 record visible in receipts and downloadable via API."""
    audit_file = tmp_path / "audit.jsonl"
    app = create_app(audit_path=audit_file, llm=None)
    client = TestClient(app)

    # 1. Create a tuition payment draft
    res = client.post(
        "/drafts",
        headers=HEADERS_PARENT,
        json={"kind": "tt_tuition", "amount_cny": "35200", "payee_id": "univ_demo", "memo": "Autumn Tuition 2026"},
    )
    assert res.status_code == 200
    draft = res.json()
    draft_id = draft["id"]

    # 2. Both parent and student approve (two-person rule)
    client.post(f"/drafts/{draft_id}/approve", headers=HEADERS_PARENT)
    client.post(f"/drafts/{draft_id}/approve", headers=HEADERS_STUDENT)

    # 3. Parent executes the transfer
    exec_res = client.post(f"/drafts/{draft_id}/execute", headers=HEADERS_PARENT)
    assert exec_res.status_code == 200

    # 4. Receipts endpoint should now contain the executed payment with SWIFT gpi UETR & ISO 20022 metadata
    receipts_res = client.get("/receipts", headers=HEADERS_PARENT)
    assert receipts_res.status_code == 200
    receipts = receipts_res.json()
    assert len(receipts) > 0

    target_receipt = next(r for r in receipts if r["draft"]["id"] == draft_id)
    assert target_receipt["uetr"] is not None
    assert is_valid_uetr(target_receipt["uetr"])
    assert target_receipt["iso20022"] is not None
    assert target_receipt["iso20022"]["schema"] == "pain.001.001.09"
    assert target_receipt["iso20022"]["valid"] is True
    assert target_receipt["iso20022"]["checks_passed"] == 13
    assert target_receipt["iso20022"]["origin_bic"] == "BRAKBDDHXXX"
    assert target_receipt["iso20022"]["dest_bic"] == "BKCHCNBJXXX"
    assert target_receipt["iso20022"]["regulatory_reporting"] == "STUDTUIT"

    # 5. GET /receipts/{draft_id}/iso20022 returns full JSON metadata and validation report
    iso_json_res = client.get(f"/receipts/{draft_id}/iso20022", headers=HEADERS_PARENT)
    assert iso_json_res.status_code == 200
    iso_data = iso_json_res.json()
    assert iso_data["uetr"] == target_receipt["uetr"]
    assert "xml" in iso_data
    assert iso_data["validation"]["valid"] is True

    # 6. GET /receipts/{draft_id}/pain001.xml returns raw XML with official content-type
    xml_res = client.get(f"/receipts/{draft_id}/pain001.xml", headers=HEADERS_PARENT)
    assert xml_res.status_code == 200
    assert "application/xml" in xml_res.headers["content-type"]
    assert f"<UETR>{target_receipt['uetr']}</UETR>" in xml_res.text
    assert "STUDTUIT" in xml_res.text


def test_iso_api_error_handling(tmp_path):
    """Querying non-existent draft returns 404; ATM draft returns 400."""
    audit_file = tmp_path / "audit.jsonl"
    app = create_app(audit_path=audit_file, llm=None)
    client = TestClient(app)

    # 404 on missing draft
    res404 = client.get("/receipts/nonexistent_draft/iso20022", headers=HEADERS_PARENT)
    assert res404.status_code == 404

    # Create an ATM draft
    res_atm = client.post(
        "/drafts",
        headers=HEADERS_STUDENT,
        json={"kind": "atm_plan", "amount_cny": "2000", "withdrawals": ["2000"], "memo": "Cash ATM"},
    )
    assert res_atm.status_code == 200
    atm_id = res_atm.json()["id"]

    # 400 on ATM draft (only wires use pain.001)
    res400 = client.get(f"/receipts/{atm_id}/iso20022", headers=HEADERS_PARENT)
    assert res400.status_code == 400


def test_message_follows_the_schema_rules():
    """Values the official pain.001.001.09 schema rejects never appear: charge bearer codes, lengths, BIC format."""
    from app.integrations.iso20022 import BIC_RE, CHARGE_BEARER

    for kind, bearer, purpose in (("tt_tuition", "DEBT", "EDUC"), ("tt_living", "SHAR", "FAMI")):
        _, _, xml = build_pain001_xml(draft_id="draft-0042-with-a-rather-long-identifier", kind=kind,
                                      amount_cny=Decimal("35200"), total_bdt=Decimal("612000"),
                                      rate_bdt_per_cny=Decimal("17.39"), payer_name="Demo Parent",
                                      payee_name="Demo University Finance Office", payee_account="6021",
                                      memo="x" * 300, timestamp=datetime(2026, 10, 18, 9, 0))
        root = ET.fromstring(xml.encode())
        tag = lambda n: [el for el in root.iter() if el.tag.endswith("}" + n)]  # noqa: E731
        assert tag("ChrgBr")[0].text == bearer and bearer in CHARGE_BEARER
        assert [el.text for el in tag("Cd") if el.text in ("EDUC", "FAMI")] == [purpose]
        assert all(len(el.text) <= 35 for n in ("MsgId", "PmtInfId", "EndToEndId", "Inf") for el in tag(n))
        assert all(len(el.text) <= 10 for el in tag("RgltryRptg")[0].iter() if el.tag.endswith("}Cd"))
        assert all(BIC_RE.match(el.text) for el in tag("BICFI"))
        assert validate_pain001(xml)["valid"], validate_pain001(xml)["errors"]
