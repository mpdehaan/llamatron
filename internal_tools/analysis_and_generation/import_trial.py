#!/usr/bin/env python3
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Import every MIDI file in a folder as the Import Wizard would, and report, file by file, how well the song was cut up.

    internal_tools/analysis_and_generation/import_trial.sh FOLDER                  # every .mid and .midi under FOLDER
    internal_tools/analysis_and_generation/import_trial.sh FOLDER --limit 40       # the first 40, in name order
    internal_tools/analysis_and_generation/import_trial.sh FOLDER --name classical # the report's name, by default the folder's

It judges every step of the Import Wizard (.claude/DESIGNS.md, "The Import Wizard") before and after, on the corpus's scores
and on the user's own folders of files, which are for private testing only: nothing it reads or writes enters the repository,
and no file, folder or work it meets is named in a document, a commit or a test. The reports go to
/tmp/claude/llamatron/import_trials/NAME/: one JSON file per MIDI file and summary.txt, a line per file and the totals.

For each file: the grid the import chose and how many notes it moved; the tracks; the scenes and their lengths in bars, and
each scene's scale; the patterns, how many a minute, the share used only once and the share shorter than four bars; whether
the song, played and exported again, plays the same notes as the file; what the import warned of; and a flag where the cut
looks wrong: more than a dozen scenes, or many of odd lengths.
"""

import argparse
import collections
import json
import mido
import os
import sys
import traceback

from llamatron.engine.realizer.song_realizer import SongRealizer
from llamatron.exporters.midi_arrangement import MidiSong
from llamatron.importers import midi_import as midi_import_values, voices
from llamatron.importers.comparison import compared
from llamatron.importers.midi_import import ImportChoices, MidiImport
from llamatron.importers.writing import add_imported
from llamatron.math.rational import Rational
from llamatron.model.objects.setlist import Setlist

TRIALS = os.path.join('/tmp', 'claude', 'llamatron', 'import_trials')
SUFFIXES = ('.mid', '.midi')
SONG_NAME = 'trial'
SUMMARY = 'summary.txt'
# A cut with more scenes than this, or with more than this share of its scenes an odd length, is flagged as likely wrong.
MOST_SCENES = 12
ODD_SHARE = 0.25
# Lengths in bars a section usually has; any other is odd.
USUAL_BARS = (1, 2, 4, 8, 12, 16, 24, 32)
SHORT_BARS = 4
SECONDS_IN_A_MINUTE = 60
FLAG = '!'
NO_FLAG = ' '
LINE = '{flag} {file:<44} {grid:>6} {moved:>6} {tracks:>6} {scenes:>6} {patterns:>8} {per_minute:>7} {once:>5} {short:>6} {plays:>6}'
HEADING = LINE.format(flag=' ', file='file', grid='grid', moved='moved', tracks='tracks', scenes='scenes', patterns='patterns',
                      per_minute='per min', once='once', short='<4 bar', plays='same')
FAILED_LINE = '{flag} {file:<44} {problem}'
TOTALS = 'files {files}, failed {failed}, flagged {flagged}, plays the same {same}; mean scenes {scenes:.1f}, patterns a minute {per_minute:.1f}, used once {once:.0%}, shorter than 4 bars {short:.0%}'
PERCENT = '{:.0%}'
ONE_PLACE = '{:.1f}'
YES = 'yes'
NO = 'no'
JSON_SUFFIX = '.json'
SHAPES_REPORT = 'unnamed_shapes.txt'
SHAPES_SHOWN = 40
SHAPE_LINE = '{count:>7} {files:>5}  {kind:<20} {shape}'
KIND_LINE = '{count:>7}  {kind}'
OCTAVE = 12
FIFTH = 7
OCTAVE_KIND = 'octave'
SPREAD_KIND = 'inversion or spread'
NO_FIFTH_KIND = 'no fifth'
OTHER_KIND = 'other'


def midi_files(folder):
    """Return every MIDI file under a folder, in name order."""
    found = []
    for root, _, names in os.walk(folder):
        found += [os.path.join(root, name) for name in names if name.lower().endswith(SUFFIXES)]
    return sorted(found)


def shapes_struck(midi_import):
    """Return the shapes of the notes struck together in a file that no chord symbol names, by kind: each group of notes that
    start and end together at one velocity, as the import's chords are found, named neither in root position nor in an
    inversion, written as half steps above its lowest note,
    and its kind: "inversion or spread" where its notes are a named chord's in another order or octave (doublings left out),
    "no fifth" where they are a named chord's but for its fifth, "octave" for a note and its octaves, else "other"."""
    found = collections.Counter()
    for part in midi_import.get_contents().parts:
        if part.is_drums():
            continue
        together = collections.defaultdict(list)
        for note in part.notes:
            together[(note.start, note.end, note.velocity)].append(note.pitch)
        for pitches in together.values():
            pitches = sorted(set(pitches))
            if len(pitches) < 2 or voices.chord_named(pitches) is not None:
                continue
            found[(shape_kind(pitches), tuple(pitch - pitches[0] for pitch in pitches[1:]))] += 1
    return found


def shape_kind(pitches):
    classes = {pitch % OCTAVE for pitch in pitches}
    if len(classes) == 1:
        return OCTAVE_KIND
    for shape in voices.SHAPES:
        for root in range(OCTAVE):
            named = {(root + step) % OCTAVE for step in (0, *shape)}
            if classes == named:
                return SPREAD_KIND
            if len(shape) >= 2 and classes == named - {(root + FIFTH) % OCTAVE}:
                return NO_FIFTH_KIND
    return OTHER_KIND


def tried(path):
    """Return what importing one file came to: the measures of the song it made, or the problem that stopped it."""
    midi_file = mido.MidiFile(path, clip=True)
    setlist = Setlist.new()
    midi_import = MidiImport(midi_file=midi_file)
    imported = midi_import.imported(setlist=setlist, choices=ImportChoices(song_name=SONG_NAME, longest_bars=midi_import_values.WIZARD_LONGEST_BARS))
    shapes = shapes_struck(midi_import)
    song = add_imported(setlist=setlist, imported=imported.song)
    again = MidiSong(directory=os.curdir, grid=SongRealizer(song).render(), name=SONG_NAME).midi_file()
    comparison = compared(first=midi_file, second=again)
    measures = measures_of(song=song, setlist=setlist, imported=imported, seconds=again.length, same=comparison.is_same())
    measures['unnamed_shapes'] = [[kind, list(shape), count] for (kind, shape), count in shapes.most_common()]
    return measures


def measures_of(*, song, setlist, imported, seconds, same):
    """Return how a song made by the import is cut up, as plain data for the report."""
    bar = Rational(song.get_time_signature().bar_length())
    scenes = []
    used = collections.Counter()
    for scene in song.get_scenes():
        scenes.append({'name': scene.get_name(), 'bars': scene_bars(scene=scene, setlist=setlist, bar=bar), 'scale': scene.get_scale_name()})
        for track in scene.get_track_names():
            slot = scene.get_clip_slot(track)
            if slot is not None:
                used.update(slot.get_pattern_names())
    patterns = setlist.get_pattern_names()
    lengths = {name: pattern_bars(setlist=setlist, name=name, bar=bar) for name in patterns}
    minutes = max(seconds / SECONDS_IN_A_MINUTE, 1 / SECONDS_IN_A_MINUTE)
    odd = [scene for scene in scenes if scene['bars'] not in USUAL_BARS]
    return {
        'grid': str(imported.step_size), 'moved': imported.moved, 'warnings': imported.warnings, 'tracks': imported.tracks, 'scenes': scenes,
        'patterns': len(patterns), 'per_minute': len(patterns) / minutes,
        'used_once': share(count=sum(1 for name in patterns if used[name] <= 1), of=len(patterns)),
        'shorter_than_4_bars': share(count=sum(1 for name in patterns if lengths[name] < SHORT_BARS), of=len(patterns)),
        'groups': sorted(setlist.get_pattern_groups()), 'seconds': seconds, 'same': same,
        'flagged': len(scenes) > MOST_SCENES or len(odd) > ODD_SHARE * len(scenes),
    }


def scene_bars(*, scene, setlist, bar):
    """Return how many bars a scene's longest clip lasts, played its number of times, to a tenth of a bar."""
    longest = 0
    for track in scene.get_track_names():
        slot = scene.get_clip_slot(track)
        if slot is None:
            continue
        names = slot.get_pattern_names()
        length = sum(pattern_bars(setlist=setlist, name=name, bar=bar) for name in names) * (slot.get_repeat() or 1)
        longest = max(longest, length)
    return round(longest * (scene.get_repeat() or 1), 1)


def pattern_bars(*, setlist, name, bar):
    """Return how many bars a pattern lasts."""
    pattern = setlist.get_pattern(name)
    return float(Rational(pattern.get_steps()) * Rational(setlist.get_pattern_step_size(pattern)) / bar)


def share(*, count, of):
    return count / of if of else 0


def summary_line(*, name, measures):
    return LINE.format(
        flag=FLAG if measures['flagged'] else NO_FLAG, file=name[-44:], grid=measures['grid'], moved=measures['moved'],
        tracks=measures['tracks'], scenes=len(measures['scenes']), patterns=measures['patterns'], per_minute=ONE_PLACE.format(measures['per_minute']),
        once=PERCENT.format(measures['used_once']), short=PERCENT.format(measures['shorter_than_4_bars']), plays=YES if measures['same'] else NO,
    )


def totals_line(*, results, failed):
    if not results:
        return TOTALS.format(files=failed, failed=failed, flagged=0, same=0, scenes=0, per_minute=0, once=0, short=0)
    count = len(results)
    return TOTALS.format(
        files=count + failed, failed=failed, flagged=sum(1 for measures in results if measures['flagged']), same=sum(1 for measures in results if measures['same']),
        scenes=sum(len(measures['scenes']) for measures in results) / count, per_minute=sum(measures['per_minute'] for measures in results) / count,
        once=sum(measures['used_once'] for measures in results) / count, short=sum(measures['shorter_than_4_bars'] for measures in results) / count,
    )


def write_shapes(*, out, results):
    """Write how often each unnamed shape was struck across the files, and in how many files, the commonest first, and each kind's total."""
    counts = collections.Counter()
    files = collections.Counter()
    kinds = collections.Counter()
    for measures in results:
        for kind, shape, count in measures['unnamed_shapes']:
            counts[(kind, tuple(shape))] += count
            files[(kind, tuple(shape))] += 1
            kinds[kind] += count
    lines = [KIND_LINE.format(count=count, kind=kind) for kind, count in kinds.most_common()]
    lines += [SHAPE_LINE.format(count=count, files=files[key], kind=key[0], shape=list(key[1])) for key, count in counts.most_common(SHAPES_SHOWN)]
    with open(os.path.join(out, SHAPES_REPORT), 'w') as file:
        file.write('\n'.join(lines) + '\n')


def main(arguments):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('folder')
    parser.add_argument('--limit', type=int, default=None)
    parser.add_argument('--name', default=None)
    options = parser.parse_args(arguments)
    name = options.name or os.path.basename(os.path.normpath(options.folder))
    out = os.path.join(TRIALS, name)
    os.makedirs(out, exist_ok=True)
    files = midi_files(options.folder)[:options.limit]
    lines = [HEADING]
    results = []
    failed = 0
    for path in files:
        shown = os.path.relpath(path, options.folder)
        try:
            measures = tried(path)
        # A file of anyone's making can fail in ways no list foresees, and one such file must not end the trial of the rest.
        except Exception as problem:
            failed += 1
            lines.append(FAILED_LINE.format(flag=FLAG, file=shown[-44:], problem=repr(problem)[:80]))
            with open(os.path.join(out, shown.replace(os.sep, '__') + JSON_SUFFIX), 'w') as file:
                json.dump({'problem': traceback.format_exc()}, file, indent=1)
            continue
        results.append(measures)
        lines.append(summary_line(name=shown, measures=measures))
        with open(os.path.join(out, shown.replace(os.sep, '__') + JSON_SUFFIX), 'w') as file:
            json.dump(measures, file, indent=1, default=str)
        print(lines[-1], flush=True)
    lines.append(totals_line(results=results, failed=failed))
    write_shapes(out=out, results=results)
    with open(os.path.join(out, SUMMARY), 'w') as file:
        file.write('\n'.join(lines) + '\n')
    print(lines[-1])


if __name__ == '__main__':
    main(sys.argv[1:])
