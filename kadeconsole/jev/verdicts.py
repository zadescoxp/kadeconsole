"""
jev/verdicts.py — Buy/sell/hold probability distribution via Jev.

Uses 3 Score questions (buy_probability, hold_probability, sell_probability)
normalized to sum to 1.0. Returns timeframe-conditioned pairs: 3M and 1Y.

The state passed to Jev includes key fundamentals + technicals so it can
make an informed, calibrated judgment.
"""

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from kadeconsole.jev.client import JevClient

try:
    from typesafe_sdk import Score
    _SDK = True
except ImportError:
    _SDK = False
    Score = None  # type: ignore[assignment,misc]


def _build_verdict_state(info: dict[str, Any], timeframe: str) -> dict[str, Any]:
    """Construct the state dict for a VERDICT Jev call."""

    def _safe(k: str) -> Any:
        v = info.get(k)
        return round(float(v), 4) if v is not None else None

    return {
        "ticker":            info.get("symbol", "UNKNOWN"),
        "company":           info.get("name", ""),
        "sector":            info.get("sector", ""),
        "timeframe":         timeframe,

        # Valuation
        "trailing_pe":       _safe("trailing_pe"),
        "forward_pe":        _safe("forward_pe"),
        "peg_ratio":         _safe("peg_ratio"),
        "price_to_book":     _safe("price_to_book"),
        "ev_to_ebitda":      _safe("ev_to_ebitda"),

        # Profitability
        "roe":               _safe("roe"),
        "gross_margins":     _safe("gross_margins"),
        "profit_margins":    _safe("profit_margins"),

        # Growth
        "revenue_growth":    _safe("revenue_growth"),
        "earnings_growth":   _safe("earnings_growth"),

        # Health
        "debt_to_equity":    _safe("debt_to_equity"),
        "current_ratio":     _safe("current_ratio"),
        "free_cash_flow":    _safe("free_cash_flow"),

        # Price position
        "beta":              _safe("beta"),
        "day_change_pct":    _safe("day_change_pct"),
        "fifty_two_week_pct": _pct_from_52w(info),

        # Analyst consensus
        "analyst_rating":    info.get("analyst_rating"),
        "target_mean_price": _safe("target_mean_price"),
        "current_price":     _safe("current_price"),
    }


def _pct_from_52w(info: dict) -> Optional[float]:
    """Position of current price in 52-week range as 0–100%."""
    price = info.get("current_price")
    lo    = info.get("fifty_two_week_low")
    hi    = info.get("fifty_two_week_high")
    if price and lo and hi and (hi - lo) != 0:
        return round((price - lo) / (hi - lo) * 100, 1)
    return None


def _build_verdict_questions(timeframe: str) -> dict:
    """Build the Jev question dict for a verdict call."""
    if not _SDK:
        return {}
    horizon_label = _horizon_label(timeframe)
    return {
        "buy_probability": Score(
            instructions=(
                f"Given this company's fundamentals, valuation, and price position, "
                f"what is the probability that a buy decision is correct "
                f"over a {horizon_label} horizon? "
                "Consider valuation vs peers, growth trajectory, financial health, "
                "and sentiment."
            ),
            criteria=[
                "0.0 = very unlikely to be correct buy decision",
                "0.5 = roughly balanced odds for buying",
                "1.0 = very likely correct buy decision",
            ],
        ),
        "hold_probability": Score(
            instructions=(
                f"What is the probability that holding (neither buying nor selling) "
                f"is the correct decision over a {horizon_label} horizon? "
                "A hold is correct when risk/reward is balanced and no clear catalyst exists."
            ),
            criteria=[
                "0.0 = holding is clearly wrong (strong buy or sell signal present)",
                "0.5 = hold is plausible but not compelling",
                "1.0 = hold is clearly the right call",
            ],
        ),
        "sell_probability": Score(
            instructions=(
                f"What is the probability that selling is the correct decision "
                f"over a {horizon_label} horizon? "
                "Consider overvaluation, deteriorating fundamentals, or excessive risk."
            ),
            criteria=[
                "0.0 = selling would be clearly wrong",
                "0.5 = selling is debatable",
                "1.0 = selling is clearly the right decision",
            ],
        ),
    }


def _horizon_label(timeframe: str) -> str:
    labels = {
        "1D": "1-day", "5D": "5-day", "1M": "1-month",
        "3M": "3-month", "6M": "6-month", "1Y": "1-year",
        "2Y": "2-year", "5Y": "5-year",
    }
    return labels.get(timeframe.upper(), timeframe)


def get_verdict(
    jev: "JevClient",
    info: dict[str, Any],
    ticker: str,
    timeframe: str = "1Y",
) -> Optional[dict[str, float]]:
    """
    Call Jev for a buy/sell/hold verdict distribution.

    Returns:
        {"buy": float, "hold": float, "sell": float}  (sum ~= 1.0)
        or None if Jev is unavailable.
    """
    if not jev.available:
        return None

    state = _build_verdict_state(info, timeframe)
    questions = _build_verdict_questions(timeframe)

    response = jev.call(
        state=state,
        questions=questions,
        ticker=ticker,
        timeframe=timeframe,
        cache_tag=f"verdict:{timeframe}",
    )

    if not response:
        return None

    scores = response.get("scores", {})
    buy  = scores.get("buy_probability",  0.0)
    hold = scores.get("hold_probability", 0.0)
    sell = scores.get("sell_probability", 0.0)

    total = buy + hold + sell
    if total == 0:
        return None

    return {
        "buy":  round(buy  / total, 3),
        "hold": round(hold / total, 3),
        "sell": round(sell / total, 3),
    }


def get_multi_horizon_verdict(
    jev: "JevClient",
    info: dict[str, Any],
    ticker: str,
) -> dict[str, Optional[dict[str, float]]]:
    """
    Return verdicts for 3M and 1Y horizons simultaneously.

    Returns:
        {"3M": {...}, "1Y": {...}}
    """
    return {
        "3M": get_verdict(jev, info, ticker, "3M"),
        "1Y": get_verdict(jev, info, ticker, "1Y"),
        "3Y": get_verdict(jev, info, ticker, "5Y"),  # map 3Y intent to 5Y data
    }
