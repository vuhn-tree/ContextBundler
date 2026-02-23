"""Geometry calculations."""

import math


def circle_area(radius):
    return math.pi * radius ** 2


def rectangle_area(width, height):
    return width * height


def triangle_area(base, height):
    return 0.5 * base * height


def distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


if __name__ == "__main__":
    print(circle_area(5))
    print(rectangle_area(4, 7))
    print(distance(0, 0, 3, 4))
