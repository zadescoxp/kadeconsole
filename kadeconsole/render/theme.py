"""
render/theme.py — Color palette and Rich style tokens.

Single source of truth for all terminal styling. No scattered ANSI codes
anywhere else in the codebase — import from here only.

Palette (amber-on-dark, premium terminal aesthetic):
  Background: #0d0d0d  (near-black)
  Text:        #e8e8e8  (off-white)
  Accent:      #f5a623  (amber — primary brand color)
  Positive:    #4caf8a  (muted green)
  Negative:    #e05c5c  (muted red)
  Muted:       #666666  (dim grey)
  Jev:         #7c9fd4  (cool blue — Jev AI outputs)
  Border:      #2a2a2a  (subtle panel borders)
  Warning:     #e8a838  (warm amber-orange)
"""

from __future__ import annotations
from dataclasses import dataclass
from rich.style import Style
from rich.theme import Theme


@dataclass(frozen=True)
class _Palette:
    """Hex color tokens."""
    bg:       str = "#0d0d0d"
    text:     str = "#e8e8e8"
    accent:   str = "#f5a623"
    positive: str = "#4caf8a"
    negative: str = "#e05c5c"
    muted:    str = "#666666"
    jev:      str = "#7c9fd4"
    border:   str = "#2a2a2a"
    warning:  str = "#e8a838"
    dim_text: str = "#999999"
    white:    str = "#ffffff"
    header:   str = "#c8c8c8"


# Global palette instance — use `from kadeconsole.render.theme import t`
t = _Palette()


# ── Rich Theme ─────────────────────────────────────────────────────────────────
# Used with `console = Console(theme=RICH_THEME)` for markup like [accent]text[/]
RICH_THEME = Theme(
    {
        "accent":       f"bold {t.accent}",
        "positive":     f"bold {t.positive}",
        "negative":     f"bold {t.negative}",
        "muted":        t.muted,
        "jev":          f"italic {t.jev}",
        "jev.label":    f"bold {t.jev}",
        "warning":      f"bold {t.warning}",
        "header":       f"bold {t.accent}",
        "dim_text":     t.dim_text,
        "border":       t.border,
        "kc.panel":     f"bold {t.accent}",
        "kc.positive":  f"{t.positive}",
        "kc.negative":  f"{t.negative}",
        "kc.muted":     t.muted,
        "kc.jev":       f"italic {t.jev}",
    }
)

# ── Rich Style objects ─────────────────────────────────────────────────────────
STYLE_ACCENT    = Style(color=t.accent, bold=True)
STYLE_POSITIVE  = Style(color=t.positive, bold=True)
STYLE_NEGATIVE  = Style(color=t.negative, bold=True)
STYLE_MUTED     = Style(color=t.muted)
STYLE_JEV       = Style(color=t.jev, italic=True)
STYLE_JEV_LABEL = Style(color=t.jev, bold=True)
STYLE_HEADER    = Style(color=t.accent, bold=True)
STYLE_DIM       = Style(color=t.dim_text)
STYLE_WHITE     = Style(color=t.white)
STYLE_WARNING   = Style(color=t.warning, bold=True)


# ── Helpers ────────────────────────────────────────────────────────────────────

def delta_style(value: float) -> str:
    """Return 'positive' or 'negative' markup tag name based on sign."""
    return "positive" if value >= 0 else "negative"


def delta_arrow(value: float) -> str:
    """Return ▲ or ▼ arrow with markup."""
    if value >= 0:
        return f"[positive]▲[/]"
    return f"[negative]▼[/]"


def fmt_delta(value: float, pct: bool = True) -> str:
    """Format a signed delta value with color markup and arrow."""
    arrow = "▲" if value >= 0 else "▼"
    style = "positive" if value >= 0 else "negative"
    fmt = f"{abs(value):.2f}{'%' if pct else ''}"
    return f"[{style}]{arrow} {fmt}[/{style}]"


def section_rule(title: str) -> str:
    """Return a styled section header string for Rich console markup."""
    return f"\n[header]{title.upper()}[/header]"
