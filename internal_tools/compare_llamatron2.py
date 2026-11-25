# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Hold llamatron2, the Rust port, to the Python program, layer by layer as the port lands: every example set is put through
the same step by both, and what each makes is compared. The Rust side is native/target/release/llamatron-compare.

    .venv/bin/python internal_tools/compare_llamatron2.py load      # every example's and test set's data, as both load it
    .venv/bin/python internal_tools/compare_llamatron2.py layout    # that data written back as a set file by each writer
    .venv/bin/python internal_tools/compare_llamatron2.py migrate   # moved to today's layout, into the objects' and back
    .venv/bin/python internal_tools/compare_llamatron2.py load --only tie

It prints each set that differs with the first place it differs, and a count, and exits 1 when anything differs, so that the
commit check can run it.
"""

import argparse
import json
import pathlib
import subprocess
import sys

from llamatron.model.file.safe_yaml import load_safely
from llamatron.model.file.file_layout import as_file_layout, as_object_layout
from llamatron.model.file.migrations import migrated
from llamatron.model.file.setlist_writer import dump_file_layout
from llamatron.model.file.song_file_error import SongFileError

TOP = pathlib.Path(__file__).resolve().parent.parent
RUST = TOP / 'native' / 'target' / 'release' / 'llamatron-compare'
EXAMPLES = TOP / 'examples'
# The tests' own sets too, which hold old layouts, values out of range and every odd thing a file can hold.
TEST_SETS = TOP / 'tests' / 'data'
SHOWN = 120


def python_load(path):
    """Return a set's data as the Python program loads it, as JSON."""
    with open(path, encoding='utf-8') as file:
        return json.dumps(load_safely(file))


def rust(command, path):
    """Return what llamatron-compare prints for a set, or what went wrong."""
    finished = subprocess.run([str(RUST), command, str(path)], capture_output=True, text=True, check=False)
    if finished.returncode != 0:
        return 'FAILED: ' + finished.stderr.strip()
    return finished.stdout.rstrip('\n')


def first_difference(first, second):
    """Return where two texts first differ, with a little of each from there."""
    for place, (one, other) in enumerate(zip(first, second)):
        if one != other:
            return 'at {}: python {!r} rust {!r}'.format(place, first[max(0, place - 20):place + SHOWN], second[max(0, place - 20):place + SHOWN])
    return 'lengths {} and {}'.format(len(first), len(second))


def python_layout(path):
    """Return a set's loaded data written back as a set file by the Python writer, or None for a set laid out in an older
    way, which only the objects' migrations can write."""
    with open(path, encoding='utf-8') as file:
        data = load_safely(file)
    try:
        return dump_file_layout(data).rstrip('\n')
    except (AttributeError, TypeError, KeyError):
        return None


def python_migrate(path):
    """Return a set's data moved to today's layout, into the objects' layout and back, written as a set file, or None where the
    Python refuses its layout, a refusal the Rust must also make."""
    with open(path, encoding='utf-8') as file:
        data = load_safely(file)
    moved, _ = migrated(data, one_song_name=path.stem)
    try:
        return dump_file_layout(as_file_layout(as_object_layout(moved))).rstrip('\n')
    except (SongFileError, AttributeError, TypeError, KeyError):
        return None


STEPS = {'load': python_load, 'layout': python_layout, 'migrate': python_migrate}


def main():
    made = argparse.ArgumentParser(prog='compare_llamatron2.py', description='Hold llamatron2 to the Python program.')
    made.add_argument('step', choices=sorted(STEPS))
    made.add_argument('--only', help='only the sets whose path holds this text')
    options = made.parse_args()
    found = [*EXAMPLES.rglob('*.yml'), *TEST_SETS.rglob('*.yml')]
    sets = sorted(path for path in found if options.only is None or options.only in str(path))
    differing = 0
    skipped = 0
    for path in sets:
        python = STEPS[options.step](path)
        if python is None:
            skipped += 1
            continue
        port = rust(options.step, path)
        if python != port:
            differing += 1
            print('{}: {}'.format(path.relative_to(TOP), first_difference(python, port)))
    print('{} of {} sets differ{}'.format(differing, len(sets) - skipped, ', {} skipped as the step does not apply'.format(skipped) if skipped else ''))
    return 1 if differing else 0


if __name__ == '__main__':
    sys.exit(main())
