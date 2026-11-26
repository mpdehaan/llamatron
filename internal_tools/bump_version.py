#!/usr/bin/env python3
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Bump llamatron's version, written in native/tracker/src/version.rs, once before a push that changes the program.

Run from the top folder:

    .venv/bin/python internal_tools/bump_version.py           # 1.1.1 becomes 1.1.2, with today's date and the time now
    .venv/bin/python internal_tools/bump_version.py --before-push   # the same, where Rust under native/ changed since the last push and the version did not

`internal_tools/bump.sh` runs the first, and internal_tools/push_all.sh the second, committing the bump before it runs every
test: the version and the build date and time are raised once a push rather than with every commit. The bump
goes through this script, never a hand edit or a text replacement, because a replacement that
matches nothing changes nothing and says nothing: two commits once went in without their
bump that way. Each line this script rewrites has to be found exactly once, or it stops.
"""

import datetime
import re
import subprocess
import sys

VERSION_FILE = 'native/tracker/src/version.rs'
SOURCE_FOLDER = 'native/'
PYTHON_SUFFIX = '.rs'
BEFORE_PUSH_FLAG = '--before-push'
VERSION_PATTERN = re.compile(r'^pub const PROGRAM_VERSION: &str = "(\d+)\.(\d+)\.(\d+)";$', re.MULTILINE)
BUILD_DATE_PATTERN = re.compile(r'^pub const BUILD_DATE: &str = "[^"]*";$', re.MULTILINE)
BUILD_TIME_PATTERN = re.compile(r'^pub const BUILD_TIME: &str = "[^"]*";$', re.MULTILINE)
VERSION_LINE = 'pub const PROGRAM_VERSION: &str = "{first}.{second}.{last}";'
BUILD_DATE_LINE = 'pub const BUILD_DATE: &str = "{date}";'
BUILD_TIME_LINE = 'pub const BUILD_TIME: &str = "{time}";'
DATE_FORMAT = '%Y-%m-%d'
TIME_FORMAT = '%H:%M'
# How a diff marks the line that sets a new version.
BUMPED_LINE = '+pub const PROGRAM_VERSION: '
# What changed since the last push: the files, and the version module.
PUSHED = 'origin/main'
CHANGED_PATHS_COMMAND = ('git', 'diff', '--name-only', PUSHED, 'HEAD')
VERSION_DIFF_COMMAND = ('git', 'diff', '--unified=0', PUSHED, 'HEAD', '--', VERSION_FILE)
READ_TEXT = 'r'
WRITE_TEXT = 'w'
FAILED = 1
VERSION_SEPARATOR = '.'
NOT_FOUND = 0
BUMPED_REPORT = 'version {version}, built {date} {time}'
LINE_NOT_FOUND_ONCE = 'expected one line matching {pattern} in {path}, found {count}'


def replaced_once(*, pattern, line, text):
    """Return text with the one line the pattern matches replaced, stopping unless there is exactly one, so that a bump can never quietly change nothing."""
    found = len(pattern.findall(text))
    if found != 1:
        raise ValueError(LINE_NOT_FOUND_ONCE.format(pattern=pattern.pattern, path=VERSION_FILE, count=found))
    return pattern.sub(lambda match: line, text)


def next_version_line(text):
    """Return the line that sets the version after the one the text sets, with the last number one higher; a text with no version line gets one that replaced_once then refuses."""
    found = VERSION_PATTERN.search(text)
    first, second, last = found.groups() if found else (NOT_FOUND, NOT_FOUND, NOT_FOUND)
    return VERSION_LINE.format(first=first, second=second, last=int(last) + 1)


def bumped(*, text, now):
    """Return the version module's text with the last number one higher and the build date and time set to now."""
    text = replaced_once(pattern=VERSION_PATTERN, line=next_version_line(text), text=text)
    text = replaced_once(pattern=BUILD_DATE_PATTERN, line=BUILD_DATE_LINE.format(date=now.strftime(DATE_FORMAT)), text=text)
    return replaced_once(pattern=BUILD_TIME_PATTERN, line=BUILD_TIME_LINE.format(time=now.strftime(TIME_FORMAT)), text=text)


def version_in(text):
    """Return the version a version module's text sets, like 1.0.116."""
    return VERSION_SEPARATOR.join(VERSION_PATTERN.search(text).groups())


def changes_the_program(path):
    """Return whether a changed path is Rust under native/, the code a bump is for."""
    return path.startswith(SOURCE_FOLDER) and path.endswith(PYTHON_SUFFIX)


def is_missing_a_bump(*, changed_paths, version_diff):
    """Return whether what is to be pushed changes the program's Rust without setting a new version."""
    return any(changes_the_program(path) for path in changed_paths) and BUMPED_LINE not in version_diff


def output_of(command):
    return subprocess.run(command, capture_output=True, text=True, check=True).stdout


def bump_before_push():
    """Bump the version where what is to be pushed changes the program's Rust and does not raise the version already."""
    if is_missing_a_bump(changed_paths=output_of(CHANGED_PATHS_COMMAND).splitlines(), version_diff=output_of(VERSION_DIFF_COMMAND)):
        bump()


def bump():
    with open(VERSION_FILE, READ_TEXT) as file:
        text = file.read()
    now = datetime.datetime.now()
    text = bumped(text=text, now=now)
    with open(VERSION_FILE, WRITE_TEXT) as file:
        file.write(text)
    print(BUMPED_REPORT.format(version=version_in(text), date=now.strftime(DATE_FORMAT), time=now.strftime(TIME_FORMAT)))


def main():
    if BEFORE_PUSH_FLAG in sys.argv[1:]:
        bump_before_push()
    else:
        bump()


if __name__ == '__main__':
    main()
