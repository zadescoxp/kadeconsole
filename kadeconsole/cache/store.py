"""
cache/store.py — SQLite-backed response and Jev-verdict cache.

Two tables:
  provider_cache  — raw market data, keyed by (symbol, endpoint), TTL 15 min
  jev_cache       — Jev responses, keyed by sha256 of (ticker+timeframe+data_hash), TTL 24h

The cache lives at ~/.kadeconsole/cache.db and is created automatically.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional

CACHE_DB = Path.home() / ".kadeconsole" / "cache.db"

_CREATE_PROVIDER = """
CREATE TABLE IF NOT EXISTS provider_cache (
    key        TEXT PRIMARY KEY,
    data_json  TEXT NOT NULL,
    expires_at REAL NOT NULL
);
"""

_CREATE_JEV = """
CREATE TABLE IF NOT EXISTS jev_cache (
    key          TEXT PRIMARY KEY,
    response_json TEXT NOT NULL,
    created_at   REAL NOT NULL,
    expires_at   REAL NOT NULL
);
"""


class CacheStore:
    """Thread-safe SQLite cache store."""

    def __init__(
        self,
        db_path: Path = CACHE_DB,
        provider_ttl_minutes: int = 15,
        jev_ttl_hours: int = 24,
    ) -> None:
        self.db_path = db_path
        self.provider_ttl = provider_ttl_minutes * 60
        self.jev_ttl = jev_ttl_hours * 3600
        self._ensure_db()

    # ── Public API ─────────────────────────────────────────────────────────────

    def get_provider(self, symbol: str, endpoint: str) -> Optional[Any]:
        """Return cached provider data or None if missing/expired."""
        key = self._provider_key(symbol, endpoint)
        row = self._fetch("provider_cache", key)
        return json.loads(row) if row else None

    def set_provider(self, symbol: str, endpoint: str, data: Any) -> None:
        """Cache provider data with TTL."""
        key = self._provider_key(symbol, endpoint)
        self._upsert("provider_cache", key, json.dumps(data, default=str), self.provider_ttl)

    def get_jev(self, ticker: str, timeframe: str, data_fingerprint: str) -> Optional[Any]:
        """Return cached Jev response or None if missing/expired."""
        key = self._jev_key(ticker, timeframe, data_fingerprint)
        row = self._fetch_jev(key)
        return json.loads(row) if row else None

    def set_jev(self, ticker: str, timeframe: str, data_fingerprint: str, response: Any) -> None:
        """Cache a Jev response with TTL."""
        key = self._jev_key(ticker, timeframe, data_fingerprint)
        self._upsert("jev_cache", key, json.dumps(response, default=str), self.jev_ttl)

    def clear_expired(self) -> None:
        """Purge all expired rows from both tables."""
        now = time.time()
        with self._connect() as conn:
            conn.execute("DELETE FROM provider_cache WHERE expires_at < ?", (now,))
            conn.execute("DELETE FROM jev_cache WHERE expires_at < ?", (now,))

    def clear_all(self) -> None:
        """Nuke entire cache (useful for debugging)."""
        with self._connect() as conn:
            conn.execute("DELETE FROM provider_cache")
            conn.execute("DELETE FROM jev_cache")

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def make_data_fingerprint(data: Any) -> str:
        """Return a short sha256 fingerprint of any JSON-serialisable data."""
        raw = json.dumps(data, sort_keys=True, default=str).encode()
        return hashlib.sha256(raw).hexdigest()[:16]

    # ── Internal ───────────────────────────────────────────────────────────────

    def _ensure_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(_CREATE_PROVIDER)
            conn.execute(_CREATE_JEV)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    def _fetch(self, table: str, key: str) -> Optional[str]:
        """Fetch from provider_cache (data_json column)."""
        now = time.time()
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT data_json FROM {table} WHERE key=? AND expires_at>?",
                (key, now),
            ).fetchone()
        return row[0] if row else None

    def _fetch_jev(self, key: str) -> Optional[str]:
        """Fetch from jev_cache (response_json column)."""
        now = time.time()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT response_json FROM jev_cache WHERE key=? AND expires_at>?",
                (key, now),
            ).fetchone()
        return row[0] if row else None

    def _upsert(self, table: str, key: str, data_json: str, ttl: float) -> None:
        now = time.time()
        expires = now + ttl
        if table == "provider_cache":
            sql = (
                "INSERT OR REPLACE INTO provider_cache (key, data_json, expires_at) "
                "VALUES (?, ?, ?)"
            )
            with self._connect() as conn:
                conn.execute(sql, (key, data_json, expires))
        else:
            sql = (
                "INSERT OR REPLACE INTO jev_cache (key, response_json, created_at, expires_at) "
                "VALUES (?, ?, ?, ?)"
            )
            with self._connect() as conn:
                conn.execute(sql, (key, data_json, now, expires))

    @staticmethod
    def _provider_key(symbol: str, endpoint: str) -> str:
        return f"{symbol.upper()}:{endpoint}"

    @staticmethod
    def _jev_key(ticker: str, timeframe: str, fingerprint: str) -> str:
        raw = f"{ticker.upper()}:{timeframe}:{fingerprint}"
        return hashlib.sha256(raw.encode()).hexdigest()
