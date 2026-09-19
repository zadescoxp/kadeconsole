"""
pages/help.py — HELP / ? command: formatted command reference.

Renders a comprehensive command reference that looks and feels like
documentation from a real financial terminal — not a script's print().
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.rule import Rule
from rich.columns import Columns
from rich import box

from kadeconsole.render.theme import t, RICH_THEME
from kadeconsole import __version__

console = Console(theme=RICH_THEME)


def render_help() -> None:
    """Render the full HELP page."""
    _print_banner()
    _print_command_reference()
    _print_tips()


def _print_banner() -> None:
    """Print a compact header for the help page."""
    console.print(
        Panel(
            Text.from_markup(
                f"  [bold {t.accent}]kadeConsole[/bold {t.accent}]  "
                f"[{t.muted}]v{__version__}[/{t.muted}]  ·  "
                f"[{t.dim_text}]Bloomberg-style equity research · Free & open source[/{t.dim_text}]\n"
                f"  [{t.muted}]Powered by yfinance + Jev (TypeSafe AI) · "
                f"https://github.com/kade-console/kade-console[/{t.muted}]"
            ),
            border_style=f"{t.accent}",
            padding=(0, 1),
        )
    )


def _cmd_table(rows: list[tuple[str, str, str]]) -> Table:
    """Build a 3-column command reference table: Command | Syntax | Description."""
    table = Table(
        show_header=True,
        header_style=f"bold {t.muted}",
        box=box.SIMPLE,
        padding=(0, 2),
        expand=False,
        border_style=f"{t.border}",
    )
    table.add_column("COMMAND",     style=f"bold {t.accent}", no_wrap=True, width=22)
    table.add_column("SYNTAX",      style=f"{t.dim_text}",    no_wrap=True, width=30)
    table.add_column("DESCRIPTION", style=f"{t.text}",        width=60)

    for cmd, syntax, desc in rows:
        table.add_row(cmd, syntax, desc)
    return table


def _print_command_reference() -> None:
    """Print the full command reference organised by category."""

    # ── Security Resolution ────────────────────────────────────────────────────
    console.print(f"\n[header]  SECURITY RESOLUTION[/header]")
    console.print(_cmd_table([
        ("EQUITY",   "<TICKER> EQUITY",              "Resolve a US security and open a session"),
        ("",         "<TICKER> <EXCH> EQUITY",        "Specify exchange (e.g. AAPL US EQUITY)"),
        ("",         "<TICKER> <CC> <EXCH> EQUITY",   "Bloomberg grammar: RELIANCE IN NS EQUITY"),
    ]))

    console.print(f"\n[{t.muted}]  Supported exchanges:[/]  "
                  f"[{t.dim_text}]NS (NSE), BO (BSE), LN (LSE), PA (Euronext Paris), "
                  f"DE (Frankfurt), HK, TK (Tokyo), AU (ASX), US[/]")

    # ── Data Pages ────────────────────────────────────────────────────────────
    console.print(f"\n[header]  DATA PAGES[/header]")
    console.print(_cmd_table([
        ("DES",     "DES",          "Company description · sector · key people · business summary"),
        ("FA",      "FA",           "Full fundamentals: valuation · margins · growth · balance sheet"),
        ("FA Q",    "FA Q",         "Same as FA, quarterly granularity instead of annual"),
        ("GP",      "GP",           "In-terminal 1Y price chart with SMA20/SMA50 overlays"),
        ("GP [TF]", "GP 6M",        "Price chart with specific timeframe (1D 5D 1M 3M 6M 1Y 2Y 5Y)"),
        ("HP",      "HP",           "Historical OHLCV table · last 30 bars · color-coded returns"),
        ("HP [TF]", "HP 3M",        "Same, with specific timeframe"),
    ]))

    # ── Jev AI Pages ─────────────────────────────────────────────────────────
    console.print(f"\n[header]  JEV AI ANALYSIS[/header]  [{t.muted}](requires TYPESAFE_API_KEY)[/]")
    console.print(_cmd_table([
        ("VERDICT",  "VERDICT",     "Buy/hold/sell probability distribution · 3M, 1Y, 3Y horizons"),
        ("RATE",     "RATE",        "4-axis fundamental rating: Valuation · Growth · Quality · Momentum"),
    ]))

    # ── Coming in Phase 2/3 ───────────────────────────────────────────────────
    console.print(f"\n[header]  COMING IN PHASE 2/3[/header]  [{t.muted}](not yet available)[/]")
    console.print(_cmd_table([
        ("TA",       "TA",          "Technical panel: RSI · MACD · Bollinger Bands · volume"),
        ("NI",       "NI",          "Recent news with Jev sentiment tags + why-it-matters"),
        ("RV",       "RV",          "Relative valuation vs sector/index peers"),
        ("COMPARE",  "COMPARE MSFT","Side-by-side fundamentals + Jev comparative verdict"),
        ("MACRO",    "MACRO",       "Macro indicators + Jev linkage narrative for this stock"),
        ("SCREEN",   'SCREEN "..."',"Natural-language Jev-driven screen: 'cash-rich, low debt'"),
        ("WATCH",    "WATCH ADD <T>","Persistent watchlist with refreshable one-line verdicts"),
        ("EXPORT",   "EXPORT CSV",  "Dump current page to CSV / Markdown / JSON"),
        ("SOURCE",   "SOURCE <P>",  "Override data provider: alpaca, alphavantage, polygon"),
    ]))

    # ── Session & Utility ─────────────────────────────────────────────────────
    console.print(f"\n[header]  SESSION & UTILITY[/header]")
    console.print(_cmd_table([
        ("HELP",   "HELP  or  ?",  "Show this command reference"),
        ("EXIT",   "EXIT  or  Q",  "Exit kadeConsole"),
    ]))


def _print_tips() -> None:
    """Print quick-start tips and config hints."""
    console.print()
    console.print(Rule(style=f"{t.border}"))
    console.print(
        f"\n  [{t.dim_text}]QUICK START[/]  "
        f"[{t.muted}]AAPL EQUITY  →  FA  →  GP  →  VERDICT[/]\n"
    )
    console.print(
        f"  [{t.dim_text}]CONFIG[/]       "
        f"[{t.muted}]~/.kadeconsole/config.yaml  —  set TYPESAFE_API_KEY for Jev AI[/]\n"
    )
    console.print(
        f"  [{t.dim_text}]SESSIONS[/]     "
        f"[{t.muted}]Ticker/timeframe stay active until changed. "
        f"Commands after EQUITY resolve omit the ticker.[/]\n"
    )
    console.print(
        f"  [{t.dim_text}]TIMEFRAMES[/]   "
        f"[{t.muted}]1D  5D  1M  3M  6M  1Y  2Y  5Y[/]\n"
    )
    console.print(Rule(style=f"{t.border}"))
