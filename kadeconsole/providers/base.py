"""
providers/base.py — Abstract DataProvider interface.

All data providers (yfinance, Alpaca, Alpha Vantage, Polygon, etc.)
must implement this interface. The provider registry uses duck-typing
via this ABC for the fallback chain.

Return types are plain dicts/lists so pages are provider-agnostic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class DataProvider(ABC):
    """Abstract base class for all market data providers."""

    name: str = "base"

    # ── Security info ──────────────────────────────────────────────────────────

    @abstractmethod
    def get_info(self, symbol: str) -> dict[str, Any]:
        """
        Return a dict of company/security metadata.

        Expected keys (populate what's available, None for missing):
          name, sector, industry, country, exchange, currency,
          market_cap, employees, website, description,
          ceo, founded_year,
          trailing_pe, forward_pe, peg_ratio,
          price_to_book, price_to_sales, ev_to_ebitda,
          roe, roa, roic,
          gross_margins, operating_margins, profit_margins,
          revenue_growth, earnings_growth,
          debt_to_equity, current_ratio, quick_ratio,
          free_cash_flow, operating_cash_flow,
          dividend_yield, payout_ratio,
          beta, fifty_two_week_high, fifty_two_week_low,
          current_price, previous_close, day_change_pct,
          volume, average_volume,
          target_mean_price, target_high_price, target_low_price,
          analyst_rating,
          institutional_ownership, insider_ownership,
        """

    # ── Price history ─────────────────────────────────────────────────────────

    @abstractmethod
    def get_price_history(
        self,
        symbol: str,
        period: str = "1Y",
        interval: str = "1d",
    ) -> dict[str, Any]:
        """
        Return OHLCV price history.

        Expected shape:
          {
            "dates":   ["2024-01-02", ...],   # ISO date strings
            "opens":   [float, ...],
            "highs":   [float, ...],
            "lows":    [float, ...],
            "closes":  [float, ...],
            "volumes": [int, ...],
          }
        """

    # ── Financials ────────────────────────────────────────────────────────────

    @abstractmethod
    def get_financials(
        self,
        symbol: str,
        quarterly: bool = False,
    ) -> dict[str, Any]:
        """
        Return financial statement data.

        Expected shape:
          {
            "income": {
                "revenue":           [float, ...],   # most recent first
                "gross_profit":      [float, ...],
                "operating_income":  [float, ...],
                "net_income":        [float, ...],
                "eps":               [float, ...],
                "periods":           ["2023", "2022", ...],
            },
            "balance": {
                "total_assets":      [float, ...],
                "total_liabilities": [float, ...],
                "total_equity":      [float, ...],
                "cash":              [float, ...],
                "total_debt":        [float, ...],
                "periods":           [...],
            },
            "cashflow": {
                "operating_cf":      [float, ...],
                "capex":             [float, ...],
                "free_cash_flow":    [float, ...],
                "periods":           [...],
            },
          }
        """

    # ── News ──────────────────────────────────────────────────────────────────

    @abstractmethod
    def get_news(self, symbol: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Return recent news items.

        Each item:
          {
            "title":     str,
            "publisher": str,
            "url":       str,
            "published": str,   # ISO datetime or date string
          }
        """

    # ── Peers ─────────────────────────────────────────────────────────────────

    @abstractmethod
    def get_peers(self, symbol: str) -> list[str]:
        """Return a list of peer/comparable ticker symbols."""

    # ── Optional: health check ────────────────────────────────────────────────

    def is_available(self) -> bool:
        """Return True if this provider can currently serve data."""
        return True

    def __repr__(self) -> str:
        return f"<DataProvider:{self.name}>"
