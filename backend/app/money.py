"""Money helpers. All money math uses Decimal, never float."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

TWO_PLACES = Decimal("0.01")


def D(value: object) -> Decimal:
    """Convert int/str/Decimal to Decimal. Floats go through str() to avoid binary noise."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(value)  # type: ignore[arg-type]


def q2(value: Decimal) -> Decimal:
    """Round to 2 decimal places, half-up (bank style)."""
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def ceil_div(numerator: Decimal, denominator: Decimal) -> int:
    """Ceiling division for positive Decimals, e.g. number of ATM withdrawals."""
    if numerator <= 0:
        return 0
    whole = int(numerator // denominator)
    return whole if whole * denominator == numerator else whole + 1
