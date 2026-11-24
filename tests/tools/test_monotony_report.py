# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""internal_tools/monotony_report.py, one quick check of its main path: a subgenre is reported as a table of players by kinds of section. A tool fails loudly when it is run, so one check is enough (.claude/rules/TESTING.md)."""

import importlib.util
import pathlib
import unittest

from llamatron.math.rational import Rational
from llamatron.model.values.note import Note, NoteName

SCRIPT = pathlib.Path(__file__).resolve().parent.parent.parent / 'internal_tools' / 'monotony_report.py'
MODULE_NAME = 'monotony_report'
A_GENRE = 'rock'
A_SUBGENRE = 'hard rock'
ONE_SONG = 1
AN_OCTAVE = 4
A_QUARTER = Rational(1, 4)
A_BAR = Rational(1)
LOUD = 110


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

if __name__ == '__main__':
    unittest.main()
