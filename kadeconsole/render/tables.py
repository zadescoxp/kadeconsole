"""
render/tables.py — Reusable Rich table builders and number formatters.

All number formatting lives here. Rules:
  - Values ≥ 1B  → "1.23B"
  - Values ≥ 1M  → "4.56M"
  - Values ≥ 1K  → "789.0K"
  - Smaller       → "123.45" (2 decimal places)
  - Percentages   → "12.34%"
  - N/A sentinel  → "—"

Tables always right-align numbers, left-align labels.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from kadeconsole.render.theme import (
    t, RICH_THEME, STYLE_ACCENT, STYLE_POSITIVE, STYLE_NEGATIVE,
    STYLE_MUTED, STYLE_JEV, delta_style,
)

console = Console(theme=RICH_THEME)

_NA = "—"

# ── Number Formatters ──────────────────────────────────────────────────────────

def fmt_number(value: Any, decimals: int = 2) -> str:
    """Format a number with B/M/K suffix and thousands separators."""
    if value is None:
        return _NA
    try:
        v = float(value)
    except (TypeError, ValueError):
        return _NA

    if abs(v) >= 1_000_000_000:
        return f"{v / 1_000_000_000:.{decimals}f}B"
    if abs(v) >= 1_000_000:
        return f"{v / 1_000_000:.{decimals}f}M"
    if abs(v) >= 1_000:
        return f"{v / 1_000:.{decimals}f}K"
    return f"{v:,.{decimals}f}"


def fmt_pct(value: Any, decimals: int = 2) -> str:
    """Format a ratio (0.0–1.0 or 0–100) as a percentage string."""
    if value is None:
        return _NA
    try:
        v = float(value)
    except (TypeError, ValueError):
        return _NA
    # yfinance returns margins as decimals (0.21 = 21%)
    if abs(v) <= 1.5:
        v *= 100
    return f"{v:.{decimals}f}%"


def fmt_ratio(value: Any, decimals: int = 2) -> str:
    """Format a plain ratio/multiple (P/E, P/B, etc.)."""
    if value is None:
        return _NA
    try:
        v = float(value)
        return f"{v:.{decimals}f}x"
    except (TypeError, ValueError):
        return _NA


def fmt_price(value: Any, currency: str = "") -> str:
    """Format a price with optional currency prefix."""
    if value is None:
        return _NA
    try:
        v = float(value)
        prefix = f"{currency} " if currency else ""
        return f"{prefix}{v:,.2f}"
    except (TypeError, ValueError):
        return _NA


def fmt_delta_str(value: Any, pct: bool = True) -> str:
    """Return plain string delta (no markup) with arrow."""
    if value is None:
        return _NA
    try:
        v = float(value)
        arrow = "▲" if v >= 0 else "▼"
        sign = "+" if v >= 0 else ""
        fmt = f"{abs(v):.2f}{'%' if pct else ''}"
        return f"{arrow} {sign}{fmt}"
    except (TypeError, ValueError):
        return _NA


def color_delta(value: Any, pct: bool = True) -> Text:
    """Return a Rich Text object for a signed delta with color."""
    raw = fmt_delta_str(value, pct)
    if raw == _NA:
        return Text(_NA, style=STYLE_MUTED)
    try:
        v = float(value)
        style = STYLE_POSITIVE if v >= 0 else STYLE_NEGATIVE
        return Text(raw, style=style)
    except (TypeError, ValueError):
        return Text(raw, style=STYLE_MUTED)


# ── Table Builders ─────────────────────────────────────────────────────────────

def kv_table(
    rows: Sequence[tuple[str, Any]],
    title: Optional[str] = None,
    col_widths: tuple[int, int] = (28, 18),
) -> Table:
    """
    Build a 2-column key-value Rich table.

    rows: list of (label, value) tuples.
    Values that are None render as "—" in muted style.
    """
    table = Table(
        show_header=False,
        box=None,
        padding=(0, 1),
        expand=False,
    )
    table.add_column("label", style=f"{t.dim_text}", width=col_widths[0], no_wrap=True)
    table.add_column("value", style=f"{t.text}", width=col_widths[1], justify="right", no_wrap=True)

    for label, value in rows:
        if value is None:
            val_text = Text(_NA, style=STYLE_MUTED)
        elif isinstance(value, Text):
            val_text = value
        else:
            val_text = Text(str(value), style=f"{t.text}")
        table.add_row(label, val_text)

    return table


def section_table(
    columns: list[str],
    rows: list[list[Any]],
    title: Optional[str] = None,
    highlight_col: Optional[int] = None,
) -> Table:
    """
    Build a multi-column data table (for FA fundamentals, HP, etc.).

    columns: header names
    rows: list of row value lists (same length as columns)
    highlight_col: index of column to render in accent color
    """
    table = Table(
        title=title,
        title_style=STYLE_ACCENT,
        show_header=True,
        header_style=f"bold {t.accent}",
        border_style=f"{t.border}",
        box=_rounded_box(),
        padding=(0, 1),
        expand=False,
    )

    for i, col in enumerate(columns):
        justify = "right" if i > 0 else "left"
        style = f"{t.accent}" if i == highlight_col else f"{t.text}"
        table.add_column(col, justify=justify, style=style, no_wrap=True)

    for row in rows:
        str_row = []
        for cell in row:
            if isinstance(cell, Text):
                str_row.append(cell)
            elif cell is None:
                str_row.append(Text(_NA, style=STYLE_MUTED))
            else:
                str_row.append(str(cell))
        table.add_row(*str_row)

    return table


def jev_panel(content: str, label: str = "Jev") -> Panel:
    """Render a Jev output block as a styled panel."""
    return Panel(
        f"[jev]{content}[/jev]",
        title=f"[jev.label]◆ {label}[/jev.label]",
        border_style=f"{t.jev}",
        padding=(0, 1),
    )


def jev_unavailable_panel(reason: str = "Set TYPESAFE_API_KEY to enable Jev AI analysis") -> Panel:
    """Render a graceful 'Jev unavailable' placeholder."""
    return Panel(
        f"[muted]{reason}[/muted]",
        title=f"[muted]◆ Jev — Unavailable[/muted]",
        border_style=f"{t.muted}",
        padding=(0, 1),
    )


def page_panel(content: Any, title: str, subtitle: str = "") -> Panel:
    """Wrap page content in a branded Panel."""
    full_title = f"[header]{title}[/header]"
    if subtitle:
        full_title += f"  [muted]{subtitle}[/muted]"
    return Panel(content, title=full_title, border_style=f"{t.border}", padding=(0, 1))


# ── Internal box style ─────────────────────────────────────────────────────────

def _rounded_box():
    """Return a subtle Rich box style."""
    from rich import box as rich_box
    return rich_box.SIMPLE_HEAVY
