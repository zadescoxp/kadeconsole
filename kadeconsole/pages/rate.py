"""
pages/rate.py — RATE command: Jev multi-axis fundamental rating page.

Renders a 4-axis scoring table:
  Axis       | Score (bar) | Label      | Reason (one line)
  Valuation  | ████░░░░░░  | Average    | Fairly valued at current multiples
  Growth     | ████████░░  | Strong     | Accelerating revenue and earnings growth
  Quality    | ███████░░░  | Above Avg  | High-quality business with strong cash gen
  Momentum   | █████░░░░░  | Average    | Mixed signals, sideways price action
  ─────────────────────────────────────────
  Composite  | 6.8 / 10
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.rule import Rule
from rich import box

from kadeconsole.render.theme import t, RICH_THEME
from kadeconsole.render.tables import jev_unavailable_panel

if TYPE_CHECKING:
    from kadeconsole.core.session import Session
    from kadeconsole.providers.base import DataProvider
    from kadeconsole.jev.client import JevClient

console = Console(theme=RICH_THEME)

_BAR_WIDTH = 20  # characters for the score bar


def render_rate(
    session: "Session",
    provider: "DataProvider",
    jev: "JevClient",
) -> None:
    """Render the RATE (multi-axis fundamental rating) page."""
    symbol = session.yf_symbol

    try:
        info = provider.get_info(symbol)
    except Exception as exc:
        console.print(f"[negative]  RATE error fetching data: {exc}[/negative]")
        return

    name = info.get("name", symbol)
    console.print(f"\n[muted]  Requesting Jev rating for {symbol}...[/muted]")

    if not jev.available:
        console.print(
            Panel(
                jev_unavailable_panel("Add your TypeSafe API key to enable RATE analysis."),
                title=f"[header]RATE — {name}[/header]",
                border_style=f"{t.border}",
            )
        )
        return

    from kadeconsole.jev.ratings import get_rating, FundamentalRating
    rating = get_rating(jev, info, symbol)

    if rating is None:
        console.print("[negative]  Jev rating unavailable — check your API key or try again.[/negative]")
        return

    _render_rating_table(rating, name, symbol)


def _render_rating_table(
    rating: "FundamentalRating",
    name: str,
    symbol: str,
) -> None:
    """Render the 4-axis rating table."""
    table = Table(
        show_header=True,
        header_style=f"bold {t.accent}",
        box=box.SIMPLE_HEAVY,
        border_style=f"{t.border}",
        padding=(0, 2),
        expand=False,
    )

    table.add_column("Axis",   style=f"bold {t.text}", width=12)
    table.add_column("Score",  justify="right",         width=8)
    table.add_column("",       justify="left",          width=_BAR_WIDTH + 2)  # bar
    table.add_column("Label",  justify="left",          width=16)
    table.add_column("Jev Analysis", justify="left",    width=55)

    for axis in rating.axes:
        score_text = Text(f"{axis.score:.1f}/10", style=f"bold {_score_color(axis.score)}")
        bar        = _score_bar(axis.score)
        label_text = Text(axis.label, style=f"italic {_score_color(axis.score)}")
        reason_text = Text(axis.reason or "—", style=f"italic {t.jev}")

        table.add_row(axis.axis, score_text, bar, label_text, reason_text)

    # Composite row
    comp = rating.composite
    comp_bar = _score_bar(comp)
    table.add_row(
        Rule(style=f"{t.border}"),
        "", "", "", "",
    )
    table.add_row(
        Text("Composite", style=f"bold {t.accent}"),
        Text(f"{comp:.1f}/10", style=f"bold {_score_color(comp)}"),
        comp_bar,
        Text(_composite_label(comp), style=f"bold {_score_color(comp)}"),
        Text("", style=""),
    )

    from rich.console import Group
    console.print(
        Panel(
            Group(table),
            title=f"[jev.label]◆ RATE — {name}[/jev.label]",
            border_style=f"{t.jev}",
            padding=(1, 1),
        )
    )

    console.print(
        f"  [muted]Scored by Jev on: Valuation · Growth · Quality · Momentum[/muted]\n"
    )


def _score_bar(score: float, width: int = _BAR_WIDTH) -> Text:
    """Render a score bar: filled + empty blocks."""
    filled = round(score / 10 * width)
    empty  = width - filled
    color  = _score_color(score)
    bar    = Text()
    bar.append("█" * filled, style=color)
    bar.append("░" * empty,  style=f"{t.border}")
    return bar


def _score_color(score: float) -> str:
    if score >= 7.5: return t.positive
    if score >= 5.5: return t.accent
    if score >= 4.0: return t.warning
    return t.negative


def _composite_label(score: float) -> str:
    if score >= 8.0: return "Exceptional"
    if score >= 6.5: return "Above Average"
    if score >= 5.0: return "Average"
    if score >= 3.5: return "Below Average"
    return "Weak"
