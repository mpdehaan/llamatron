# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The batch importer: every MIDI file under a folder imported as the Import Wizard cuts it, into set files in another folder.

    sh user_scripts/batch_importer.sh --input-dir FOLDER --output-dir FOLDER [--bars-per-pattern 8] [--quantize 1/64]
        [--multiple-songs-per-set]

Each file becomes a set of its own, named after the file's path under the input folder with its folders joined by double
underscores, so that the output folder is flat however deep the input is, holding one song named after the file; or, with
--multiple-songs-per-set, every file a song of one set named after the input folder. A file that cannot be imported is said
and passed over, and the rest go on. Last come how long the imports took: the shortest, the longest and the average.
"""

import argparse
from dataclasses import dataclass, replace
import mido
import os
import sys
import time

from llamatron.importers import cutting, midi_import as midi_import_values
from llamatron.importers.midi_import import ImportChoices, MidiImport, MidiImportProblem
from llamatron.importers.writing import add_imported
from llamatron.model.file.song_file_error import SongFileError
from llamatron.model.objects.naming import unique_name
from llamatron.model.objects.setlist import Setlist
from llamatron.model.schema import limits
from llamatron.model.schema.file_format import Section
from llamatron.user_strings import importing

PROGRAM = 'batch_importer.sh'
OPTION_INPUT = '--input-dir'
OPTION_OUTPUT = '--output-dir'
OPTION_BARS = '--bars-per-pattern'
OPTION_QUANTIZE = '--quantize'
OPTION_FORMAT = '--format'
OPTION_ONE_SET = '--multiple-songs-per-set'
STORE_TRUE = 'store_true'
# The one way of writing an import so far: the song as the file plays it.
DIRECT = 'direct'
FORMATS = (DIRECT,)
MIDI_SUFFIXES = ('.mid', '.midi')
SET_SUFFIX = '.yml'
# Folders under the input folder are joined into one file name with this, so the output folder stays flat.
FOLDER_JOIN = '__'
# The grids the import may quantize to, the coarsest first, down to the finest the Import Wizard allows.
QUANTIZE_CHOICES = tuple(size for size in cutting.AUTO_STEP_SIZES if size >= cutting.FINEST_STEP_SIZE)
MILLISECONDS = 1000


@dataclass(slots=True, kw_only=True)
class TimedImport:
    """One file imported: its name under the input folder and how many seconds its import took."""

    name: str
    seconds: float


def main(*, arguments=None):
    """Import every MIDI file under the input folder into sets in the output folder, and say how long the imports took."""
    options = parser().parse_args(arguments)
    if not os.path.isdir(options.input_dir):
        sys.exit(importing.MSG_BATCH_NO_INPUT.format(path=options.input_dir))
    os.makedirs(options.output_dir, exist_ok=True)
    choices = choices_of(options)
    files = midi_files(options.input_dir)
    timed = []
    one_set = Setlist.new() if options.multiple_songs_per_set else None
    starter = one_set.first_song_name() if one_set is not None else None
    for path in files:
        name = os.path.relpath(path, options.input_dir)
        started = time.perf_counter()
        try:
            written = imported(path=path, choices=choices, setlist=one_set, output_dir=options.output_dir, name=name)
        except (MidiImportProblem, SongFileError, OSError, ValueError, EOFError) as problem:
            print(importing.MSG_BATCH_FAILED.format(file=name, problem=problem), flush=True)
            continue
        timed.append(TimedImport(name=name, seconds=time.perf_counter() - started))
        print(importing.MSG_BATCH_WROTE.format(file=name, path=written, milliseconds=round(timed[-1].seconds * MILLISECONDS)), flush=True)
    if one_set is not None and timed:
        path = os.path.join(options.output_dir, os.path.basename(os.path.normpath(options.input_dir)) + SET_SUFFIX)
        finished(setlist=one_set, starter=starter, path=path)
        print(importing.MSG_BATCH_WROTE_SET.format(path=path, songs=len(timed)))
    print(timing_report(timed=timed, failed=len(files) - len(timed)))


def parser():
    """Return the batch importer's options, which --help lists."""
    made = argparse.ArgumentParser(prog=PROGRAM, description=importing.MSG_BATCH_DESCRIPTION)
    made.add_argument(OPTION_INPUT, required=True, help=importing.MSG_BATCH_HELP_INPUT)
    made.add_argument(OPTION_OUTPUT, required=True, help=importing.MSG_BATCH_HELP_OUTPUT)
    made.add_argument(OPTION_BARS, type=bars_per_pattern, default=midi_import_values.WIZARD_LONGEST_BARS, help=importing.MSG_BATCH_HELP_BARS)
    made.add_argument(OPTION_QUANTIZE, type=quantize_grid, default=cutting.FINEST_STEP_SIZE, help=importing.MSG_BATCH_HELP_QUANTIZE.format(
        choices=importing.MSG_BATCH_CHOICES_JOIN.join(str(size) for size in QUANTIZE_CHOICES)))
    made.add_argument(OPTION_FORMAT, choices=FORMATS, default=DIRECT, help=importing.MSG_BATCH_HELP_FORMAT)
    made.add_argument(OPTION_ONE_SET, action=STORE_TRUE, help=importing.MSG_BATCH_HELP_ONE_SET)
    return made


def bars_per_pattern(text):
    """Return the longest pattern in bars as --bars-per-pattern gives it, a whole number from 1."""
    if not text.isdigit() or int(text) < 1:
        raise argparse.ArgumentTypeError(importing.MSG_BATCH_BAD_BARS.format(value=text))
    return int(text)


def quantize_grid(text):
    """Return the finest grid --quantize allows, one of QUANTIZE_CHOICES written like 1/64."""
    for size in QUANTIZE_CHOICES:
        if str(size) == text:
            return size
    raise argparse.ArgumentTypeError(importing.MSG_BATCH_BAD_QUANTIZE.format(value=text))


def choices_of(options):
    """Return the import's choices from the batch importer's options, as the Import Wizard cuts a song."""
    return ImportChoices(song_name='', longest_bars=options.bars_per_pattern, finest_step=options.quantize, numbered=True)


def midi_files(folder):
    """Return every MIDI file under a folder, at any depth, in name order."""
    found = []
    for root, _, names in os.walk(folder):
        found += [os.path.join(root, name) for name in names if name.lower().endswith(MIDI_SUFFIXES)]
    return sorted(found)


def song_name_of(path):
    """Return the name a file's song takes: the file's name without its suffix, cut to the longest a name may be."""
    return os.path.splitext(os.path.basename(path))[0][:limits.MAX_NAME_LENGTH]


def imported(*, path, choices, setlist, output_dir, name):
    """Import one file, into the one set where one is given, else into a set of its own written to the output folder, and
    return where it went."""
    midi_file = mido.MidiFile(path, clip=True)
    own = setlist is None
    if own:
        setlist = Setlist.new()
    starter = setlist.first_song_name()
    song_name = unique_name(base=song_name_of(path), taken=setlist.get_song_names())
    made = MidiImport(midi_file=midi_file).imported(setlist=setlist, choices=replace(choices, song_name=song_name))
    add_imported(setlist=setlist, imported=made.song)
    if not own:
        return song_name
    written = os.path.join(output_dir, os.path.splitext(name.replace(os.sep, FOLDER_JOIN))[0] + SET_SUFFIX)
    finished(setlist=setlist, starter=starter, path=written)
    return written


def finished(*, setlist, starter, path):
    """Write a set of imported songs, without the empty song a new set starts with and what only it used."""
    setlist.remove_item(section=Section.SONGS, name=starter)
    setlist.remove_unused()
    setlist.write_file(path)


def timing_report(*, timed, failed):
    """Return the line saying how many files were imported, how many failed, and the shortest, longest and average import."""
    if not timed:
        return importing.MSG_BATCH_NOTHING.format(failed=failed)
    shortest = min(timed, key=lambda each: each.seconds)
    longest = max(timed, key=lambda each: each.seconds)
    average = sum(each.seconds for each in timed) / len(timed)
    return importing.MSG_BATCH_TIMES.format(
        count=len(timed), failed=failed, shortest=round(shortest.seconds * MILLISECONDS), shortest_file=shortest.name,
        longest=round(longest.seconds * MILLISECONDS), longest_file=longest.name, average=round(average * MILLISECONDS),
    )


if __name__ == '__main__':
    main()
