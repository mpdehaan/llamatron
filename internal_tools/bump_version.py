#!/usr/bin/env python3
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Bump llamatron's version for a commit that changes the program's Python, or check that a commit carries its bump.

Run from the top folder:

    .venv/bin/python internal_tools/bump_version.py           # 1.0.115 becomes 1.0.116, with today's date and the time now
    .venv/bin/python internal_tools/bump_version.py --check   # fail if Python under src/ is staged for a commit without a bump

`internal_tools/bump.sh` runs the first, and internal_tools/check_before_commit.sh runs the second before the tests. The bump
goes through this script, never a hand edit or a text replacement, because a replacement that
matches nothing changes nothing and says nothing: on 2026-11-09 two commits went in without their
bump that way. Each line this script rewrites has to be found exactly once, or it stops.
"""

import datetime
import re
import subprocess
import sys

VERSION_FILE = 'src/llamatron/support/version.py'
SOURCE_FOLDER = 'src/'
PYTHON_SUFFIX = '.py'
CHECK_FLAG = '--check'
VERSION_PATTERN = re.compile(r"^VERSION = '(\d+)\.(\d+)\.(\d+)'$", re.MULTILINE)
BUILD_DATE_PATTERN = re.compile(r"^BUILD_DATE = '[^']*'$", re.MULTILINE)
BUILD_TIME_PATTERN = re.compile(r"^BUILD_TIME = '[^']*'$", re.MULTILINE)
VERSION_LINE = "VERSION = '{first}.{second}.{last}'"
BUILD_DATE_LINE = "BUILD_DATE = '{date}'"
BUILD_TIME_LINE = "BUILD_TIME = '{time}'"
DATE_FORMAT = '%Y-%m-%d'
TIME_FORMAT = '%H:%M'
# How a staged diff marks the line that sets a new version.
BUMPED_LINE = '+VERSION = '
STAGED_PATHS_COMMAND = ('git', 'diff', '--cached', '--name-only')
STAGED_VERSION_DIFF_COMMAND = ('git', 'diff', '--cached', '--unified=0', '--', VERSION_FILE)
READ_TEXT = 'r'
WRITE_TEXT = 'w'
FAILED = 1
VERSION_SEPARATOR = '.'
NOT_FOUND = 0
BUMPED_REPORT = 'version {version}, built {date} {time}'
LINE_NOT_FOUND_ONCE = 'expected one line matching {pattern} in {path}, found {count}'
NO_BUMP = "Python under src/ is staged without a version bump: run 'internal_tools/bump.sh' and add {path}"


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
    """Return whether a staged path is Python under src/, the code a bump is for."""
    return path.startswith(SOURCE_FOLDER) and path.endswith(PYTHON_SUFFIX)


def is_missing_a_bump(*, staged_paths, version_diff):
    """Return whether a commit would change the program's Python without setting a new version."""
    return any(changes_the_program(path) for path in staged_paths) and BUMPED_LINE not in version_diff


def output_of(command):
    return subprocess.run(command, capture_output=True, text=True, check=True).stdout


def check():
    """Stop a commit that changes the program without its bump, by exiting with a failure and the reason."""
    staged_paths = output_of(STAGED_PATHS_COMMAND).splitlines()
    if is_missing_a_bump(staged_paths=staged_paths, version_diff=output_of(STAGED_VERSION_DIFF_COMMAND)):
        print(NO_BUMP.format(path=VERSION_FILE))
        sys.exit(FAILED)


def bump():
    with open(VERSION_FILE, READ_TEXT) as file:
        text = file.read()
    now = datetime.datetime.now()
    text = bumped(text=text, now=now)
    with open(VERSION_FILE, WRITE_TEXT) as file:
        file.write(text)
    print(BUMPED_REPORT.format(version=version_in(text), date=now.strftime(DATE_FORMAT), time=now.strftime(TIME_FORMAT)))


def main():
    if CHECK_FLAG in sys.argv[1:]:
        check()
    else:
        bump()


if __name__ == '__main__':
    main()
