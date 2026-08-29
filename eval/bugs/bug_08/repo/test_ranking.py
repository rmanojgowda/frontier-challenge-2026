import pytest

from ranking import rank_by_time, fastest, podium


RACERS = [
    {"name": "Ada", "time": 42.0},
    {"name": "Bo", "time": 37.5},
    {"name": "Cy", "time": 55.1},
    {"name": "Di", "time": 40.2},
]


def test_rank_order_is_fastest_first():
    ranked = rank_by_time(RACERS)
    assert [r["name"] for r in ranked] == ["Bo", "Di", "Ada", "Cy"]


def test_rank_numbers_start_at_one_for_fastest():
    ranked = rank_by_time(RACERS)
    assert ranked[0]["name"] == "Bo"
    assert ranked[0]["rank"] == 1
    assert ranked[-1]["name"] == "Cy"
    assert ranked[-1]["rank"] == 4


def test_fastest():
    assert fastest(RACERS) == "Bo"


def test_podium():
    assert podium(RACERS) == ["Bo", "Di", "Ada"]


def test_single_racer():
    assert rank_by_time([{"name": "Solo", "time": 10.0}]) == [
        {"name": "Solo", "time": 10.0, "rank": 1}
    ]
