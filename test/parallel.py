# llamatron: a Python language and framework for producing MIDI clips.
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

"""Runs every test, one test class to a process, with as many processes at once as the computer has cores.

The tests don't depend on each other, and the slow ones are the text UI tests, so this finishes
in about the time of the slowest class rather than of all of them together. Every result is
still reported: a class with a failure prints unittest's whole output for it, and the total
counts every test. It finds the tests just as `python -m unittest discover -s test` does, and
runs each class from the top folder with test/ on the path, as discovery would.

Run it from the top folder, usually through ./run_tests.sh:

    .venv/bin/python test/parallel.py
"""

import os
import re
import subprocess
import sys
import time
import unittest
from concurrent.futures import ThreadPoolExecutor

TEST_FOLDER = 'test'
# What unittest prints when it finishes, which says how many tests a class ran.
RAN_COUNT = re.compile(r'Ran (\d+) tests?')
MSG_CANT_LOAD = 'Some tests could not be loaded:\n{errors}'
MSG_NO_COUNT = '{name} did not say how many tests it ran:\n{output}'
MSG_SUMMARY = 'Ran {tests} tests in {classes} classes in {seconds:.1f}s, with {workers} at a time. The slowest was {slowest}, at {slowest_seconds:.1f}s.'
MSG_OK = 'OK'
MSG_FAILED = 'FAILED: {count} of {classes} classes had failures or errors: {names}'
NAME_SEPARATOR = ', '
SUCCESS = 0
FAILURE = 1


def test_classes(suite):
    """Return the name of every test class in a suite, like test_blend.TestBlend, each once, in order."""
    names = []
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            names += test_classes(item)
        else:
            names.append(class_name(item))
    return list(dict.fromkeys(names))


def class_name(test):
    """Return the name unittest runs a test's class by: its module and class."""
    return f'{type(test).__module__}.{type(test).__qualname__}'


def run_class(name, root):
    """Run one test class in its own process, and return (name, whether it passed, its output, how many tests it ran, seconds)."""
    started = time.monotonic()
    environment = dict(os.environ, PYTHONPATH=os.path.join(root, TEST_FOLDER))
    finished = subprocess.run(
        [sys.executable, '-m', 'unittest', name], cwd=root, env=environment, capture_output=True, text=True,
    )
    found = RAN_COUNT.search(finished.stderr)
    count = int(found.group(1)) if found else None
    return name, finished.returncode == SUCCESS, finished.stderr, count, time.monotonic() - started


def main():
    root = os.getcwd()
    sys.path.insert(0, os.path.join(root, TEST_FOLDER))
    loader = unittest.TestLoader()
    names = test_classes(loader.discover(TEST_FOLDER))
    if loader.errors:
        print(MSG_CANT_LOAD.format(errors='\n'.join(loader.errors)))
        return FAILURE
    workers = os.cpu_count() or 1
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda name: run_class(name, root), names))
    failed = []
    for name, passed, output, count, _ in results:
        if not passed:
            failed.append(name)
            print(output)
        elif count is None:
            failed.append(name)
            print(MSG_NO_COUNT.format(name=name, output=output))
    slowest = max(results, key=lambda result: result[-1])
    print(MSG_SUMMARY.format(
        tests=sum(result[3] or 0 for result in results), classes=len(names), seconds=time.monotonic() - started,
        workers=workers, slowest=slowest[0], slowest_seconds=slowest[-1],
    ))
    if failed:
        print(MSG_FAILED.format(count=len(failed), classes=len(names), names=NAME_SEPARATOR.join(failed)))
        return FAILURE
    print(MSG_OK)
    return SUCCESS


if __name__ == '__main__':
    sys.exit(main())
