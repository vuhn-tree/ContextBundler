#!/usr/bin/env python3
"""Bundle a project directory."""

import argparse
import os
import platform
import subprocess
import sys

EXCLUDED_DIRS = {
    ".git", "__pycache__", ".venv", "venv", "env",
    "node_modules", ".mypy_cache", ".pytest_cache",
    ".tox", ".eggs", "dist", "build", ".idea", ".vscode",
    ".claude", ".ruff_cache",
}

EXCLUDED_FILES = {".DS_Store", "Thumbs.db", ".env"}

EXCLUDED_EXTENSIONS = {
    ".pyc", ".pyo", ".so", ".dylib", ".dll", ".exe",
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg", ".webp",
    ".mp3", ".mp4", ".wav", ".avi", ".mov",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".lock", ".log", ".egg-info",
}

LOCKFILE_NAMES = {
    "package-lock.json", "yarn.lock", "poetry.lock",
    "Pipfile.lock", "pnpm-lock.yaml", "Cargo.lock",
    "composer.lock", "Gemfile.lock",
}

MAX_FILE_SIZE = 100 * 1024

HEADER_TEMPLATE = """\
===== PROJECT BUNDLE =====
Project: {project_name}
Files: {file_count}
Total size: {total_size}

When you respond with modified files, use EXACTLY this format for each file:

  ===== FILE: path/to/file.py =====
  ```
  <full file contents>
  ```
  ===== END FILE: path/to/file.py =====

IMPORTANT: Always wrap the file contents in ``` code fences as shown above.
Only include files you have changed. Do not include unchanged files.
===== END INSTRUCTIONS =====
"""


def is_binary(filepath):
    try:
        with open(filepath, "rb") as f:
            return b"\x00" in f.read(8192)
    except OSError:
        return True


def should_exclude(filename, ext, config):
    if filename in EXCLUDED_FILES:
        return "excluded filename"
    if filename in LOCKFILE_NAMES:
        return "lockfile"
    if ext in EXCLUDED_EXTENSIONS:
        return "excluded extension"
    if filename in config.get("exclude_files", []):
        return "user-excluded"
    return None


def collect_files(root, config):
    root = os.path.abspath(root)
    files, skipped = [], []
    max_size = config.get("max_file_size", MAX_FILE_SIZE)
    extra_exclude = set(config.get("exclude_dirs", []))

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            d for d in dirnames
            if d not in EXCLUDED_DIRS and d not in extra_exclude
        )

        for filename in sorted(filenames):
            filepath = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(filepath, root)
            ext = os.path.splitext(filename)[1].lower()

            reason = should_exclude(filename, ext, config)
            if reason:
                skipped.append((rel_path, reason))
                continue

            try:
                size = os.path.getsize(filepath)
            except OSError:
                skipped.append((rel_path, "unreadable"))
                continue

            if size > max_size:
                skipped.append((rel_path, f"exceeds {max_size // 1024} KB"))
                continue

            if is_binary(filepath):
                skipped.append((rel_path, "binary"))
                continue

            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    files.append((rel_path, f.read()))
            except OSError:
                skipped.append((rel_path, "read error"))

    return files, skipped


def build_tree(files):
    lines = []
    prev_parts = []

    for rel_path, _ in files:
        parts = rel_path.split(os.sep)
        common = 0
        for i in range(min(len(prev_parts), len(parts) - 1)):
            if prev_parts[i] == parts[i]:
                common = i + 1
            else:
                break

        for i in range(common, len(parts) - 1):
            lines.append(f"{'  ' * i}{parts[i]}/")
        lines.append(f"{'  ' * (len(parts) - 1)}{parts[-1]}")
        prev_parts = parts

    return "\n".join(lines)


def human_size(n):
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


def build_bundle(root, files):
    name = os.path.basename(os.path.abspath(root))
    total = sum(len(c.encode("utf-8")) for _, c in files)

    parts = [
        HEADER_TEMPLATE.format(project_name=name, file_count=len(files), total_size=human_size(total)),
        "===== TREE =====",
        build_tree(files),
        "===== END TREE =====\n",
    ]

    for rel_path, content in files:
        ext = os.path.splitext(rel_path)[1].lstrip(".")
        if not content.endswith("\n"):
            content += "\n"
        parts.append(
            f"===== FILE: {rel_path} =====\n"
            f"```{ext}\n"
            f"{content}"
            f"```\n"
            f"===== END FILE: {rel_path} ====="
        )

    return "\n".join(parts)


def copy_to_clipboard(text):
    system = platform.system()
    if system == "Darwin":
        cmd = ["pbcopy"]
    elif system == "Windows":
        cmd = ["clip"]
    else:
        return False
    try:
        subprocess.run(cmd, input=text.encode("utf-8"), check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def main():
    parser = argparse.ArgumentParser(description="Bundle a projects context.")
    parser.add_argument("project_dir", help="Path to the project directory")
    parser.add_argument("-o", "--output", type=str, default=None,
                        help="Output file path (default: <project_name>_bundle.txt)")
    parser.add_argument("--clipboard", action="store_true",
                        help="Copy to clipboard instead of writing to file")
    parser.add_argument("--stdout", action="store_true",
                        help="Print to stdout instead of writing to file")
    parser.add_argument("--max-file-size", type=int, default=MAX_FILE_SIZE // 1024,
                        help="Skip files larger than this in KB (default: 100)")
    parser.add_argument("--exclude-dir", action="append", default=[],
                        help="Additional directories to exclude (repeatable)")
    parser.add_argument("--exclude-file", action="append", default=[],
                        help="Additional files to exclude (repeatable)")
    args = parser.parse_args()

    if not os.path.isdir(args.project_dir):
        print(f"Error: '{args.project_dir}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    config = {
        "max_file_size": args.max_file_size * 1024,
        "exclude_dirs": args.exclude_dir,
        "exclude_files": args.exclude_file,
    }

    files, skipped = collect_files(args.project_dir, config)
    if not files:
        print("No files found to bundle.", file=sys.stderr)
        sys.exit(1)

    bundle = build_bundle(args.project_dir, files)
    bundle_size = len(bundle.encode("utf-8"))
    proj_name = os.path.basename(os.path.abspath(args.project_dir))

    if args.stdout:
        print(bundle)
    elif args.clipboard:
        if copy_to_clipboard(bundle):
            print("Copied to clipboard.", file=sys.stderr)
        else:
            print("Failed to copy to clipboard.", file=sys.stderr)
            sys.exit(1)
    else:
        out_path = args.output or f"{proj_name}_bundle.txt"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(bundle)
        print(f"Wrote {out_path}", file=sys.stderr)

    print(f"\nBundled {len(files)} files ({human_size(bundle_size)}) from \"{proj_name}\"", file=sys.stderr)

    if skipped:
        print(f"\nSkipped {len(skipped)} files:", file=sys.stderr)
        for path, reason in skipped:
            print(f"  {path} ({reason})", file=sys.stderr)

    if bundle_size > 1024 * 1024:
        print(f"\nWARNING: Bundle is {human_size(bundle_size)}. Context might be truncated.", file=sys.stderr)
    elif bundle_size > 500 * 1024:
        print(f"\nWARNING: Bundle is {human_size(bundle_size)}. May exceed context limits.", file=sys.stderr)


if __name__ == "__main__":
    main()
