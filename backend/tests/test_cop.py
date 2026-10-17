"""Automated tests for Confirmation of Payee (CoP) under UK PSR & EU VoP standards.

Verifies:
1. Exact name match against receiving bank records.
2. Close match detection for typos and institutional aliases.
3. No-match detection stopping Authorised Push Payment (APP) scams.
4. Integration with compliance checks on payment drafts.
5. REST endpoint POST /security/cop/verify.
"""
from decimal import Decimal
import pytest
from starlette.testclient import TestClient

from app.main import create_app
from app.security.cop import ConfirmationOfPayeeService, CopStatus


def test_cop_exact_match():
    cop = ConfirmationOfPayeeService()
    
    # Exact registered legal name
    res = cop.verify_payee("univ_demo", "Demo University Finance Office")
    assert res.status == CopStatus.MATCH
    assert res.match_score == 1.0
    assert res.app_scam_risk == "low"
    assert "BKCHCNBJXXX" in res.bic


def test_cop_alias_match():
    cop = ConfirmationOfPayeeService()
    
    # University recognized alias
    res = cop.verify_payee("univ_demo", "Demo University")
    assert res.status == CopStatus.MATCH
    assert res.app_scam_risk == "low"


def test_cop_close_match_with_typo():
    cop = ConfirmationOfPayeeService()
    
    # Minor misspelling: "Demo Univ Finace"
    res = cop.verify_payee("univ_demo", "Demo Univ Finace")
    assert res.status in (CopStatus.MATCH, CopStatus.CLOSE_MATCH)
    assert res.app_scam_risk in ("low", "medium")
    assert "Demo University Finance Office" in res.registered_name


def test_cop_no_match_app_fraud_detection():
    cop = ConfirmationOfPayeeService()
    
    # Victim is told to pay "Demo University Tuition", but account is agent_x (Shenzhen Apex Trading Co)
    res = cop.verify_payee("agent_x", "Demo University Tuition")
    assert res.status == CopStatus.NO_MATCH
    assert res.app_scam_risk == "critical"
    assert "Shenzhen Apex Trading Co" in res.registered_name
    assert "Authorised Push Payment" in res.reason


def test_cop_draft_checks_and_endpoint():
    app = create_app(audit_path=None)
    client = TestClient(app)
    headers = {"Authorization": "Bearer demo-parent"}
    
    # 1. Test standalone verification endpoint
    verify_res = client.post("/security/cop/verify", headers=headers, json={
        "payee_id": "univ_demo",
        "intended_name": "Demo University",
    })
    assert verify_res.status_code == 200
    data = verify_res.json()
    assert data["status"] == "match"
    assert data["app_scam_risk"] == "low"
    assert data["account_type"] == "business"
    
    # 2. Test draft creation includes passing CoP check
    draft_res = client.post("/drafts", headers=headers, json={
        "kind": "tt_tuition",
        "amount_cny": 35200.0,
        "payee_id": "univ_demo",
    })
    assert draft_res.status_code == 200
    draft_data = draft_res.json()
    
    cop_checks = [c for c in draft_data["checks"] if c["id"] == "cop_verification"]
    assert len(cop_checks) == 1
    assert cop_checks[0]["passed"] is True
    assert "MATCHED" in cop_checks[0]["message"]
    assert "cop_verification" in draft_data
    assert draft_data["cop_verification"]["status"] == "match"
