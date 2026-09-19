"""
cli.py — kadeConsole REPL entrypoint.

Entry point: `kadeconsole` (via pyproject.toml console_scripts)

Startup sequence:
  1. Load config from ~/.kadeconsole/config.yaml
  2. Initialise provider registry + Jev client + SQLite cache
  3. Print startup banner
  4. Drop into prompt_toolkit REPL loop
  5. Parse each input line → Router.dispatch() → continue or exit
"""

from __future__ import annotations

import sys
from typing import Optional

from rich.console import Console

from kadeconsole.render.theme import RICH_THEME, t
from kadeconsole import __version__

console = Console(theme=RICH_THEME)

# ── Banner ─────────────────────────────────────────────────────────────────────
_BANNER = r"""
  ██╗  ██╗ █████╗ ██████╗ ███████╗
  ██║ ██╔╝██╔══██╗██╔══██╗██╔════╝
  █████╔╝ ███████║██║  ██║█████╗
  ██╔═██╗ ██╔══██║██║  ██║██╔══╝
  ██║  ██╗██║  ██║██████╔╝███████╗
  ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚══════╝
"""


def _print_banner() -> None:
    console.print(f"[accent]{_BANNER}[/accent]", highlight=False)
    console.print(
        f"  [bold {t.accent}]CONSOLE[/bold {t.accent}]  "
        f"[{t.muted}]v{__version__}[/]  "
        f"[{t.dim_text}]·  Bloomberg-style equity research terminal[/]\n"
    )
    console.print(
        f"  [{t.muted}]Type [accent]HELP[/accent] or [accent]?[/accent] for the command reference.  "
        f"[accent]EXIT[/accent] or [accent]Q[/accent] to quit.[/]\n"
    )


# ── Autocomplete word list ─────────────────────────────────────────────────────
_AUTOCOMPLETE_WORDS = [
    "EQUITY", "DES", "FA", "FA Q", "GP", "HP", "VERDICT", "RATE",
    "TA", "NI", "RV", "COMPARE", "MACRO", "SCREEN", "WATCH", "EXPORT",
    "SOURCE", "HELP", "EXIT", "QUIT",
    "1D", "5D", "1M", "3M", "6M", "1Y", "2Y", "5Y",
]


def _build_completer():
    """Build a prompt_toolkit WordCompleter for the REPL."""
    try:
        from prompt_toolkit.completion import WordCompleter
        return WordCompleter(_AUTOCOMPLETE_WORDS, ignore_case=True, sentence=True)
    except ImportError:
        return None


def _build_prompt_session():
    """Build a prompt_toolkit PromptSession (with history)."""
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import FileHistory
        from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
        from pathlib import Path

        hist_file = Path.home() / ".kadeconsole" / "history"
        hist_file.parent.mkdir(parents=True, exist_ok=True)

        return PromptSession(
            history=AutoSuggestFromHistory() and FileHistory(str(hist_file)),
            auto_suggest=AutoSuggestFromHistory(),
            completer=_build_completer(),
            complete_while_typing=False,
        )
    except ImportError:
        return None


def _simple_input(prompt: str) -> str:
    """Fallback to built-in input() when prompt_toolkit is unavailable."""
    try:
        return input(prompt)
    except EOFError:
        return "EXIT"


def main() -> None:
    """Main entrypoint — called by the `kadeconsole` console script."""

    # ── 1. Load config ─────────────────────────────────────────────────────────
    from kadeconsole.config.loader import load_config
    config = load_config()

    # ── 2. Initialise cache ────────────────────────────────────────────────────
    from kadeconsole.cache.store import CacheStore
    cache = CacheStore(
        provider_ttl_minutes = config.get("cache_ttl_provider_minutes", 15),
        jev_ttl_hours        = config.get("cache_ttl_jev_hours", 24),
    )
    cache.clear_expired()  # housekeeping on startup

    # ── 3. Initialise providers ────────────────────────────────────────────────
    from kadeconsole.providers.registry import ProviderRegistry
    registry = ProviderRegistry(config)
    provider = registry.get_primary()

    # ── 4. Initialise Jev client ───────────────────────────────────────────────
    from kadeconsole.jev.client import JevClient
    jev = JevClient(
        api_key = config.get("typesafe_api_key", ""),
        cache   = cache,
    )

    # ── 5. Session + Router ───────────────────────────────────────────────────
    from kadeconsole.core.session import Session
    from kadeconsole.core.router import Router
    session = Session(timeframe=config.get("default_timeframe", "1Y"))
    router  = Router(session=session, provider=provider, jev=jev)

    # ── 6. Banner ──────────────────────────────────────────────────────────────
    _print_banner()

    # Provider status line
    provider_line = f"[{t.muted}]  Data: [accent]{provider.name}[/accent]"
    if registry.provider_names:
        provider_line += f"  [{t.muted}]({', '.join(registry.provider_names)})[/]"
    jev_status = (
        f"[positive]◆ Jev active[/positive]"
        if jev.available
        else f"[{t.muted}]◆ Jev inactive — set TYPESAFE_API_KEY to enable AI analysis[/]"
    )
    console.print(f"{provider_line}   {jev_status}\n")

    # ── 7. REPL loop ───────────────────────────────────────────────────────────
    prompt_session = _build_prompt_session()

    # Prompt style — amber "kadeConsole >" prefix
    prompt_str = f"kadeConsole > "

    while True:
        try:
            if prompt_session is not None:
                try:
                    from prompt_toolkit.styles import Style as PTStyle
                    pt_style = PTStyle.from_dict({
                        "": f"#{t.text[1:]}",
                        "prompt": f"bold #{t.accent[1:]}",
                    })
                    raw = prompt_session.prompt(
                        [("class:prompt", prompt_str)],
                        style=pt_style,
                    )
                except Exception:
                    raw = prompt_session.prompt(prompt_str)
            else:
                raw = _simple_input(prompt_str)

        except KeyboardInterrupt:
            console.print(f"\n[{t.muted}]  Use EXIT or Q to quit.[/]\n")
            continue
        except EOFError:
            break

        raw = raw.strip()
        if not raw:
            continue

        # Parse and dispatch
        from kadeconsole.core.parser import parse, ParseError
        try:
            parsed = parse(raw)
        except ParseError as exc:
            console.print(f"[negative]  Parse error: {exc}[/negative]")
            continue

        keep_going = router.dispatch(parsed)
        if not keep_going:
            console.print(f"\n[{t.muted}]  Goodbye.[/]\n")
            break


if __name__ == "__main__":
    main()
