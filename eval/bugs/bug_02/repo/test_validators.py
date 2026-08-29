import pytest

from validators import is_valid_email, is_in_range, validate_row, filter_valid


def test_email_accepts_plain_address():
    assert is_valid_email("user@example.com")


def test_email_rejects_garbage():
    assert not is_valid_email("not-an-email")


def test_in_range_true_for_number_inside():
    assert is_in_range(50, 0, 130)


def test_in_range_false_for_number_outside():
    assert not is_in_range(200, 0, 130)


def test_in_range_rejects_non_numeric_string():
    # A string age like "forty" is bad data; it is simply not in range.
    assert is_in_range("forty", 0, 130) is False


def test_in_range_rejects_none():
    assert is_in_range(None, 0, 130) is False


def test_validate_row_flags_bad_age_type():
    problems = validate_row({"email": "a@b.com", "age": "forty"})
    assert "age is out of range" in problems


def test_filter_valid_drops_row_with_mistyped_age():
    rows = [
        {"email": "a@b.com", "age": 30},
        {"email": "c@d.com", "age": "forty"},
        {"email": "e@f.com", "age": 45},
    ]
    assert filter_valid(rows) == [
        {"email": "a@b.com", "age": 30},
        {"email": "e@f.com", "age": 45},
    ]
