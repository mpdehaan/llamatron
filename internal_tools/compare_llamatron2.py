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
    .venv/bin/python internal_tools/compare_llamatron2.py midi      # every MIDI file each song exports, byte for byte
    .venv/bin/python internal_tools/compare_llamatron2.py live      # each song's Live set, its XML byte for byte
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
    if finished.returncode == NOT_PORTED:
        return NotPorted(finished.stderr.strip())
    if finished.returncode != 0:
        return 'FAILED: ' + finished.stderr.strip()
    return finished.stdout.rstrip('\n')


# What llamatron-compare exits with for a set using a part of the program not ported yet.
NOT_PORTED = 3


class NotPorted(str):
    """What llamatron-compare says of a set that uses a part of the program not ported yet, which is counted apart."""


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
    each start, end, MIDI number and velocity, the times exact, then its CC values."""
    from llamatron.engine.timing.timing import timed_events
    lines = []
    for row_place, row in enumerate(grid.get_rows()):
        lines.append('scene {} tempo {}'.format(row_place, row.get_tempo()))
        for time, tempo in row.get_tempo_changes():
            lines.append('  tempo {} {}'.format(time, tempo))
        for column in grid.get_columns():
            clip = grid.get_clip(row=row, column=column)
            if clip is None:
                continue
            notes, length = timed_events(clip=clip, scale=grid.scale_at(row=row, column=column))
            lines.append('  {} length {}'.format(column.get_name(), length))
            for note in notes:
                lines.append('    {} {} {} {}'.format(note.start, note.end, note.midi_number, note.velocity))
            for control in clip.get_controls():
                lines.append('    cc {} {} {} {}'.format(control.get_time(), control.get_number(), control.get_value(), control.get_slide()))
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
        return '\n'.join(texts).rstrip('\n')
    except SongFileError:
        return None


# Where the midi step's exporters are pointed, which write nothing there: the files are made in memory.
EXPORT_DIRECTORY = '/tmp/claude/llamatron/compare'


def midi_bytes(midi_file):
    """Return a mido file's bytes as it saves them."""
    import io
    written = io.BytesIO()
    midi_file.save(file=written)
    return written.getvalue()


def python_midi(path):
    """Return every MIDI file each song of a set exports from one seed, each clip's, the whole song's, the stems and the
    General MIDI file, one line a file with its name and its SHA-512, or None where the Python refuses the set."""
    import hashlib
    import os
    from llamatron.engine.realizer.song_realizer import SongRealizer
    from llamatron.exporters.clip_tree import ClipTree
    from llamatron.exporters.exports import export_name
    from llamatron.exporters.midi_arrangement import MidiGeneralMidi, MidiSong, MidiStems
    from llamatron.model.objects.setlist import Setlist
    os.makedirs(EXPORT_DIRECTORY, exist_ok=True)
    with open(path, encoding='utf-8') as file:
        data = load_safely(file)
    moved, _ = migrated(data, one_song_name=path.stem)
    lines = []
    try:
        setlist = Setlist.from_data(data=as_object_layout(moved))
        for name in setlist.get_song_names():
            grid = SongRealizer(setlist.get_song(name), seed=RENDER_SEED).render()
            base = export_name(setlist=path.stem, song=name)
            files = []
            tree = ClipTree(directory=EXPORT_DIRECTORY, grid=grid, name=base)
            files += tree._built_files(tree._filled_slots())
            song = MidiSong(directory=EXPORT_DIRECTORY, grid=grid, name=base)
            files.append((os.path.basename(song.path()), song.midi_file()))
            stems = MidiStems(directory=EXPORT_DIRECTORY, grid=grid, name=base)
            files += list(zip(stems.filenames(), [stems.midi_file(track) for track in stems.sounding_tracks()]))
            general = MidiGeneralMidi(directory=EXPORT_DIRECTORY, grid=grid, name=base)
            files.append((os.path.basename(general.path()), general.midi_file()))
            for filename, midi_file in files:
                lines.append('{} {}'.format(filename, hashlib.sha512(midi_bytes(midi_file)).hexdigest()))
    except SongFileError:
        return None
    return '\n'.join(lines)


def python_live(path):
    """Return each song of a set as a Live set from one seed, the SHA-512 of its XML before it is zipped, or that the song is
    refused, one line a song, or None where the Python refuses the set."""
    import hashlib
    from llamatron.engine.realizer.song_realizer import SongRealizer
    from llamatron.exporters.ableton_project import AbletonProject
    from llamatron.exporters.exports import export_name
    from llamatron.model.objects.setlist import Setlist
    import os
    os.makedirs(EXPORT_DIRECTORY, exist_ok=True)
    with open(path, encoding='utf-8') as file:
        data = load_safely(file)
    moved, _ = migrated(data, one_song_name=path.stem)
    lines = []
    try:
        setlist = Setlist.from_data(data=as_object_layout(moved))
        for name in setlist.get_song_names():
            grid = SongRealizer(setlist.get_song(name), seed=RENDER_SEED).render()
            project = AbletonProject(directory=EXPORT_DIRECTORY, grid=grid, name=export_name(setlist=path.stem, song=name))
            try:
                lines.append('{} {}'.format(name, hashlib.sha512(project._build()).hexdigest()))
            except ValueError:
                lines.append('{} refused'.format(name))
    except SongFileError:
        return None
    return '\n'.join(lines)


def same_as_data(python, port):
    """Return whether two saved sets hold the same data: mappings in any order, lists in order (the user's rule)."""
    if port.startswith('FAILED'):
        return False
    return load_safely(python) == load_safely(port)


STEPS = {'load': python_load, 'layout': python_layout, 'migrate': python_migrate, 'save': python_save, 'render': python_render, 'midi': python_midi, 'live': python_live}
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
    waiting = {}
    for path in sets:
        python = STEPS[options.step](path)
        if python is None:
            skipped += 1
            continue
        port = rust(options.step, path)
        if isinstance(port, NotPorted):
            waiting[port] = waiting.get(port, 0) + 1
            continue
        same = COMPARED.get(options.step, str.__eq__)(python, port)
        if not same:
            differing += 1
            print('{}: {}'.format(path.relative_to(TOP), first_difference(python, port)))
    ported = len(sets) - skipped - sum(waiting.values())
    print('{} of {} sets differ{}'.format(differing, ported, ', {} skipped as the step does not apply'.format(skipped) if skipped else ''))
    if waiting:
        print('{} sets wait on parts not ported yet:'.format(sum(waiting.values())))
        for what, count in sorted(waiting.items(), key=lambda item: -item[1]):
            print('  {} {}'.format(count, what))
    return 1 if differing else 0


if __name__ == '__main__':
    sys.exit(main())
