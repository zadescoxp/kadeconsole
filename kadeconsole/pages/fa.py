"""
pages/fa.py — FA command: full fundamentals page.

Sections:
  1. Valuation ratios
  2. Profitability & margins
  3. Growth rates
  4. Balance sheet health
  5. Cash flow & dividends
  6. Analyst consensus
  7. Jev anomaly flag (if available)

FA Q switches to quarterly financials from the provider.
"""

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text
from rich import box

from kadeconsole.render.theme import t, RICH_THEME
from kadeconsole.render.tables import (
    kv_table, fmt_number, fmt_pct, fmt_ratio, fmt_price,
    color_delta, jev_panel, jev_unavailable_panel,
)

if TYPE_CHECKING:
    from kadeconsole.core.session import Session
    from kadeconsole.core.parser import ParsedCommand
    from kadeconsole.providers.base import DataProvider
    from kadeconsole.jev.client import JevClient

console = Console(theme=RICH_THEME)


def render_fa(
    session: "Session",
    parsed: "ParsedCommand",
    provider: "DataProvider",
    jev: "JevClient",
) -> None:
    """Render the FA (fundamentals) page."""
    symbol    = session.yf_symbol
    quarterly = parsed.qualifier == "Q"
    mode_label = "Quarterly" if quarterly else "Annual"

    console.print(f"\n[muted]  Fetching fundamentals for {symbol} ({mode_label})...[/muted]")

    try:
        info = provider.get_info(symbol)
    except Exception as exc:
        console.print(f"[negative]  FA error: {exc}[/negative]")
        return

    name = info.get("name", symbol)

    console.print(
        Panel(
            _build_fa_content(info),
            title=f"[header]FA — {name}  ({mode_label})[/header]",
            border_style=f"{t.accent}",
            padding=(1, 2),
        )
    )

    # ── Jev anomaly flag ───────────────────────────────────────────────────────
    if jev.available:
        from kadeconsole.jev.narratives import get_anomaly_flag
        console.print("[muted]  Jev scanning for anomalies...[/muted]")
        flag = get_anomaly_flag(jev, info, symbol)
        if flag:
            console.print(jev_panel(f"⚠  {flag}", label="Jev — Anomaly Detected"))
        else:
            console.print(
                Panel(
                    "[jev]No significant anomalies detected in the current fundamental profile.[/jev]",
                    title=f"[jev.label]◆ Jev — Anomaly Check[/jev.label]",
                    border_style=f"{t.jev}",
                    padding=(0, 1),
                )
            )
    else:
        console.print(jev_unavailable_panel("Set TYPESAFE_API_KEY for Jev anomaly detection."))


def _build_fa_content(info: dict[str, Any]) -> Text:
    """Build the combined fundamentals content as a rich renderable."""
    from rich.console import Group

    sections = [
        _valuation_section(info),
        Rule(style=f"{t.border}"),
        _profitability_section(info),
        Rule(style=f"{t.border}"),
        _growth_section(info),
        Rule(style=f"{t.border}"),
        _balance_sheet_section(info),
        Rule(style=f"{t.border}"),
        _cashflow_dividends_section(info),
        Rule(style=f"{t.border}"),
        _analyst_section(info),
    ]
    return Group(*sections)


def _section_header(title: str) -> Text:
    t_ = Text(f"\n{title.upper()}", style=f"bold {t.accent}")
    return t_


def _valuation_section(info: dict) -> Any:
    rows = [
        ("Trailing P/E",     fmt_ratio(info.get("trailing_pe"))),
        ("Forward P/E",      fmt_ratio(info.get("forward_pe"))),
        ("PEG Ratio",        fmt_ratio(info.get("peg_ratio"))),
        ("Price / Book",     fmt_ratio(info.get("price_to_book"))),
        ("Price / Sales",    fmt_ratio(info.get("price_to_sales"))),
        ("EV / EBITDA",      fmt_ratio(info.get("ev_to_ebitda"))),
        ("Enterprise Value", fmt_number(info.get("enterprise_value"))),
        ("Market Cap",       fmt_number(info.get("market_cap"))),
        ("Trailing EPS",     fmt_price(info.get("trailing_eps"), info.get("currency", ""))),
        ("Forward EPS",      fmt_price(info.get("forward_eps"),  info.get("currency", ""))),
    ]
    from rich.console import Group
    return Group(_section_header("Valuation"), kv_table(rows))


def _profitability_section(info: dict) -> Any:
    rows = [
        ("Gross Margin",     fmt_pct(info.get("gross_margins"))),
        ("Operating Margin", fmt_pct(info.get("operating_margins"))),
        ("Net Margin",       fmt_pct(info.get("profit_margins"))),
        ("ROE",              fmt_pct(info.get("roe"))),
        ("ROA",              fmt_pct(info.get("roa"))),
        ("ROIC",             fmt_pct(info.get("roic"))),
    ]
    from rich.console import Group
    return Group(_section_header("Profitability"), kv_table(rows))


def _growth_section(info: dict) -> Any:
    rev_growth = info.get("revenue_growth")
    earn_growth = info.get("earnings_growth")
    rows = [
        ("Revenue Growth (YoY)",  color_delta(rev_growth  * 100 if rev_growth  is not None else None)),
        ("Earnings Growth (YoY)", color_delta(earn_growth * 100 if earn_growth is not None else None)),
    ]
    from rich.console import Group
    return Group(_section_header("Growth"), kv_table(rows))


def _balance_sheet_section(info: dict) -> Any:
    rows = [
        ("Total Debt",      fmt_number(info.get("total_debt"))),
        ("Total Cash",      fmt_number(info.get("total_cash"))),
        ("Debt / Equity",   fmt_ratio(info.get("debt_to_equity"))),
        ("Current Ratio",   f"{info['current_ratio']:.2f}x" if info.get("current_ratio") else "—"),
        ("Quick Ratio",     f"{info['quick_ratio']:.2f}x"   if info.get("quick_ratio")   else "—"),
        ("Shares Out.",     fmt_number(info.get("shares_outstanding"))),
        ("Float",           fmt_number(info.get("float_shares"))),
        ("Insider Own.",    fmt_pct(info.get("insider_ownership"))),
        ("Inst. Own.",      fmt_pct(info.get("institutional_ownership"))),
    ]
    from rich.console import Group
    return Group(_section_header("Balance Sheet & Ownership"), kv_table(rows))


def _cashflow_dividends_section(info: dict) -> Any:
    rows = [
        ("Operating CF",   fmt_number(info.get("operating_cash_flow"))),
        ("Free Cash Flow", fmt_number(info.get("free_cash_flow"))),
        ("Dividend Yield", fmt_pct(info.get("dividend_yield"))),
        ("Payout Ratio",   fmt_pct(info.get("payout_ratio"))),
        ("Beta",           f"{info['beta']:.2f}" if info.get("beta") else "—"),
        ("52W High",       fmt_price(info.get("fifty_two_week_high"), info.get("currency", ""))),
        ("52W Low",        fmt_price(info.get("fifty_two_week_low"),  info.get("currency", ""))),
    ]
    from rich.console import Group
    return Group(_section_header("Cash Flow & Dividends"), kv_table(rows))


def _analyst_section(info: dict) -> Any:
    rating = (info.get("analyst_rating") or "N/A").upper()
    num    = info.get("num_analyst_opinions")
    target_mean = fmt_price(info.get("target_mean_price"), info.get("currency", ""))
    target_high = fmt_price(info.get("target_high_price"), info.get("currency", ""))
    target_low  = fmt_price(info.get("target_low_price"),  info.get("currency", ""))

    # Target dispersion
    hi = info.get("target_high_price")
    lo = info.get("target_low_price")
    mean = info.get("target_mean_price")
    dispersion = "—"
    if hi and lo and mean and mean != 0:
        spread = (hi - lo) / mean * 100
        dispersion = f"{spread:.1f}% spread"

    rows = [
        ("Consensus Rating",  rating),
        ("# Analysts",        str(num) if num else "—"),
        ("Target (Mean)",     target_mean),
        ("Target (High)",     target_high),
        ("Target (Low)",      target_low),
        ("Target Dispersion", dispersion),
    ]
    from rich.console import Group
    return Group(_section_header("Analyst Consensus"), kv_table(rows))
