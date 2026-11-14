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

"""Play one of the demos' WAV files, picked from a numbered list, with afplay.

Run it from the top folder (sh user_scripts/play_demo.sh), after sh user_scripts/demos_to_wavs.sh has made the WAV files:

    .venv/bin/python internal_tools/play_demo.py             # lists previews/*.wav, numbered, and asks which
    .venv/bin/python internal_tools/play_demo.py classic_strum       # plays previews/classic_strum.wav straight away
    .venv/bin/python internal_tools/play_demo.py 12                  # plays the twelfth of the list straight away
    .venv/bin/python internal_tools/play_demo.py --list              # only prints the numbered list

Before it plays, it says the demo's number in the list and what the demo is: the set it was made from, its title,
genre and description.

It builds nothing, so it starts at once: sh user_scripts/demos_to_wavs.sh makes the previews and
their WAV files, and this only plays them. afplay is macOS's own command line audio player, which
plays the file through the speakers and exits, without opening Music or adding the file to a
library. Ctrl+C stops it. While it plays, one line shows how far into the demo it is, as the time
played, the demo's length and a bar filling across.
"""

import argparse
import glob
import os
import subprocess
import sys
import time
import wave

from llamatron.composition.setlist import Setlist
from llamatron.support.example_sets import example_sets

PREVIEWS = 'previews'
WAVE_SUFFIX = '.wav'
WAVE_FILES = '*' + WAVE_SUFFIX
PLAYER = 'afplay'
DEMO_LINE = '  {number:2}  {name}'
ASK_WHICH = 'Which demo? Type its number:'
NOT_A_CHOICE = 'that is not one of the numbers'
NO_WAVES = 'no WAV files in {folder}/: run sh user_scripts/demos_to_wavs.sh first'
NO_SUCH_DEMO = 'no {path}: run sh user_scripts/demos_to_wavs.sh first, or sh user_scripts/play_demo.sh to pick from the list'
PLAYING = 'playing {path} (Ctrl+C stops it)'
NUMBER_PLAYING = 'demo {number} of {count}: {name}'
DETAIL_SET = '  set:         {path}'
DETAIL_TITLE = '  title:       {title}'
DETAIL_GENRE = '  genre:       {genre}'
DETAIL_DESCRIPTION = '  description: {description}'
NO_SUCH_NUMBER = 'there is no demo {number}: the list has {count}'
SET_SUFFIX = '.yml'
GENRE_JOIN = ', '
NAME_JOIN = '_'
DIGITS = '0123456789'
STOPPED = 'stopped'
# The line that shows how far into the demo it is, drawn over itself as it plays.
PROGRESS_LINE = '\r▶ {played} / {length}  {bar}'
CLOCK = '{minutes}:{seconds:02d}'
SECONDS_A_MINUTE = 60
BAR_WIDTH = 50
BAR_PLAYED = '█'
BAR_TO_PLAY = '░'
LINE_END = '\n'
# How often the line is drawn again, in seconds.
REDRAW_SECONDS = 0.25


def wave_files(*, folder):
    """Return the WAV files in folder, sorted by name."""
    return sorted(glob.glob(os.path.join(folder, WAVE_FILES)))


def demo_name(path):
    """Return what a WAV file is called in the list: its name without the folder or the suffix."""
    return os.path.basename(path).removesuffix(WAVE_SUFFIX)


def ask_for_wave(*, folder):
    """Print the WAV files in folder, numbered, and return the one typed, or None."""
    if not print_list(folder=folder):
        return None
    paths = wave_files(folder=folder)
    print(ASK_WHICH)
    typed = input().strip()
    if not typed.isdigit() or not 1 <= int(typed) <= len(paths):
        print(NOT_A_CHOICE, file=sys.stderr)
        return None
    return paths[int(typed) - 1]


def numbered_wave(*, folder, number):
    """Return the WAV file at a number of the list, counted from 1, or None when the list is shorter."""
    paths = wave_files(folder=folder)
    if not 1 <= number <= len(paths):
        print(NO_SUCH_NUMBER.format(number=number, count=len(paths)), file=sys.stderr)
        return None
    return paths[number - 1]


def print_list(*, folder):
    """Print the WAV files in folder, numbered, and return whether there were any."""
    paths = wave_files(folder=folder)
    if not paths:
        print(NO_WAVES.format(folder=folder), file=sys.stderr)
    for number, path in enumerate(paths, start=1):
        print(DEMO_LINE.format(number=number, name=demo_name(path)))
    return bool(paths)


def set_of_demo(*, name, sets):
    """Return the example set a demo's preview was made from, or None: the set of the demo's own name, or, for a set of
    several songs, the set whose name the demo's name starts with, the longest such; a learning demo's number
    at the front of its file's name is passed over."""
    stems = {os.path.basename(path).removesuffix(SET_SUFFIX): path for path in sets}
    if name in stems:
        return stems[name]
    unnumbered = {stem.lstrip(DIGITS).lstrip(NAME_JOIN): path for stem, path in stems.items()}
    if name in unnumbered:
        return unnumbered[name]
    starting = [stem for stem in stems if name.startswith(stem + NAME_JOIN)]
    return stems[max(starting, key=len)] if starting else None


def detail_lines(*, path, folder, sets=None):
    """Return what to say of a demo before it plays: its number in the list and its name, and, when the set it was made from
    is found, the set, its title, genre and description."""
    paths = wave_files(folder=folder)
    name = demo_name(path)
    number = paths.index(path) + 1 if path in paths else 0
    lines = [NUMBER_PLAYING.format(number=number, count=len(paths), name=name)]
    made_from = set_of_demo(name=name, sets=example_sets() if sets is None else sets)
    if made_from is None:
        return lines
    setlist = Setlist.read_file(made_from)
    return lines + [DETAIL_SET.format(path=made_from), DETAIL_TITLE.format(title=setlist.get_title() or name), DETAIL_GENRE.format(genre=GENRE_JOIN.join(setlist.get_genres())),
              DETAIL_DESCRIPTION.format(description=setlist.get_description() or '')]


def named_wave(*, folder, name):
    """Return the WAV file of the demo named, given as a name or a path, or None when there is none."""
    path = name if name.endswith(WAVE_SUFFIX) else os.path.join(folder, name + WAVE_SUFFIX)
    if not os.path.isfile(path):
        print(NO_SUCH_DEMO.format(path=path), file=sys.stderr)
        return None
    return path


def wave_seconds(path):
    """Return how long the WAV file plays, in seconds, or None when the wave module can't read it."""
    try:
        with wave.open(path, 'rb') as file:
            return file.getnframes() / file.getframerate()
    except (wave.Error, EOFError, OSError):
        return None


def clock(seconds):
    """Return seconds as minutes and seconds, like 1:05."""
    whole = int(seconds)
    return CLOCK.format(minutes=whole // SECONDS_A_MINUTE, seconds=whole % SECONDS_A_MINUTE)


def progress_line(*, played, length):
    """Return the line that shows how far into the demo it is: the time played, the length and a bar."""
    played = min(played, length)
    filled = round(BAR_WIDTH * played / length) if length else BAR_WIDTH
    return PROGRESS_LINE.format(played=clock(played), length=clock(length), bar=BAR_PLAYED * filled + BAR_TO_PLAY * (BAR_WIDTH - filled))


def play(path, *, now=time.monotonic, sleep=time.sleep, out=sys.stdout):
    """Play the WAV file with afplay until it ends or Ctrl+C stops it, showing how far along it is, and return afplay's exit code."""
    print(PLAYING.format(path=path), file=out)
    length = wave_seconds(path)
    player = subprocess.Popen([PLAYER, path])
    started = now()
    try:
        while player.poll() is None:
            if length is not None:
                out.write(progress_line(played=now() - started, length=length))
                out.flush()
            sleep(REDRAW_SECONDS)
    except KeyboardInterrupt:
        player.terminate()
        player.wait()
        out.write(LINE_END)
        print(STOPPED, file=out)
        return 0
    if length is not None:
        out.write(progress_line(played=length, length=length) + LINE_END)
    return player.returncode


def main(*, argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('demo', nargs='?', help='the demo to play, by its name, such as strum, or by its number in the list; with none, a list to pick from')
    parser.add_argument('--folder', default=PREVIEWS, help='where the WAV files are')
    parser.add_argument('--list', action='store_true', dest='listing', help='print the numbered list and play nothing')
    arguments = parser.parse_args(argv)
    if arguments.listing:
        return 0 if print_list(folder=arguments.folder) else 1
    if arguments.demo and arguments.demo.isdigit():
        path = numbered_wave(folder=arguments.folder, number=int(arguments.demo))
    elif arguments.demo:
        path = named_wave(folder=arguments.folder, name=arguments.demo)
    else:
        path = ask_for_wave(folder=arguments.folder)
    if path is None:
        return 1
    for line in detail_lines(path=path, folder=arguments.folder):
        print(line)
    return play(path)


if __name__ == '__main__':
    sys.exit(main())
