#!/usr/bin/env python3
"""Apply modified context."""

import argparse
import difflib
import os
import platform
import re
import subprocess
import sys
import tempfile

FILE_BLOCK_PATTERN = re.compile(
    r'^={5}\s*FILE:\s*(.+?)\s*={5}\s*\n'
    r'(.*?)'
    r'^={5}\s*END FILE:\s*(.+?)\s*={5}',
    re.MULTILINE | re.DOTALL
)

CODE_FENCE_PATTERN = re.compile(
    r'^```\w*\n(.*?)^```\s*$',
    re.MULTILINE | re.DOTALL
)

FALLBACK_PATTERN = re.compile(
    r'`([^`\n]+\.\w+)`\s*\n'
    r'```\w*\n'
    r'(.*?)'
    r'\n```',
    re.DOTALL
)

RED, GREEN, YELLOW, CYAN = "\033[91m", "\033[92m", "\033[93m", "\033[96m"
BOLD, RESET = "\033[1m", "\033[0m"


def colored(text, color):
    if hasattr(sys.stderr, "isatty") and sys.stderr.isatty():
        return f"{color}{text}{RESET}"
    return text


def read_clipboard():
    system = platform.system()
    if system == "Darwin":
        cmd = ["pbpaste"]
    elif system == "Windows":
        cmd = ["powershell", "-command", "Get-Clipboard"]
    else:
        return None
    try:
        r = subprocess.run(cmd, capture_output=True, check=True)
        return r.stdout.decode("utf-8")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def parse_file_blocks(text):
    blocks = []

    for match in FILE_BLOCK_PATTERN.finditer(text):
        open_path = match.group(1).strip()
        content = match.group(2)
        close_path = match.group(3).strip()

        if open_path != close_path:
            print(colored(f"  Warning: mismatched markers: '{open_path}' vs '{close_path}', skipping", YELLOW), file=sys.stderr)
            continue

        fence_match = CODE_FENCE_PATTERN.search(content)
        if fence_match:
            content = fence_match.group(1)
        else:
            if content.startswith("\n"):
                content = content[1:]

        content = content.replace("\r\n", "\n").replace("\r", "\n")

        if content.endswith("\n\n"):
            content = content[:-1]

        blocks.append((open_path, content))

    if blocks:
        return blocks

    # Fallback: markdown code blocks with `filename` on the line before
    print(colored("No ===== FILE: ... ===== blocks found. Trying fallback (markdown code blocks)...", YELLOW), file=sys.stderr)
    for match in FALLBACK_PATTERN.finditer(text):
        blocks.append((match.group(1).strip(), match.group(2)))

    return blocks


def validate_path(rel_path, project_root):
    if os.path.isabs(rel_path):
        print(colored(f"  Rejected '{rel_path}': absolute path", RED), file=sys.stderr)
        return None

    normalized = os.path.normpath(rel_path)
    if normalized.startswith(".."):
        print(colored(f"  Rejected '{rel_path}': path traversal", RED), file=sys.stderr)
        return None

    full_path = os.path.abspath(os.path.join(project_root, normalized))
    abs_root = os.path.abspath(project_root)
    if not full_path.startswith(abs_root + os.sep) and full_path != abs_root:
        print(colored(f"  Rejected '{rel_path}': outside project root", RED), file=sys.stderr)
        return None

    return full_path


def compute_diff(rel_path, old, new):
    return list(difflib.unified_diff(
        old.splitlines(keepends=True), new.splitlines(keepends=True),
        fromfile=f"a/{rel_path}", tofile=f"b/{rel_path}",
    ))


def colorize_diff(lines):
    out = []
    for line in lines:
        if line.startswith("+++") or line.startswith("---"):
            out.append(colored(line, BOLD))
        elif line.startswith("+"):
            out.append(colored(line, GREEN))
        elif line.startswith("-"):
            out.append(colored(line, RED))
        elif line.startswith("@@"):
            out.append(colored(line, CYAN))
        else:
            out.append(line)
    return out


def count_changes(diff_lines):
    added = sum(1 for l in diff_lines if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in diff_lines if l.startswith("-") and not l.startswith("---"))
    return added, removed


def write_file_atomic(filepath, content):
    directory = os.path.dirname(filepath)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".tmp_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, filepath)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def main():
    parser = argparse.ArgumentParser(description="Apply modified context.")
    parser.add_argument("project_dir", help="Path to the project directory")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing")
    parser.add_argument("--no-confirm", action="store_true", help="Skip confirmation prompt")
    parser.add_argument("--from-file", type=str, default=None, help="Read from file instead of clipboard")
    args = parser.parse_args()

    if not os.path.isdir(args.project_dir):
        print(f"Error: '{args.project_dir}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    abs_root = os.path.abspath(args.project_dir)

    if args.from_file:
        try:
            with open(args.from_file, "r", encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        text = read_clipboard()
        if not text:
            print("Error: clipboard is empty or unreadable.", file=sys.stderr)
            sys.exit(1)

    blocks = parse_file_blocks(text)
    if not blocks:
        print("No file blocks found in the input.", file=sys.stderr)
        print("Make sure the context used the ===== FILE: ... ===== format.", file=sys.stderr)
        sys.exit(1)

    changes = []
    for rel_path, new_content in blocks:
        full_path = validate_path(rel_path, abs_root)
        if full_path is None:
            continue

        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                old_content = f.read()
            if old_content == new_content:
                changes.append((rel_path, "unchanged", [], new_content, full_path))
            else:
                changes.append((rel_path, "modified", compute_diff(rel_path, old_content, new_content), new_content, full_path))
        else:
            added = [f"+{line}\n" for line in new_content.splitlines()]
            changes.append((rel_path, "added", added, new_content, full_path))

    if not changes:
        print("No valid changes to apply.", file=sys.stderr)
        sys.exit(1)

    print(colored("\nChanges to apply:", BOLD), file=sys.stderr)
    has_changes = False
    for rel_path, status, diff_lines, _, _ in changes:
        if status == "modified":
            a, r = count_changes(diff_lines)
            print(f"  [M] {rel_path}  (+{a}, -{r} lines)", file=sys.stderr)
            has_changes = True
        elif status == "added":
            print(colored(f"  [A] {rel_path}  (new file, {len(diff_lines)} lines)", GREEN), file=sys.stderr)
            has_changes = True
        else:
            print(f"  [=] {rel_path}  (unchanged, skipping)", file=sys.stderr)

    if not has_changes:
        print("\nAll files are unchanged. Nothing to do.", file=sys.stderr)
        sys.exit(0)

    print(file=sys.stderr)
    for rel_path, status, diff_lines, _, _ in changes:
        if status == "unchanged":
            continue
        if status == "added":
            print(colored(f"--- New file: {rel_path} ---", GREEN), file=sys.stderr)
            for line in diff_lines:
                print(colored(line.rstrip(), GREEN), file=sys.stderr)
        else:
            for line in colorize_diff(diff_lines):
                print(line.rstrip(), file=sys.stderr)
        print(file=sys.stderr)

    if args.dry_run:
        print(colored("Dry run, no files were modified.", YELLOW), file=sys.stderr)
        sys.exit(0)

    if not args.no_confirm:
        try:
            answer = input("Apply these changes? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.", file=sys.stderr)
            sys.exit(1)
        if answer != "y":
            print("Aborted.", file=sys.stderr)
            sys.exit(1)

    applied = 0
    for rel_path, status, _, new_content, full_path in changes:
        if status == "unchanged":
            continue
        try:
            write_file_atomic(full_path, new_content)
            print(f"  Wrote {rel_path}", file=sys.stderr)
            applied += 1
        except Exception as e:
            print(colored(f"  Error writing {rel_path}: {e}", RED), file=sys.stderr)

    print(f"\nApplied {applied} file(s).", file=sys.stderr)


if __name__ == "__main__":
    main()
