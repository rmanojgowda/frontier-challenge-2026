"""Record validation helpers for the batch import pipeline."""

import re

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(value):
    """True if ``value`` looks like an email address."""
    return bool(_EMAIL_RE.match(value or ""))


def is_in_range(value, low, high):
    """True if ``low <= value <= high``.

    Non-numeric or missing values are not in any range, so this should return
    ``False`` for them rather than blowing up.
    """
    try:
        return low <= value <= high
    except ValueError:
        return False


def validate_row(row):
    """Return a list of problem strings for ``row`` (empty list == valid)."""
    problems = []
    if not is_valid_email(row.get("email")):
        problems.append("email is not valid")
    if not is_in_range(row.get("age"), 0, 130):
        problems.append("age is out of range")
    return problems


def filter_valid(rows):
    """Return only the rows that pass :func:`validate_row`."""
    return [row for row in rows if not validate_row(row)]
