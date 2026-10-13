"""Download Bangladeshi banks' published daily CNY rates into backend/app/data/bank_rates.csv.

Today: Eastern Bank PLC (EBL), whose daily exchange-rate sheet has a CNY row. Incremental: days already saved
are skipped; days without a sheet (weekends, holidays) are skipped quietly. Polite: one request at a time.

Usage:  python scripts/fetch_bank_rates.py                  (from 1 March 2026 to today)
        python scripts/fetch_bank_rates.py --since 2026-08-01
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.bank_rates import SheetError, fetch_ebl, load_rates, save_rates  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2026-03-01")
    ap.add_argument("--until", default=date.today().isoformat())
    ap.add_argument("--pause", type=float, default=0.4, help="seconds between requests")
    args = ap.parse_args()
    rates = load_rates()
    have = {(r.bank_id, r.date) for r in rates}
    day, end = date.fromisoformat(args.since), date.fromisoformat(args.until)
    added = skipped = 0
    while day <= end:
        if ("ebl", day.isoformat()) not in have:
            try:
                r = fetch_ebl(day)
                rates.append(r)
                added += 1
                print(f"{day}  EBL CNY TT selling {r.cny_tt_selling}  bank mid {r.cny_bank_mid}")
            except SheetError as e:
                skipped += 1
                print(f"{day}  no sheet ({e})")
            except Exception as e:  # network problems: keep what we have
                skipped += 1
                print(f"{day}  failed ({type(e).__name__})")
            time.sleep(args.pause)
        day += timedelta(days=1)
    save_rates(rates)
    print(f"added {added}, skipped {skipped}, total {len(load_rates())} saved sheets")
    return 0


if __name__ == "__main__":
    sys.exit(main())
