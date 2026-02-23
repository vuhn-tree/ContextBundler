"""String transformation functions."""


def reverse(s):
    return s[::-1]


def capitalize_words(s):
    return s.title()


def snake_to_camel(s):
    parts = s.split("_")
    return parts[0] + "".join(w.capitalize() for w in parts[1:])


def camel_to_snake(s):
    result = [s[0].lower()]
    for c in s[1:]:
        if c.isupper():
            result.append("_")
        result.append(c.lower())
    return "".join(result)


if __name__ == "__main__":
    print(reverse("hello"))
    print(snake_to_camel("my_variable_name"))
    print(camel_to_snake("myVariableName"))
