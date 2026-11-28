# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fail any Rust or Python line a change adds that types a value with a meaning in place rather than naming it.

Two kinds of value are caught, in code and tests alike (.claude/rules/STYLE.md, "Every value with a meaning is
named"): a number other than 0 and 1, and a string literal that is a name used as a value, such as "osc2_pitch" or
"type". A line that defines a constant or a named `let` is where a value gets its name, and is passed over. The files
that define names, and the texts the program shows, are passed over too.

The program's Rust and the Python of its tools and tests are read alike (.claude/rules/STYLE.md: every tool and test is
held to the program's standard). The lines read are those the working tree adds to the last commit, and every line
of a file git does not track yet, so that nothing new breaks the rule while older lines are cleaned area by area. With --everything it reads every
line of the program instead.
"""

import pathlib
import re
import subprocess
import sys

TOP = pathlib.Path(__file__).resolve().parent.parent
RUST = "src"
RUST_SUFFIX = ".rs"
PYTHON_SUFFIX = ".py"
# The folders read: the program, and the tools and tests beside it.
READ_FOLDERS = ("src", "internal_tools", "python")
SUFFIXES = (RUST_SUFFIX, PYTHON_SUFFIX)
EVERYTHING = "--everything"
# The git commands the check reads the change by: its diff from the last commit with no lines of context, and the files
# git does not track yet, leaving out what it ignores.
GIT, DIFF, LAST_COMMIT, NO_CONTEXT, PATHS_FOLLOW = "git", "diff", "HEAD", "-U0", "--"
LIST_FILES, UNTRACKED, STANDARD_IGNORES = "ls-files", "--others", "--exclude-standard"

# Where a value is given its name, or where the program's shown text lives: the names crate, the strings crate's
# texts, and the tables the schema and the tracker generate from them.
DEFINING_PLACES = (
    "src/names/",
    "python/tests/data/",
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


# Python's: a string in either quotes, a comment, a line that binds a plain value to a name or names, and where a
# module's constant begins, whose every line to its closing bracket gives values their names.
PYTHON_STRING = re.compile(r"""\"((?:[^\"\\]|\\.)*)\"|'((?:[^'\\]|\\.)*)'""")
PYTHON_COMMENT = re.compile(r"#.*$")
PYTHON_NAMING_LINE = re.compile(r"""^\s*[A-Za-z_]\w*(?:\s*,\s*[A-Za-z_]\w*)*\s*(?::[^=]+)?=\s*(?:[-\d\"'(\[{]|b[\"'])""")
PYTHON_DEFINITION_START = re.compile(r"^[A-Z_][A-Z0-9_]*\s*(?::[^=]+)?=")

# Where a constant or a static begins, whose every line, to the semicolon that ends it, gives values their names.
DEFINITION_START = re.compile(r"^\s*(?:pub(?:\([a-z]+\))?\s+)?(?:const|static)\s")


def is_python(path: str) -> bool:
    """Whether a file is Python, read by Python's patterns, rather than Rust."""
    return path.endswith(PYTHON_SUFFIX)


def bare_code(line: str, python: bool) -> str:
    """A line with its texts emptied and its comment cut, so that what is left is its code."""
    if python:
        return PYTHON_COMMENT.sub("", PYTHON_STRING.sub('""', line))
    return STRING_LITERAL.sub('""', COMMENT.sub("", line))


def definition_lines(text: str, python: bool = False) -> set[int]:
    """The numbers of the lines inside a constant's definition, such as the rows of a table: a Rust constant or static to
    the semicolon that ends it, or a Python module's constant to its closing bracket."""
    start = PYTHON_DEFINITION_START if python else DEFINITION_START
    inside, depth, numbers = False, 0, set()
    for number, line in enumerate(text.splitlines(), 1):
        code = bare_code(line, python)
        if not inside and start.match(line):
            inside, depth = True, 0
        if inside:
            numbers.add(number)
            depth += code.count("[") + code.count("(") + code.count("{") - code.count("]") - code.count(")") - code.count("}")
            ended = depth <= 0 and (python or code.rstrip().endswith(";"))
            if ended:
                inside = False
    return numbers


def passed_over(path: str) -> bool:
    """Whether a file is one the check never reads: built output, or a place where values are given their names."""
    return BUILT in path or path.startswith(DEFINING_PLACES)


def breakages(line: str, python: bool = False) -> list[str]:
    """What a line types in place that should be named: each name typed as text, and each number other than 0 or 1."""
    naming = PYTHON_NAMING_LINE if python else NAMING_LINE
    if naming.match(line) or (not python and ATTRIBUTE.match(line)):
        return []
    if python:
        texts = [first or second for first, second in PYTHON_STRING.findall(line)]
    else:
        code = COMMENT.sub("", line)
        texts = STRING_LITERAL.findall(code)
    found = [f'"{text}"' for text in texts if NAME.match(text)]
    found += [number for number in NUMBER.findall(bare_code(line, python)) if number not in PLAIN_NUMBERS]
    return found


def added_lines() -> list[tuple[str, int, str]]:
    """Every line the working tree adds to the last commit, and every line of a file not yet tracked, in the folders read."""
    lines = []
    diff = subprocess.run([GIT, DIFF, LAST_COMMIT, NO_CONTEXT, PATHS_FOLLOW, *READ_FOLDERS], cwd=TOP, capture_output=True, text=True, check=True)
    path, number = None, 0
    for line in diff.stdout.splitlines():
        if line.startswith("+++ "):
            path = line[len("+++ b/"):] if line.startswith("+++ b/") else None
        elif line.startswith("@@"):
            number = int(re.search(r"\+(\d+)", line).group(1))
        elif line.startswith("+") and path and path.endswith(SUFFIXES):
            lines.append((path, number, line[1:]))
            number += 1
    untracked = subprocess.run(
        [GIT, LIST_FILES, UNTRACKED, STANDARD_IGNORES, PATHS_FOLLOW, *READ_FOLDERS], cwd=TOP, capture_output=True, text=True, check=True
    )
    for path in untracked.stdout.split():
        if path.endswith(SUFFIXES):
            for number, line in enumerate((TOP / path).read_text().splitlines(), 1):
                lines.append((path, number, line))
    return lines


def every_line() -> list[tuple[str, int, str]]:
    """Every line of every file in the folders read."""
    lines = []
    files = [file for folder in READ_FOLDERS for suffix in SUFFIXES for file in (TOP / folder).rglob(f"*{suffix}")]
    for file in sorted(files):
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
        python = is_python(path)
        if path not in definitions:
            definitions[path] = definition_lines((TOP / path).read_text(), python)
        if number in definitions[path]:
            continue
        found = breakages(line, python)
        if found:
            failures.append(f"{path}:{number}: {', '.join(found)} typed in place: name it (.claude/rules/STYLE.md)")
    for failure in failures:
        print(failure)
    if EVERYTHING in sys.argv[1:]:
        print(f"{len(failures)} lines type a value in place")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
