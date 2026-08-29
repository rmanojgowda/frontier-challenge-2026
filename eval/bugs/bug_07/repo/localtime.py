"""Turn UTC timestamps into local-calendar answers."""

from datetime import datetime, timedelta


def to_local(ts_utc, tz_offset_hours):
    """Return ``ts_utc`` shifted into a fixed-offset local zone."""
    return ts_utc + timedelta(hours=tz_offset_hours)


def event_day(ts_utc, tz_offset_hours):
    """Return the local calendar date on which ``ts_utc`` falls.

    ``ts_utc`` is a naive :class:`datetime` understood to be UTC.
    ``tz_offset_hours`` is the viewer's offset from UTC (e.g. ``-5`` for US
    Eastern standard time).
    """
    return ts_utc.date()


def is_weekend(ts_utc, tz_offset_hours):
    """True if the event falls on Saturday or Sunday, local time."""
    return event_day(ts_utc, tz_offset_hours).weekday() >= 5
