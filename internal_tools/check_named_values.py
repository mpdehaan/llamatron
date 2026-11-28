# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fail any Rust line a change adds that types a value with a meaning in place rather than naming it.

Two kinds of value are caught, in code and tests alike (.claude/rules/STYLE.md, "Every value with a meaning is
named"): a number other than 0 and 1, and a string literal that is a name used as a value, such as "osc2_pitch" or
"type". A line that defines a constant or a named `let` is where a value gets its name, and is passed over. The files
that define names, and the texts the program shows, are passed over too.

The lines read are those the working tree adds to the last commit, and every line of a Rust file git does not track
yet, so that nothing new breaks the rule while older lines are cleaned area by area. With --everything it reads every
line of the program instead.
"""

import pathlib
import re
import subprocess
import sys

TOP = pathlib.Path(__file__).resolve().parent.parent
RUST = "src"
RUST_SUFFIX = ".rs"
EVERYTHING = "--everything"

# Where a value is given its name, or where the program's shown text lives: the names crate, the strings crate's
# texts, and the tables the schema and the tracker generate from them.
DEFINING_PLACES = (
    "src/names/",
    "src/strings/src/texts/",
    "src/model/src/schema/generated/",
    "src/tracker/src/generated/",
)
# Build output, never read.
BUILT = "/target/"

# A string literal, its text the first group, and one that is a name: lowercase words joined by underscores.
STRING_LITERAL = re.compile(r'"((?:[^"\\]|\\.)*)"')
NAME = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
# A number standing alone, with a type suffix or not, and the numbers that need no name.
NUMBER = re.compile(r"(?<![\w.])(\d[\d_]*(?:\.\d+)?(?:[eE]-?\d+)?)(?:_?(?:f32|f64|i8|i16|i32|i64|i128|u8|u16|u32|u64|u128|usize|isize))?(?![\w.])")
PLAIN_NUMBERS = {"0", "1", "0.0", "1.0"}
# Lines that give a value its name: a constant or a static, or a `let` binding a plain number or text to a name, or
# several to a tuple of names.
NAMING_LINE = re.compile(r"^\s*(?:pub(?:\([a-z]+\))?\s+)?(?:const|static)\s|^\s*let\s+(?:mut\s+)?(?:[a-z_][a-z0-9_]*|\((?:mut\s+)?[a-z_][a-z0-9_]*(?:\s*,\s*(?:mut\s+)?[a-z_][a-z0-9_]*)*\s*,?\))(?:\s*:\s*[\w<>(),&' \[\];]+)?\s*=\s*(?:[-\d\"(\[]|b\")")
# A comment, from where it starts to the line's end, and an attribute line.
COMMENT = re.compile(r"//.*$")
ATTRIBUTE = re.compile(r"^\s*#!?\[")


# Where a constant or a static begins, whose every line, to the semicolon that ends it, gives values their names.
DEFINITION_START = re.compile(r"^\s*(?:pub(?:\([a-z]+\))?\s+)?(?:const|static)\s")


def definition_lines(text: str) -> set[int]:
    """The numbers of the lines inside a constant's or a static's definition, such as the rows of a table."""
    inside, depth, numbers = False, 0, set()
    for number, line in enumerate(text.splitlines(), 1):
        code = STRING_LITERAL.sub('""', COMMENT.sub("", line))
        if not inside and DEFINITION_START.match(line):
            inside, depth = True, 0
        if inside:
            numbers.add(number)
            depth += code.count("[") + code.count("(") + code.count("{") - code.count("]") - code.count(")") - code.count("}")
            if depth <= 0 and code.rstrip().endswith(";"):
                inside = False
    return numbers


def passed_over(path: str) -> bool:
    """Whether a file is one the check never reads: built output, or a place where values are given their names."""
    return BUILT in path or path.startswith(DEFINING_PLACES)


def breakages(line: str) -> list[str]:
    """What a line types in place that should be named: each name typed as text, and each number other than 0 or 1."""
    if NAMING_LINE.match(line) or ATTRIBUTE.match(line):
        return []
    code = COMMENT.sub("", line)
    found = [f'"{text}"' for text in STRING_LITERAL.findall(code) if NAME.match(text)]
    without_text = STRING_LITERAL.sub('""', code)
    found += [number for number in NUMBER.findall(without_text) if number not in PLAIN_NUMBERS]
    return found


def added_lines() -> list[tuple[str, int, str]]:
    """Every Rust line the working tree adds to the last commit, and every line of a Rust file not yet tracked."""
    lines = []
    diff = subprocess.run(["git", "diff", "HEAD", "-U0", "--", RUST], cwd=TOP, capture_output=True, text=True, check=True)
    path, number = None, 0
    for line in diff.stdout.splitlines():
        if line.startswith("+++ "):
            path = line[len("+++ b/"):] if line.startswith("+++ b/") else None
        elif line.startswith("@@"):
            number = int(re.search(r"\+(\d+)", line).group(1))
        elif line.startswith("+") and path and path.endswith(RUST_SUFFIX):
            lines.append((path, number, line[1:]))
            number += 1
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "--", RUST], cwd=TOP, capture_output=True, text=True, check=True
    )
    for path in untracked.stdout.split():
        if path.endswith(RUST_SUFFIX):
            for number, line in enumerate((TOP / path).read_text().splitlines(), 1):
                lines.append((path, number, line))
    return lines


def every_line() -> list[tuple[str, int, str]]:
    """Every line of every Rust file in the program."""
    lines = []
    for file in sorted((TOP / RUST).rglob(f"*{RUST_SUFFIX}")):
        path = str(file.relative_to(TOP))
        for number, line in enumerate(file.read_text().splitlines(), 1):
            lines.append((path, number, line))
    return lines


def main() -> int:
    """Report every breakage in the lines read, and fail where there is one."""
    lines = every_line() if EVERYTHING in sys.argv[1:] else added_lines()
    failures = []
    definitions: dict[str, set[int]] = {}
    for path, number, line in lines:
        if passed_over(path):
            continue
        if path not in definitions:
            definitions[path] = definition_lines((TOP / path).read_text())
        if number in definitions[path]:
            continue
        found = breakages(line)
        if found:
            failures.append(f"{path}:{number}: {', '.join(found)} typed in place: name it (.claude/rules/STYLE.md)")
    for failure in failures:
        print(failure)
    if EVERYTHING in sys.argv[1:]:
        print(f"{len(failures)} lines type a value in place")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
