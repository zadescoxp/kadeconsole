"""
providers/yfinance_provider.py — yfinance DataProvider implementation.

Normalises yfinance's various return formats into the standard
DataProvider interface. Handles .NS/.BO and other exchange suffixes
transparently.
"""

from __future__ import annotations

import warnings
from typing import Any, Optional

# Suppress yfinance's noisy deprecation warnings in terminal output
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

try:
    import yfinance as yf
    _YF_AVAILABLE = True
except ImportError:
    _YF_AVAILABLE = False

import pandas as pd

from kadeconsole.providers.base import DataProvider

# yfinance period/interval tokens
_PERIOD_MAP: dict[str, str] = {
    "1D": "1d",
    "5D": "5d",
    "1M": "1mo",
    "3M": "3mo",
    "6M": "6mo",
    "1Y": "1y",
    "2Y": "2y",
    "5Y": "5y",
}

_INTERVAL_MAP: dict[str, str] = {
    "1D": "5m",
    "5D": "15m",
    "1M": "1d",
    "3M": "1d",
    "6M": "1d",
    "1Y": "1d",
    "2Y": "1wk",
    "5Y": "1wk",
}


def _safe(d: dict, *keys: str, default: Any = None) -> Any:
    """Safely retrieve nested dict keys, returning default on miss."""
    cur = d
    for key in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key, default)
    return cur


def _pct(value: Any) -> Optional[float]:
    """Return a float percentage or None."""
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


class YFinanceProvider(DataProvider):
    """Market data provider backed by the yfinance library (free, no API key)."""

    name = "yfinance"

    def get_info(self, symbol: str) -> dict[str, Any]:
        """Fetch and normalise yfinance Ticker.info."""
        if not _YF_AVAILABLE:
            raise RuntimeError("yfinance is not installed. Run: pip install yfinance")

        ticker = yf.Ticker(symbol)
        info: dict = {}
        try:
            info = ticker.info or {}
        except Exception:  # noqa: BLE001
            pass

        # Current price — yfinance uses different keys depending on market/time
        current_price = (
            info.get("currentPrice")
            or info.get("regularMarketPrice")
            or info.get("previousClose")
        )

        previous_close = info.get("previousClose") or info.get("regularMarketPreviousClose")

        day_change_pct: Optional[float] = None
        if current_price and previous_close and previous_close != 0:
            day_change_pct = (current_price - previous_close) / previous_close * 100

        return {
            # Identity
            "name":              info.get("longName") or info.get("shortName") or symbol,
            "sector":            info.get("sector"),
            "industry":          info.get("industry"),
            "country":           info.get("country"),
            "exchange":          info.get("exchange"),
            "currency":          info.get("currency", "USD"),
            "market_cap":        info.get("marketCap"),
            "employees":         info.get("fullTimeEmployees"),
            "website":           info.get("website"),
            "description":       info.get("longBusinessSummary"),
            "ceo":               self._extract_ceo(info),
            "founded_year":      None,  # yfinance doesn't reliably expose this

            # Valuation
            "trailing_pe":       info.get("trailingPE"),
            "forward_pe":        info.get("forwardPE"),
            "peg_ratio":         info.get("pegRatio"),
            "price_to_book":     info.get("priceToBook"),
            "price_to_sales":    info.get("priceToSalesTrailing12Months"),
            "ev_to_ebitda":      info.get("enterpriseToEbitda"),

            # Profitability
            "roe":               _pct(info.get("returnOnEquity")),
            "roa":               _pct(info.get("returnOnAssets")),
            "roic":              None,  # not in yfinance info
            "gross_margins":     _pct(info.get("grossMargins")),
            "operating_margins": _pct(info.get("operatingMargins")),
            "profit_margins":    _pct(info.get("profitMargins")),

            # Growth
            "revenue_growth":    _pct(info.get("revenueGrowth")),
            "earnings_growth":   _pct(info.get("earningsGrowth")),

            # Balance sheet
            "debt_to_equity":    info.get("debtToEquity"),
            "current_ratio":     info.get("currentRatio"),
            "quick_ratio":       info.get("quickRatio"),

            # Cash flow
            "free_cash_flow":    info.get("freeCashflow"),
            "operating_cash_flow": info.get("operatingCashflow"),

            # Dividends
            "dividend_yield":    _pct(info.get("dividendYield")),
            "payout_ratio":      _pct(info.get("payoutRatio")),

            # Price / range
            "current_price":     current_price,
            "previous_close":    previous_close,
            "day_change_pct":    day_change_pct,
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low":  info.get("fiftyTwoWeekLow"),
            "beta":              info.get("beta"),

            # Volume
            "volume":            info.get("volume") or info.get("regularMarketVolume"),
            "average_volume":    info.get("averageVolume") or info.get("averageVolume10days"),

            # Analyst targets
            "target_mean_price": info.get("targetMeanPrice"),
            "target_high_price": info.get("targetHighPrice"),
            "target_low_price":  info.get("targetLowPrice"),
            "analyst_rating":    info.get("recommendationKey"),
            "num_analyst_opinions": info.get("numberOfAnalystOpinions"),

            # Ownership
            "institutional_ownership": _pct(info.get("heldPercentInstitutions")),
            "insider_ownership":       _pct(info.get("heldPercentInsiders")),

            # Enterprise value
            "enterprise_value": info.get("enterpriseValue"),
            "total_cash":        info.get("totalCash"),
            "total_debt":        info.get("totalDebt"),

            # EPS
            "trailing_eps":      info.get("trailingEps"),
            "forward_eps":       info.get("forwardEps"),

            # Shares
            "shares_outstanding": info.get("sharesOutstanding"),
            "float_shares":       info.get("floatShares"),
        }

    def get_price_history(
        self,
        symbol: str,
        period: str = "1Y",
        interval: str = "1d",
    ) -> dict[str, Any]:
        """Download OHLCV history and normalise to the standard shape."""
        if not _YF_AVAILABLE:
            raise RuntimeError("yfinance is not installed.")

        yf_period   = _PERIOD_MAP.get(period.upper(), "1y")
        yf_interval = _INTERVAL_MAP.get(period.upper(), interval)

        ticker = yf.Ticker(symbol)
        try:
            hist: pd.DataFrame = ticker.history(period=yf_period, interval=yf_interval)
        except Exception:  # noqa: BLE001
            hist = pd.DataFrame()

        if hist.empty:
            return {"dates": [], "opens": [], "highs": [], "lows": [], "closes": [], "volumes": []}

        # Normalise index to ISO date strings
        if hasattr(hist.index, "strftime"):
            dates = hist.index.strftime("%Y-%m-%d").tolist()
        else:
            dates = [str(d)[:10] for d in hist.index.tolist()]

        return {
            "dates":   dates,
            "opens":   hist["Open"].round(2).tolist(),
            "highs":   hist["High"].round(2).tolist(),
            "lows":    hist["Low"].round(2).tolist(),
            "closes":  hist["Close"].round(2).tolist(),
            "volumes": hist["Volume"].fillna(0).astype(int).tolist(),
        }

    def get_financials(
        self,
        symbol: str,
        quarterly: bool = False,
    ) -> dict[str, Any]:
        """Fetch income statement, balance sheet, and cash flow data."""
        if not _YF_AVAILABLE:
            raise RuntimeError("yfinance is not installed.")

        ticker = yf.Ticker(symbol)

        try:
            if quarterly:
                income   = ticker.quarterly_income_stmt
                balance  = ticker.quarterly_balance_sheet
                cashflow = ticker.quarterly_cashflow
            else:
                income   = ticker.income_stmt
                balance  = ticker.balance_sheet
                cashflow = ticker.cashflow
        except Exception:  # noqa: BLE001
            return {"income": {}, "balance": {}, "cashflow": {}}

        def _extract(df: "pd.DataFrame", row: str) -> list[float]:
            if df is None or df.empty or row not in df.index:
                return []
            return [
                float(v) if pd.notna(v) else None
                for v in df.loc[row].tolist()
            ]

        def _periods(df: "pd.DataFrame") -> list[str]:
            if df is None or df.empty:
                return []
            return [str(c)[:10] for c in df.columns.tolist()]

        rev     = _extract(income, "Total Revenue")
        gp      = _extract(income, "Gross Profit")
        op_inc  = _extract(income, "Operating Income")
        net_inc = _extract(income, "Net Income")
        eps     = _extract(income, "Basic EPS")

        ta = _extract(balance, "Total Assets")
        tl = _extract(balance, "Total Liabilities Net Minority Interest")
        te = _extract(balance, "Stockholders Equity")
        ca = _extract(balance, "Cash And Cash Equivalents")
        td = _extract(balance, "Total Debt")

        ocf  = _extract(cashflow, "Operating Cash Flow")
        capx = _extract(cashflow, "Capital Expenditure")

        fcf: list[float] = []
        for o, c in zip(ocf, capx):
            if o is not None and c is not None:
                fcf.append(o + c)  # capex is negative in yfinance
            else:
                fcf.append(None)

        periods = _periods(income)

        return {
            "income": {
                "revenue":          rev,
                "gross_profit":     gp,
                "operating_income": op_inc,
                "net_income":       net_inc,
                "eps":              eps,
                "periods":          periods,
            },
            "balance": {
                "total_assets":      ta,
                "total_liabilities": tl,
                "total_equity":      te,
                "cash":              ca,
                "total_debt":        td,
                "periods":           _periods(balance),
            },
            "cashflow": {
                "operating_cf":   ocf,
                "capex":          capx,
                "free_cash_flow": fcf,
                "periods":        _periods(cashflow),
            },
        }

    def get_news(self, symbol: str, limit: int = 10) -> list[dict[str, Any]]:
        """Fetch recent news via yfinance."""
        if not _YF_AVAILABLE:
            return []

        ticker = yf.Ticker(symbol)
        try:
            raw_news = ticker.news or []
        except Exception:  # noqa: BLE001
            raw_news = []

        results = []
        for item in raw_news[:limit]:
            # yfinance news structure varies by version
            content = item.get("content", item)
            results.append({
                "title":     content.get("title") or item.get("title", ""),
                "publisher": content.get("provider", {}).get("displayName") or item.get("publisher", ""),
                "url":       content.get("canonicalUrl", {}).get("url") or item.get("link", ""),
                "published": str(content.get("pubDate") or item.get("providerPublishTime", ""))[:10],
            })
        return results

    def get_peers(self, symbol: str) -> list[str]:
        """
        Return peer tickers.

        yfinance doesn't have a direct peers endpoint, so we return
        an empty list for now — Phase 2 will enrich this via sector ETF
        constituents or external peer APIs.
        """
        return []

    def is_available(self) -> bool:
        return _YF_AVAILABLE

    @staticmethod
    def _extract_ceo(info: dict) -> Optional[str]:
        """Try to extract the CEO name from yfinance companyOfficers."""
        officers = info.get("companyOfficers") or []
        for officer in officers:
            title = (officer.get("title") or "").upper()
            if "CEO" in title or "CHIEF EXECUTIVE" in title:
                return officer.get("name")
        return None
