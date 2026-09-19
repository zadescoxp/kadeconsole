"""
core/parser.py — Command grammar parser.

Parses raw user input strings into structured ParsedCommand objects.
The grammar is intentionally Bloomberg-inspired:

    AAPL EQUITY                      → security resolution
    RELIANCE IN NS EQUITY            → with country + exchange
    GP 6M                            → command + timeframe modifier
    FA Q                             → command + qualifier
    WATCH ADD AAPL                   → command + subcommand + arg
    SCREEN "cash-rich, low debt"     → command + quoted natural-language arg
    COMPARE MSFT                     → command + ticker arg
    SOURCE alpaca                    → command + provider name
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from typing import Optional


# ── Command type constants ─────────────────────────────────────────────────────
CMD_EQUITY   = "EQUITY"
CMD_DES      = "DES"
CMD_FA       = "FA"
CMD_GP       = "GP"
CMD_TA       = "TA"
CMD_RV       = "RV"
CMD_HP       = "HP"
CMD_NI       = "NI"
CMD_MACRO    = "MACRO"
CMD_VERDICT  = "VERDICT"
CMD_RATE     = "RATE"
CMD_COMPARE  = "COMPARE"
CMD_SCREEN   = "SCREEN"
CMD_WATCH    = "WATCH"
CMD_EXPORT   = "EXPORT"
CMD_SOURCE   = "SOURCE"
CMD_HELP     = "HELP"
CMD_EXIT     = "EXIT"
CMD_UNKNOWN  = "UNKNOWN"

# ── Valid timeframe tokens ────────────────────────────────────────────────────
TIMEFRAMES = {"1D", "5D", "1M", "3M", "6M", "1Y", "2Y", "5Y"}

# ── Known exchange codes (for EQUITY parser) ──────────────────────────────────
EXCHANGE_CODES = {
    "NS", "BO",                          # India
    "LN", "PA", "DE", "AS", "MI",        # Europe
    "HK", "TK", "AU", "SG", "KS",        # Asia-Pacific
    "US", "CN",                           # Americas
}

# ── Known country codes (Bloomberg grammar: "RELIANCE IN NS EQUITY") ──────────
COUNTRY_CODES = {"IN", "US", "GB", "AU", "HK", "JP", "DE", "SG", "CN", "KR"}

# ── Simple command aliases ────────────────────────────────────────────────────
ALIASES: dict[str, str] = {
    "?":    CMD_HELP,
    "EXIT": CMD_EXIT,
    "QUIT": CMD_EXIT,
    "Q":    CMD_EXIT,
}


@dataclass
class ParsedCommand:
    """Structured result of parsing a raw input string."""
    command: str                        # One of the CMD_* constants
    ticker: Optional[str] = None        # e.g. "AAPL", "RELIANCE"
    exchange: Optional[str] = None      # e.g. "NS", "US"
    country: Optional[str] = None       # e.g. "IN"
    timeframe: Optional[str] = None     # e.g. "6M", "1Y"
    qualifier: Optional[str] = None     # e.g. "Q" for FA Q
    subcommand: Optional[str] = None    # e.g. "ADD" for WATCH ADD
    args: list[str] = field(default_factory=list)   # remaining positional args
    raw: str = ""                       # original input


class ParseError(Exception):
    """Raised when input cannot be parsed into a valid command."""


def parse(raw_input: str) -> ParsedCommand:
    """
    Parse a raw REPL input string into a ParsedCommand.

    Raises ParseError on malformed input.
    Returns a ParsedCommand with CMD_UNKNOWN for unrecognised commands.
    """
    raw = raw_input.strip()
    if not raw:
        return ParsedCommand(command=CMD_UNKNOWN, raw=raw)

    # ── Tokenise (respects quoted strings) ────────────────────────────────────
    try:
        tokens = shlex.split(raw.upper(), posix=False)
        # Preserve original casing for natural-language args (SCREEN "...")
        raw_tokens = shlex.split(raw, posix=False)
    except ValueError as exc:
        raise ParseError(f"Unmatched quote: {exc}") from exc

    # Strip outer quotes from tokens for comparison
    tokens_clean = [t.strip('"\'') for t in tokens]

    # ── Alias resolution ──────────────────────────────────────────────────────
    first = tokens_clean[0]
    if first in ALIASES:
        return ParsedCommand(command=ALIASES[first], raw=raw)

    # ── EQUITY resolution: ends with "EQUITY" ────────────────────────────────
    if tokens_clean[-1] == CMD_EQUITY:
        return _parse_equity(tokens_clean, raw)

    # ── Direct command dispatch ────────────────────────────────────────────────
    cmd = first
    rest = tokens_clean[1:]
    raw_rest = raw_tokens[1:]

    if cmd == CMD_DES:
        return ParsedCommand(command=CMD_DES, raw=raw)

    if cmd == CMD_FA:
        qualifier = rest[0] if rest and rest[0] == "Q" else None
        return ParsedCommand(command=CMD_FA, qualifier=qualifier, raw=raw)

    if cmd == CMD_GP:
        tf = rest[0] if rest and rest[0] in TIMEFRAMES else None
        return ParsedCommand(command=CMD_GP, timeframe=tf, raw=raw)

    if cmd == CMD_HP:
        tf = rest[0] if rest and rest[0] in TIMEFRAMES else None
        return ParsedCommand(command=CMD_HP, timeframe=tf, raw=raw)

    if cmd == CMD_TA:
        return ParsedCommand(command=CMD_TA, raw=raw)

    if cmd == CMD_RV:
        return ParsedCommand(command=CMD_RV, raw=raw)

    if cmd == CMD_NI:
        return ParsedCommand(command=CMD_NI, raw=raw)

    if cmd == CMD_MACRO:
        return ParsedCommand(command=CMD_MACRO, raw=raw)

    if cmd == CMD_VERDICT:
        return ParsedCommand(command=CMD_VERDICT, raw=raw)

    if cmd == CMD_RATE:
        return ParsedCommand(command=CMD_RATE, raw=raw)

    if cmd == CMD_COMPARE:
        if not rest:
            raise ParseError("COMPARE requires a ticker argument, e.g. COMPARE MSFT")
        return ParsedCommand(command=CMD_COMPARE, ticker=rest[0], raw=raw)

    if cmd == CMD_SCREEN:
        # Natural-language arg — preserve original casing
        if not raw_rest:
            raise ParseError('SCREEN requires a quoted query, e.g. SCREEN "cash-rich, low debt"')
        query = " ".join(raw_rest).strip('"\'')
        return ParsedCommand(command=CMD_SCREEN, args=[query], raw=raw)

    if cmd == CMD_WATCH:
        sub = rest[0] if rest else None
        args = rest[1:] if len(rest) > 1 else []
        return ParsedCommand(command=CMD_WATCH, subcommand=sub, args=args, raw=raw)

    if cmd == CMD_EXPORT:
        fmt = rest[0] if rest else "csv"
        return ParsedCommand(command=CMD_EXPORT, args=[fmt.lower()], raw=raw)

    if cmd == CMD_SOURCE:
        if not rest:
            raise ParseError("SOURCE requires a provider name, e.g. SOURCE alpaca")
        return ParsedCommand(command=CMD_SOURCE, args=[rest[0].lower()], raw=raw)

    if cmd in (CMD_HELP, "HELP"):
        return ParsedCommand(command=CMD_HELP, raw=raw)

    if cmd in (CMD_EXIT, "EXIT", "QUIT"):
        return ParsedCommand(command=CMD_EXIT, raw=raw)

    # ── Unknown command ───────────────────────────────────────────────────────
    return ParsedCommand(command=CMD_UNKNOWN, raw=raw, args=tokens_clean)


def _parse_equity(tokens: list[str], raw: str) -> ParsedCommand:
    """
    Parse EQUITY command variations:
        AAPL EQUITY
        AAPL US EQUITY
        RELIANCE IN NS EQUITY
        RELIANCE IN EQUITY         (country only → default exchange)
    """
    # Strip trailing "EQUITY"
    parts = tokens[:-1]  # everything before EQUITY

    if not parts:
        raise ParseError("EQUITY command requires a ticker symbol")

    ticker = parts[0]
    exchange: Optional[str] = None
    country: Optional[str] = None

    if len(parts) == 1:
        # Just "AAPL EQUITY" — US market assumed
        pass

    elif len(parts) == 2:
        # "AAPL US EQUITY" or "RELIANCE IN EQUITY"
        code = parts[1]
        if code in EXCHANGE_CODES:
            exchange = code
        elif code in COUNTRY_CODES:
            country = code
        else:
            # treat as exchange anyway (unknown, will degrade gracefully)
            exchange = code

    elif len(parts) == 3:
        # "RELIANCE IN NS EQUITY"
        country = parts[1] if parts[1] in COUNTRY_CODES else None
        exchange = parts[2] if parts[2] in EXCHANGE_CODES else parts[2]

    else:
        # Extra tokens — take first as ticker, last exchange-like token as exchange
        ticker = parts[0]
        exchange = parts[-1] if parts[-1] in EXCHANGE_CODES else None

    return ParsedCommand(
        command=CMD_EQUITY,
        ticker=ticker,
        exchange=exchange,
        country=country,
        raw=raw,
    )
