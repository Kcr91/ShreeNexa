"""Unit tests for Indian trading calendar, segment sessions, holidays, and timezone handling."""

from __future__ import annotations

from datetime import UTC, date, datetime, time

from app.marketdata.calendar import (
    TradingCalendar,
    make_ist_datetime,
    to_ist,
    to_utc,
)


def test_timezone_normalization_deterministic() -> None:
    """Verify deterministic bidirectional UTC and IST timezone conversion."""
    # 09:15 IST is 03:45 UTC
    utc_dt = datetime(2026, 8, 3, 3, 45, tzinfo=UTC)
    ist_dt = to_ist(utc_dt)

    assert ist_dt.hour == 9
    assert ist_dt.minute == 15
    offset = ist_dt.utcoffset()
    assert offset is not None
    assert offset.total_seconds() == 19800  # +05:30 = 5.5 * 3600

    # Convert back to UTC
    re_utc = to_utc(ist_dt)
    assert re_utc == utc_dt


def test_trading_day_and_holiday_exclusion() -> None:
    """Verify regular weekdays are trading days, while weekends and holidays are excluded."""
    cal = TradingCalendar()

    # Regular Monday (2026-08-03)
    assert cal.is_trading_day(date(2026, 8, 3), segment="NSE_EQ") is True

    # Weekend Saturday (2026-08-08)
    assert cal.is_trading_day(date(2026, 8, 8), segment="NSE_EQ") is False

    # Republic Day (2026-01-26 Monday)
    assert cal.is_holiday(date(2026, 1, 26), segment="NSE_EQ") is True
    assert cal.is_trading_day(date(2026, 1, 26), segment="NSE_EQ") is False

    # Independence Day (2026-08-15 Saturday)
    assert cal.is_holiday(date(2026, 8, 15), segment="NSE_EQ") is True
    assert cal.is_trading_day(date(2026, 8, 15), segment="NSE_EQ") is False


def test_segment_session_bounds() -> None:
    """Verify session bounds for Equity/FNO, Currency, and Commodity segments."""
    cal = TradingCalendar()
    sample_date = date(2026, 8, 3)

    # Equity / FNO: 09:15 to 15:30 IST
    eq_bounds = cal.get_session_bounds_utc(sample_date, segment="NSE_EQ")
    assert len(eq_bounds) == 1
    start_utc, end_utc = eq_bounds[0]
    assert to_ist(start_utc).time() == time(9, 15)
    assert to_ist(end_utc).time() == time(15, 30)

    # Currency: 09:00 to 17:00 IST
    curr_bounds = cal.get_session_bounds_utc(sample_date, segment="NSE_CURR")
    assert len(curr_bounds) == 1
    assert to_ist(curr_bounds[0][0]).time() == time(9, 0)
    assert to_ist(curr_bounds[0][1]).time() == time(17, 0)

    # Commodity: 09:00 to 23:30 IST
    comm_bounds = cal.get_session_bounds_utc(sample_date, segment="MCX_COMM")
    assert len(comm_bounds) == 1
    assert to_ist(comm_bounds[0][0]).time() == time(9, 0)
    assert to_ist(comm_bounds[0][1]).time() == time(23, 30)


def test_special_muhurat_and_dr_sessions() -> None:
    """Verify special Diwali Muhurat and DR Saturday sessions."""
    cal = TradingCalendar()

    # Diwali 2026-11-08 has special Muhurat evening session (18:15 - 19:15 IST)
    muhurat_date = date(2026, 11, 8)
    assert cal.is_trading_day(muhurat_date, segment="NSE_EQ") is True

    muhurat_bounds = cal.get_session_bounds_utc(muhurat_date, segment="NSE_EQ")
    assert len(muhurat_bounds) == 1
    assert to_ist(muhurat_bounds[0][0]).time() == time(18, 15)
    assert to_ist(muhurat_bounds[0][1]).time() == time(19, 15)

    # During Muhurat hours: session is active
    muhurat_time = make_ist_datetime(muhurat_date, time(18, 30))
    assert cal.is_session_time(muhurat_time, segment="NSE_EQ") is True

    # During regular morning hours on Diwali: session is inactive
    morning_time = make_ist_datetime(muhurat_date, time(10, 0))
    assert cal.is_session_time(morning_time, segment="NSE_EQ") is False


def test_validate_bar_session_boundaries() -> None:
    """Verify validating bar timestamps against active session intervals."""
    cal = TradingCalendar()
    sample_date = date(2026, 8, 3)

    # Valid in-session bar (10:30 IST)
    bar_valid = make_ist_datetime(sample_date, time(10, 30))
    assert cal.validate_bar_session(bar_valid, segment="NSE_EQ") is True

    # Invalid out-of-session bar (16:00 IST / post-market)
    bar_invalid = make_ist_datetime(sample_date, time(16, 0))
    assert cal.validate_bar_session(bar_invalid, segment="NSE_EQ") is False

    # Invalid pre-market bar (08:30 IST)
    bar_early = make_ist_datetime(sample_date, time(8, 30))
    assert cal.validate_bar_session(bar_early, segment="NSE_EQ") is False
