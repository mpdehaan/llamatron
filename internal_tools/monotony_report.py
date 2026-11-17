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
"""How much of what the song wizard makes repeats: for each player and each kind of section, the share of bars that play the
same notes at the same places as an earlier bar of the same section, over a few songs of a subgenre.

    .venv/bin/python internal_tools/monotony_report.py                      # every subgenre of every genre, one line each
    .venv/bin/python internal_tools/monotony_report.py rock                 # every subgenre of rock, one line each
    .venv/bin/python internal_tools/monotony_report.py rock "hard rock"     # one subgenre: a table of players by kinds of section
    .venv/bin/python internal_tools/monotony_report.py rock --songs 5       # over five songs a subgenre in place of three
    .venv/bin/python internal_tools/monotony_report.py rock --loudness      # a bar played louder or softer counts as another bar

A bar with nothing in it is left out. It is run before and after a change to what the wizard writes, to see whether the change
made the players repeat themselves less. It makes its songs in memory and writes nothing.
"""

import argparse
import re
import sys

from llamatron.macro_composer.wizard_choices import WizardChoices, genre_names
from llamatron.music.chord import Chord
from llamatron.music.held import Held
from llamatron.music.note import Note, Rest
from llamatron.playback.song_renderer import SongRenderer
from llamatron.support.rational import Rational
from llamatron.support.version import VERSION

A_NAME = 'song'
USUAL_SONGS = 3
FIRST_SEED = 1
WHOLE = 100
NO_TIME = Rational(0)
# What a scene is called beyond its kind: a number, or a stage's letter, after a space.
SCENE_COUNT = re.compile(r' (\d+|[a-z])$')
EVERY_SECTION = 'all'
MSG_NO_BARS = '-'
MSG_SHARE = '{:.0f}%'
MSG_SUBGENRE_LINE = '{genre:<14}{subgenre:<20}{share:>5}   most: {most}'
MSG_MOST = '{player} {share}'
MSG_TITLE = '{genre}, {subgenre}: the share of bars the same as an earlier bar of the section, over {songs} songs'
MSG_PLAYER_COLUMN = '{:<16}'
MSG_SECTION_COLUMN = '{:>12}'
MOST_SHOWN = 3
SEPARATOR = ', '
ERR_NO_SUCH_GENRE = 'no genre called ({}): expected one of {}'
ERR_NO_SUCH_SUBGENRE = 'no subgenre of {} called ({}): expected one of {}'


def kind_of_scene(name):
    """The kind of section a scene is, from the scene's name: a verse for (verse 2), an intro for (intro b)."""
    return SCENE_COUNT.sub('', name)


def pitches(*, position, loudness):
    """What a position sounds, as something to compare: its notes' numbers, with how loud each is where loudness counts."""
    if isinstance(position, Note):
        return ((position.get_midi_number(), position.get_velocity() if loudness else None),)
    if isinstance(position, Chord):
        return tuple(sorted(pitch for note in position.get_notes() for pitch in pitches(position=note, loudness=loudness)))
    if isinstance(position, Held):
        return pitches(position=position.get_sound(), loudness=loudness)
    return ()


def bars_of(*, positions, bar_length, loudness):
    """What each bar of a run of positions holds: for every bar, the sounds that start in the bar, each with where in the bar
    the sound starts and how long the sound lasts."""
    bars = {}
    now = NO_TIME
    for position in positions:
        length = position.get_length()
        sounded = pitches(position=position, loudness=loudness)
        if sounded and not isinstance(position, Rest):
            bar = int(now // bar_length)
            bars.setdefault(bar, []).append((str(now - bar * bar_length), str(length), sounded))
        now = now + length
    count = int(-(-now // bar_length)) if now else 0
    return [tuple(bars.get(bar, ())) for bar in range(count)]


def looped(*, bars, count):
    """A clip's bars as often as the scene plays them: a clip shorter than its scene goes round."""
    if not bars:
        return []
    return [bars[place % len(bars)] for place in range(count)]


def repeats(bars):
    """How many of the bars that hold anything are the same as an earlier bar, and how many hold anything."""
    seen = set()
    same = 0
    played = 0
    for bar in bars:
        if not bar:
            continue
        played += 1
        if bar in seen:
            same += 1
        seen.add(bar)
    return same, played


def counted_song(*, choices, seed, loudness):
    """Each player's repeats in each kind of section of one song: {(player, kind): [same, played]}."""
    setlist = choices.made_setlist(name=A_NAME, version=VERSION)
    grid = SongRenderer(setlist.get_song(A_NAME), seed=seed).render()
    bar_length = grid.get_time_signature().bar_length()
    counts = {}
    for row in grid.get_rows():
        scene_bars = int(grid.row_length(row) // bar_length)
        for column in grid.get_columns():
            clip = grid.get_clip(row=row, column=column)
            if clip is None:
                continue
            own = bars_of(positions=clip.played_notes(), bar_length=bar_length, loudness=loudness)
            bars = looped(bars=own, count=scene_bars) if clip.get_loop() else own
            same, played = repeats(bars)
            for kind in (kind_of_scene(row.get_name()), EVERY_SECTION):
                count = counts.setdefault((column.get_name(), kind), [0, 0])
                count[0] += same
                count[1] += played
    return counts


def counted(*, genre, subgenre, songs, loudness):
    """The repeats of a subgenre over a few songs, each of another seed."""
    total = {}
    for seed in range(FIRST_SEED, FIRST_SEED + songs):
        choices = WizardChoices()
        choices.set_genre(genre)
        choices.set_subgenre(subgenre)
        choices.set_seed(seed)
        for key, (same, played) in counted_song(choices=choices, seed=seed, loudness=loudness).items():
            count = total.setdefault(key, [0, 0])
            count[0] += same
            count[1] += played
    return total


def share(count):
    """A count as a share of a hundred, or nothing where no bar was played."""
    same, played = count
    return None if not played else WHOLE * same / played


def shown(count):
    part = share(count)
    return MSG_NO_BARS if part is None else MSG_SHARE.format(part)


def in_order(names):
    """Names in the order first met, each once."""
    return list(dict.fromkeys(names))


def table(*, genre, subgenre, songs, counts):
    """A subgenre's table: a row a player, a column a kind of section, and the whole song last."""
    players = in_order(player for player, _ in counts)
    kinds = [kind for kind in in_order(kind for _, kind in counts) if kind != EVERY_SECTION] + [EVERY_SECTION]
    lines = [MSG_TITLE.format(genre=genre, subgenre=subgenre, songs=songs), '']
    lines.append(MSG_PLAYER_COLUMN.format('') + ''.join(MSG_SECTION_COLUMN.format(kind) for kind in kinds))
    for player in players:
        cells = [MSG_SECTION_COLUMN.format(shown(counts[(player, kind)]) if (player, kind) in counts else MSG_NO_BARS) for kind in kinds]
        lines.append(MSG_PLAYER_COLUMN.format(player) + ''.join(cells))
    return lines


def whole_song(counts):
    """Every player's repeats in the whole song, added up."""
    of_all = [count for (_, kind), count in counts.items() if kind == EVERY_SECTION]
    return [sum(count[0] for count in of_all), sum(count[1] for count in of_all)]


def one_line(*, genre, subgenre, counts):
    """A subgenre in a line: the share over every player, and the players who repeat most."""
    by_player = [(share(count), player) for (player, kind), count in counts.items() if kind == EVERY_SECTION and share(count) is not None]
    most = sorted(by_player, reverse=True)[:MOST_SHOWN]
    return MSG_SUBGENRE_LINE.format(genre=genre, subgenre=subgenre, share=shown(whole_song(counts)),
                                    most=SEPARATOR.join(MSG_MOST.format(player=player, share=MSG_SHARE.format(part)) for part, player in most))


def subgenres_of(genre):
    choices = WizardChoices()
    choices.set_genre(genre)
    return choices.subgenres()


def report(*, genre, subgenre, songs, loudness):
    """The lines of the report: one subgenre's table, or a line for each subgenre of a genre or of every genre."""
    if genre is not None and genre not in genre_names():
        raise ValueError(ERR_NO_SUCH_GENRE.format(genre, SEPARATOR.join(genre_names())))
    if subgenre is not None:
        if subgenre not in subgenres_of(genre):
            raise ValueError(ERR_NO_SUCH_SUBGENRE.format(genre, subgenre, SEPARATOR.join(subgenres_of(genre))))
        return table(genre=genre, subgenre=subgenre, songs=songs, counts=counted(genre=genre, subgenre=subgenre, songs=songs, loudness=loudness))
    lines = []
    for a_genre in genre_names() if genre is None else [genre]:
        for a_subgenre in subgenres_of(a_genre):
            lines.append(one_line(genre=a_genre, subgenre=a_subgenre, counts=counted(genre=a_genre, subgenre=a_subgenre, songs=songs, loudness=loudness)))
    return lines


def main(*, arguments=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('genre', nargs='?')
    parser.add_argument('subgenre', nargs='?')
    parser.add_argument('--songs', type=int, default=USUAL_SONGS)
    parser.add_argument('--loudness', action='store_true')
    given = parser.parse_args(arguments)
    try:
        lines = report(genre=given.genre, subgenre=given.subgenre, songs=given.songs, loudness=given.loudness)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    print('\n'.join(lines))
    return 0


if __name__ == '__main__':
    sys.exit(main())
