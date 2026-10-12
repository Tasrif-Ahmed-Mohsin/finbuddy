"""FX ranges: honest uncertainty instead of point predictions.

Exchange-rate *direction* is notoriously hard to forecast (Meese & Rogoff 1983: a random walk
beats most models out of sample). So we do not predict. We answer a different, useful question:

    "If I wait h days, how far could the rate plausibly move?"

Method: empirical quantiles of h-day log returns over a rolling window of history. The centre is the
random walk (today's rate); the width is learned from history. We then *check our own honesty* with a
coverage backtest: an 80% range should contain the realised rate about 80% of the time.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class RateRange:
    horizon_days: int
    spot: float
    low: float  # lower quantile of the rate after h days
    mid: float
    high: float
    level: float  # e.g. 0.8 for an 80% range
    n_samples: int

    def to_dict(self) -> dict:
        return {
            "horizon_days": self.horizon_days,
            "spot": round(self.spot, 6),
            "low": round(self.low, 6),
            "mid": round(self.mid, 6),
            "high": round(self.high, 6),
            "level": self.level,
            "n_samples": self.n_samples,
        }


def h_day_log_returns(rates: np.ndarray, h: int) -> np.ndarray:
    rates = np.asarray(rates, dtype=float)
    if h < 1 or len(rates) <= h:
        raise ValueError("need more history than the horizon")
    return np.log(rates[h:] / rates[:-h])


def rate_range(rates: np.ndarray, h: int, level: float = 0.8, window: int | None = 500) -> RateRange:
    """Range for the rate h days from the last observation."""
    rates = np.asarray(rates, dtype=float)
    hist = rates[-window:] if window else rates
    r = h_day_log_returns(hist, h)
    lo_q, hi_q = (1 - level) / 2, 1 - (1 - level) / 2
    spot = float(rates[-1])
    q_lo, q_mid, q_hi = np.quantile(r, [lo_q, 0.5, hi_q])
    return RateRange(h, spot, spot * float(np.exp(q_lo)), spot * float(np.exp(q_mid)), spot * float(np.exp(q_hi)), level, len(r))


def coverage_backtest(rates: np.ndarray, h: int, level: float = 0.8, window: int = 500, step: int = 5) -> dict:
    """Walk forward through history; at each point build the range from the past only, then check
    whether the realised rate h days later fell inside it. Returns the empirical coverage."""
    rates = np.asarray(rates, dtype=float)
    hits, total, widths = 0, 0, []
    for t in range(window + h, len(rates) - h, step):
        past = rates[t - window : t + 1]
        rr = rate_range(past, h, level, window=None)
        realised = rates[t + h]
        hits += int(rr.low <= realised <= rr.high)
        total += 1
        widths.append((rr.high - rr.low) / rr.spot)
    if total == 0:
        raise ValueError("not enough history for a backtest")
    return {
        "horizon_days": h,
        "nominal_level": level,
        "empirical_coverage": round(hits / total, 4),
        "tests": total,
        "mean_relative_width": round(float(np.mean(widths)), 6),
    }
