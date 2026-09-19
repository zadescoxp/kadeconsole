"""
pages/verdict.py — VERDICT command: Jev buy/sell/hold distribution page.

Renders:
  - Multi-horizon verdict bars (3M, 1Y, 3Y)
  - Dominant signal with confidence
  - Timeframe-conditioned recommendation
  - Confidence/uncertainty flag (low analyst coverage, thin data)
"""

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from kadeconsole.render.theme import t, RICH_THEME, STYLE_MUTED
from kadeconsole.render.tables import jev_unavailable_panel

if TYPE_CHECKING:
    from kadeconsole.core.session import Session
    from kadeconsole.providers.base import DataProvider
    from kadeconsole.jev.client import JevClient

console = Console(theme=RICH_THEME)


def render_verdict(
    session: "Session",
    provider: "DataProvider",
    jev: "JevClient",
) -> None:
    """Render the VERDICT page with Jev probability distribution."""
    symbol = session.yf_symbol

    # Always fetch info for data quality check
    try:
        info = provider.get_info(symbol)
    except Exception as exc:
        console.print(f"[negative]  VERDICT error fetching data: {exc}[/negative]")
        return

    name = info.get("name", symbol)

    console.print(f"\n[muted]  Requesting Jev verdict for {symbol}...[/muted]")

    if not jev.available:
        console.print(
            Panel(
                jev_unavailable_panel("Add your TypeSafe API key to enable VERDICT analysis."),
                title=f"[header]VERDICT — {name}[/header]",
                border_style=f"{t.border}",
            )
        )
        return

    from kadeconsole.jev.verdicts import get_multi_horizon_verdict
    horizons = get_multi_horizon_verdict(jev, info, symbol)

    if all(v is None for v in horizons.values()):
        console.print("[negative]  Jev verdict unavailable — check your API key or try again.[/negative]")
        return

    # ── Build verdict table ────────────────────────────────────────────────────
    table = Table(
        show_header=True,
        header_style=f"bold {t.accent}",
        box=box.SIMPLE_HEAVY,
        border_style=f"{t.border}",
        padding=(0, 2),
    )
    table.add_column("Horizon",   style=f"bold {t.text}", width=10)
    table.add_column("BUY",       justify="center", width=8)
    table.add_column("HOLD",      justify="center", width=8)
    table.add_column("SELL",      justify="center", width=8)
    table.add_column("Signal",    justify="left",   width=14)
    table.add_column("Distribution", justify="left", width=42)

    for horizon, verdict in horizons.items():
        if verdict is None:
            table.add_row(horizon, "—", "—", "—", "Unavailable", Text("—", style=STYLE_MUTED))
            continue

        buy  = verdict["buy"]
        hold = verdict["hold"]
        sell = verdict["sell"]

        dominant = max(verdict, key=lambda k: verdict[k])
        dom_pct  = verdict[dominant]

        color_map = {"buy": t.positive, "hold": t.accent, "sell": t.negative}
        dom_color = color_map[dominant]

        # Signal cell
        signal_text = Text(f"{dominant.upper()} ({dom_pct*100:.0f}%)", style=f"bold {dom_color}")

        # Distribution bar
        bar = _make_bar(buy, hold, sell, width=36)

        table.add_row(
            horizon,
            Text(f"{buy*100:.0f}%",  style=f"{t.positive}"),
            Text(f"{hold*100:.0f}%", style=f"{t.accent}"),
            Text(f"{sell*100:.0f}%", style=f"{t.negative}"),
            signal_text,
            bar,
        )

    # ── Data quality / confidence flag ─────────────────────────────────────────
    confidence_note = _build_confidence_note(info)

    content_group = [table]
    if confidence_note:
        content_group.append(Text(f"\n  ⚠  {confidence_note}", style=f"italic {t.warning}"))

    from rich.console import Group
    console.print(
        Panel(
            Group(*content_group),
            title=f"[jev.label]◆ VERDICT — {name}[/jev.label]",
            border_style=f"{t.jev}",
            padding=(1, 1),
        )
    )

    console.print(
        f"  [muted]Jev conditions verdict on fundamentals + valuation + analyst consensus. "
        f"This is not financial advice.[/muted]\n"
    )


def _make_bar(buy: float, hold: float, sell: float, width: int = 36) -> Text:
    """Render a colored block-character distribution bar."""
    buy_w  = round(buy  * width)
    hold_w = round(hold * width)
    sell_w = width - buy_w - hold_w

    bar = Text()
    bar.append("█" * buy_w,  style=f"{t.positive}")
    bar.append("█" * hold_w, style=f"{t.accent}")
    bar.append("█" * sell_w, style=f"{t.negative}")

    # Labels
    bar.append(
        f"  [{t.positive}]Buy[/]  [{t.accent}]Hold[/]  [{t.negative}]Sell[/]"
    )
    return bar


def _build_confidence_note(info: dict) -> Optional[str]:
    """Flag data quality issues that reduce Jev confidence."""
    issues = []
    num_analysts = info.get("num_analyst_opinions")
    if num_analysts is not None and num_analysts < 3:
        issues.append(f"Low analyst coverage ({num_analysts} analysts)")
    if info.get("trailing_pe") is None and info.get("forward_pe") is None:
        issues.append("Valuation ratios unavailable")
    if info.get("revenue_growth") is None and info.get("earnings_growth") is None:
        issues.append("Growth data unavailable")

    if issues:
        return "Jev confidence is reduced: " + "; ".join(issues) + ". Interpret with caution."
    return None
