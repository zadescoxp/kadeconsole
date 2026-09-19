"""
providers/registry.py — Provider registry with fallback chain.

Builds the ordered list of active DataProviders from config, tries
each in turn on errors or rate-limits, and injects API keys.
"""

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from kadeconsole.providers.base import DataProvider


class ProviderRegistry:
    """
    Manages the active provider chain.

    On any call, tries the first provider. If it raises an exception
    (rate-limit, auth error, empty response), falls back to the next,
    and so on.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self._chain: list["DataProvider"] = []
        self._build_chain()

    def _build_chain(self) -> None:
        """Instantiate providers in priority order from config."""
        priority: list[str] = self.config.get("provider_priority", ["yfinance"])

        for name in priority:
            provider = self._load_provider(name)
            if provider and provider.is_available():
                self._chain.append(provider)

        if not self._chain:
            # Always fall back to yfinance as last resort
            from kadeconsole.providers.yfinance_provider import YFinanceProvider
            self._chain.append(YFinanceProvider())

    def _load_provider(self, name: str) -> Optional["DataProvider"]:
        """Dynamically load a provider by name."""
        name = name.lower().strip()
        try:
            if name == "yfinance":
                from kadeconsole.providers.yfinance_provider import YFinanceProvider
                return YFinanceProvider()

            # Phase 2 providers — stubs for now
            if name == "alpaca":
                try:
                    from kadeconsole.providers.alpaca_provider import AlpacaProvider
                    return AlpacaProvider(api_key=self.config.get("alpaca_api_key", ""))
                except ImportError:
                    return None

            if name in ("alphavantage", "alpha_vantage"):
                try:
                    from kadeconsole.providers.alphavantage_provider import AlphaVantageProvider
                    return AlphaVantageProvider(api_key=self.config.get("alphavantage_api_key", ""))
                except ImportError:
                    return None

        except Exception:  # noqa: BLE001
            return None
        return None

    def get_primary(self) -> "DataProvider":
        """Return the first available provider."""
        if not self._chain:
            raise RuntimeError("No data providers available. Check your installation.")
        return self._chain[0]

    def call_with_fallback(self, method: str, *args: Any, **kwargs: Any) -> Any:
        """
        Call `method` on each provider in the chain until one succeeds.

        Raises the last exception if all providers fail.
        """
        last_exc: Optional[Exception] = None
        for provider in self._chain:
            try:
                fn = getattr(provider, method)
                result = fn(*args, **kwargs)
                # Treat empty results from non-last providers as a soft failure
                if result is not None:
                    return result
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                continue

        if last_exc:
            raise last_exc
        raise RuntimeError(f"All providers returned empty results for {method}({args!r})")

    @property
    def provider_names(self) -> list[str]:
        """Return names of active providers in order."""
        return [p.name for p in self._chain]
