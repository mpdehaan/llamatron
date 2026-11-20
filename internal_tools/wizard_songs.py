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

"""Print a line for the usual song of every subgenre, in each of its kinds of song, and for the song every choice of the song
wizard makes, each choice once, on the first subgenre of each genre, each song as a short hash.

    internal_tools/wizard_songs.sh > before.txt        # every genre: about two thousand songs, on every core
    internal_tools/wizard_songs.sh rock > before.txt   # one genre

It is run before and after a change that should leave the wizard's songs alone, such as a refactoring of the arranger or
of the wizard's choices, and the two outputs are compared: a line that differs names the genre, the subgenre and the
choice whose song changed. The choices are the ones the suite goes through (every_choice in
tests/macro_composer/test_wizard_effect.py), each made on a subgenre's usual song with one seed, so that a new choice of
the wizard is covered once the suite covers it. A choice runs the same code whatever the subgenre, so each is made once, on
the first subgenre of its genre, and every subgenre's own style is covered by its usual song. A song is made under one
version, whatever the program's is, so that a version bump changes no line. The subgenres are made side by side on every core,
and the lines come out in one order. It writes nothing but what it prints.
"""

import argparse
import hashlib
import json
import multiprocessing
import sys

from llamatron.macro_composer import arranger
from llamatron.macro_composer.wizard_choices import genre_names, WizardChoices
from tests.macro_composer.test_wizard_effect import every_choice, fresh

A_NAME = 'song'
# The version every song is made under, so that the lines are the same from one version of the program to the next.
MADE_VERSION = '1.0.0'
HASH_LENGTH = 16
ENCODING = 'utf-8'
NEW_LINE = '\n'
SEPARATOR = ', '
MSG_LINE = '{genre} | {subgenre} | {kind} | {what} | {place} | {made}'
MSG_FAILED = 'FAILED {error}: {text}'
ERR_NO_SUCH_GENRE = 'no genre called ({}): expected one of {}'
TEXT_KEPT = 60
# The two kinds of task: a subgenre's usual songs, and every choice on one subgenre.
USUAL = 'usual'
CHOICES = 'choices'


def digest_of(choices):
    """A short hash of the song some choices make with what the song keeps of the choices, or what went wrong making it."""
    try:
        made = [choices.made_setlist(name=A_NAME, version=MADE_VERSION).to_data(), choices.to_data()]
    except Exception as error:
        return MSG_FAILED.format(error=type(error).__name__, text=str(error)[:TEXT_KEPT])
    return hashlib.sha256(json.dumps(made, sort_keys=True, default=str).encode(ENCODING)).hexdigest()[:HASH_LENGTH]


def made_after(*, genre, subgenre, first, change):
    """The hash of a subgenre's song after one choice, made after something done first, or what refused the choice."""
    choices = fresh(genre=genre, subgenre=subgenre)
    try:
        first(choices)
        change(choices)
    except (TypeError, ValueError) as error:
        return MSG_FAILED.format(error=type(error).__name__, text=str(error)[:TEXT_KEPT])
    return digest_of(choices)


def lines_of_subgenre(*, genre, subgenre, choices=None):
    """A line for every choice of a subgenre, or for the choices given: the genre, the subgenre, the choice and its song's hash."""
    offered = every_choice(fresh(genre=genre, subgenre=subgenre)) if choices is None else choices
    lines = []
    for kind, what, change, firsts in offered:
        for place, first in enumerate(firsts):
            made = made_after(genre=genre, subgenre=subgenre, first=first, change=change)
            lines.append(MSG_LINE.format(genre=genre, subgenre=subgenre, kind=kind, what=what, place=place, made=made))
    return lines


def usual_lines(*, genre, subgenre):
    """A line for a subgenre's usual song in each of its kinds of song, the subgenre's own first."""
    lines = []
    for variant in [None, *fresh(genre=genre, subgenre=subgenre).variants()]:
        choices = fresh(genre=genre, subgenre=subgenre)
        if variant is not None:
            choices.set_variant(variant)
        lines.append(MSG_LINE.format(genre=genre, subgenre=subgenre, kind=USUAL, what=variant, place=0, made=digest_of(choices)))
    return lines


def lines_of_task(task):
    """The lines of one task: (USUAL, genre, subgenre) for a subgenre's usual songs, or (CHOICES, genre, subgenre) for every choice."""
    kind, genre, subgenre = task
    if kind == USUAL:
        return usual_lines(genre=genre, subgenre=subgenre)
    return lines_of_subgenre(genre=genre, subgenre=subgenre)


def tasks_of(genres):
    """Every task, in the order the lines come out: each subgenre's usual songs, then every choice on each genre's first subgenre."""
    usual = [(USUAL, genre, subgenre) for genre in genres for subgenre in WizardChoices.from_data({arranger.GENRE: genre}).subgenres()]
    choices = [(CHOICES, genre, WizardChoices.from_data({arranger.GENRE: genre}).subgenres()[0]) for genre in genres]
    return usual + choices


def main(*, arguments):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('genre', nargs='?', help='a genre, where every genre is not wanted')
    options = parser.parse_args(arguments)
    if options.genre is not None and options.genre not in genre_names():
        print(ERR_NO_SUCH_GENRE.format(options.genre, SEPARATOR.join(genre_names())), file=sys.stderr)
        return 1
    genres = genre_names() if options.genre is None else [options.genre]
    with multiprocessing.Pool() as pool:
        for lines in pool.map(lines_of_task, tasks_of(genres), chunksize=1):
            print(NEW_LINE.join(lines))
    return 0


if __name__ == '__main__':
    sys.exit(main(arguments=sys.argv[1:]))
