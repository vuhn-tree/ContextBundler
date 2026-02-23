"""List helper functions."""


def flatten(nested):
    result = []
    for item in nested:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result


def chunk(lst, size):
    return [lst[i:i + size] for i in range(0, len(lst), size)]


def unique(lst):
    seen = set()
    return [x for x in lst if not (x in seen or seen.add(x))]


if __name__ == "__main__":
    print(flatten([1, [2, [3, 4]], 5]))
    print(chunk([1, 2, 3, 4, 5, 6], 2))
    print(unique([1, 2, 2, 3, 3, 3]))
