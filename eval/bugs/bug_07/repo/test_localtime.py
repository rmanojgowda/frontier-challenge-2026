from datetime import datetime, date

import pytest

from localtime import to_local, event_day, is_weekend


def test_to_local_shifts_by_offset():
    ts = datetime(2023, 3, 11, 2, 0, 0)   # 02:00 UTC
    assert to_local(ts, -5) == datetime(2023, 3, 10, 21, 0, 0)


def test_event_day_same_day_in_both_zones():
    ts = datetime(2023, 3, 11, 15, 0, 0)  # 15:00 UTC -> 10:00 local
    assert event_day(ts, -5) == date(2023, 3, 11)


def test_event_day_before_local_midnight():
    # 02:00 UTC on the 11th is still 21:00 on the 10th in a -5 zone
    ts = datetime(2023, 3, 11, 2, 0, 0)
    assert event_day(ts, -5) == date(2023, 3, 10)


def test_event_day_after_local_midnight_ahead_zone():
    # 22:00 UTC on the 10th is 04:00 on the 11th in a +6 zone
    ts = datetime(2023, 3, 10, 22, 0, 0)
    assert event_day(ts, 6) == date(2023, 3, 11)


def test_is_weekend_uses_local_day():
    # 02:00 UTC Monday -> Sunday 21:00 local, which is the weekend
    ts = datetime(2023, 3, 13, 2, 0, 0)   # Monday UTC
    assert is_weekend(ts, -5) is True
