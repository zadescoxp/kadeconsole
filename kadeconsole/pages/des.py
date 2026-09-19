"""
pages/des.py — DES command: company description page.

Renders:
  - Company identity panel (name, sector, industry, country, exchange, employees, website)
  - Key people (CEO)
  - Business summary (word-wrapped)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich import box

from kadeconsole.render.theme import t, RICH_THEME
from kadeconsole.render.tables import kv_table, fmt_number

if TYPE_CHECKING:
    from kadeconsole.core.session import Session
    from kadeconsole.providers.base import DataProvider

console = Console(theme=RICH_THEME)


def render_des(session: "Session", provider: "DataProvider") -> None:
    """Render the DES (company description) page."""
    symbol = session.yf_symbol
    console.print(f"\n[muted]  Fetching description for {symbol}...[/muted]")

    try:
        info = provider.get_info(symbol)
    except Exception as exc:
        console.print(f"[negative]  DES error: {exc}[/negative]")
        return

    name     = info.get("name", symbol)
    sector   = info.get("sector")
    industry = info.get("industry")
    country  = info.get("country")
    exchange = info.get("exchange")
    currency = info.get("currency", "USD")
    employees = info.get("employees")
    website  = info.get("website")
    ceo      = info.get("ceo")
    mkt_cap  = info.get("market_cap")
    founded  = info.get("founded_year")
    description = info.get("description")

    # ── Identity table ─────────────────────────────────────────────────────────
    identity_rows = [
        ("Full Name",      name),
        ("Sector",         sector),
        ("Industry",       industry),
        ("Country",        country),
        ("Exchange",       exchange),
        ("Currency",       currency),
        ("Market Cap",     fmt_number(mkt_cap)),
        ("Employees",      f"{employees:,}" if employees else None),
        ("Website",        website),
        ("CEO",            ceo),
    ]
    if founded:
        identity_rows.insert(-1, ("Founded", str(founded)))

    identity_table = kv_table(identity_rows, col_widths=(20, 35))

    console.print(
        Panel(
            identity_table,
            title=f"[header]DES — {name}[/header]",
            border_style=f"{t.accent}",
            padding=(1, 2),
        )
    )

    # ── Business summary ───────────────────────────────────────────────────────
    if description:
        # Truncate to ~800 chars for readability; users can scroll
        display = description[:800]
        if len(description) > 800:
            display += " [dim]…[/dim]"

        console.print(
            Panel(
                f"[{t.text}]{display}[/]",
                title=f"[header]Business Summary[/header]",
                border_style=f"{t.border}",
                padding=(1, 2),
            )
        )
    else:
        console.print(Panel("[muted]No business summary available.[/muted]", border_style=t.border))
