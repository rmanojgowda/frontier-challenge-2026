"""Primitive geometry formulas."""

import math


def cylinder_volume(radius, height):
    """Volume of a right circular cylinder."""
    return math.pi * radius ** 2 * height


def rectangle_area(width, height):
    """Area of a rectangle."""
    return width * height
