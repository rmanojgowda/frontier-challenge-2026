import pytest

from humanize import intword


def test_intword_million():
    assert intword(1_000_000) == "1.0 million"


def test_intword_fractional_million():
    assert intword(1_200_000) == "1.2 million"


def test_intword_reported_case_rounds_into_billions():
    # 999,999,999 rounded to one decimal is 1.0 billion, not "1000.0 million".
    assert intword(999_999_999) == "1.0 billion"


def test_intword_carry_just_below_boundary():
    # 999,950,000 / 1e6 == 999.95, which "%.1f" rounds to "1000.0" -> it must
    # tip into the next unit even though 999.95 is numerically below 1000.
    assert intword(999_950_000) == "1.0 billion"


def test_intword_carry_into_trillions():
    # Same rounding carry, one tier higher.
    assert intword(999_999_999_999) == "1.0 trillion"


def test_intword_exact_billion():
    assert intword(1_000_000_000) == "1.0 billion"


def test_intword_below_million_unchanged():
    assert intword(100) == "100"
