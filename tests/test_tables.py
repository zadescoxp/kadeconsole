"""
tests/test_tables.py — Unit tests for number formatters in render/tables.py
"""

import pytest
from kadeconsole.render.tables import fmt_number, fmt_pct, fmt_ratio, fmt_price, fmt_delta_str


class TestFmtNumber:
    def test_billions(self):
        assert fmt_number(2_500_000_000) == "2.50B"

    def test_millions(self):
        assert fmt_number(1_234_567) == "1.23M"

    def test_thousands(self):
        assert fmt_number(9_876) == "9.88K"

    def test_small(self):
        assert fmt_number(123.456) == "123.46"

    def test_zero(self):
        assert fmt_number(0) == "0.00"

    def test_none(self):
        assert fmt_number(None) == "—"

    def test_negative_millions(self):
        result = fmt_number(-5_000_000)
        assert "-5.00M" in result

    def test_string_numeric(self):
        # Should coerce "1000000" string to float
        assert fmt_number("1000000") == "1.00M"

    def test_non_numeric_string(self):
        assert fmt_number("N/A") == "—"


class TestFmtPct:
    def test_decimal_ratio(self):
        # yfinance returns margins as 0.0–1.0
        assert fmt_pct(0.2134) == "21.34%"

    def test_large_percent(self):
        # values > 1.5 treated as already-percentage
        assert fmt_pct(45.6) == "45.60%"

    def test_none(self):
        assert fmt_pct(None) == "—"

    def test_negative(self):
        result = fmt_pct(-0.05)
        assert "-5.00%" in result


class TestFmtRatio:
    def test_pe_ratio(self):
        assert fmt_ratio(25.5) == "25.50x"

    def test_none(self):
        assert fmt_ratio(None) == "—"

    def test_zero(self):
        assert fmt_ratio(0) == "0.00x"


class TestFmtPrice:
    def test_basic(self):
        assert fmt_price(150.75) == "150.75"

    def test_with_currency(self):
        result = fmt_price(150.75, "USD")
        assert "150.75" in result
        assert "USD" in result

    def test_none(self):
        assert fmt_price(None) == "—"

    def test_thousands(self):
        result = fmt_price(1500.00)
        assert "1,500.00" in result


class TestFmtDelta:
    def test_positive(self):
        result = fmt_delta_str(3.5)
        assert "▲" in result
        assert "3.50%" in result

    def test_negative(self):
        result = fmt_delta_str(-2.1)
        assert "▼" in result
        assert "2.10%" in result

    def test_none(self):
        assert fmt_delta_str(None) == "—"

    def test_no_percent(self):
        result = fmt_delta_str(1.5, pct=False)
        assert "%" not in result
