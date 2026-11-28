#!/usr/bin/env python3
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Bump llamatron's version, written in src/tracker/src/version.rs, once before a push that changes the program.

Run from the top folder:

    .venv/bin/python internal_tools/bump_version.py           # 1.1.1 becomes 1.1.2, with today's date and the time now
    .venv/bin/python internal_tools/bump_version.py --before-push   # the same, where Rust under src/ changed since the last push and the version did not

`internal_tools/bump.sh` runs the first, and internal_tools/push_all.sh the second, committing the bump before it runs every
test: the version and the build date and time are raised once a push rather than with every commit. The version file
is written whole from its template, `internal_tools/templates/version.rs.template`, never edited by hand or by a text
replacement, since a replacement that matches nothing changes nothing and says nothing: two commits once went in
without their bump that way.
"""

import datetime
import pathlib
import re
import string
import subprocess
import sys

TOP = pathlib.Path(__file__).resolve().parent.parent
VERSION_FILE = 'src/tracker/src/version.rs'
TEMPLATE_FILE = TOP / 'internal_tools' / 'templates' / 'version.rs.template'
SOURCE_FOLDER = 'src/'
RUST_SUFFIX = '.rs'
BEFORE_PUSH_FLAG = '--before-push'
# The version the file sets, read back as its three numbers.
VERSION_PATTERN = re.compile(r'^pub const PROGRAM_VERSION: &str = "(\d+)\.(\d+)\.(\d+)";$', re.MULTILINE)
DATE_FORMAT = '%Y-%m-%d'
TIME_FORMAT = '%H:%M'
# How a diff marks the line that sets a new version.
BUMPED_LINE = '+pub const PROGRAM_VERSION: '
# What changed since the last push: the files, and the version module.
PUSHED = 'origin/main'
CHANGED_PATHS_COMMAND = ('git', 'diff', '--name-only', PUSHED, 'HEAD')
VERSION_DIFF_COMMAND = ('git', 'diff', '--unified=0', PUSHED, 'HEAD', '--', VERSION_FILE)
VERSION_SEPARATOR = '.'
BUMPED_REPORT = 'version {version}, built {date} {time}'
NO_VERSION = 'expected the version line in {path}'


def numbers_in(text):
    """Return the three numbers of the version a version module's text sets, stopping where it sets none."""
    found = VERSION_PATTERN.search(text)
    if not found:
        raise ValueError(NO_VERSION.format(path=VERSION_FILE))
    return [int(number) for number in found.groups()]


def version_in(text):
    """Return the version a version module's text sets, such as 1.0.116."""
    return VERSION_SEPARATOR.join(str(number) for number in numbers_in(text))


def bumped(*, text, now):
    """Return the version module written from its template: the version the text sets with its last number one higher,
    and the build date and time now."""
    first, second, last = numbers_in(text)
    version = VERSION_SEPARATOR.join(str(number) for number in (first, second, last + 1))
    template = string.Template(TEMPLATE_FILE.read_text())
    return template.substitute(version=version, date=now.strftime(DATE_FORMAT), time=now.strftime(TIME_FORMAT))


def changes_the_program(path):
    """Return whether a changed path is Rust under src/, the code a bump is for."""
    return path.startswith(SOURCE_FOLDER) and path.endswith(RUST_SUFFIX)


def is_missing_a_bump(*, changed_paths, version_diff):
    """Return whether what is to be pushed changes the program's Rust without setting a new version."""
    return any(changes_the_program(path) for path in changed_paths) and BUMPED_LINE not in version_diff


def output_of(command):
    """Return what a command prints."""
    return subprocess.run(command, capture_output=True, text=True, check=True).stdout


def bump_before_push():
    """Bump the version where what is to be pushed changes the program's Rust and does not raise the version already."""
    if is_missing_a_bump(changed_paths=output_of(CHANGED_PATHS_COMMAND).splitlines(), version_diff=output_of(VERSION_DIFF_COMMAND)):
        bump()


def bump():
    """Write the version module anew from its template, its version one higher and its build time now."""
    path = TOP / VERSION_FILE
    now = datetime.datetime.now()
    text = bumped(text=path.read_text(), now=now)
    path.write_text(text)
    print(BUMPED_REPORT.format(version=version_in(text), date=now.strftime(DATE_FORMAT), time=now.strftime(TIME_FORMAT)))


def main():
    """Bump the version, or before a push only where the push needs one."""
    if BEFORE_PUSH_FLAG in sys.argv[1:]:
        bump_before_push()
    else:
        bump()


if __name__ == '__main__':
    main()
