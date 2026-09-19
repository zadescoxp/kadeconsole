"""
pages/hp.py — HP command: historical OHLCV table.

Displays the last N bars of OHLCV data with daily return %,
formatted as a Rich table. Defaults to last 30 rows.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from kadeconsole.render.theme import t, RICH_THEME, STYLE_POSITIVE, STYLE_NEGATIVE, STYLE_MUTED
from kadeconsole.render.tables import fmt_number

if TYPE_CHECKING:
    from kadeconsole.core.session import Session
    from kadeconsole.core.parser import ParsedCommand
    from kadeconsole.providers.base import DataProvider

console = Console(theme=RICH_THEME)

_MAX_ROWS = 30


def render_hp(
    session: "Session",
    parsed: "ParsedCommand",
    provider: "DataProvider",
) -> None:
    """Render the HP (historical price) page."""
    symbol = session.yf_symbol

    if parsed.timeframe:
        session.set_timeframe(parsed.timeframe)

    timeframe = session.timeframe
    console.print(f"\n[muted]  Fetching OHLCV for {symbol} ({timeframe})...[/muted]")

    try:
        history = provider.get_price_history(symbol, period=timeframe)
    except Exception as exc:
        console.print(f"[negative]  HP error: {exc}[/negative]")
        return

    dates   = history.get("dates",   [])
    opens   = history.get("opens",   [])
    highs   = history.get("highs",   [])
    lows    = history.get("lows",    [])
    closes  = history.get("closes",  [])
    volumes = history.get("volumes", [])

    if not closes:
        console.print("[muted]  No historical data available.[/muted]")
        return

    # Show only last _MAX_ROWS (most recent at top)
    n = len(dates)
    start = max(0, n - _MAX_ROWS)
    # Reverse so most recent is first
    s_dates   = list(reversed(dates[start:]))
    s_opens   = list(reversed(opens[start:]))
    s_highs   = list(reversed(highs[start:]))
    s_lows    = list(reversed(lows[start:]))
    s_closes  = list(reversed(closes[start:]))
    s_volumes = list(reversed(volumes[start:]))

    # Build table
    table = Table(
        show_header=True,
        header_style=f"bold {t.accent}",
        box=box.SIMPLE_HEAVY,
        border_style=f"{t.border}",
        padding=(0, 1),
        expand=False,
    )
    table.add_column("Date",    style=f"{t.dim_text}", no_wrap=True, width=12)
    table.add_column("Open",    justify="right", style=f"{t.text}", width=10)
    table.add_column("High",    justify="right", style=f"{t.positive}", width=10)
    table.add_column("Low",     justify="right", style=f"{t.negative}", width=10)
    table.add_column("Close",   justify="right", style=f"bold {t.text}", width=10)
    table.add_column("Volume",  justify="right", style=f"{t.muted}", width=10)
    table.add_column("Change",  justify="right", width=10)

    prev_close: float | None = None
    for i, (d, o, h, l, c, v) in enumerate(
        zip(s_dates, s_opens, s_highs, s_lows, s_closes, s_volumes)
    ):
        # Day return vs previous close (in reversed order, prev = next index)
        if i < len(s_closes) - 1:
            prev_close = s_closes[i + 1]
        else:
            prev_close = o  # fallback to open for oldest bar

        if prev_close and prev_close != 0:
            chg = (c - prev_close) / prev_close * 100
            arrow = "▲" if chg >= 0 else "▼"
            style = STYLE_POSITIVE if chg >= 0 else STYLE_NEGATIVE
            chg_cell = Text(f"{arrow} {abs(chg):.2f}%", style=style)
        else:
            chg_cell = Text("—", style=STYLE_MUTED)

        table.add_row(
            d,
            f"{o:,.2f}",
            f"{h:,.2f}",
            f"{l:,.2f}",
            f"{c:,.2f}",
            fmt_number(v, 1),
            chg_cell,
        )

    console.print(
        Panel(
            table,
            title=f"[header]HP — {symbol}  ({timeframe})  [muted]Last {min(n, _MAX_ROWS)} bars[/muted][/header]",
            border_style=f"{t.accent}",
            padding=(0, 1),
        )
    )
    if n > _MAX_ROWS:
        console.print(f"[muted]  Showing {_MAX_ROWS} of {n} bars. Use EXPORT CSV to get the full dataset.[/muted]\n")
