# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Say how big the step in loudness is into the first chorus of what the song wizard makes.

    .venv/bin/python internal_tools/loudness_steps.py                 # every subgenre of every genre that has a chorus
    .venv/bin/python internal_tools/loudness_steps.py rock            # every subgenre of one genre
    .venv/bin/python internal_tools/loudness_steps.py rock --seed 4   # another song of each

For each subgenre the wizard makes one song and plays it. What the band adds up to in a section is the loudness of every
note sounded, for each bar. A line names the section before the first chorus and says how many times that section the chorus
adds up to: as the song is written, and as made, after each player has traded loudness for a much denser part
(src/llamatron/wizards/create_song/loudness_steps.py). It is run before and after a change to a style template's Energy or to the
trade's numbers. It makes its songs in memory and writes nothing.
"""

import argparse
import sys

from llamatron.model.file import version
from llamatron.wizards.create_song import loudness_steps, song_plan
from llamatron.wizards.create_song.wizard_choices import genre_names, WizardChoices

A_NAME = 'song'
USUAL_SEED = 11
SEPARATOR = ', '
MSG_LINE = '{genre:<14}{subgenre:<20}after {before:<12} written x{written:.2f}   made x{made:.2f}'
ERR_NO_SUCH_GENRE = 'no genre called ({}): expected one of {}'


def first_chorus(song):
    """The place of a song's first chorus that has a section before it, or None."""
    for place, scene in enumerate(song.get_scenes()):
        if place and scene.get_section() == song_plan.CHORUS:
            return place
    return None


def step_of(*, setlist, place):
    """How many times the section before a place the place adds up to, in a set's one song as played."""
    scenes = loudness_steps.measured(song=setlist.get_song(A_NAME))
    return loudness_steps.step(before=scenes[place - 1], now=scenes[place])


def chorus_step(*, genre, subgenre, seed):
    """The step into a subgenre's first chorus: the name of the section before, the step as written and the step as made, or
    None where the song has no chorus."""
    choices = WizardChoices()
    choices.set_genre(genre)
    choices.set_subgenre(subgenre)
    choices.set_seed(seed)
    written = choices.written_setlist(name=A_NAME, version=version.VERSION)
    place = first_chorus(written.get_song(A_NAME))
    if place is None:
        return None
    before = written.get_song(A_NAME).get_scenes()[place - 1].get_name()
    return before, step_of(setlist=written, place=place), step_of(setlist=choices.made_setlist(name=A_NAME, version=version.VERSION), place=place)


def subgenres_of(genre):
    choices = WizardChoices()
    choices.set_genre(genre)
    return choices.subgenres()


def report(*, genre, seed):
    """The lines of the report: one for each subgenre that has a chorus, of one genre or of every genre."""
    if genre is not None and genre not in genre_names():
        raise ValueError(ERR_NO_SUCH_GENRE.format(genre, SEPARATOR.join(genre_names())))
    lines = []
    for a_genre in genre_names() if genre is None else [genre]:
        for subgenre in subgenres_of(a_genre):
            found = chorus_step(genre=a_genre, subgenre=subgenre, seed=seed)
            if found is not None and None not in found:
                before, written, made = found
                lines.append(MSG_LINE.format(genre=a_genre, subgenre=subgenre, before=before, written=written, made=made))
    return lines


def main(*, arguments=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('genre', nargs='?')
    parser.add_argument('--seed', type=int, default=USUAL_SEED)
    given = parser.parse_args(arguments)
    try:
        lines = report(genre=given.genre, seed=given.seed)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    print('\n'.join(lines))
    return 0


if __name__ == '__main__':
    sys.exit(main())
