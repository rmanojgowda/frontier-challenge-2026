import pytest

from stringutils import truncate, word_count, normalize_spaces, initials


def test_truncate_shorter_than_limit():
    assert truncate("hello", 10) == "hello"


def test_truncate_equal_to_limit():
    assert truncate("hello", 5) == "hello"


def test_truncate_longer_than_limit():
    # "hello world" cut to 5 characters should be exactly "hello"
    assert truncate("hello world", 5) == "hello"


def test_truncate_keeps_all_requested_characters():
    assert truncate("abcdefgh", 3) == "abc"


def test_word_count():
    assert word_count("the quick brown fox") == 4


def test_normalize_spaces():
    assert normalize_spaces("  a   b \t c\n") == "a b c"


def test_initials():
    assert initials("ada lovelace") == "AL"
