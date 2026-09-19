"""
indicators/volume.py — OBV, volume metrics, and spike detection.
"""

from __future__ import annotations

from typing import Optional
import numpy as np
from kadeconsole.indicators.moving_averages import sma


def obv(closes: list[float], volumes: list[float]) -> list[float]:
    """
    On-Balance Volume (OBV).

    OBV accumulates volume: +vol on up-close days, -vol on down-close days.
    """
    if not closes or not volumes:
        return []

    result = [0.0]
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            result.append(result[-1] + volumes[i])
        elif closes[i] < closes[i - 1]:
            result.append(result[-1] - volumes[i])
        else:
            result.append(result[-1])
    return result


def volume_ma(volumes: list[float], window: int = 20) -> list[Optional[float]]:
    """Rolling volume moving average."""
    return sma(volumes, window)


def volume_ratio(volumes: list[float], window: int = 20) -> list[Optional[float]]:
    """
    Volume ratio: current volume / 20D average volume.

    Values > 2.0 indicate a volume spike (>2× average).
    """
    avg = sma(volumes, window)
    result: list[Optional[float]] = []
    for v, a in zip(volumes, avg):
        if a is None or a == 0:
            result.append(None)
        else:
            result.append(v / a)
    return result


def detect_volume_spike(
    volumes: list[float],
    window: int = 20,
    threshold: float = 2.0,
) -> Optional[dict]:
    """
    Detect if the most recent bar has an anomalous volume spike.

    Returns a dict with spike info, or None if no spike.
    """
    if len(volumes) < window + 1:
        return None

    ratios = volume_ratio(volumes, window)
    if not ratios or ratios[-1] is None:
        return None

    ratio = ratios[-1]
    if ratio >= threshold:
        avg = float(np.mean(volumes[-window - 1 : -1]))
        return {
            "ratio": round(ratio, 2),
            "current_volume": volumes[-1],
            "avg_volume": avg,
            "description": f"{ratio:.1f}× average volume — significant spike",
        }
    return None
