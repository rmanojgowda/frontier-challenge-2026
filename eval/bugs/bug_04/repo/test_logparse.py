import pytest

from logparse import parse_kv, get_level, is_error


def test_parse_single_pair():
    assert parse_kv('user="alice"') == {"user": "alice"}


def test_parse_multiple_pairs():
    line = 'user="alice" action="login" result="ok"'
    assert parse_kv(line) == {
        "user": "alice",
        "action": "login",
        "result": "ok",
    }


def test_parse_pair_among_other_text():
    line = 'ts=2023-01-01 msg="hello" latency_ms="12" done'
    assert parse_kv(line) == {"msg": "hello", "latency_ms": "12"}


def test_value_with_spaces_is_kept_whole():
    line = 'msg="disk almost full" level="WARNING"'
    assert parse_kv(line) == {"msg": "disk almost full", "level": "WARNING"}


def test_get_level():
    assert get_level("2023-01-01 ERROR something broke") == "ERROR"


def test_is_error():
    assert is_error("ERROR boom")
    assert not is_error("INFO fine")
