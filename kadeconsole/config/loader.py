"""
config/loader.py — ~/.kadeconsole/config.yaml reader.

Creates a default config file on first run. Returns a validated config dict.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False

CONFIG_DIR = Path.home() / ".kadeconsole"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

DEFAULT_CONFIG: dict[str, Any] = {
    "provider_priority": ["yfinance"],
    "typesafe_api_key": "",
    "alpaca_api_key": "",
    "alphavantage_api_key": "",
    "polygon_api_key": "",
    "default_timeframe": "1Y",
    "theme": "default",
    "cache_ttl_provider_minutes": 15,
    "cache_ttl_jev_hours": 24,
}


def load_config() -> dict[str, Any]:
    """
    Load configuration from ~/.kadeconsole/config.yaml.

    Creates the directory and a default config file if they don't exist.
    Merges loaded values over the defaults (new keys in defaults are preserved
    across upgrades without blowing away user customisations).
    """
    _ensure_dir()

    if not CONFIG_FILE.exists():
        _write_default()

    if not _YAML_AVAILABLE:
        # Fallback: return defaults, don't crash if PyYAML not installed yet
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_FILE, "r") as f:
            user_config: dict[str, Any] = yaml.safe_load(f) or {}
    except Exception:  # noqa: BLE001
        user_config = {}

    # Merge: defaults first, user values override
    merged = {**DEFAULT_CONFIG, **user_config}

    # Also honour environment variable overrides (CI-friendly)
    _apply_env_overrides(merged)

    return merged


def _ensure_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _write_default() -> None:
    if not _YAML_AVAILABLE:
        return
    comment_block = """\
# kadeConsole configuration
# ─────────────────────────────────────────────────────────────
# Set your API keys below to unlock all data providers.
# kadeConsole works without any keys using yfinance (free).
#
# Get a TypeSafe AI key at: https://typesafe.ai
# ─────────────────────────────────────────────────────────────

"""
    with open(CONFIG_FILE, "w") as f:
        f.write(comment_block)
        yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False, allow_unicode=True)


def _apply_env_overrides(config: dict[str, Any]) -> None:
    """Override config values from environment variables."""
    env_map = {
        "TYPESAFE_API_KEY": "typesafe_api_key",
        "ALPACA_API_KEY": "alpaca_api_key",
        "ALPHAVANTAGE_API_KEY": "alphavantage_api_key",
        "POLYGON_API_KEY": "polygon_api_key",
    }
    for env_key, config_key in env_map.items():
        val = os.environ.get(env_key)
        if val:
            config[config_key] = val


def get_api_key(config: dict[str, Any], provider: str) -> str:
    """Convenience helper to retrieve a provider's API key from config."""
    key_map = {
        "typesafe": "typesafe_api_key",
        "alpaca": "alpaca_api_key",
        "alphavantage": "alphavantage_api_key",
        "polygon": "polygon_api_key",
    }
    return config.get(key_map.get(provider, ""), "") or ""
