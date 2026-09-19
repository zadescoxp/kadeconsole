"""
pages/gp.py — GP command: in-terminal price chart.

Renders a plotext price chart with SMA20/SMA50 overlays.
Updates session.timeframe if a timeframe modifier was provided.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console

from kadeconsole.render.theme import t, RICH_THEME
from kadeconsole.render.charts import price_chart
from kadeconsole.indicators.moving_averages import sma

if TYPE_CHECKING:
    from kadeconsole.core.session import Session
    from kadeconsole.core.parser import ParsedCommand
    from kadeconsole.providers.base import DataProvider

console = Console(theme=RICH_THEME)


def render_gp(
    session: "Session",
    parsed: "ParsedCommand",
    provider: "DataProvider",
) -> None:
    """Render the GP (price chart) page."""
    symbol = session.yf_symbol

    # Update session timeframe if modifier provided
    if parsed.timeframe:
        session.set_timeframe(parsed.timeframe)

    timeframe = session.timeframe
    console.print(f"\n[muted]  Loading chart for {symbol} ({timeframe})...[/muted]")

    try:
        history = provider.get_price_history(symbol, period=timeframe)
    except Exception as exc:
        console.print(f"[negative]  GP error: {exc}[/negative]")
        return

    closes  = history.get("closes", [])
    dates   = history.get("dates", [])
    highs   = history.get("highs", [])
    lows    = history.get("lows", [])
    volumes = history.get("volumes", [])

    if not closes:
        console.print("[muted]  No price data available for this period.[/muted]")
        return

    # Compute SMA overlays
    sma20_vals = sma(closes, 20)
    sma50_vals = sma(closes, 50)

    # plotext renders inline
    price_chart(
        dates    = dates,
        closes   = closes,
        symbol   = symbol,
        timeframe= timeframe,
        sma20    = sma20_vals,
        sma50    = sma50_vals,
    )

    # Print volume and range summary below the chart
    if closes:
        lo, hi = min(closes), max(closes)
        cur = closes[-1]
        first = closes[0]
        pct = ((cur - first) / first * 100) if first else 0.0
        vol_avg = sum(volumes) / len(volumes) if volumes else 0
        color = "positive" if pct >= 0 else "negative"
        arrow = "▲" if pct >= 0 else "▼"

        console.print(
            f"  [dim_text]Open: {first:,.2f}[/dim_text]  "
            f"[dim_text]Close: {cur:,.2f}[/dim_text]  "
            f"[{color}]{arrow} {abs(pct):.2f}% ({timeframe})[/]  "
            f"[muted]Lo: {lo:,.2f}  Hi: {hi:,.2f}  Avg Vol: {vol_avg:,.0f}[/muted]"
        )

    console.print(f"  [muted]SMA20 (cyan)  ·  SMA50 (blue)  ·  {len(dates)} bars[/muted]\n")
