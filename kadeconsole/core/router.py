"""
core/router.py — Command dispatcher.

Routes ParsedCommand objects to the appropriate page handler.
Each page handler receives (session, parsed_command, provider, jev_client)
and returns None (output is rendered directly via rich).
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from rich.console import Console

from kadeconsole.core.parser import (
    ParsedCommand,
    ParseError,
    CMD_EQUITY, CMD_DES, CMD_FA, CMD_GP, CMD_HP,
    CMD_VERDICT, CMD_RATE, CMD_HELP, CMD_EXIT, CMD_UNKNOWN,
    CMD_TA, CMD_RV, CMD_NI, CMD_MACRO, CMD_COMPARE,
    CMD_SCREEN, CMD_WATCH, CMD_EXPORT, CMD_SOURCE,
)
from kadeconsole.render.theme import t

if TYPE_CHECKING:
    from kadeconsole.core.session import Session
    from kadeconsole.providers.base import DataProvider
    from kadeconsole.jev.client import JevClient

console = Console()


class Router:
    """Dispatches parsed commands to page handlers."""

    def __init__(self, session: "Session", provider: "DataProvider", jev: "JevClient") -> None:
        self.session = session
        self.provider = provider
        self.jev = jev

    def dispatch(self, parsed: ParsedCommand) -> bool:
        """
        Route a parsed command to the correct handler.

        Returns False if the user requested EXIT, True otherwise.
        """
        cmd = parsed.command
        s = self.session

        try:
            if cmd == CMD_EXIT:
                return False

            elif cmd == CMD_HELP:
                from kadeconsole.pages.help import render_help
                render_help()

            elif cmd == CMD_EQUITY:
                from kadeconsole.pages.equity import render_equity
                render_equity(s, parsed, self.provider, self.jev)

            elif cmd == CMD_DES:
                self._require_security(cmd)
                from kadeconsole.pages.des import render_des
                render_des(s, self.provider)

            elif cmd == CMD_FA:
                self._require_security(cmd)
                from kadeconsole.pages.fa import render_fa
                render_fa(s, parsed, self.provider, self.jev)

            elif cmd == CMD_GP:
                self._require_security(cmd)
                from kadeconsole.pages.gp import render_gp
                render_gp(s, parsed, self.provider)

            elif cmd == CMD_HP:
                self._require_security(cmd)
                from kadeconsole.pages.hp import render_hp
                render_hp(s, parsed, self.provider)

            elif cmd == CMD_VERDICT:
                self._require_security(cmd)
                from kadeconsole.pages.verdict import render_verdict
                render_verdict(s, self.provider, self.jev)

            elif cmd == CMD_RATE:
                self._require_security(cmd)
                from kadeconsole.pages.rate import render_rate
                render_rate(s, self.provider, self.jev)

            elif cmd in (CMD_TA, CMD_RV, CMD_NI, CMD_MACRO,
                         CMD_COMPARE, CMD_SCREEN, CMD_WATCH, CMD_EXPORT):
                console.print(
                    f"[{t.muted}]  {cmd} is coming in Phase 2/3. "
                    f"Try: EQUITY, DES, FA, GP, HP, VERDICT, RATE, HELP[/]"
                )

            elif cmd == CMD_SOURCE:
                if parsed.args:
                    s.provider_override = parsed.args[0]
                    console.print(f"[{t.accent}]  Provider set to: {parsed.args[0]}[/]")

            elif cmd == CMD_UNKNOWN:
                _raw = parsed.raw or ""
                console.print(
                    f"[{t.negative}]  Unknown command: [bold]{_raw}[/bold]. "
                    f"Type HELP or ? for the command reference.[/]"
                )

        except _SecurityRequired as exc:
            console.print(f"[{t.negative}]  {exc}[/]")
        except Exception as exc:  # noqa: BLE001
            console.print(f"[{t.negative}]  Error: {exc}[/]")

        return True  # continue REPL

    def _require_security(self, cmd: str) -> None:
        if not self.session.has_security():
            raise _SecurityRequired(
                f"{cmd} requires an active security. "
                f"First run: <TICKER> EQUITY  (e.g. AAPL EQUITY)"
            )


class _SecurityRequired(Exception):
    """Raised when a page command is called without a security in session."""
