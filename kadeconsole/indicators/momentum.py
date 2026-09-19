"""
indicators/momentum.py — RSI, MACD, Stochastic, Rate of Change.

Pure NumPy/Python. All functions take plain lists, return plain lists.
"""

from __future__ import annotations

from typing import Optional
import numpy as np
from kadeconsole.indicators.moving_averages import ema


def rsi(closes: list[float], period: int = 14) -> list[Optional[float]]:
    """
    Relative Strength Index (RSI).

    Uses Wilder's smoothing (same as standard RSI definition).
    Returns None for the first `period` values.
    """
    if len(closes) < period + 1:
        return [None] * len(closes)

    result: list[Optional[float]] = [None] * period
    arr = np.array(closes, dtype=float)
    deltas = np.diff(arr)

    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    # Initial averages (simple mean over first window)
    avg_gain = float(np.mean(gains[:period]))
    avg_loss = float(np.mean(losses[:period]))

    # First RSI value
    if avg_loss == 0:
        result.append(100.0)
    else:
        rs = avg_gain / avg_loss
        result.append(100.0 - 100.0 / (1 + rs))

    # Wilder smoothing for subsequent values
    for g, l in zip(gains[period:], losses[period:]):
        avg_gain = (avg_gain * (period - 1) + g) / period
        avg_loss = (avg_loss * (period - 1) + l) / period
        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(100.0 - 100.0 / (1 + rs))

    return result


def rsi_signal(rsi_value: Optional[float]) -> str:
    """Interpret RSI level as a human-readable signal."""
    if rsi_value is None:
        return "N/A"
    if rsi_value >= 70:
        return "Overbought"
    if rsi_value <= 30:
        return "Oversold"
    if rsi_value >= 60:
        return "Bullish"
    if rsi_value <= 40:
        return "Bearish"
    return "Neutral"


def macd(
    closes: list[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> dict[str, list[Optional[float]]]:
    """
    MACD (Moving Average Convergence/Divergence).

    Returns:
      {
        "macd":      [...],   # MACD line (fast EMA - slow EMA)
        "signal":    [...],   # Signal line (EMA of MACD)
        "histogram": [...],   # MACD - Signal
      }
    """
    fast_ema = ema(closes, fast)
    slow_ema = ema(closes, slow)

    macd_line: list[Optional[float]] = []
    for f, s in zip(fast_ema, slow_ema):
        if f is None or s is None:
            macd_line.append(None)
        else:
            macd_line.append(f - s)

    # Signal line: EMA of MACD line (using valid values only)
    valid_macd = [v for v in macd_line if v is not None]
    if len(valid_macd) < signal:
        signal_line: list[Optional[float]] = [None] * len(macd_line)
    else:
        # Embed back into full-length list
        none_prefix = macd_line.index(next(v for v in macd_line if v is not None))
        sig_vals = ema(valid_macd, signal)
        signal_line = [None] * none_prefix + [None] * (signal - 1) + sig_vals[signal - 1:]
        # Pad to full length if needed
        while len(signal_line) < len(macd_line):
            signal_line.append(None)

    histogram: list[Optional[float]] = []
    for m, s in zip(macd_line, signal_line):
        if m is None or s is None:
            histogram.append(None)
        else:
            histogram.append(m - s)

    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}


def stochastic(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    k_period: int = 14,
    d_period: int = 3,
) -> dict[str, list[Optional[float]]]:
    """
    Stochastic Oscillator (%K and %D).

    %K = (Close - Lowest Low) / (Highest High - Lowest Low) * 100
    %D = SMA of %K over d_period
    """
    n = len(closes)
    k_vals: list[Optional[float]] = [None] * (k_period - 1)

    for i in range(k_period - 1, n):
        lo = min(lows[i - k_period + 1 : i + 1])
        hi = max(highs[i - k_period + 1 : i + 1])
        span = hi - lo
        k_vals.append(((closes[i] - lo) / span * 100) if span != 0 else 50.0)

    # %D = rolling mean of %K
    valid_k = [v for v in k_vals if v is not None]
    d_vals_raw: list[Optional[float]] = [None] * (len(k_vals) - len(valid_k))
    for i in range(len(valid_k)):
        if i < d_period - 1:
            d_vals_raw.append(None)
        else:
            d_vals_raw.append(float(np.mean(valid_k[i - d_period + 1 : i + 1])))

    return {"k": k_vals, "d": d_vals_raw}


def rate_of_change(closes: list[float], period: int = 12) -> list[Optional[float]]:
    """
    Rate of Change (ROC).

    ROC = (Close_t - Close_{t-n}) / Close_{t-n} * 100
    """
    result: list[Optional[float]] = [None] * period
    for i in range(period, len(closes)):
        prev = closes[i - period]
        if prev and prev != 0:
            result.append((closes[i] - prev) / prev * 100)
        else:
            result.append(None)
    return result
