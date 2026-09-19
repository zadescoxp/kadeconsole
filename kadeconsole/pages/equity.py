"""
pages/equity.py — EQUITY command: resolve security and show snapshot.

Renders a 3-section header:
  1. Price/change bar (ticker, price, delta, volume)
  2. Key ratios strip (P/E, mkt cap, 52w range, beta, analyst)
  3. Jev quick verdict teaser (buy/hold/sell pill)
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from rich.console import Console
from rich.columns import Columns
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from kadeconsole.render.theme import t, RICH_THEME, STYLE_ACCENT, STYLE_MUTED
from kadeconsole.render.tables import (
    fmt_number, fmt_pct, fmt_price, fmt_ratio, color_delta, jev_unavailable_panel,
)

if TYPE_CHECKING:
    from kadeconsole.core.session import Session
    from kadeconsole.core.parser import ParsedCommand
    from kadeconsole.providers.base import DataProvider
    from kadeconsole.jev.client import JevClient

console = Console(theme=RICH_THEME)


def render_equity(
    session: "Session",
    parsed: "ParsedCommand",
    provider: "DataProvider",
    jev: "JevClient",
) -> None:
    """Resolve security, update session state, and render the snapshot."""

    # ── 1. Resolve security ───────────────────────────────────────────────────
    session.set_security(
        ticker   = parsed.ticker,
        exchange = parsed.exchange,
        country  = parsed.country,
    )
    symbol = session.yf_symbol

    console.print(f"\n[muted]  Resolving {symbol}...[/muted]")

    try:
        info = provider.get_info(symbol)
    except Exception as exc:
        console.print(f"[negative]  Could not fetch data for {symbol}: {exc}[/negative]")
        return

    # Store name in session
    session.company_name = info.get("name") or symbol
    session.last_page = "EQUITY"
    session.last_data = info

    # ── 2. Render header bar ──────────────────────────────────────────────────
    _render_header(info, symbol, session)

    # ── 3. Key ratios strip ───────────────────────────────────────────────────
    _render_ratios(info)

    # ── 4. Jev quick verdict ──────────────────────────────────────────────────
    _render_jev_teaser(jev, info, symbol, session.timeframe)

    console.print(
        f"\n[muted]  Session: [accent]{session.yf_symbol}[/accent] | "
        f"Timeframe: [accent]{session.timeframe}[/accent] | "
        f"Provider: [accent]{provider.name}[/accent][/muted]\n"
    )


def _render_header(info: dict[str, Any], symbol: str, session: "Session") -> None:
    """Render the price/company header panel."""
    name     = info.get("name", symbol)
    sector   = info.get("sector") or ""
    industry = info.get("industry") or ""
    exchange = info.get("exchange") or ""
    currency = info.get("currency", "USD")

    price    = info.get("current_price")
    prev     = info.get("previous_close")
    change   = info.get("day_change_pct")
    volume   = info.get("volume")
    mkt_cap  = info.get("market_cap")

    # Build header title line
    title_line = Text()
    title_line.append(f"  {name}", style=STYLE_ACCENT)
    if sector:
        title_line.append(f"  ·  {sector}", style=f"{t.muted}")
    if industry:
        title_line.append(f" / {industry}", style=f"{t.muted}")

    # Price + change line
    price_text = Text()
    if price:
        price_text.append(f"  {currency} {price:,.2f}", style=f"bold {t.white}")
    else:
        price_text.append("  Price unavailable", style=f"{t.muted}")

    if change is not None:
        delta = color_delta(change, pct=True)
        price_text.append("   ")
        price_text.append_text(delta)

    if prev:
        price_text.append(f"   Prev: {prev:,.2f}", style=f"{t.muted}")

    # Sub-info line
    sub_line = Text()
    if volume:
        sub_line.append(f"  Vol: {fmt_number(volume, 1)}", style=f"{t.dim_text}")
    if mkt_cap:
        sub_line.append(f"   Mkt Cap: {fmt_number(mkt_cap, 2)}", style=f"{t.dim_text}")
    if exchange:
        sub_line.append(f"   {exchange}", style=f"{t.muted}")

    content = Text()
    content.append_text(title_line)
    content.append("\n")
    content.append_text(price_text)
    content.append("\n")
    content.append_text(sub_line)

    console.print(
        Panel(
            content,
            title=f"[header]  {symbol}  ·  EQUITY[/header]",
            border_style=f"{t.accent}",
            padding=(0, 1),
        )
    )


def _render_ratios(info: dict[str, Any]) -> None:
    """Render a horizontal key ratios table."""
    pe        = fmt_ratio(info.get("trailing_pe"))
    fwd_pe    = fmt_ratio(info.get("forward_pe"))
    pb        = fmt_ratio(info.get("price_to_book"))
    ev_ebitda = fmt_ratio(info.get("ev_to_ebitda"))
    beta      = f"{info['beta']:.2f}" if info.get("beta") else "—"
    hi52      = fmt_price(info.get("fifty_two_week_high"))
    lo52      = fmt_price(info.get("fifty_two_week_low"))
    rating    = (info.get("analyst_rating") or "—").upper()
    target    = fmt_price(info.get("target_mean_price"))
    div_yield = fmt_pct(info.get("dividend_yield"))

    table = Table(
        show_header=True,
        header_style=f"bold {t.muted}",
        box=box.SIMPLE,
        padding=(0, 2),
        expand=True,
    )
    table.add_column("P/E",       justify="center", style=f"{t.text}")
    table.add_column("Fwd P/E",   justify="center", style=f"{t.text}")
    table.add_column("P/B",       justify="center", style=f"{t.text}")
    table.add_column("EV/EBITDA", justify="center", style=f"{t.text}")
    table.add_column("Beta",      justify="center", style=f"{t.text}")
    table.add_column("52W Range", justify="center", style=f"{t.text}")
    table.add_column("Analyst",   justify="center", style=f"{t.accent}")
    table.add_column("Target",    justify="center", style=f"{t.text}")
    table.add_column("Div Yield", justify="center", style=f"{t.text}")

    table.add_row(
        pe, fwd_pe, pb, ev_ebitda, beta,
        f"{lo52} – {hi52}",
        rating, target, div_yield,
    )

    console.print(Panel(table, border_style=f"{t.border}", padding=(0, 0)))


def _render_jev_teaser(
    jev: "JevClient",
    info: dict[str, Any],
    symbol: str,
    timeframe: str,
) -> None:
    """Show a quick Jev verdict teaser (or unavailable notice)."""
    if not jev.available:
        console.print(jev_unavailable_panel("Run VERDICT or RATE for Jev AI analysis."))
        return

    from kadeconsole.jev.verdicts import get_verdict
    verdict = get_verdict(jev, info, symbol, timeframe)

    if verdict is None:
        console.print(jev_unavailable_panel("Jev analysis temporarily unavailable."))
        return

    buy  = verdict["buy"]
    hold = verdict["hold"]
    sell = verdict["sell"]

    # Dominant signal
    dominant = max(verdict, key=lambda k: verdict[k])
    dom_pct  = verdict[dominant]

    color_map = {"buy": t.positive, "hold": t.accent, "sell": t.negative}
    dom_color = color_map.get(dominant, t.accent)

    bar = _verdict_bar(buy, hold, sell, width=40)

    content = Text()
    content.append(f"  {bar}\n", style=f"{t.text}")
    content.append(
        f"  Buy {buy*100:.0f}%  ·  Hold {hold*100:.0f}%  ·  Sell {sell*100:.0f}%",
        style=f"{t.muted}",
    )
    content.append(
        f"   →  [{dom_color}]{dominant.upper()} ({dom_pct*100:.0f}%)[/]",
    )
    content.append(f"\n  [{t.muted}]Run VERDICT for full horizon analysis[/]")

    from rich.panel import Panel
    console.print(
        Panel(
            content,
            title=f"[jev.label]◆ Jev — Quick Verdict ({timeframe})[/jev.label]",
            border_style=f"{t.jev}",
            padding=(0, 1),
        )
    )


def _verdict_bar(buy: float, hold: float, sell: float, width: int = 40) -> str:
    """Render an inline verdict distribution bar using block characters."""
    buy_w  = round(buy  * width)
    hold_w = round(hold * width)
    sell_w = width - buy_w - hold_w

    # Use Rich markup inline won't work in Text directly, build as plain string
    # for embedding in Rich Text objects
    bar = (
        "[positive]" + "█" * buy_w + "[/positive]"
        + "[warning]" + "█" * hold_w + "[/warning]"
        + "[negative]" + "█" * sell_w + "[/negative]"
    )
    return bar
