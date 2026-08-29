import math

import pytest

from mathlib import cylinder_volume
from containers import tank_capacity_litres, fill_time_seconds


def test_cylinder_volume_direct():
    # radius 2, height 10
    assert cylinder_volume(2, 10) == pytest.approx(math.pi * 4 * 10)


def test_tank_capacity_radius_2_height_10():
    # A tank 10 m tall with a 2 m radius holds pi * 2**2 * 10 m^3 -> * 1000 L
    expected = math.pi * (2 ** 2) * 10 * 1000
    assert tank_capacity_litres(10, 2) == pytest.approx(expected)


def test_tank_capacity_is_not_symmetric_in_its_args():
    # swapping height and radius must change the answer
    assert tank_capacity_litres(10, 2) != pytest.approx(tank_capacity_litres(2, 10))


def test_fill_time():
    expected_cap = math.pi * (2 ** 2) * 10 * 1000
    assert fill_time_seconds(10, 2, 5) == pytest.approx(expected_cap / 5)
