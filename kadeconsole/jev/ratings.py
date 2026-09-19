"""
jev/ratings.py — Multi-axis fundamental rating via Jev.

Four axes, each scored 1–10 with a one-line rationale:
  1. Valuation  — is the stock cheap or expensive vs fundamentals?
  2. Growth     — is top/bottom line growth accelerating or stalling?
  3. Quality    — how strong are margins, ROIC, and balance sheet?
  4. Momentum   — what do price/analyst trends suggest?
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from kadeconsole.jev.client import JevClient

try:
    from typesafe_sdk import Score, Choice
    _SDK = True
except ImportError:
    _SDK = False
    Score  = None  # type: ignore[assignment,misc]
    Choice = None  # type: ignore[assignment,misc]


@dataclass
class AxisRating:
    axis:   str
    score:  float          # 1–10
    label:  str            # e.g. "Strong", "Weak", "Average"
    reason: Optional[str] = None


@dataclass
class FundamentalRating:
    valuation: AxisRating
    growth:    AxisRating
    quality:   AxisRating
    momentum:  AxisRating
    axes: list[AxisRating] = field(init=False)

    def __post_init__(self) -> None:
        self.axes = [self.valuation, self.growth, self.quality, self.momentum]

    @property
    def composite(self) -> float:
        """Equally-weighted composite score, 1–10."""
        return round(sum(a.score for a in self.axes) / len(self.axes), 1)


def _score_to_label(score: float) -> str:
    if score >= 8.0:  return "Strong"
    if score >= 6.5:  return "Above Average"
    if score >= 5.0:  return "Average"
    if score >= 3.5:  return "Below Average"
    return "Weak"


def _build_rating_state(info: dict[str, Any]) -> dict[str, Any]:
    """Construct the state dict for a RATE Jev call."""

    def s(k: str) -> Any:
        v = info.get(k)
        return round(float(v), 4) if v is not None else None

    return {
        "company":           info.get("name", ""),
        "sector":            info.get("sector", ""),
        "ticker":            info.get("symbol", ""),

        # Valuation
        "trailing_pe":       s("trailing_pe"),
        "forward_pe":        s("forward_pe"),
        "peg_ratio":         s("peg_ratio"),
        "price_to_book":     s("price_to_book"),
        "price_to_sales":    s("price_to_sales"),
        "ev_to_ebitda":      s("ev_to_ebitda"),

        # Growth
        "revenue_growth_yoy":  s("revenue_growth"),
        "earnings_growth_yoy": s("earnings_growth"),
        "forward_eps":         s("forward_eps"),
        "trailing_eps":        s("trailing_eps"),

        # Quality
        "roe":               s("roe"),
        "roa":               s("roa"),
        "gross_margins":     s("gross_margins"),
        "operating_margins": s("operating_margins"),
        "profit_margins":    s("profit_margins"),
        "debt_to_equity":    s("debt_to_equity"),
        "current_ratio":     s("current_ratio"),
        "free_cash_flow":    s("free_cash_flow"),

        # Momentum
        "beta":              s("beta"),
        "analyst_rating":    info.get("analyst_rating"),
        "target_vs_price":   _target_upside(info),
        "day_change_pct":    s("day_change_pct"),
        "52w_position_pct":  _pct_52w(info),
    }


def _target_upside(info: dict) -> Optional[float]:
    price  = info.get("current_price")
    target = info.get("target_mean_price")
    if price and target and price != 0:
        return round((target - price) / price * 100, 2)
    return None


def _pct_52w(info: dict) -> Optional[float]:
    price = info.get("current_price")
    lo    = info.get("fifty_two_week_low")
    hi    = info.get("fifty_two_week_high")
    if price and lo and hi and (hi - lo) != 0:
        return round((price - lo) / (hi - lo) * 100, 1)
    return None


def _build_rating_questions() -> dict:
    """Build the Jev question dict for RATE."""
    if not _SDK:
        return {}
    _score_criteria = [
        "0.0 = very weak / worst possible",
        "0.25 = below average",
        "0.5 = average / neutral",
        "0.75 = above average",
        "1.0 = exceptional / best possible",
    ]
    return {
        "valuation_score": Score(
            instructions=(
                "Score the company's valuation from 0 (massively overvalued) to 1 "
                "(deeply undervalued) based on P/E, P/B, EV/EBITDA, PEG, and P/S ratios. "
                "Consider whether these are cheap or expensive relative to typical sector benchmarks."
            ),
            criteria=_score_criteria,
        ),
        "valuation_reason": Choice(
            instructions="Summarise the valuation assessment in one concise sentence (under 15 words).",
            criteria={
                "Deeply discounted vs sector peers": None,
                "Modest discount to fair value": None,
                "Fairly valued at current multiples": None,
                "Modest premium to intrinsic value": None,
                "Significantly overvalued on most metrics": None,
            },
        ),
        "growth_score": Score(
            instructions=(
                "Score the company's growth profile from 0 (declining/contracting) to 1 "
                "(hyper-growth). Consider YoY revenue growth, earnings growth, and forward EPS "
                "vs trailing EPS trend."
            ),
            criteria=_score_criteria,
        ),
        "growth_reason": Choice(
            instructions="Summarise the growth assessment in one concise sentence (under 15 words).",
            criteria={
                "Accelerating revenue and earnings growth": None,
                "Solid growth, steady execution": None,
                "Modest growth, limited upside catalysts": None,
                "Growth stalling or turning negative": None,
                "Declining top and bottom line": None,
            },
        ),
        "quality_score": Score(
            instructions=(
                "Score the company's business quality from 0 (very weak) to 1 (exceptional). "
                "Consider ROE, gross/operating margins, debt-to-equity, current ratio, "
                "and free cash flow generation."
            ),
            criteria=_score_criteria,
        ),
        "quality_reason": Choice(
            instructions="Summarise the quality assessment in one concise sentence (under 15 words).",
            criteria={
                "Exceptional margins and fortress balance sheet": None,
                "High-quality business with strong cash generation": None,
                "Average quality, some balance sheet risk": None,
                "Weak margins or elevated financial leverage": None,
                "Distressed fundamentals, significant risk": None,
            },
        ),
        "momentum_score": Score(
            instructions=(
                "Score the stock's price and sentiment momentum from 0 (strong downtrend) to 1 "
                "(strong uptrend). Consider analyst rating, target price upside, "
                "52-week price position, beta, and recent price change."
            ),
            criteria=_score_criteria,
        ),
        "momentum_reason": Choice(
            instructions="Summarise the momentum assessment in one concise sentence (under 15 words).",
            criteria={
                "Strong analyst support and bullish price trend": None,
                "Positive momentum, improving sentiment": None,
                "Mixed signals, sideways price action": None,
                "Weakening trend, analyst downgrades": None,
                "Strong downtrend, bearish sentiment": None,
            },
        ),
    }



def get_rating(
    jev: "JevClient",
    info: dict[str, Any],
    ticker: str,
) -> Optional[FundamentalRating]:
    """
    Call Jev for a multi-axis fundamental rating.

    Returns a FundamentalRating or None if Jev is unavailable.
    """
    if not jev.available:
        return None

    state     = _build_rating_state(info)
    questions = _build_rating_questions()

    response = jev.call(
        state=state,
        questions=questions,
        ticker=ticker,
        timeframe="fundamental",
        cache_tag="rating",
    )

    if not response:
        return None

    scores  = response.get("scores",  {})
    choices = response.get("choices", {})

    def _axis(name: str, score_key: str, reason_key: str) -> AxisRating:
        raw_score = scores.get(score_key, 5.0)
        score = max(1.0, min(10.0, raw_score * 10))  # normalize 0–1 → 1–10
        reason_choice = choices.get(reason_key, {})
        reason = reason_choice.get("choice") if isinstance(reason_choice, dict) else None
        return AxisRating(axis=name, score=score, label=_score_to_label(score), reason=reason)

    return FundamentalRating(
        valuation=_axis("Valuation", "valuation_score", "valuation_reason"),
        growth   =_axis("Growth",    "growth_score",    "growth_reason"),
        quality  =_axis("Quality",   "quality_score",   "quality_reason"),
        momentum =_axis("Momentum",  "momentum_score",  "momentum_reason"),
    )
