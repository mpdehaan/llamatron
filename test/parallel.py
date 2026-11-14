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

"""Runs every test, one test class to a process, with as many processes at once as the computer has cores.

The tests don't depend on each other, and the slow ones are the text UI tests, so this finishes
in about the time of the slowest class rather than of all of them together. The slowest classes
start first, by the seconds each took last time, kept in .test_times.json (which git ignores), and
a class with no time yet starts before them all, so that no slow class is left to start last. Every result is
still reported: a class with a failure prints unittest's whole output for it, and the total
counts every test. It finds the tests just as `python -m unittest discover -s test` does, and
runs each class from the top folder with test/ on the path, as discovery would.

Run it from the top folder, usually through internal_tools/test.sh, with any names to narrow it to the
tests whose module, class or method name contains one of them, as unittest's -k does:

    .venv/bin/python test/parallel.py
    .venv/bin/python test/parallel.py test_tui_pages test_examples
"""

import json
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
MSG_NOTHING_MATCHES = 'No test matches {names}.'
# unittest's own option for running only the tests whose name contains a word, which each class is run with.
FILTER_OPTION = '-k'
MSG_NO_COUNT = '{name} did not say how many tests it ran:\n{output}'
MSG_TIMED_OUT = '{name} did not finish within {seconds}s and was stopped: a test is probably looping, waiting for a key to do something it never does.\n{output}'
# How long one class may run before it's stopped and counted as failed: the slowest takes about 35 seconds, so a class that
# runs this long is a test looping, like one pressing a key until a row appears that never does, which the user asked to be caught on 2026-11-08.
CLASS_TIMEOUT_SECONDS = 120
MSG_SUMMARY = 'Ran {tests} tests in {classes} classes in {seconds:.1f}s, with {workers} at a time. The slowest was {slowest}, at {slowest_seconds:.1f}s.'
MSG_OK = 'OK'
MSG_FAILED = 'FAILED: {count} of {classes} classes had failures or errors: {names}'
NAME_SEPARATOR = ', '
# Where the seconds each class took are kept between runs, to start the slowest first.
TIMES_FILE = '.test_times.json'
# A class with no time yet counts as slower than any, so that it starts first.
NOT_TIMED = float('inf')
SUCCESS = 0
FAILURE = 1


def test_ids(suite):
    """Return the id of every test in a suite, like test_blend.TestBlend.test_rests, in order."""
    ids = []
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            ids += test_ids(item)
        else:
            ids.append(item.id())
    return ids


def test_classes(suite, *, filters):
    """Return the name of every test class in a suite with a test whose id contains one of the filters, like test_blend.TestBlend, each once, in order."""
    names = [test[:test.rindex('.')] for test in test_ids(suite) if not filters or any(word in test for word in filters)]
    return list(dict.fromkeys(names))


def class_name(test):
    """Return the name unittest runs a test's class by: its module and class."""
    return f'{type(test).__module__}.{type(test).__qualname__}'


def filter_options(filters):
    """Return unittest's options for running only the tests whose names contain one of the filters."""
    return [option for word in filters for option in (FILTER_OPTION, word)]


def run_class(*, name, root, filters):
    """Run one test class in its own process, only the tests the filters allow, and return (name, whether it passed, its output, how many tests it ran, seconds)."""
    started = time.monotonic()
    environment = dict(os.environ, PYTHONPATH=os.path.join(root, TEST_FOLDER))
    try:
        finished = subprocess.run(
            [sys.executable, '-m', 'unittest', name, *filter_options(filters)], cwd=root, env=environment, capture_output=True, text=True, timeout=CLASS_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as stopped:
        output = MSG_TIMED_OUT.format(name=name, seconds=CLASS_TIMEOUT_SECONDS, output=(stopped.stderr or b'').decode(errors='replace'))
        return name, False, output, None, time.monotonic() - started
    found = RAN_COUNT.search(finished.stderr)
    count = int(found.group(1)) if found else None
    return name, finished.returncode == SUCCESS, finished.stderr, count, time.monotonic() - started


def remembered_times(path):
    """Return the seconds each class took when it last ran, by its name, or nothing when there is no record or it can't be read."""
    try:
        with open(path, encoding='utf-8') as file:
            return json.load(file)
    except (OSError, ValueError):
        return {}


def slowest_first(*, names, times):
    """Return the classes in the order to start them: those never timed, then the slowest by their last time, each group in discovery order."""
    return sorted(names, key=lambda name: -times.get(name, NOT_TIMED))


def remember_times(*, path, times, results):
    """Keep the seconds each class just took beside those of the classes that didn't run, for the next run's order."""
    kept = dict(times)
    kept.update({result[0]: round(result[-1], 2) for result in results})
    try:
        with open(path, 'w', encoding='utf-8') as file:
            json.dump(kept, file, indent=0, sort_keys=True)
    except OSError:
        pass


def main(filters):
    root = os.getcwd()
    sys.path.insert(0, os.path.join(root, TEST_FOLDER))
    loader = unittest.TestLoader()
    names = test_classes(loader.discover(TEST_FOLDER), filters=filters)
    if loader.errors:
        print(MSG_CANT_LOAD.format(errors='\n'.join(loader.errors)))
        return FAILURE
    if not names:
        print(MSG_NOTHING_MATCHES.format(names=NAME_SEPARATOR.join(filters)))
        return FAILURE
    workers = os.cpu_count() or 1
    times_path = os.path.join(root, TIMES_FILE)
    times = remembered_times(times_path)
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda name: run_class(name=name, root=root, filters=filters), slowest_first(names=names, times=times)))
    if not filters:
        remember_times(path=times_path, times=times, results=results)
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
    sys.exit(main(sys.argv[1:]))
