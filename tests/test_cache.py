"""
tests/test_cache.py — Unit tests for the SQLite cache store.
"""

import time
import pytest
import tempfile
from pathlib import Path

from kadeconsole.cache.store import CacheStore


@pytest.fixture
def tmp_cache(tmp_path):
    """Create a temporary CacheStore backed by a temp SQLite file."""
    db = tmp_path / "test_cache.db"
    return CacheStore(
        db_path=db,
        provider_ttl_minutes=1,
        jev_ttl_hours=1,
    )


class TestProviderCache:
    def test_set_and_get(self, tmp_cache):
        tmp_cache.set_provider("AAPL", "info", {"name": "Apple Inc."})
        result = tmp_cache.get_provider("AAPL", "info")
        assert result is not None
        assert result["name"] == "Apple Inc."

    def test_miss_returns_none(self, tmp_cache):
        assert tmp_cache.get_provider("MSFT", "info") is None

    def test_different_symbols_isolated(self, tmp_cache):
        tmp_cache.set_provider("AAPL", "info", {"v": 1})
        tmp_cache.set_provider("GOOG", "info", {"v": 2})
        assert tmp_cache.get_provider("AAPL", "info")["v"] == 1
        assert tmp_cache.get_provider("GOOG", "info")["v"] == 2

    def test_overwrite(self, tmp_cache):
        tmp_cache.set_provider("AAPL", "info", {"v": 1})
        tmp_cache.set_provider("AAPL", "info", {"v": 99})
        assert tmp_cache.get_provider("AAPL", "info")["v"] == 99

    def test_clear_all(self, tmp_cache):
        tmp_cache.set_provider("AAPL", "info", {"v": 1})
        tmp_cache.clear_all()
        assert tmp_cache.get_provider("AAPL", "info") is None


class TestJevCache:
    def test_set_and_get(self, tmp_cache):
        tmp_cache.set_jev("AAPL", "1Y", "abc123", {"buy": 0.6, "hold": 0.3, "sell": 0.1})
        result = tmp_cache.get_jev("AAPL", "1Y", "abc123")
        assert result is not None
        assert result["buy"] == 0.6

    def test_miss_returns_none(self, tmp_cache):
        assert tmp_cache.get_jev("MSFT", "1Y", "xyz") is None

    def test_different_fingerprints_isolated(self, tmp_cache):
        tmp_cache.set_jev("AAPL", "1Y", "fp1", {"v": 1})
        tmp_cache.set_jev("AAPL", "1Y", "fp2", {"v": 2})
        assert tmp_cache.get_jev("AAPL", "1Y", "fp1")["v"] == 1
        assert tmp_cache.get_jev("AAPL", "1Y", "fp2")["v"] == 2


class TestFingerprint:
    def test_deterministic(self):
        data = {"ticker": "AAPL", "pe": 25.5}
        fp1 = CacheStore.make_data_fingerprint(data)
        fp2 = CacheStore.make_data_fingerprint(data)
        assert fp1 == fp2

    def test_different_data_different_fp(self):
        fp1 = CacheStore.make_data_fingerprint({"a": 1})
        fp2 = CacheStore.make_data_fingerprint({"a": 2})
        assert fp1 != fp2

    def test_length(self):
        fp = CacheStore.make_data_fingerprint({"x": 1})
        assert len(fp) == 16  # we trim to 16 chars
