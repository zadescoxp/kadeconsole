"""
jev/narratives.py — Anomaly flagging and plain-English narratives via Jev.

Used on the FA page to unprompted surface inconsistencies in fundamentals
(debt spike, margin compression vs peers, guidance mismatch, etc.).
"""

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from kadeconsole.jev.client import JevClient

try:
    from typesafe_sdk import Choice
    _SDK = True
except ImportError:
    _SDK = False
    Choice = None  # type: ignore[assignment,misc]


def _build_anomaly_state(info: dict[str, Any]) -> dict[str, Any]:
    """Build the Jev state dict for anomaly detection."""

    def s(k: str) -> Any:
        v = info.get(k)
        return round(float(v), 4) if v is not None else None

    return {
        "company":           info.get("name", ""),
        "sector":            info.get("sector", ""),

        # Profitability trends
        "gross_margins":     s("gross_margins"),
        "operating_margins": s("operating_margins"),
        "profit_margins":    s("profit_margins"),
        "roe":               s("roe"),

        # Growth
        "revenue_growth":    s("revenue_growth"),
        "earnings_growth":   s("earnings_growth"),

        # Leverage
        "debt_to_equity":    s("debt_to_equity"),
        "current_ratio":     s("current_ratio"),
        "free_cash_flow":    s("free_cash_flow"),

        # Valuation vs earnings trajectory
        "forward_pe":        s("forward_pe"),
        "trailing_pe":       s("trailing_pe"),
        "peg_ratio":         s("peg_ratio"),
        "trailing_eps":      s("trailing_eps"),
        "forward_eps":       s("forward_eps"),

        # Analyst signals
        "analyst_rating":    info.get("analyst_rating"),
        "target_mean_price": s("target_mean_price"),
        "target_high_price": s("target_high_price"),
        "target_low_price":  s("target_low_price"),
        "current_price":     s("current_price"),
        "num_analyst_opinions": info.get("num_analyst_opinions"),
    }


def _build_anomaly_questions() -> dict:
    """Jev questions for anomaly detection."""
    if not _SDK:
        return {}
    return {
        "has_anomaly": Choice(
            instructions=(
                "Looking at this company's fundamentals, is there any notable anomaly, "
                "inconsistency, or red flag that a fundamental analyst should investigate? "
                "Examples: debt-to-equity spiking while margins compress, "
                "earnings growth decelerating while valuation re-rates higher, "
                "analyst target dispersion is extreme, forward PE much lower than trailing PE "
                "despite weak growth, negative free cash flow with high debt. "
                "Only flag something if it is genuinely unusual."
            ),
            criteria={
                "yes": None,
                "no":  None,
            },
        ),
        "anomaly_description": Choice(
            instructions=(
                "If there is an anomaly, describe it in one direct sentence (max 20 words). "
                "If no anomaly, return 'No anomalies detected in the current fundamental profile.'"
            ),
            criteria={
                "Debt rising sharply while margins are compressing — leverage risk growing": None,
                "Valuation re-rating higher despite decelerating earnings growth": None,
                "Wide analyst target dispersion suggests high uncertainty in fair value": None,
                "Negative free cash flow combined with elevated debt — watch liquidity": None,
                "Forward PE significantly below trailing PE despite flat or negative EPS growth": None,
                "Low analyst coverage — limited visibility into fundamentals": None,
                "No anomalies detected in the current fundamental profile.": None,
            },
        ),
    }


def get_anomaly_flag(
    jev: "JevClient",
    info: dict[str, Any],
    ticker: str,
) -> Optional[str]:
    """
    Ask Jev to scan fundamentals for anomalies.

    Returns a one-sentence anomaly description, or None if Jev is
    unavailable or no anomaly is detected.
    """
    if not jev.available:
        return None

    state     = _build_anomaly_state(info)
    questions = _build_anomaly_questions()

    response = jev.call(
        state=state,
        questions=questions,
        ticker=ticker,
        timeframe="fundamental",
        cache_tag="anomaly",
    )

    if not response:
        return None

    choices = response.get("choices", {})
    has_anomaly = choices.get("has_anomaly", {})

    if isinstance(has_anomaly, dict) and has_anomaly.get("choice") == "yes":
        desc = choices.get("anomaly_description", {})
        if isinstance(desc, dict):
            text = desc.get("choice", "")
            if text and "No anomalies" not in text:
                return text

    return None  # no anomaly or description indeterminate
