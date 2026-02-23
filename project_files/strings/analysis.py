"""String analysis functions."""


def count_vowels(s):
    return sum(1 for c in s.lower() if c in "aeiou")


def count_words(s):
    return len(s.split())


def is_palindrome(s):
    cleaned = s.lower().replace(" ", "")
    return cleaned == cleaned[::-1]


if __name__ == "__main__":
    print(count_vowels("banana"))
    print(count_words("the quick brown fox"))
    print(is_palindrome("racecar"))
    print(is_palindrome("hello"))
