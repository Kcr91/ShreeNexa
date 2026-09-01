"""Indian market trading calendar, per-segment sessions, holidays, and timezone normalization."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CALENDAR_PATH = REPO_ROOT / "config" / "calendars" / "nse_calendar.yaml"
IST = ZoneInfo("Asia/Kolkata")


def to_utc(dt: datetime) -> datetime:
    """Normalize any datetime to UTC timezone-aware datetime."""
    if dt.tzinfo is None:
        # Assume naive datetime is already UTC or attach UTC
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def to_ist(dt: datetime) -> datetime:
    """Convert any timezone-aware datetime to IST (Asia/Kolkata)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(IST)


def make_ist_datetime(d: date, t: time) -> datetime:
    """Construct an IST datetime from date and time and convert to UTC."""
    dt_ist = datetime.combine(d, t, tzinfo=IST)
    return dt_ist.astimezone(UTC)


class SessionBounds(BaseModel):
    """Start and end time for a regular or special trading session."""

    model_config = ConfigDict(frozen=True)

    start: time
    end: time


class SpecialSession(BaseModel):
    """Special trading session definition (e.g. Muhurat trading, DR live switch)."""

    model_config = ConfigDict(frozen=True)

    session_date: date
    name: str
    segments: list[str]
    start: time
    end: time


class Holiday(BaseModel):
    """Market holiday definition."""

    model_config = ConfigDict(frozen=True)

    holiday_date: date
    name: str
    segments: list[str] = Field(default_factory=lambda: ["ALL"])


class TradingCalendar:
    """Trading calendar for Indian market segments, holiday resolution, and session validation."""

    def __init__(self, config_path: Path | str | None = None) -> None:
        self.config_path = (
            Path(config_path).resolve() if config_path else DEFAULT_CALENDAR_PATH.resolve()
        )
        self.calendar_version: str = "unknown"
        self.timezone_name: str = "Asia/Kolkata"
        self.default_sessions: dict[str, SessionBounds] = {}
        self.holidays: dict[date, list[Holiday]] = {}
        self.special_sessions: dict[date, list[SpecialSession]] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load calendar YAML configuration."""
        if not self.config_path.is_file():
            logger.warning("Calendar config file not found at %s; using defaults", self.config_path)
            self._load_fallback_defaults()
            return

        with self.config_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        self.calendar_version = str(data.get("calendar_version", "cal-default"))
        self.timezone_name = str(data.get("timezone", "Asia/Kolkata"))

        for seg, bounds in data.get("default_sessions", {}).items():
            s_time = time.fromisoformat(bounds["start"])
            e_time = time.fromisoformat(bounds["end"])
            self.default_sessions[seg.upper()] = SessionBounds(start=s_time, end=e_time)

        for h in data.get("holidays", []):
            h_date = date.fromisoformat(h["date"])
            hol = Holiday(
                holiday_date=h_date,
                name=h["name"],
                segments=[s.upper() for s in h.get("segments", ["ALL"])],
            )
            self.holidays.setdefault(h_date, []).append(hol)

        for s in data.get("special_sessions", []):
            s_date = date.fromisoformat(s["date"])
            spec = SpecialSession(
                session_date=s_date,
                name=s["name"],
                segments=[seg.upper() for seg in s.get("segments", ["ALL"])],
                start=time.fromisoformat(s["start"]),
                end=time.fromisoformat(s["end"]),
            )
            self.special_sessions.setdefault(s_date, []).append(spec)

    def _load_fallback_defaults(self) -> None:
        """Fallback session baselines if config is absent."""
        self.calendar_version = "cal-fallback-v1"
        standard = SessionBounds(start=time(9, 15), end=time(15, 30))
        for seg in ["NSE_EQ", "BSE_EQ", "NSE_FNO", "BSE_FNO", "IDX_I"]:
            self.default_sessions[seg] = standard
        self.default_sessions["NSE_CURR"] = SessionBounds(start=time(9, 0), end=time(17, 0))
        self.default_sessions["BSE_CURR"] = SessionBounds(start=time(9, 0), end=time(17, 0))
        self.default_sessions["MCX_COMM"] = SessionBounds(start=time(9, 0), end=time(23, 30))

    def is_holiday(self, day: date, segment: str = "NSE_EQ") -> bool:
        """Check if date is an official trading holiday for the given segment."""
        seg_upper = segment.upper()
        if day in self.holidays:
            for h in self.holidays[day]:
                if "ALL" in h.segments or seg_upper in h.segments:
                    return True
        return False

    def is_trading_day(self, day: date, segment: str = "NSE_EQ") -> bool:
        """Check if date has an active trading session for the given segment."""
        seg_upper = segment.upper()

        # Check special sessions (e.g. Diwali Muhurat or DR Saturday trading)
        if day in self.special_sessions:
            for s in self.special_sessions[day]:
                if "ALL" in s.segments or seg_upper in s.segments:
                    return True

        # Weekend check: Saturday (5) and Sunday (6) are non-trading days
        if day.weekday() in (5, 6):
            return False

        # Regular holiday check
        if self.is_holiday(day, segment=segment):
            return False

        return True

    def get_session_bounds_utc(
        self, day: date, segment: str = "NSE_EQ"
    ) -> list[tuple[datetime, datetime]]:
        """Return list of (start_utc, end_utc) intervals for the given date and segment."""
        seg_upper = segment.upper()
        intervals: list[tuple[datetime, datetime]] = []

        # Check special sessions for this day
        if day in self.special_sessions:
            for s in self.special_sessions[day]:
                if "ALL" in s.segments or seg_upper in s.segments:
                    start_utc = make_ist_datetime(day, s.start)
                    end_utc = make_ist_datetime(day, s.end)
                    intervals.append((start_utc, end_utc))

        # If it's a regular trading day, add regular session bounds
        if not self.is_holiday(day, segment=segment) and day.weekday() not in (5, 6):
            def_bounds = self.default_sessions.get(
                seg_upper, SessionBounds(start=time(9, 15), end=time(15, 30))
            )
            start_utc = make_ist_datetime(day, def_bounds.start)
            end_utc = make_ist_datetime(day, def_bounds.end)
            intervals.append((start_utc, end_utc))

        return intervals

    def is_session_time(self, dt: datetime, segment: str = "NSE_EQ") -> bool:
        """Check if a timestamp falls within an active trading session for the segment."""
        dt_utc = to_utc(dt)
        dt_ist = to_ist(dt_utc)
        day_ist = dt_ist.date()

        intervals = self.get_session_bounds_utc(day_ist, segment=segment)
        for s_utc, e_utc in intervals:
            if s_utc <= dt_utc <= e_utc:
                return True

        return False

    def get_trading_days(
        self, start_date: date, end_date: date, segment: str = "NSE_EQ"
    ) -> list[date]:
        """Return chronological list of all trading days between start_date and end_date."""
        if start_date > end_date:
            return []

        days: list[date] = []
        cur = start_date
        while cur <= end_date:
            if self.is_trading_day(cur, segment=segment):
                days.append(cur)
            cur += timedelta(days=1)

        return days

    def validate_bar_session(self, bar_timestamp: datetime, segment: str = "NSE_EQ") -> bool:
        """Validate that a bar timestamp strictly falls within active market hours."""
        return self.is_session_time(bar_timestamp, segment=segment)
