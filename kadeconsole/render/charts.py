"""
render/charts.py — plotext-based in-terminal price and indicator charts.

Handles terminal width detection and degrades gracefully to a text
summary when plotext is unavailable or the terminal is non-capable.
"""

from __future__ import annotations

import shutil
from typing import Optional, Sequence

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from kadeconsole.render.theme import t, RICH_THEME

console = Console(theme=RICH_THEME)

try:
    import plotext as plt
    _PLT_AVAILABLE = True
except ImportError:
    _PLT_AVAILABLE = False


def _terminal_width() -> int:
    """Return usable terminal width, capped sensibly."""
    cols, _ = shutil.get_terminal_size(fallback=(120, 40))
    # Leave some margin for panel borders
    return min(max(cols - 6, 60), 200)


def _terminal_height() -> int:
    """Return usable terminal height for chart."""
    _, rows = shutil.get_terminal_size(fallback=(120, 40))
    return min(max(rows // 2, 18), 36)


def price_chart(
    dates: Sequence[str],
    closes: Sequence[float],
    symbol: str,
    timeframe: str = "1Y",
    sma20: Optional[Sequence[float]] = None,
    sma50: Optional[Sequence[float]] = None,
) -> None:
    """
    Render an in-terminal price chart using plotext.

    Falls back to a plain Rich text summary if plotext is unavailable
    or the terminal cannot render the chart.
    """
    if not _PLT_AVAILABLE or not dates or not closes:
        _fallback_price_summary(closes, symbol, timeframe)
        return

    try:
        _render_price_chart(dates, closes, symbol, timeframe, sma20, sma50)
    except Exception:  # noqa: BLE001
        _fallback_price_summary(closes, symbol, timeframe)


def _render_price_chart(
    dates: Sequence[str],
    closes: Sequence[float],
    symbol: str,
    timeframe: str,
    sma20: Optional[Sequence[float]],
    sma50: Optional[Sequence[float]],
) -> None:
    """Internal: render via plotext."""
    width = _terminal_width()
    height = _terminal_height()

    plt.clf()
    plt.theme("dark")

    # Subsample dates for x-axis labels (plotext handles dense series poorly)
    step = max(1, len(dates) // 8)
    x_labels = list(range(len(dates)))
    sampled_labels = {i: dates[i] for i in range(0, len(dates), step)}

    plt.plot(x_labels, list(closes), color="orange", label=symbol)

    if sma20 and len(sma20) == len(closes):
        plt.plot(x_labels, list(sma20), color="cyan", label="SMA20")

    if sma50 and len(sma50) == len(closes):
        plt.plot(x_labels, list(sma50), color="blue+", label="SMA50")

    # Price range annotation
    lo, hi = min(closes), max(closes)
    pct_change = ((closes[-1] - closes[0]) / closes[0]) * 100 if closes[0] else 0
    direction = "▲" if pct_change >= 0 else "▼"
    title = f"{symbol}  {timeframe}  |  {direction} {pct_change:+.2f}%  Lo:{lo:,.2f}  Hi:{hi:,.2f}"

    plt.title(title)
    plt.xlabel("")
    plt.plotsize(width, height)
    plt.show()


def _fallback_price_summary(
    closes: Sequence[float],
    symbol: str,
    timeframe: str,
) -> None:
    """Render a simple text summary when chart can't be drawn."""
    if not closes:
        console.print(Panel("[muted]No price data available.[/muted]", title="GP", border_style=t.muted))
        return

    lo, hi = min(closes), max(closes)
    cur = closes[-1]
    first = closes[0]
    pct = ((cur - first) / first * 100) if first else 0.0
    color = "positive" if pct >= 0 else "negative"
    arrow = "▲" if pct >= 0 else "▼"

    lines = [
        f"[dim_text]Symbol:[/dim_text]  [{t.accent}]{symbol}[/]  [{t.muted}]({timeframe})[/]",
        f"[dim_text]Current:[/dim_text] [{t.white}]{cur:,.2f}[/]  [{color}]{arrow} {pct:+.2f}%[/]",
        f"[dim_text]Range:[/dim_text]   [{t.muted}]{lo:,.2f}[/] — [{t.muted}]{hi:,.2f}[/]",
        f"\n[{t.muted}](Install plotext or use a modern terminal for the full chart.)[/]",
    ]
    console.print(Panel("\n".join(lines), title=f"[header]GP — {symbol}[/header]", border_style=t.border))


def sparkline(values: Sequence[float], width: int = 20) -> str:
    """Return a single-line Unicode sparkline string for a data series."""
    if not values:
        return "—" * width

    blocks = "▁▂▃▄▅▆▇█"
    lo, hi = min(values), max(values)
    span = hi - lo or 1

    # Subsample to desired width
    step = max(1, len(values) // width)
    sampled = [values[i] for i in range(0, len(values), step)][:width]

    return "".join(blocks[int((v - lo) / span * (len(blocks) - 1))] for v in sampled)
