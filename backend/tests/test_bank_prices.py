"""Real bank prices: published daily rate sheets, published fee schedules, labels for every number."""
from datetime import date
from decimal import Decimal as D

import pytest
from fastapi.testclient import TestClient

from app.bank_rates import BankRateStore, PublishedRate, SheetError, parse_ebl_sheet, pdf_text
from app.engines.cost import tt_cost
from app.engines.cost_truth import field_payment_truth
from app.fx import FIXTURE, load_history
from app.main import create_app
from app.market import MidRates, build_market, fee_schedule, load_quote_config, student_file_fees

H = {"parent": {"Authorization": "Bearer demo-parent"}}

# Text extracted from Eastern Bank's real sheet of 20 Aug 2026 (rows trimmed to what the parser reads).
EBL_20_AUG = """Eastern Bank PLC.
Exchange Rate
Effective Date:                20 August 2026
             SPOT SELLING                         CURRENCY                                                  SPOT BUYING
       Former BC & TT/OD Rate                                                          Former T.T Clean/T.T Doc/OD Sight/OD Transfer
       122.7500                122.7500                 USD               121.7500            121.7500                  121.7500                    121.7500
       145.1887                145.1887                 EUR               140.3291            140.3291                  140.3291                    140.3291
        18.3659                 18.3659                CNY                 18.0000             18.0000                   18.0000                     18.0000
        1.2904                   1.2904                 INR                1.2664              1.2664                     1.2664                      1.2664
       1 ACU DOLLAR= 1 US DOLLAR                                      NOK                      9.21            13.25               CNY                  18.1392
                                                                                                                                   INR                  1.2748
"""
CFG = load_quote_config()


def sheet(day: str, selling: str, mid: str) -> PublishedRate:
    return PublishedRate(day, "ebl", D(selling), D(selling), D(mid) - D("0.2"), D(mid), D("122.75"), "test")


# ---- published rate sheets -----------------------------------------------------------------------
def test_parses_a_real_ebl_sheet():
    r = parse_ebl_sheet(EBL_20_AUG, "u")
    assert (r.date, r.cny_tt_selling, r.cny_tt_buying, r.cny_bank_mid, r.usd_tt_selling) == (
        "2026-08-20", D("18.3659"), D("18.0000"), D("18.1392"), D("122.7500"))
    assert D("1.2") < r.markup_vs_bank_mid_pct < D("1.3")


def test_both_date_layouts_are_understood():
    other = EBL_20_AUG.replace("20 August 2026", "Thursday, August 20, 2026")
    assert parse_ebl_sheet(other).date == "2026-08-20"


@pytest.mark.parametrize("broken", [
    EBL_20_AUG.replace("Effective Date:", "Date:"),                    # layout changed
    EBL_20_AUG.replace("CNY                 18.0000", "XXX 18.0000"),  # CNY row missing
    EBL_20_AUG.replace("18.3659", "17.9000"),                          # selling below the mid: wrong column
    EBL_20_AUG.replace("18.3659", "19.9000"),                          # 10% spread: not plausible
])
def test_a_changed_or_wrong_sheet_is_rejected_not_guessed(broken):
    with pytest.raises(SheetError):
        parse_ebl_sheet(broken)


def test_downloaded_files_must_be_small_pdfs():
    with pytest.raises(SheetError):
        pdf_text(b"<html>not a pdf</html>")
    with pytest.raises(SheetError):
        pdf_text(b"%PDF-" + b"0" * 2_100_000)


def test_live_mode_falls_back_to_saved_sheets_and_does_not_hammer_the_bank(monkeypatch):
    calls = []

    def boom(day, timeout=8.0):
        calls.append(day)
        raise OSError("offline")

    monkeypatch.setattr("app.bank_rates.fetch_ebl", boom)
    store = BankRateStore(mode="live", rates=[sheet("2026-10-01", "18.50", "18.33")])
    assert store.latest("ebl").date == "2026-10-01"
    store.latest("ebl")
    assert len(calls) == 1  # at most one live attempt per hour


def test_saved_history_is_real_and_plausible():
    rates = BankRateStore(mode="offline").history("ebl", 2000)
    assert len(rates) >= 20
    assert all(D("0") < r.markup_vs_bank_mid_pct < D("3") for r in rates)


# ---- published fees ------------------------------------------------------------------------------------
def test_ebl_fee_schedule_from_the_published_pdfs():
    f = fee_schedule("ebl", CFG["fees"])
    lines = dict(f.lines(D("113000")))  # a monthly living transfer: commission tier ৳100,001–5,00,000
    assert lines["Bank commission"] == D("200") and lines["Correspondent bank charge"] == D("2500")
    assert lines["SWIFT charge"] == D("500") and lines["VAT 15% on fees"] == D("480")
    assert f.total(D("113000")) == D("3680") and f.total(D("650000")) == D("3795")  # tuition: ৳300 tier
    assert f.confidence == "secondary"  # correspondent + SWIFT come from EBL's SME schedule


def test_unpublished_fees_are_never_invented():
    assert fee_schedule("southeast", CFG["fees"]) is None  # correspondent charge not published
    assert fee_schedule("prime", CFG["fees"]) is None  # no transfer fees in the student schedule
    brac = fee_schedule("brac", CFG["fees"])
    assert brac.confidence == "assumption" and brac.total(D("113000")) == D("3680")  # labelled peer assumption


def test_student_file_fees_include_vat():
    by = {x["bank_id"]: x for x in student_file_fees(CFG["fees"])}
    assert (by["ebl"]["opening_bdt"], by["ebl"]["renewal_bdt"]) == ("8625", "7475")  # as on EBL's Student File page
    assert (by["prime"]["opening_bdt"], by["southeast"]["renewal_bdt"]) == ("6900", "4025")
    assert by["brac"]["opening_bdt"] is None and by["brac"]["confidence"] == "field"


# ---- market: every price says where it comes from ---------------------------------------------------------
def test_published_rate_is_used_as_is_on_the_same_day_with_a_real_mid():
    store = BankRateStore(mode="offline", rates=[sheet("2026-10-12", "18.5895", "18.4220")])
    real_mid = MidRates(D("123.55"), D("6.71"), "2026-10-12", "real", sample=False)
    m = build_market(real_mid, CFG, published=store)
    ebl = m.quote("ebl-published")
    assert ebl.basis == "published" and ebl.bdt_per_cny == D("18.5895") and "2026-10-12" in ebl.source


def test_with_a_test_rate_the_banks_own_markup_is_applied():
    store = BankRateStore(mode="offline", rates=[sheet("2026-10-12", "18.5895", "18.4220")])
    ebl = build_market(FIXTURE, CFG, published=store).quote("ebl-published")
    assert ebl.bdt_per_cny == (FIXTURE.bdt_per_cny * D("18.5895") / D("18.4220")).quantize(D("0.0001"))


def test_no_sheet_means_no_ebl_price_and_a_note():
    m = build_market(FIXTURE, CFG, published=BankRateStore(mode="offline", rates=[]))
    assert all(q.quote_id != "ebl-published" for q in m.quotes) and m.notes


def test_quality_labels_and_no_unnamed_estimates():
    m = build_market(FIXTURE, CFG, published=BankRateStore(mode="offline"))
    assert {q.basis for q in m.quotes} == {"published", "real_payment"}
    assert not any(q.sample for q in m.quotes)
    assert m.quality == "mixed"  # BRAC's fees are an assumption until its schedule is found


def test_transfer_cost_itemises_published_fees():
    q = build_market(FIXTURE, CFG, published=BankRateStore(mode="offline")).quote("ebl-published")
    c = tt_cost(D("6000"), q, FIXTURE.bdt_per_cny)
    labels = [line.label for line in c.lines]
    assert {"Bank commission", "Correspondent bank charge", "SWIFT charge", "VAT 15% on fees"} <= set(labels)
    assert sum(line.bdt for line in c.lines) == c.total_bdt
    assert c.by_kind("fee") == q.fee_total(D("6000") * q.bdt_per_cny)


def test_cost_truth_compares_the_real_payment_with_published_sheets():
    fp = CFG["field_payments"][0]
    store = [sheet("2026-08-20", "18.3659", "18.1392"), sheet("2026-09-10", "18.4400", "18.2000")]
    t = field_payment_truth(fp, load_history(), store)
    pub = t["published_same_window"]
    assert pub["sheets"] == 2 and pub["avg"] == "18.40" and pub["paid_below_every_sheet"] is True
    assert "one-time Student File opening fee" in t["fee_note"]


# ---- API --------------------------------------------------------------------------------------------
@pytest.fixture
def client():
    return TestClient(create_app(audit_path=None, llm=None))


def test_prices_endpoint_shows_sources_for_every_number(client):
    r = client.get("/market/prices").json()
    ebl = next(q for q in r["quotes"] if q["quote_id"] == "ebl-published")
    assert ebl["basis"] == "published" and "rate sheet" in ebl["rate_source"]
    assert ebl["fee_example"]["total_bdt"] == "3565.00"  # ৳1,00,000: (100 + 2,500 + 500) + 15% VAT
    assert {x["bank"] for x in r["student_file_fees"]} >= {"Eastern Bank (EBL)", "Prime Bank", "Southeast Bank"}
    assert len(r["published_history"]) >= 20


def test_tuition_options_carry_their_basis(client):
    p = client.post("/plan/tuition", json={"amount_cny": "35200", "deadline": "2026-11-15"}, headers=H["parent"]).json()
    assert {o["basis"] for o in p["options"]} == {"published", "real_payment"}
    assert all(any(line["label"] == "Correspondent bank charge" for line in o["lines"]) for o in p["options"])
    assert date.fromisoformat(next(o for o in p["options"] if o["basis"] == "published")["rate_date"]) >= date(2026, 3, 1)


# ---- rate watch: the bank's price vs the market, and whether timing it pays ---------------------------
def _sheet(day: str, tt: str) -> PublishedRate:
    return PublishedRate(day, "ebl", D(tt), D(tt), D(tt), D(tt), D("122"), "test")


def test_rate_watch_on_the_saved_sheets():
    from app.bank_rates import load_rates
    from app.engines.rate_watch import rate_watch
    rw = rate_watch(load_rates(), load_history(), "ebl", date(2026, 10, 12))
    assert rw["sheets"] >= 130 and 0.5 < rw["markup"]["median"] < 1.5 and rw["markup"]["p25"] <= rw["markup"]["p75"]
    assert rw["latest"]["date"] <= "2026-10-12" and rw["latest"]["position"] in {"high", "usual", "low"}
    bt = rw["timing_backtest"]
    # the honest finding: waiting for a "better day" saves next to nothing compared with a transfer's fees
    assert bt["cases"] > 20 and abs(bt["saving_per_lakh_bdt"]) < 200


def test_rate_watch_backtest_counts_real_savings():
    from app.engines.rate_watch import rate_watch
    from app.fx import FxPoint
    days = [f"2026-05-{d:02d}" for d in range(1, 21)]
    fx = [FxPoint(d, 120.0, 6.0) for d in days]  # market: ৳20.00 every day
    tts = ["20.2", "20.2", "20.4", "20.1", "20.2", "20.2", "20.2", "20.2", "20.4", "20.4", "20.4", "20.4",
           "20.2", "20.2", "20.2", "20.2", "20.2", "20.2", "20.2", "20.2"]
    rw = rate_watch([_sheet(d, t) for d, t in zip(days, tts)], fx, "ebl")
    bt = rw["timing_backtest"]
    assert rw["markup"]["median"] == 1.0 and bt["cases"] == 5  # every 2.0% day is in the top quarter
    assert bt["cheaper_cases"] == 4  # only after day 9 are the next three sheets all still at 20.4
    assert rate_watch([_sheet(d, t) for d, t in zip(days[:5], tts)], fx, "ebl") is None  # too few sheets: no claims


def test_prices_endpoint_includes_the_rate_watch(client):
    rw = client.get("/market/prices", headers={"Authorization": "Bearer demo-parent"}).json()["rate_watch"]
    assert rw["bank_id"] == "ebl" and len(rw["series"]) == rw["sheets"]
