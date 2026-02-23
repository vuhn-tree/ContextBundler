"""Dictionary helper functions."""


def merge(a, b):
    result = a.copy()
    result.update(b)
    return result


def invert(d):
    return {v: k for k, v in d.items()}


def filter_by_value(d, predicate):
    return {k: v for k, v in d.items() if predicate(v)}


if __name__ == "__main__":
    print(merge({"a": 1}, {"b": 2}))
    print(invert({"x": 1, "y": 2}))
    print(filter_by_value({"a": 1, "b": 5, "c": 3}, lambda v: v > 2))
