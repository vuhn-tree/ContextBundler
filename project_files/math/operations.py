"""Basic arithmetic operations."""


def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


def multiply(a, b):
    return a * b


def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


def power(a, b):
    return a ** b


if __name__ == "__main__":
    print(add(2, 3))
    print(subtract(10, 4))
    print(multiply(5, 6))
    print(divide(9, 3))
    print(power(2, 8))
