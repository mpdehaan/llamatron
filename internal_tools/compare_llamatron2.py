# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Hold llamatron2, the Rust port, to the Python program, layer by layer as the port lands: every example set is put through
the same step by both, and what each makes is compared. The Rust side is native/target/release/llamatron-compare.

    .venv/bin/python internal_tools/compare_llamatron2.py load      # every example's and test set's data, as both load it
    .venv/bin/python internal_tools/compare_llamatron2.py layout    # that data written back as a set file by each writer
    .venv/bin/python internal_tools/compare_llamatron2.py migrate   # moved to today's layout, into the objects' and back
    .venv/bin/python internal_tools/compare_llamatron2.py save      # read into objects and saved, compared as data
    .venv/bin/python internal_tools/compare_llamatron2.py render    # every song rendered from one seed, each clip's notes
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


def python_save(path):
    """Return a set read into objects and saved, as the Python program saves it, or None where the Python refuses the set,
    whose refusal the Rust is held to separately."""
    from llamatron.model.file.setlist_writer import dump_setlist
    from llamatron.model.objects.setlist import Setlist
    with open(path, encoding='utf-8') as file:
        data = load_safely(file)
    moved, _ = migrated(data, one_song_name=path.stem)
    try:
        return dump_setlist(Setlist.from_data(data=as_object_layout(moved)).to_data()).rstrip("\n")
    except SongFileError:
        return None


RENDER_SEED = 1


def rendered_text(grid):
    """Return a rendered grid as text both programs write alike: each scene's tempo, then each clip's length and its notes,
    each start, end, MIDI number and velocity, the times exact."""
    from llamatron.engine.timing.timing import timed_events
    lines = []
    for row_place, row in enumerate(grid.get_rows()):
        lines.append('scene {} tempo {}'.format(row_place, row.get_tempo()))
        for column in grid.get_columns():
            clip = grid.get_clip(row=row, column=column)
            if clip is None:
                continue
            notes, length = timed_events(clip=clip, scale=grid.scale_at(row=row, column=column))
            lines.append('  {} length {}'.format(column.get_name(), length))
            for note in notes:
                lines.append('    {} {} {} {}'.format(note.start, note.end, note.midi_number, note.velocity))
    return '\n'.join(lines)


def python_render(path):
    """Return every song of a set rendered from one seed, as text, or None where the Python refuses the set."""
    from llamatron.engine.realizer.song_realizer import SongRealizer
    from llamatron.model.objects.setlist import Setlist
    with open(path, encoding='utf-8') as file:
        data = load_safely(file)
    moved, _ = migrated(data, one_song_name=path.stem)
    try:
        setlist = Setlist.from_data(data=as_object_layout(moved))
        texts = []
        for name in setlist.get_song_names():
            texts.append('song {}'.format(name))
            texts.append(rendered_text(SongRealizer(setlist.get_song(name), seed=RENDER_SEED).render()))
        return '\n'.join(texts)
    except SongFileError:
        return None


def same_as_data(python, port):
    """Return whether two saved sets hold the same data: mappings in any order, lists in order (the user's rule)."""
    if port.startswith('FAILED'):
        return False
    return load_safely(python) == load_safely(port)


STEPS = {'load': python_load, 'layout': python_layout, 'migrate': python_migrate, 'save': python_save, 'render': python_render}
# How each step's two outputs are compared: as text unless named here.
COMPARED = {'save': same_as_data}


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
        same = COMPARED.get(options.step, str.__eq__)(python, port)
        if not same:
            differing += 1
            print('{}: {}'.format(path.relative_to(TOP), first_difference(python, port)))
    print('{} of {} sets differ{}'.format(differing, len(sets) - skipped, ', {} skipped as the step does not apply'.format(skipped) if skipped else ''))
    return 1 if differing else 0


if __name__ == '__main__':
    sys.exit(main())
