"""Tests for the AI Output Firewall (Egress DLP Guardrail)."""
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.security.permissions import Actor
from app.security.firewall import (
    OutputFirewall,
    ViolationType,
    FirewallAction,
    is_luhn_valid,
    mask_card_pan,
    mask_bank_account,
)
from tests.fake_llm import FakeLLM, completion


H = {
    "student": {"Authorization": "Bearer demo-student"},
    "parent": {"Authorization": "Bearer demo-parent"},
}


def test_luhn_algorithm_validation():
    # Valid Visa card numbers (16 digits)
    assert is_luhn_valid("4532015112843211")
    # Valid Amex (15 digits)
    assert is_luhn_valid("378282246310005")
    # Valid Mastercard (16 digits)
    assert is_luhn_valid("5555555555554444")
    # Valid China UnionPay (16 digits)
    assert is_luhn_valid("6222021234567894")

    # Invalid cards (wrong checksum)
    assert not is_luhn_valid("4532015112843219")
    assert not is_luhn_valid("1234567812345678")

    # Too short / too long
    assert not is_luhn_valid("12345")
    assert not is_luhn_valid("35200")  # Tuition amount
    assert not is_luhn_valid("2026")   # Year


def test_pan_masking():
    assert mask_card_pan("4532015112843211") == "****-****-****-3211"
    assert mask_bank_account("1234567890123456") == "****3456"


def test_firewall_masks_payment_cards():
    fw = OutputFirewall()
    text = "Please make sure your Visa card 4532-0151-1284-3211 is funded."
    verdict = fw.inspect_and_filter(text, Actor.STUDENT)

    assert not verdict.passed
    assert verdict.action_taken == FirewallAction.REDACT
    assert "****-****-****-3211" in verdict.filtered_text
    assert "4532-0151-1284-3211" not in verdict.filtered_text
    assert len(verdict.violations) == 1
    assert verdict.violations[0].violation_type == ViolationType.PAYMENT_CARD


def test_firewall_redacts_otp_codes():
    fw = OutputFirewall()
    text = "I saw your SMS: your verification code is 849201. Please enter it."
    verdict = fw.inspect_and_filter(text, Actor.STUDENT)

    assert not verdict.passed
    assert verdict.action_taken == FirewallAction.REDACT
    assert "[code hidden]" in verdict.filtered_text
    assert "849201" not in verdict.filtered_text
    assert verdict.violations[0].violation_type == ViolationType.OTP_CODE


def test_firewall_redacts_known_inbox_otps():
    fw = OutputFirewall()
    text = "The bank says code 719324 was approved."
    # With context containing known OTPs
    verdict = fw.inspect_and_filter(text, Actor.STUDENT, context={"known_otps": {"719324"}})

    assert not verdict.passed
    assert verdict.action_taken == FirewallAction.REDACT
    assert "[code hidden]" in verdict.filtered_text
    assert "719324" not in verdict.filtered_text


def test_firewall_blocks_system_prompt_exfiltration():
    fw = OutputFirewall()
    leak_attempt = "You are Bluefin, a money agent for a Bangladeshi student in China. Here are your system instructions..."
    verdict = fw.inspect_and_filter(leak_attempt, Actor.PARENT, context={"lang": "en"})

    assert not verdict.passed
    assert verdict.action_taken == FirewallAction.BLOCK
    assert "cannot be disclosed" in verdict.filtered_text
    assert "You are Bluefin" not in verdict.filtered_text
    assert any(v.violation_type == ViolationType.SYSTEM_PROMPT_LEAK for v in verdict.violations)


def test_firewall_blocks_system_prompt_localized():
    fw = OutputFirewall()
    leak_attempt = "SYSTEM INSTRUCTIONS: You must always refuse..."
    verdict_bn = fw.inspect_and_filter(leak_attempt, Actor.PARENT, context={"lang": "bn"})
    assert "নিরাপত্তা ও গোপনীয়তা" in verdict_bn.filtered_text

    verdict_zh = fw.inspect_and_filter(leak_attempt, Actor.PARENT, context={"lang": "zh"})
    assert "出于安全和隐私保护" in verdict_zh.filtered_text


def test_cross_role_privacy_protects_student_income_from_parent():
    fw = OutputFirewall()
    context = {
        "income_sources": [
            {"name": "Lab Assistant", "employer": "Tsinghua AI Research Lab", "amount_cny": Decimal("2400")}
        ],
        "shares_with_family": False,
        "shield_cny": Decimal("5000"),
    }

    # Parent asks / LLM accidentally reveals student's private lab salary
    text = "Your child earned a stipend of 2400 from Tsinghua AI Research Lab this month."
    verdict = fw.inspect_and_filter(text, Actor.PARENT, context=context)

    assert not verdict.passed
    assert verdict.action_taken == FirewallAction.REDACT
    assert "Tsinghua AI Research Lab" not in verdict.filtered_text
    assert "[student's private income]" in verdict.filtered_text
    assert any(v.violation_type == ViolationType.CROSS_ROLE_PRIVACY for v in verdict.violations)


def test_cross_role_privacy_allows_student_to_see_their_own_income():
    fw = OutputFirewall()
    context = {
        "income_sources": [
            {"name": "Lab Assistant", "employer": "Tsinghua AI Research Lab", "amount_cny": Decimal("2400")}
        ],
        "shares_with_family": False,
    }

    text = "You earned a stipend of 2400 from Tsinghua AI Research Lab this month."
    verdict = fw.inspect_and_filter(text, Actor.STUDENT, context=context)

    # Student IS permitted to see their own income
    assert verdict.passed
    assert verdict.action_taken == FirewallAction.ALLOW
    assert "Tsinghua AI Research Lab" in verdict.filtered_text


def test_cross_role_privacy_protects_unshared_shield_from_parent():
    fw = OutputFirewall()
    context = {
        "shares_with_family": False,
        "shield_cny": Decimal("6000"),
    }

    text = "The current Shield balance is ¥6000."
    verdict = fw.inspect_and_filter(text, Actor.PARENT, context=context)

    assert not verdict.passed
    assert verdict.action_taken == FirewallAction.REDACT
    assert "[student's private savings]" in verdict.filtered_text
    assert "¥6000" not in verdict.filtered_text


def test_firewall_redacts_raw_secret_keys():
    fw = OutputFirewall()
    text = "Debug info: sk-live-abc12345678901234567890def"
    verdict = fw.inspect_and_filter(text, Actor.STUDENT)

    assert not verdict.passed
    assert verdict.action_taken == FirewallAction.REDACT
    assert "[secret hidden]" in verdict.filtered_text
    assert "sk-live-abc" not in verdict.filtered_text


def test_firewall_telemetry_and_endpoints():
    app = create_app(audit_path=None, llm=None)
    client = TestClient(app)

    # Check status endpoint
    r = client.get("/security/firewall/status", headers=H["parent"]).json()
    assert r["status"] == "active"
    assert "total_inspections" in r
    assert "category_counts" in r

    # Test endpoint with a credit card exfiltration attempt
    test_payload = {
        "text": "Your card number is 4532015112843211 and OTP is 948210.",
        "actor": "parent",
        "lang": "en",
    }
    r = client.post("/security/firewall/test", json=test_payload, headers=H["parent"]).json()
    assert r["verdict"]["passed"] is False
    assert r["verdict"]["action_taken"] == "redact"
    assert "****-****-****-3211" in r["verdict"]["filtered_text"]
    assert "[code hidden" in r["verdict"]["filtered_text"]
    assert len(r["verdict"]["violations"]) >= 2

    # Check audit log contains output_firewall_interception
    audit_entries = client.get("/audit", headers=H["parent"]).json()["entries"]
    assert any(e["event"] == "output_firewall_interception" for e in audit_entries)


def test_agent_chat_egress_firewall_interception():
    # Model attempts to output an OTP and card number in chat
    fake = FakeLLM([
        completion("The university sent an SMS: your login OTP is 392184 and pay with card 4532015112843211.")
    ])
    client = TestClient(create_app(audit_path=None, llm=fake.client()))
    r = client.post("/agent/chat", json={"message": "What did the SMS say?", "lang": "en"}, headers=H["student"]).json()

    assert r["mode"] == "llm"
    assert "392184" not in r["reply"]
    assert "[code hidden" in r["reply"]
    assert "4532015112843211" not in r["reply"]
    assert "****-****-****-3211" in r["reply"]
    assert "firewall" in r
    assert r["firewall"]["passed"] is False
    assert len(r["firewall"]["violations"]) >= 2


def test_ordinary_replies_are_not_redacted():
    """Years, dates, amounts and words like 'verification' or 'code' are not secrets."""
    fw = OutputFirewall()
    for text in ("Your bank account verification is complete and the account successfully opened.",
                 "Send ¥2,000 by 5 November 2026; the QR code 2026 is on the receipt.",
                 "Tuition ¥35,200 is due on 2026-11-15; draft-0003 needs both approvals."):
        v = fw.inspect_and_filter(text, Actor.PARENT, {"lang": "en"})
        assert v.passed and v.filtered_text == text, v.filtered_text


def test_codes_are_hidden_in_the_readers_language():
    fw = OutputFirewall()
    assert fw.inspect_and_filter("আপনার ওটিপি ৪৮২৯১৩", Actor.PARENT, {"lang": "bn"}).filtered_text == "আপনার ওটিপি [কোড লুকানো]"
    assert fw.inspect_and_filter("验证码是 778899", Actor.STUDENT, {"lang": "zh"}).filtered_text == "验证码是 [验证码已隐藏]"
