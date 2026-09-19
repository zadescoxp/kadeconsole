"""
tests/test_parser.py — Unit tests for the command parser.
"""

import pytest
from kadeconsole.core.parser import (
    parse, ParseError,
    CMD_EQUITY, CMD_DES, CMD_FA, CMD_GP, CMD_HP,
    CMD_VERDICT, CMD_RATE, CMD_HELP, CMD_EXIT, CMD_UNKNOWN,
    CMD_COMPARE, CMD_SCREEN, CMD_WATCH, CMD_SOURCE,
)


# ── EQUITY resolution ─────────────────────────────────────────────────────────

class TestEquityParsing:
    def test_us_simple(self):
        p = parse("AAPL EQUITY")
        assert p.command == CMD_EQUITY
        assert p.ticker == "AAPL"
        assert p.exchange is None
        assert p.country is None

    def test_us_explicit_exchange(self):
        p = parse("AAPL US EQUITY")
        assert p.command == CMD_EQUITY
        assert p.ticker == "AAPL"
        assert p.exchange == "US"

    def test_indian_nse_full(self):
        p = parse("RELIANCE IN NS EQUITY")
        assert p.command == CMD_EQUITY
        assert p.ticker == "RELIANCE"
        assert p.country == "IN"
        assert p.exchange == "NS"

    def test_indian_bse_country_only(self):
        p = parse("INFY IN EQUITY")
        assert p.command == CMD_EQUITY
        assert p.ticker == "INFY"
        assert p.country == "IN"

    def test_nse_exchange_only(self):
        p = parse("TCS NS EQUITY")
        assert p.command == CMD_EQUITY
        assert p.ticker == "TCS"
        assert p.exchange == "NS"

    def test_london(self):
        p = parse("HSBA LN EQUITY")
        assert p.command == CMD_EQUITY
        assert p.ticker == "HSBA"
        assert p.exchange == "LN"

    def test_lowercase_tolerated(self):
        p = parse("aapl equity")
        assert p.command == CMD_EQUITY
        assert p.ticker == "AAPL"

    def test_equity_no_ticker_raises(self):
        with pytest.raises(ParseError):
            parse("EQUITY")


# ── Simple commands ───────────────────────────────────────────────────────────

class TestSimpleCommands:
    def test_des(self):
        assert parse("DES").command == CMD_DES

    def test_fa_annual(self):
        p = parse("FA")
        assert p.command == CMD_FA
        assert p.qualifier is None

    def test_fa_quarterly(self):
        p = parse("FA Q")
        assert p.command == CMD_FA
        assert p.qualifier == "Q"

    def test_gp_default(self):
        p = parse("GP")
        assert p.command == CMD_GP
        assert p.timeframe is None

    def test_gp_with_timeframe(self):
        for tf in ("1D", "5D", "1M", "3M", "6M", "1Y", "2Y", "5Y"):
            p = parse(f"GP {tf}")
            assert p.command == CMD_GP
            assert p.timeframe == tf

    def test_hp(self):
        p = parse("HP")
        assert p.command == CMD_HP

    def test_verdict(self):
        assert parse("VERDICT").command == CMD_VERDICT

    def test_rate(self):
        assert parse("RATE").command == CMD_RATE


# ── Aliases ───────────────────────────────────────────────────────────────────

class TestAliases:
    def test_question_mark_is_help(self):
        assert parse("?").command == CMD_HELP

    def test_exit_variants(self):
        for cmd in ("EXIT", "QUIT", "Q"):
            assert parse(cmd).command == CMD_EXIT


# ── Compound commands ─────────────────────────────────────────────────────────

class TestCompoundCommands:
    def test_compare(self):
        p = parse("COMPARE MSFT")
        assert p.command == CMD_COMPARE
        assert p.ticker == "MSFT"

    def test_compare_no_ticker_raises(self):
        with pytest.raises(ParseError):
            parse("COMPARE")

    def test_screen_with_quote(self):
        p = parse('SCREEN "cash-rich, low debt, recovering earnings"')
        assert p.command == CMD_SCREEN
        assert "cash-rich" in p.args[0]

    def test_watch_add(self):
        p = parse("WATCH ADD AAPL")
        assert p.command == CMD_WATCH
        assert p.subcommand == "ADD"
        assert "AAPL" in p.args

    def test_source(self):
        p = parse("SOURCE alpaca")
        assert p.command == CMD_SOURCE
        assert p.args[0] == "alpaca"


# ── Unknown ───────────────────────────────────────────────────────────────────

class TestUnknown:
    def test_empty_string(self):
        assert parse("").command == CMD_UNKNOWN

    def test_gibberish(self):
        assert parse("FOOBAR XYZ").command == CMD_UNKNOWN
