"""
core/session.py — REPL session state.

Holds the current security context (ticker, exchange, timeframe) and
any watchlist entries. Mutated in-place by the router as commands execute.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ── Exchange suffix map ────────────────────────────────────────────────────────
# Maps Bloomberg-style exchange codes → yfinance ticker suffix.
# Built-in from day one to support Indian and other non-US markets.
EXCHANGE_SUFFIX: dict[str, str] = {
    # Indian
    "NS": ".NS",   # NSE India
    "BO": ".BO",   # BSE India
    # European
    "LN": ".L",    # London Stock Exchange
    "PA": ".PA",   # Paris (Euronext)
    "DE": ".DE",   # Frankfurt XETRA
    "AS": ".AS",   # Amsterdam (Euronext)
    "MI": ".MI",   # Milan
    # Asia-Pacific
    "HK": ".HK",   # Hong Kong
    "TK": ".T",    # Tokyo
    "AU": ".AX",   # Australia (ASX)
    "SG": ".SI",   # Singapore
    "KS": ".KS",   # Korea (KOSPI)
    # Americas
    "US": "",      # US markets — no suffix
    "CN": ".TO",   # Toronto (TSX)
    # Country shortcodes (Bloomberg alt grammar: "RELIANCE IN NS EQUITY")
    "IN": None,    # Resolved dynamically alongside exchange code
}

# Country code → default exchange suffix when exchange not specified
COUNTRY_DEFAULT_SUFFIX: dict[str, str] = {
    "IN": ".NS",   # Default Indian tickers to NSE
    "US": "",
    "GB": ".L",
    "AU": ".AX",
    "HK": ".HK",
    "JP": ".T",
}


@dataclass
class Session:
    """
    Mutable REPL session state.

    All page handlers receive a reference to this object and may read or
    update it.  The session persists for the lifetime of a REPL run.
    """

    # ── Security context ──────────────────────────────────────────────────────
    ticker: Optional[str] = None        # Raw ticker (e.g. "AAPL", "RELIANCE")
    exchange: Optional[str] = None      # Exchange code (e.g. "NS", "US")
    country: Optional[str] = None       # Country code (e.g. "IN", "US")
    yf_symbol: Optional[str] = None     # Resolved yfinance symbol (e.g. "RELIANCE.NS")
    company_name: Optional[str] = None  # Human-readable name, set on EQUITY resolution

    # ── Timeframe ─────────────────────────────────────────────────────────────
    timeframe: str = "1Y"               # Active chart/data timeframe

    # ── Provider ──────────────────────────────────────────────────────────────
    provider_override: Optional[str] = None  # Set by SOURCE command

    # ── Watchlist ─────────────────────────────────────────────────────────────
    watchlist: list[str] = field(default_factory=list)

    # ── Last page context (for EXPORT) ───────────────────────────────────────
    last_page: Optional[str] = None
    last_data: Optional[dict] = field(default=None, repr=False)

    # ── Jev context (cached verdict for banner) ───────────────────────────────
    jev_verdict_cache: Optional[dict] = field(default=None, repr=False)

    # ─────────────────────────────────────────────────────────────────────────

    def set_security(
        self,
        ticker: str,
        exchange: Optional[str] = None,
        country: Optional[str] = None,
    ) -> None:
        """Resolve and set the active security from parser output."""
        self.ticker = ticker.upper()
        self.exchange = exchange.upper() if exchange else None
        self.country = country.upper() if country else None
        self.yf_symbol = self._resolve_symbol()
        self.company_name = None  # Cleared until EQUITY page sets it
        self.jev_verdict_cache = None

    def _resolve_symbol(self) -> str:
        """Build the yfinance-compatible symbol from ticker + exchange/country."""
        base = self.ticker

        # Explicit exchange code takes priority
        if self.exchange and self.exchange in EXCHANGE_SUFFIX:
            suffix = EXCHANGE_SUFFIX[self.exchange]
            if suffix is not None:
                return f"{base}{suffix}"

        # Fall back to country default
        if self.country and self.country in COUNTRY_DEFAULT_SUFFIX:
            return f"{base}{COUNTRY_DEFAULT_SUFFIX[self.country]}"

        # Default: assume US, no suffix
        return base

    def has_security(self) -> bool:
        """Return True if a security has been resolved."""
        return self.ticker is not None

    def set_timeframe(self, tf: str) -> None:
        """Validate and set session timeframe."""
        valid = {"1D", "5D", "1M", "3M", "6M", "1Y", "2Y", "5Y"}
        tf = tf.upper()
        if tf in valid:
            self.timeframe = tf

    def __str__(self) -> str:
        if not self.has_security():
            return "No security selected"
        name = f" ({self.company_name})" if self.company_name else ""
        return f"{self.yf_symbol}{name} | {self.timeframe}"
