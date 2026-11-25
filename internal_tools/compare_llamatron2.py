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
    .venv/bin/python internal_tools/compare_llamatron2.py import    # each song's MIDI export, and examples/midi, imported again
    .venv/bin/python internal_tools/compare_llamatron2.py load --only tie

It prints each set that differs with the first place it differs, and a count, and exits 1 when anything differs, so that the
commit check can run it.
"""

import argparse
import hashlib
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


def import_inputs(path):
    """Return what the import step imports for a path, each a song name and a MIDI file's bytes: a MIDI file itself, or each
    song of a set as the whole-song MIDI export writes it from one seed; None where the Python refuses the set."""
    if path.suffix == '.mid':
        return [(path.stem, path.read_bytes())]
    import os
    from llamatron.engine.realizer.song_realizer import SongRealizer
    from llamatron.exporters.exports import export_name
    from llamatron.exporters.midi_arrangement import MidiSong
    from llamatron.model.objects.setlist import Setlist
    os.makedirs(EXPORT_DIRECTORY, exist_ok=True)
    with open(path, encoding='utf-8') as file:
        data = load_safely(file)
    moved, _ = migrated(data, one_song_name=path.stem)
    try:
        setlist = Setlist.from_data(data=as_object_layout(moved))
        inputs = []
        for name in setlist.get_song_names():
            grid = SongRealizer(setlist.get_song(name), seed=RENDER_SEED).render()
            base = export_name(setlist=path.stem, song=name)
            inputs.append((base, midi_bytes(MidiSong(directory=EXPORT_DIRECTORY, grid=grid, name=base).midi_file())))
        return inputs
    except SongFileError:
        return None


def python_import(path):
    """Return what importing each input of a path into a new set makes, with the import dialog's first choices: the song's
    name and data and the patterns, scales and instruments it adds, as JSON, or None where the Python refuses the set."""
    import io
    import mido
    from llamatron.importers.midi_import import ImportChoices, MidiImport, MidiImportProblem
    from llamatron.model.objects.setlist import Setlist
    inputs = import_inputs(path)
    if inputs is None:
        return None
    made = []
    for name, data in inputs:
        try:
            imported = MidiImport(midi_file=mido.MidiFile(file=io.BytesIO(data), clip=True)).imported(setlist=Setlist.new(), choices=ImportChoices(song_name=name)).song
        except MidiImportProblem:
            made.append({'refused': name})
            continue
        made.append({'name': imported.name, 'song': imported.song, 'patterns': imported.patterns, 'scales': imported.scales, 'instruments': imported.instruments})
    return json.dumps(made)


def same_as_data(python, port):
    """Return whether two saved sets hold the same data: mappings in any order, lists in order (the user's rule)."""
    if port.startswith('FAILED'):
        return False
    return load_safely(python) == load_safely(port)


STEPS = {'load': python_load, 'layout': python_layout, 'migrate': python_migrate, 'save': python_save, 'render': python_render, 'midi': python_midi, 'live': python_live, 'import': python_import}
# Where the Python's answers are kept, git-ignored and never committed: since the Python program is frozen, an answer is
# worked out from the Python only when none is kept for its step and its file as the file is now.
KEPT = pathlib.Path('.cache/compare_llamatron2')
NOTHING_KEPT = 'none'


def kept_python(step, path):
    """Return the Python's answer for a step on a set or MIDI file, worked out by the Python only when none is kept yet."""
    digest = hashlib.sha256('{}\0'.format(step).encode('utf-8') + path.read_bytes()).hexdigest()
    kept = KEPT / step / (digest + '.json')
    if kept.exists():
        held = json.loads(kept.read_text(encoding='utf-8'))
        return None if held == NOTHING_KEPT else held
    answer = STEPS[step](path)
    kept.parent.mkdir(parents=True, exist_ok=True)
    kept.write_text(json.dumps(NOTHING_KEPT if answer is None else answer), encoding='utf-8')
    return answer


# How each step's two outputs are compared: as text unless named here.
COMPARED = {'save': same_as_data, 'import': same_as_data}


# The screen tour: the Python's capture, made once, since the Python program is frozen, and where the Rust's replay of its
# keys is written. The tour starts by exporting a PDF, which stays in the Python program, so the Rust starts after it.
SCREENS = pathlib.Path('/tmp/claude/llamatron/screens')
SCREEN_SIZES = ((80, 24), (160, 50))
NOT_PORTED_PAGE = '(not ported)'
# What the capture writes for the folder its tour ran in.
FOLDER = 'FOLDER'
PDF_PAGE = 'PdfExportPage'
LEAVE = 'escape'


def python_screens():
    """Return the Python's screen tour at each size, capturing it first when it has not been."""
    files = [SCREENS / 'screens_{}x{}.json'.format(*size) for size in SCREEN_SIZES]
    if not all(path.exists() for path in files) or not (SCREENS / 'tour.yml').exists() or 'sets_before' not in json.loads(files[0].read_text(encoding='utf-8'))[0]:
        subprocess.run([str(TOP / 'internal_tools' / 'compare_screens.sh'), 'capture', str(SCREENS)], check=True, cwd=TOP)
    return [(size, json.loads(path.read_text(encoding='utf-8'))) for size, path in zip(SCREEN_SIZES, files)]


def pieces(line):
    """Return a screen line's pieces as one comparable list: empty pieces left out, and neighbours of one style joined."""
    joined = []
    for text, style in line:
        if not text:
            continue
        if joined and joined[-1][1] == style:
            joined[-1][0] += text
        else:
            joined.append([text, style])
    return joined


def keys_with_stacks(stop):
    """Return a stop's keys, each with the pages and dialogs open as it was pressed and, where the key before changed the
    set, the file the set was then written to, whether it held unsaved changes and its current song, joined by a unit
    separator."""
    keys = []
    for key, stack, (written, dirty, song) in zip(stop['keys'], stop['stacks_before'], stop['sets_before']):
        parts = [key, ','.join(stack)]
        if written:
            parts += [written, str(dirty), song]
        keys.append('\x1f'.join(parts))
    return keys


def after_the_pdf(stops):
    """Return the tour's stops from its first past the PDF export page, that stop's keys from where ESC left the PDF page."""
    first = next(place for place, stop in enumerate(stops) if stop['page'] != PDF_PAGE)
    stops = [dict(stop) for stop in stops[first:]]
    keys = stops[0]['keys']
    stops[0]['keys'] = keys[keys.index(LEAVE) + 1:]
    stops[0]['stacks_before'] = stops[0]['stacks_before'][keys.index(LEAVE) + 1:]
    stops[0]['sets_before'] = stops[0]['sets_before'][keys.index(LEAVE) + 1:]
    return stops


def compare_screens(shown_most=None):
    """Replay the screen tour's keys in the Rust tracker at each size and compare every stop's screen; return the exit code."""
    differing = 0
    for size, stops in python_screens():
        stops = after_the_pdf(stops)
        keys_file = SCREENS / 'keys_{}x{}.txt'.format(*size)
        keys_file.write_text(''.join('\t'.join([','.join(stop['stack']), stop['set'] or '', str(stop['dirty']), stop['song'], *keys_with_stacks(stop)]) + '\n' for stop in stops), encoding='utf-8')
        # The set is opened as the Python's tour held its path, in its folder or by its name alone from inside it.
        held = stops[0]['path']
        opened = str(SCREENS / 'tour.yml') if held.startswith(FOLDER) else held
        done = subprocess.run([str(RUST), 'screens', opened, str(keys_file), str(size[0]), str(size[1])], capture_output=True, text=True, cwd=SCREENS)
        if done.returncode != 0:
            print('{}x{}: the Rust tour failed: {}'.format(*size, done.stderr.strip()[:SHOWN]))
            return 1
        port = json.loads(done.stdout)
        pages = {}
        shown = 0
        # The pages the Rust has ported, which it shows as themselves somewhere on the tour; a stop on any other waits.
        ported = {rust_stop['page'] for rust_stop in port}
        for number, (python, rust_stop) in enumerate(zip(stops, port)):
            counts = pages.setdefault(python['page'], [0, 0, 0])
            if rust_stop['page'] == NOT_PORTED_PAGE or python['page'] not in ported:
                counts[2] += 1
                continue
            same = rust_stop['page'] == python['page'] and [pieces(line) for line in python['screen']] == [pieces(line) for line in rust_stop['screen']]
            counts[0 if same else 1] += 1
            if not same and shown < (shown_most or MOST_SCREEN_DIFFERENCES):
                shown += 1
                print(screen_difference(size=size, number=number, python=python, port=rust_stop))
        ported_differ = sum(counts[1] for counts in pages.values())
        differing += ported_differ
        waiting = sum(counts[2] for counts in pages.values())
        print('{}x{}: {} of {} stops differ, {} wait on pages not ported yet'.format(*size, ported_differ, len(stops) - waiting, waiting))
        for page, (same, different, unported) in pages.items():
            if different:
                print('  {}: {} of {} differ'.format(page, different, same + different))
    return 1 if differing else 0


MOST_SCREEN_DIFFERENCES = 3


def screen_difference(*, size, number, python, port):
    """Return where a stop's screens first differ, the line's text and pieces on each side."""
    if port['page'] != python['page']:
        return '{}x{} stop {}: the Rust shows {}, the Python {}'.format(*size, number, port['page'], python['page'])
    for line, (first, second) in enumerate(zip(python['screen'], port['screen'])):
        if pieces(first) != pieces(second):
            return '{}x{} stop {} ({}, {}) line {}:\n  python: {}\n  rust:   {}'.format(*size, number, python['page'], python['place'], line, pieces(first), pieces(second))
    return '{}x{} stop {}: the screens have {} and {} lines'.format(*size, number, len(python['screen']), len(port['screen']))


def main():
    made = argparse.ArgumentParser(prog='compare_llamatron2.py', description='Hold llamatron2 to the Python program.')
    made.add_argument('step', choices=sorted([*STEPS, 'screens']))
    made.add_argument('--only', help='only the sets whose path holds this text')
    made.add_argument('--differences', type=int, help='for screens, how many differing stops to show, three unless given')
    options = made.parse_args()
    if options.step == 'screens':
        return compare_screens(shown_most=options.differences)
    found = [*EXAMPLES.rglob('*.yml'), *TEST_SETS.rglob('*.yml')]
    if options.step == 'import':
        found += EXAMPLES.rglob('*.mid')
    sets = sorted(path for path in found if options.only is None or options.only in str(path))
    differing = 0
    skipped = 0
    waiting = {}
    for path in sets:
        python = kept_python(options.step, path)
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
