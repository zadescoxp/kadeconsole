"""
indicators/moving_averages.py — SMA, EMA, VWAP, and crossover detection.

Pure NumPy/Python — no external TA libraries required.
All functions accept plain Python lists and return plain lists
(or None for insufficient data).
"""

from __future__ import annotations

from typing import Optional
import numpy as np


def sma(values: list[float], window: int) -> list[Optional[float]]:
    """
    Simple Moving Average.

    Returns a list of the same length as `values`.
    First `window-1` elements are None (insufficient data).
    """
    result: list[Optional[float]] = [None] * len(values)
    arr = np.array(values, dtype=float)
    for i in range(window - 1, len(arr)):
        result[i] = float(np.mean(arr[i - window + 1 : i + 1]))
    return result


def ema(values: list[float], window: int) -> list[Optional[float]]:
    """
    Exponential Moving Average (Wilder smoothing: multiplier = 2/(n+1)).

    Returns None for initial values before the first full window.
    """
    if len(values) < window:
        return [None] * len(values)

    result: list[Optional[float]] = [None] * (window - 1)
    k = 2.0 / (window + 1)

    # Seed with simple mean of first window
    seed = float(np.mean(values[:window]))
    result.append(seed)
    prev = seed

    for v in values[window:]:
        cur = v * k + prev * (1 - k)
        result.append(float(cur))
        prev = cur

    return result


def wma(values: list[float], window: int) -> list[Optional[float]]:
    """Weighted Moving Average (linear weights, most recent = highest weight)."""
    result: list[Optional[float]] = [None] * len(values)
    weights = np.arange(1, window + 1, dtype=float)
    denom = weights.sum()
    arr = np.array(values, dtype=float)
    for i in range(window - 1, len(arr)):
        result[i] = float(np.dot(arr[i - window + 1 : i + 1], weights) / denom)
    return result


def vwap(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    volumes: list[float],
) -> list[Optional[float]]:
    """
    Volume-Weighted Average Price (cumulative, reset per session).

    For daily bars this is a single-session VWAP (running from bar 0).
    Typical price = (H + L + C) / 3.
    """
    if not (highs and lows and closes and volumes):
        return []

    result: list[float] = []
    cum_tpv = 0.0
    cum_vol = 0.0

    for h, l, c, v in zip(highs, lows, closes, volumes):
        tp = (h + l + c) / 3.0
        vol = float(v)
        cum_tpv += tp * vol
        cum_vol += vol
        result.append(cum_tpv / cum_vol if cum_vol else c)

    return result


def golden_cross(sma_fast: list[Optional[float]], sma_slow: list[Optional[float]]) -> Optional[bool]:
    """
    Detect golden cross / death cross between two MAs.

    Returns:
        True  → golden cross (fast just crossed above slow)
        False → death cross (fast just crossed below slow)
        None  → no recent crossover (last two bars both same direction)
    """
    # Need at least last 2 bars of both series
    valid_pairs = [
        (f, s)
        for f, s in zip(sma_fast[-3:], sma_slow[-3:])
        if f is not None and s is not None
    ]
    if len(valid_pairs) < 2:
        return None

    prev_f, prev_s = valid_pairs[-2]
    curr_f, curr_s = valid_pairs[-1]

    if prev_f <= prev_s and curr_f > curr_s:
        return True   # golden cross
    if prev_f >= prev_s and curr_f < curr_s:
        return False  # death cross
    return None       # no crossover


def ma_position(price: float, ma_value: Optional[float]) -> Optional[str]:
    """Return 'above' or 'below' relative to a moving average."""
    if ma_value is None:
        return None
    return "above" if price > ma_value else "below"
