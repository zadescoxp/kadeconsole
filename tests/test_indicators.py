"""
tests/test_indicators.py — Unit tests for indicator math.
"""

import pytest
from kadeconsole.indicators.moving_averages import sma, ema, golden_cross
from kadeconsole.indicators.momentum import rsi, rsi_signal, macd, rate_of_change
from kadeconsole.indicators.volatility import bollinger_bands, realized_volatility
from kadeconsole.indicators.volume import obv, volume_ratio, detect_volume_spike


# ── SMA ───────────────────────────────────────────────────────────────────────

class TestSMA:
    def test_basic(self):
        result = sma([1, 2, 3, 4, 5], 3)
        assert result[:2] == [None, None]
        assert abs(result[2] - 2.0) < 1e-9
        assert abs(result[3] - 3.0) < 1e-9
        assert abs(result[4] - 4.0) < 1e-9

    def test_length_preserved(self):
        values = list(range(20))
        assert len(sma(values, 5)) == len(values)

    def test_window_larger_than_data(self):
        result = sma([1, 2], 5)
        assert all(v is None for v in result)


# ── EMA ───────────────────────────────────────────────────────────────────────

class TestEMA:
    def test_basic_length(self):
        values = list(range(30))
        result = ema(values, 12)
        assert len(result) == len(values)

    def test_first_values_are_none(self):
        result = ema(list(range(20)), 5)
        assert all(v is None for v in result[:4])

    def test_seed_equals_mean(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = ema(values, 5)
        # First valid value should equal mean([1,2,3,4,5]) = 3.0
        assert abs(result[4] - 3.0) < 1e-9


# ── Golden Cross ──────────────────────────────────────────────────────────────

class TestGoldenCross:
    def test_golden_cross_detected(self):
        fast = [None, 1.0, 2.0, 4.0]  # fast crosses above slow
        slow = [None, 3.0, 3.0, 3.0]
        assert golden_cross(fast, slow) is True

    def test_death_cross_detected(self):
        fast = [None, 5.0, 3.0, 2.0]  # fast crosses below slow
        slow = [None, 3.0, 3.0, 3.0]
        assert golden_cross(fast, slow) is False

    def test_no_crossover(self):
        fast = [None, 5.0, 5.0, 5.0]
        slow = [None, 3.0, 3.0, 3.0]
        assert golden_cross(fast, slow) is None


# ── RSI ───────────────────────────────────────────────────────────────────────

class TestRSI:
    def _make_trending(self, n=30, up=True):
        base = 100.0
        prices = [base]
        for _ in range(n - 1):
            prices.append(prices[-1] + (1.0 if up else -1.0))
        return prices

    def test_uptrend_rsi_high(self):
        prices = self._make_trending(30, up=True)
        result = rsi(prices, 14)
        # Strong uptrend → RSI should be high (>60)
        valid = [v for v in result if v is not None]
        assert valid[-1] > 60

    def test_downtrend_rsi_low(self):
        prices = self._make_trending(30, up=False)
        result = rsi(prices, 14)
        valid = [v for v in result if v is not None]
        assert valid[-1] < 40

    def test_length_preserved(self):
        prices = list(range(1, 31))
        assert len(rsi(prices, 14)) == 30

    def test_rsi_signal_labels(self):
        assert rsi_signal(75) == "Overbought"
        assert rsi_signal(25) == "Oversold"
        assert rsi_signal(50) == "Neutral"
        assert rsi_signal(None) == "N/A"

    def test_values_in_range(self):
        prices = [100 + (i % 5) for i in range(30)]
        result = rsi(prices, 14)
        for v in result:
            if v is not None:
                assert 0 <= v <= 100


# ── MACD ─────────────────────────────────────────────────────────────────────

class TestMACD:
    def test_keys_present(self):
        prices = [float(i) for i in range(1, 60)]
        result = macd(prices)
        assert "macd" in result
        assert "signal" in result
        assert "histogram" in result

    def test_lengths_match(self):
        prices = [float(i) for i in range(1, 60)]
        result = macd(prices)
        n = len(prices)
        assert len(result["macd"]) == n
        assert len(result["signal"]) == n
        assert len(result["histogram"]) == n


# ── Rate of Change ────────────────────────────────────────────────────────────

class TestROC:
    def test_basic(self):
        prices = [100.0] * 15 + [110.0]
        result = rate_of_change(prices, 12)
        assert result[-1] is not None
        assert abs(result[-1] - 10.0) < 0.01


# ── Bollinger Bands ───────────────────────────────────────────────────────────

class TestBollinger:
    def test_keys(self):
        prices = [float(i) for i in range(1, 31)]
        result = bollinger_bands(prices, 20)
        assert all(k in result for k in ("middle", "upper", "lower", "width", "pct_b"))

    def test_upper_above_lower(self):
        prices = [100.0 + (i % 5) for i in range(30)]
        result = bollinger_bands(prices, 20)
        for u, l in zip(result["upper"], result["lower"]):
            if u is not None and l is not None:
                assert u >= l


# ── OBV ───────────────────────────────────────────────────────────────────────

class TestOBV:
    def test_up_day_adds_volume(self):
        closes  = [100.0, 101.0, 100.5]
        volumes = [1000.0, 2000.0, 500.0]
        result = obv(closes, volumes)
        assert result[0] == 0.0
        assert result[1] == 2000.0   # up day → +vol
        assert result[2] == 1500.0   # down day → -vol

    def test_flat_day_unchanged(self):
        closes  = [100.0, 100.0]
        volumes = [1000.0, 500.0]
        result = obv(closes, volumes)
        assert result[1] == result[0]  # flat → no change


# ── Volume Spike ──────────────────────────────────────────────────────────────

class TestVolumeSpike:
    def test_spike_detected(self):
        # 20 days of avg=1000, then one day at 5000
        volumes = [1000.0] * 20 + [5000.0]
        result = detect_volume_spike(volumes, window=20, threshold=2.0)
        assert result is not None
        assert result["ratio"] >= 2.0

    def test_no_spike(self):
        volumes = [1000.0] * 21
        result = detect_volume_spike(volumes, window=20, threshold=2.0)
        assert result is None
