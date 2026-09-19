"""
indicators/volatility.py — Bollinger Bands, ATR, Realized Volatility.
"""

from __future__ import annotations

from typing import Optional
import numpy as np
from kadeconsole.indicators.moving_averages import sma


def bollinger_bands(
    closes: list[float],
    window: int = 20,
    num_std: float = 2.0,
) -> dict[str, list[Optional[float]]]:
    """
    Bollinger Bands.

    Returns:
      {
        "middle": [...],   # SMA(window)
        "upper":  [...],   # middle + num_std * rolling_std
        "lower":  [...],   # middle - num_std * rolling_std
        "width":  [...],   # (upper - lower) / middle  (bandwidth %)
        "pct_b":  [...],   # (close - lower) / (upper - lower)
      }
    """
    mid = sma(closes, window)
    arr = np.array(closes, dtype=float)

    upper: list[Optional[float]] = []
    lower: list[Optional[float]] = []
    width: list[Optional[float]] = []
    pct_b: list[Optional[float]] = []

    for i, m in enumerate(mid):
        if m is None or i < window - 1:
            upper.append(None)
            lower.append(None)
            width.append(None)
            pct_b.append(None)
        else:
            std = float(np.std(arr[i - window + 1 : i + 1], ddof=0))
            u = m + num_std * std
            l = m - num_std * std
            upper.append(u)
            lower.append(l)
            span = u - l
            width.append((span / m * 100) if m else None)
            pct_b.append(((closes[i] - l) / span) if span else None)

    return {"middle": mid, "upper": upper, "lower": lower, "width": width, "pct_b": pct_b}


def atr(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int = 14,
) -> list[Optional[float]]:
    """
    Average True Range (ATR) using Wilder's smoothing.

    True Range = max(H-L, |H-C_prev|, |L-C_prev|)
    """
    if len(closes) < 2:
        return [None] * len(closes)

    tr_vals: list[float] = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        h, l, c_prev = highs[i], lows[i], closes[i - 1]
        tr_vals.append(max(h - l, abs(h - c_prev), abs(l - c_prev)))

    result: list[Optional[float]] = [None] * period
    if len(tr_vals) < period:
        return [None] * len(closes)

    # Seed with simple mean
    atr_val = float(np.mean(tr_vals[:period]))
    result.append(atr_val)

    for tr in tr_vals[period:]:
        atr_val = (atr_val * (period - 1) + tr) / period
        result.append(atr_val)

    return result


def realized_volatility(
    closes: list[float],
    window: int = 30,
    annualize: bool = True,
) -> list[Optional[float]]:
    """
    Rolling Realized (Historical) Volatility.

    Computed as rolling std of log returns, optionally annualized
    by multiplying by sqrt(252) (trading days per year).
    """
    if len(closes) < 2:
        return [None] * len(closes)

    arr = np.array(closes, dtype=float)
    log_returns = np.diff(np.log(arr))

    result: list[Optional[float]] = [None] * window  # first window bars invalid

    for i in range(window, len(log_returns) + 1):
        std = float(np.std(log_returns[i - window : i], ddof=1))
        vol = std * np.sqrt(252) * 100 if annualize else std * 100
        result.append(vol)

    return result
