"""Data validation helpers."""


def is_valid_email(email):
    return "@" in email and "." in email.split("@")[-1]


def is_positive(n):
    return isinstance(n, (int, float)) and n > 0


def is_non_empty(s):
    return isinstance(s, str) and len(s.strip()) > 0


def is_in_range(n, low, high):
    return low <= n <= high


if __name__ == "__main__":
    print(is_valid_email("user@example.com"))
    print(is_positive(-5))
    print(is_non_empty("  "))
    print(is_in_range(5, 1, 10))
