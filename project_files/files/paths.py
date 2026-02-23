"""File path utilities."""

import os


def get_extension(filepath):
    return os.path.splitext(filepath)[1]


def swap_extension(filepath, new_ext):
    base = os.path.splitext(filepath)[0]
    return base + new_ext


def list_files(directory, ext=None):
    files = os.listdir(directory)
    if ext:
        files = [f for f in files if f.endswith(ext)]
    return sorted(files)


if __name__ == "__main__":
    print(get_extension("report.pdf"))
    print(swap_extension("data.csv", ".json"))
