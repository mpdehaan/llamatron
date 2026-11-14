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

"""Record a batch video of every example, shortest first, each with the visualizer mode internal_tools/visualizer_pairings.yml gives it, through FluidSynth.

    .venv/bin/python internal_tools/record_batch.py
    LLAMATRON_BATCH_RECORD_MAX=2 sh user_scripts/record_all.sh     # the two shortest only, to try it

The user's design. Each take is internal_tools/record_demo.py's batch video (tui/batch_stage.py): the
title on black, Arrange with READY, then the song with its mode filling the scene frame, recorded from
the rectangle the terminal window's cells cover alone, written as recordings/<set>_<mode>.mov. The
examples go shortest first, so that a problem shows in the first minute; an example that has any video in
recordings/ already, its plain take or a take of any mode (has_a_video), is left out, the user's rule, so that running it again records only what is
missing; and LLAMATRON_BATCH_RECORD_MAX stops after that many. An example the pairings don't list gets the mode
they use least, which tells a new demo what is seen less. It lists the takes and the time they need
and asks once before starting, unless --go, and stops at the first take that fails. The screen and
the sound are set up as docs/RECORDING.md says for --fluidsynth; turn on Do Not Disturb, since
anything that appears over the window is recorded.
"""

import argparse
import collections
import importlib.util
import os
import sys

from llamatron.composition.setlist import file_stem
from llamatron.support.safe_yaml import load_safely
from llamatron.tui.document import Document
from llamatron.visualizers.cycle import Cycle
from llamatron.visualizers.modes import MODES, mode_options
from llamatron.support.example_sets import example_sets

PAIRINGS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'visualizer_pairings.yml')
RECORDER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'record_demo.py')
RECORDER_MODULE = 'record_demo'
MOST_VARIABLE = 'LLAMATRON_BATCH_RECORD_MAX'
READ_TEXT = 'r'
SUCCESS = 0
FAILURE = 1
# The mode of modes is given only by name, never chosen for a set the pairings lack.
CHOSEN_FROM = [mode.OPTION for mode in MODES if mode is not Cycle]
LIST_SEPARATOR = ', '
NOTHING = ''
PLAN_LINE = '  {number:2}  {stem:30} {mode:14} {length}'
PLAN_TOTAL = '{count} takes, about {minutes:.0f} minutes of recording'
UNKNOWN_LENGTH = 'left out, its length cannot be worked out: {path}'
BAD_PAIRING = 'internal_tools/visualizer_pairings.yml gives {stem} the mode {mode}, which is not one of: {modes}'
BAD_MOST = '{variable} must be a whole number, got {value}'
TAKE_FAILED = 'stopped: the take of {stem} failed'
ALREADY_RECORDED = 'left out, recorded already: {stem} with {mode}'
NOTHING_TO_RECORD = 'every example has its video in recordings/ already'
ALL_DONE = 'recorded {count} videos into recordings/'
LENGTH = '{minutes}:{seconds:02d}'
SECONDS_IN_A_MINUTE = 60
# What a take adds to its song, in seconds, for the total: the title, READY, the box growing, the lead-out and the hold.
EACH_TAKE_ADDS = 15


def pairings(*, path=PAIRINGS):
    """Return the mode each set's batch video shows, by the set's file stem."""
    with open(path, READ_TEXT) as file:
        data = load_safely(file) or {}
    for stem, mode in data.items():
        if mode not in mode_options():
            raise ValueError(BAD_PAIRING.format(stem=stem, mode=mode, modes=LIST_SEPARATOR.join(mode_options())))
    return data


def least_used(paired):
    """Return the mode the pairings use least, the first in the visualizer's order among those used as little."""
    counts = collections.Counter(paired.values())
    return min(CHOSEN_FROM, key=lambda mode: (counts[mode], CHOSEN_FROM.index(mode)))


def mode_for(*, stem, paired):
    """Return the mode a set's video shows: its pairing, or the mode used least, which is then counted as used."""
    if stem not in paired:
        paired[stem] = least_used(paired)
    return paired[stem]


def song_seconds(path):
    """Return how long a set's song plays, in seconds, or None."""
    seconds = Document.load(path).lengths().song_seconds()
    return None if seconds is None else float(seconds)


def most_takes(environment):
    """Return how many takes LLAMATRON_BATCH_RECORD_MAX allows, or None for every one."""
    value = environment.get(MOST_VARIABLE)
    if value is None or value == NOTHING:
        return None
    if not value.isdigit():
        raise ValueError(BAD_MOST.format(variable=MOST_VARIABLE, value=value))
    return int(value)


def has_a_video(*, path, recorder):
    """Return whether the set at path has any video in the recordings folder: its plain take, recordings/<set>.mov, or a take of any mode, recordings/<set>_<mode>.mov, whatever mode the pairings now give it."""
    videos = [os.path.join(recorder.RECORDINGS, file_stem(path) + recorder.VIDEO_SUFFIX)]
    videos += [recorder.batch_video_path(path=path, mode=option) for option in mode_options()]
    return any(os.path.exists(video) for video in videos)


def never_recorded(*, path, mode):
    """Return that no take is recorded already, for a plan that asks nothing."""
    return False


def plan(*, paths, paired, most, lengths=song_seconds, recorded=never_recorded):
    """Return the takes to record, shortest first, each the set's path, its mode and its length in seconds, leaving out those recorded already, as many as most allows."""
    takes = []
    for path in paths:
        seconds = lengths(path)
        if seconds is None:
            print(UNKNOWN_LENGTH.format(path=path), file=sys.stderr)
            continue
        takes.append((seconds, path))
    takes.sort()
    planned = []
    for seconds, path in takes:
        mode = mode_for(stem=file_stem(path), paired=paired)
        if recorded(path=path, mode=mode):
            print(ALREADY_RECORDED.format(stem=file_stem(path), mode=mode))
            continue
        planned.append((path, mode, seconds))
    return planned if most is None else planned[:most]


def shown_length(seconds):
    whole = round(seconds)
    return LENGTH.format(minutes=whole // SECONDS_IN_A_MINUTE, seconds=whole % SECONDS_IN_A_MINUTE)


def recorder():
    """Return internal_tools/record_demo.py, which lies beside this tool, loaded as a module."""
    specification = importlib.util.spec_from_file_location(RECORDER_MODULE, RECORDER_SCRIPT)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def record_all(*, takes, record, driver, max_seconds, audio_device, fluidsynth_output, window_id):
    """Record each take in turn with record (record_demo.record), stopping at the first that fails. Return the exit code."""
    for path, mode, _ in takes:
        code = record(path=path, driver=driver, audio_device=audio_device, assignment=None, max_seconds=max_seconds, window_id=window_id, go=True,
                      visualizer=mode, fluidsynth=True, fluidsynth_output=fluidsynth_output, batch=True)
        if code != SUCCESS:
            print(TAKE_FAILED.format(stem=file_stem(path)), file=sys.stderr)
            return FAILURE
    print(ALL_DONE.format(count=len(takes)))
    return SUCCESS


def main(*, argv=None, environment=os.environ):
    shared = recorder()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--audio-device', default=shared.DEFAULT_AUDIO_DEVICE, help='the audio input device to record the sound from: the first whose name holds this text')
    parser.add_argument('--fluidsynth-output', default=None, help='the audio output FluidSynth plays to, such as a Multi-Output Device that reaches the recorded one too')
    parser.add_argument('--window-id', type=int, default=None, help='the id of the window to record, when the terminal program cannot be asked')
    parser.add_argument('--go', action='store_true', help='start at once, without waiting for Enter after the list of takes')
    arguments = parser.parse_args(argv)
    try:
        takes = plan(paths=example_sets(), paired=pairings(), most=most_takes(environment),
                     recorded=lambda path, mode: has_a_video(path=path, recorder=shared))
    except ValueError as error:
        print(error, file=sys.stderr)
        return FAILURE
    if not takes:
        print(NOTHING_TO_RECORD)
        return SUCCESS
    for number, (path, mode, seconds) in enumerate(takes, start=1):
        print(PLAN_LINE.format(number=number, stem=file_stem(path), mode=mode, length=shown_length(seconds)))
    total = sum(seconds + EACH_TAKE_ADDS for _, _, seconds in takes)
    print(PLAN_TOTAL.format(count=len(takes), minutes=total / SECONDS_IN_A_MINUTE))
    shared.wait_for_go(go=arguments.go)
    return record_all(takes=takes, record=shared.record, driver=shared.DEFAULT_DRIVER, max_seconds=shared.DEFAULT_MAX_SECONDS, audio_device=arguments.audio_device, fluidsynth_output=arguments.fluidsynth_output, window_id=arguments.window_id)


if __name__ == '__main__':
    sys.exit(main())
