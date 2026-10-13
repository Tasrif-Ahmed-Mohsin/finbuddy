"""Published bank rates: Bangladeshi banks' own daily CNY selling rates (the "rate" half of a real price).

Source today: Eastern Bank PLC (EBL) publishes a daily exchange-rate sheet (PDF) at a fixed address, with a
CNY row (TT/OD selling = what a customer pays per yuan sent by bank transfer) and the bank's own standard
mid-rate. Banks label these sheets "indicative, not for transaction", so the app calls them "published"
rates, never a binding quote. Real payments and quotes the user enters stay the gold standard.

`scripts/fetch_bank_rates.py` downloads the sheets into `data/bank_rates.csv`. At runtime, `live` mode also
tries today's sheet (short timeout, cached); any failure falls back to the saved file.
"""
from __future__ import annotations

import csv
import io
import os
import re
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
RATES_CSV = DATA_DIR / "bank_rates.csv"
EBL_URL = "https://www.ebl.com.bd/assets/other/exchange/Exchange_Rate_{d:%d}_{d:%B}_{d:%Y}.pdf"
MAX_PDF_BYTES = 2_000_000  # the sheets are ~180 KB; anything bigger is not a rate sheet
FIELDS = ["date", "bank_id", "cny_tt_selling", "cny_bc_selling", "cny_tt_buying", "cny_bank_mid", "usd_tt_selling", "source_url"]

_SPOT = re.compile(r"^\s*([\d.]+)\s+([\d.]+)\s+{cur}\s+([\d.]+)", re.MULTILINE)
_MID = re.compile(r"CNY\s+([\d.]+)\s*$", re.MULTILINE)
# Two layouts seen: "20 August 2026" and "Thursday, September 17, 2026".
_DATE = re.compile(r"Effective Date:\s*(?:[A-Za-z]+,\s*)?(\d{1,2} [A-Za-z]+ \d{4}|[A-Za-z]+ \d{1,2}, \d{4})")


@dataclass(frozen=True)
class PublishedRate:
    date: str
    bank_id: str
    cny_tt_selling: Decimal  # BDT per CNY, bank transfer (TT/OD) selling
    cny_bc_selling: Decimal
    cny_tt_buying: Decimal
    cny_bank_mid: Decimal  # the bank's own "standard mid rate"
    usd_tt_selling: Decimal
    source_url: str

    @property
    def markup_vs_bank_mid_pct(self) -> Decimal:
        return (self.cny_tt_selling / self.cny_bank_mid - 1) * 100

    def to_row(self) -> dict:
        return {k: str(getattr(self, k)) for k in FIELDS}

    @classmethod
    def from_row(cls, r: dict) -> "PublishedRate":
        return cls(r["date"], r["bank_id"], Decimal(r["cny_tt_selling"]), Decimal(r["cny_bc_selling"]),
                   Decimal(r["cny_tt_buying"]), Decimal(r["cny_bank_mid"]), Decimal(r["usd_tt_selling"]), r["source_url"])


class SheetError(ValueError):
    pass


def parse_ebl_sheet(text: str, source_url: str = "") -> PublishedRate:
    """Parse the text of an EBL exchange-rate sheet. Raises SheetError if anything looks wrong."""
    m = _DATE.search(text)
    if not m:
        raise SheetError("no effective date")
    raw = m.group(1)
    when = datetime.strptime(raw, "%B %d, %Y" if "," in raw else "%d %B %Y").date()
    cny = re.compile(_SPOT.pattern.replace("{cur}", "CNY"), re.MULTILINE).search(text)
    usd = re.compile(_SPOT.pattern.replace("{cur}", "USD"), re.MULTILINE).search(text)
    mid = _MID.search(text)
    if not (cny and usd and mid):
        raise SheetError("CNY, USD or mid-rate row not found")
    bc, tt, buy = (Decimal(x) for x in cny.groups())
    bank_mid = Decimal(mid.group(1))
    # Sanity: buying < mid < selling, and the spread is plausible (protects against a changed layout).
    if not (buy < bank_mid < tt and Decimal("10") < bank_mid < Decimal("40") and tt / bank_mid < Decimal("1.05")):
        raise SheetError(f"implausible CNY row: selling {tt}, mid {bank_mid}, buying {buy}")
    return PublishedRate(when.isoformat(), "ebl", tt, bc, buy, bank_mid, Decimal(usd.group(2)), source_url)


def pdf_text(data: bytes) -> str:
    """Text of a downloaded PDF (untrusted input: size- and page-limited, parsed in memory, never executed)."""
    if not data.startswith(b"%PDF-") or len(data) > MAX_PDF_BYTES:
        raise SheetError("not a rate-sheet PDF")
    from pypdf import PdfReader  # imported lazily: only the fetcher and live mode need it

    reader = PdfReader(io.BytesIO(data))
    if len(reader.pages) > 5:
        raise SheetError("too many pages for a rate sheet")
    return "\n".join(p.extract_text(extraction_mode="layout") or "" for p in reader.pages)


def fetch_ebl(day: date, timeout: float = 8.0) -> PublishedRate:
    import httpx

    url = EBL_URL.format(d=day)
    r = httpx.get(url, timeout=timeout, follow_redirects=False, headers={"User-Agent": "Sathi student-finance research"})
    if r.status_code != 200:
        raise SheetError(f"HTTP {r.status_code}")
    rate = parse_ebl_sheet(pdf_text(r.content), url)
    if rate.date != day.isoformat():
        raise SheetError(f"sheet is dated {rate.date}, not {day}")
    return rate


def load_rates(path: Path = RATES_CSV) -> list[PublishedRate]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return sorted((PublishedRate.from_row(r) for r in csv.DictReader(f)), key=lambda r: (r.bank_id, r.date))


def save_rates(rates: list[PublishedRate], path: Path = RATES_CSV) -> None:
    uniq = {(r.bank_id, r.date): r for r in rates}
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for key in sorted(uniq):
            w.writerow(uniq[key].to_row())


class BankRateStore:
    """Saved sheets + (live mode) today's sheet, fetched at most once an hour."""

    def __init__(self, mode: str | None = None, rates: list[PublishedRate] | None = None):
        self.mode = mode or os.environ.get("SATHI_FX_MODE", "live")
        self.rates = rates if rates is not None else load_rates()
        self._tried: dict[str, float] = {}

    def latest(self, bank_id: str, on_or_before: date | None = None) -> PublishedRate | None:
        if self.mode == "live":
            self._try_live(bank_id, date.today())
        cutoff = (on_or_before or date.max).isoformat()
        mine = [r for r in self.rates if r.bank_id == bank_id and r.date <= cutoff]
        return mine[-1] if mine else None

    def _try_live(self, bank_id: str, today: date) -> None:
        if bank_id != "ebl" or any(r.bank_id == bank_id and r.date == today.isoformat() for r in self.rates):
            return
        if time.time() - self._tried.get(bank_id, 0) < 3600:
            return
        self._tried[bank_id] = time.time()
        try:
            self.rates.append(fetch_ebl(today, timeout=4.0))
            self.rates.sort(key=lambda r: (r.bank_id, r.date))
        except Exception:  # network down or no sheet yet today: the saved history is used
            pass

    def history(self, bank_id: str, days: int = 400) -> list[PublishedRate]:
        since = (date.today() - timedelta(days=days)).isoformat()
        return [r for r in self.rates if r.bank_id == bank_id and r.date >= since]
