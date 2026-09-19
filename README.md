# kadeConsole

> A Bloomberg-terminal-style equity research console — free, open-source, and AI-powered.

```
  ██╗  ██╗ █████╗ ██████╗ ███████╗
  ██║ ██╔╝██╔══██╗██╔══██╗██╔════╝
  █████╔╝ ███████║██║  ██║█████╗
  ██╔═██╗ ██╔══██║██║  ██║██╔══╝
  ██║  ██╗██║  ██║██████╔╝███████╗
  ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚══════╝  CONSOLE  v0.1.0
```

Bloomberg terminals cost ~$24k/year. kadeConsole is free. It gives you the muscle-memory command grammar of a real terminal, dense richly-formatted output, and **Jev** (TypeSafe AI) embedded in every screen — delivering the one non-obvious insight that raw numbers alone can't.

---

## Install

```bash
pip install kadeconsole
```

Then launch the REPL:

```bash
kadeconsole
```

---

## Quickstart

```
kadeConsole > AAPL EQUITY          # resolve Apple, set session
kadeConsole > DES                  # company description
kadeConsole > FA                   # full fundamentals
kadeConsole > FA Q                 # quarterly fundamentals
kadeConsole > GP                   # 1Y price chart
kadeConsole > GP 6M                # 6-month chart
kadeConsole > HP                   # historical OHLCV
kadeConsole > VERDICT              # Jev buy/sell/hold distribution
kadeConsole > RATE                 # Jev multi-axis fundamental rating
kadeConsole > HELP                 # full command reference
kadeConsole > EXIT                 # quit
```

**Indian markets:**
```
kadeConsole > RELIANCE IN NS EQUITY    # Reliance Industries on NSE
kadeConsole > INFY BO EQUITY           # Infosys on BSE
```

---

## Command Reference

| Command | Description |
|---|---|
| `<TICKER> [EXCHANGE] EQUITY` | Resolve security, set session, show snapshot |
| `DES` | Company description, sector, key people |
| `FA` / `FA Q` | Full fundamentals (annual / quarterly) |
| `GP [timeframe]` | In-terminal price chart (`1D 5D 1M 3M 6M 1Y 2Y 5Y`) |
| `HP` | Historical OHLCV table |
| `VERDICT` | Jev buy/sell/hold probability distribution |
| `RATE` | Jev multi-axis rating (valuation/growth/quality/momentum) |
| `HELP` / `?` | Command reference |
| `EXIT` / `QUIT` | Exit the REPL |

*(Phase 2: TA, NI, COMPARE, SOURCE — Phase 3: SCREEN, MACRO, WATCH, EXPORT)*

---

## Configuration

On first run, kadeConsole creates `~/.kadeconsole/config.yaml`:

```yaml
provider_priority:
  - yfinance

typesafe_api_key: ""        # Get yours at https://typesafe.ai
alpaca_api_key: ""
alphavantage_api_key: ""

default_timeframe: 1Y
theme: default
```

Set `typesafe_api_key` to enable **Jev** AI analysis (VERDICT, RATE, anomaly flags). The terminal is fully functional without it — Jev sections show a graceful "unavailable" notice.

---

## Provider Plugins

The `providers/base.py` `DataProvider` interface is public. To add a new source:

1. Subclass `DataProvider`
2. Implement `get_info()`, `get_price_history()`, `get_financials()`, `get_news()`, `get_peers()`
3. Register in `~/.kadeconsole/config.yaml` under `provider_priority`

---

## Requirements

- Python 3.10+
- A modern terminal: **iTerm2** (macOS), **Windows Terminal** (Windows), **GNOME Terminal** / **Kitty** (Linux)
- *Optional:* TypeSafe AI key for Jev features

---

## Roadmap

- **v0.1 (MVP):** EQUITY, DES, FA, GP, HP, VERDICT, RATE
- **v0.2:** TA (technical panel), NI (news + sentiment), COMPARE, multi-provider
- **v0.3:** SCREEN (NL filtering), MACRO, WATCH, EXPORT
- **v0.4:** Full Textual TUI, tabbed panels, community plugins

---

## License

MIT — use freely, contribute openly.
