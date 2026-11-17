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
"""internal_tools/monotony_report.py says how much of what the song wizard makes repeats, bar by bar."""

import contextlib
import importlib.util
import io
import pathlib
import unittest

from llamatron.music.chord import Chord
from llamatron.music.note import Note, NoteName, Rest
from llamatron.support.rational import Rational

SCRIPT = pathlib.Path(__file__).resolve().parent.parent.parent / 'internal_tools' / 'monotony_report.py'
MODULE_NAME = 'monotony_report'
A_GENRE = 'rock'
A_SUBGENRE = 'hard rock'
NOT_A_GENRE = 'polka'
NOT_A_SUBGENRE = 'soft rock'
ONE_SONG = 1
SONGS_FLAG = '--songs'
AN_OCTAVE = 4
A_QUARTER = Rational(1, 4)
A_HALF = Rational(1, 2)
A_BAR = Rational(1)
LOUD = 110
SOFT = 60
FAILED = 1
WORKED = 0


def load_script():
    """Load the tool as a module, since internal_tools/ is not a package."""
    spec = importlib.util.spec_from_file_location(MODULE_NAME, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TOOL = load_script()


def note(*, name=NoteName.C, length=A_QUARTER, velocity=LOUD):
    return Note(name=name, octave_number=AN_OCTAVE, length=length, velocity=velocity)


def four(name):
    """A bar of one note four times."""
    return [note(name=name) for _ in range(4)]


def bars(positions, *, loudness=False):
    return TOOL.bars_of(positions=positions, bar_length=A_BAR, loudness=loudness)


class TestMonotonyReport(unittest.TestCase):
    """The bars of a run of notes, which of them repeat, and the report of a subgenre."""

    __slots__ = ()

    def test_a_bar_the_same_as_an_earlier_bar_repeats_and_another_does_not(self):
        played = bars(four(NoteName.C) + four(NoteName.E) + four(NoteName.C) + four(NoteName.C))
        self.assertEqual(len(played), 4)
        self.assertEqual(TOOL.repeats(played), (2, 4))

    def test_the_same_notes_at_other_places_in_the_bar_are_another_bar(self):
        on_the_beat = [note(), Rest(A_QUARTER), note(), Rest(A_QUARTER)]
        off_the_beat = [Rest(A_QUARTER), note(), Rest(A_QUARTER), note()]
        self.assertEqual(TOOL.repeats(bars(on_the_beat + off_the_beat)), (0, 2))

    def test_a_longer_note_is_another_bar(self):
        self.assertEqual(TOOL.repeats(bars([note(length=A_HALF), note(length=A_HALF), note(length=A_BAR)])), (0, 2))

    def test_an_empty_bar_is_left_out(self):
        played = bars(four(NoteName.C) + [Rest(A_BAR), Rest(A_BAR)] + four(NoteName.C))
        self.assertEqual(TOOL.repeats(played), (1, 2))

    def test_loudness_counts_only_when_asked(self):
        quiet = [note(velocity=SOFT) for _ in range(4)]
        self.assertEqual(TOOL.repeats(bars(four(NoteName.C) + quiet)), (1, 2))
        self.assertEqual(TOOL.repeats(bars(four(NoteName.C) + quiet, loudness=True)), (0, 2))

    def test_a_chord_is_its_notes_in_any_order(self):
        up = Chord([note(name=NoteName.C, length=A_BAR), note(name=NoteName.E, length=A_BAR)])
        down = Chord([note(name=NoteName.E, length=A_BAR), note(name=NoteName.C, length=A_BAR)])
        self.assertEqual(TOOL.repeats(bars([up, down])), (1, 2))

    def test_a_short_clip_goes_round_its_scene(self):
        self.assertEqual(TOOL.repeats(TOOL.looped(bars=bars(four(NoteName.C) + four(NoteName.E)), count=6)), (4, 6))
        self.assertEqual(TOOL.looped(bars=[], count=6), [])

    def test_a_scene_is_of_the_kind_its_name_starts_with(self):
        self.assertEqual([TOOL.kind_of_scene(name) for name in ('verse', 'verse 2', 'intro b', 'drum solo', 'pre-chorus 3')],
                         ['verse', 'verse', 'intro', 'drum solo', 'pre-chorus'])

    def test_a_subgenre_is_reported_as_a_table_of_players_by_kinds_of_section(self):
        counts = TOOL.counted(genre=A_GENRE, subgenre=A_SUBGENRE, songs=ONE_SONG, loudness=False)
        lines = TOOL.table(genre=A_GENRE, subgenre=A_SUBGENRE, songs=ONE_SONG, counts=counts)
        players = {player for player, _ in counts}
        self.assertEqual({line.split()[0] for line in lines[3:] if not line.startswith(' ')} - {name.split()[0] for name in players}, set())
        self.assertIn(TOOL.EVERY_SECTION, lines[2])
        for same, played in counts.values():
            self.assertLessEqual(same, played)
        # A player's whole song is the sum of the player's sections.
        for player in players:
            of_sections = sum(count[1] for (name, kind), count in counts.items() if name == player and kind != TOOL.EVERY_SECTION)
            self.assertEqual(counts[(player, TOOL.EVERY_SECTION)][1], of_sections)

    def test_the_command_reports_a_genre_a_line_a_subgenre_and_refuses_what_is_not_one(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(TOOL.main(arguments=[A_GENRE, SONGS_FLAG, str(ONE_SONG)]), WORKED)
        self.assertEqual(len(out.getvalue().strip().split('\n')), len(TOOL.subgenres_of(A_GENRE)))
        for wrong in ([NOT_A_GENRE], [A_GENRE, NOT_A_SUBGENRE]):
            with contextlib.redirect_stderr(io.StringIO()) as said:
                self.assertEqual(TOOL.main(arguments=wrong), FAILED)
            self.assertIn(wrong[-1], said.getvalue())


if __name__ == '__main__':
    unittest.main()
