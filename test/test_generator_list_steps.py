# noose6: a Python language and framework for producing MIDI clips.
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

"""Every generator with a list of values uses it for notes, and never for rests."""

import unittest

from src.legacy.generators.backfill import Backfill
from src.legacy.generators.duration_change import DurationChange
from src.legacy.generators.mix_up import MixUp
from src.legacy.generators.mix_up2 import MixUp2
from src.generators.auto_ratchet import AutoRatchet
from src.note import Note, Rest
from src.scale import Scale, ScaleType
from src.song import Clip

SIXTEENTH = 0.0625
C_MAJOR = Scale(Note('C', 4), ScaleType.MAJOR)
PITCHES = ['C', 'G', 'C', 'G', 'C', 'G', 'C']


def notes_only(clip):
    return [position for position in clip.notes if not isinstance(position, Rest)]


def pattern(rests_between):
    """Return sixteenth notes that are a whole note apart, with the silence in some rests."""
    positions = []
    for name in PITCHES:
        positions.append(Note(name, 4, SIXTEENTH))
        positions += [Rest(0.9375 / rests_between)] * rests_between
    return positions[:-rests_between]


class TestListsOnlyStepThroughNotes(unittest.TestCase):

    def assert_rests_make_no_difference(self, generator):
        """The same notes must be chosen, however many rests the silence is split into."""
        results = [
            notes_only(generator.generate(Clip(notes=pattern(rests_between))))
            for rests_between in [1, 2, 5]
        ]
        self.assertEqual(results[1], results[0])
        self.assertEqual(results[2], results[0])

    def test_duration_change(self):
        self.assert_rests_make_no_difference(DurationChange([0.25, 1, 0.5]))

    def test_stutter(self):
        self.assert_rests_make_no_difference(AutoRatchet([1, 3, 2]))

    def test_backfill(self):
        self.assert_rests_make_no_difference(Backfill([1, 0, 0], scale=C_MAJOR))

    def test_mix_up(self):
        self.assert_rests_make_no_difference(MixUp([1, 0, 0], seed=1))

    def test_mix_up2(self):
        self.assert_rests_make_no_difference(MixUp2([1, 0, 0]))

    def test_list_positions_line_up_with_notes(self):
        notes = pattern(5)
        third_note = notes_only(Clip(notes=notes))[2]

        changed = notes_only(DurationChange([1, 1, 0.5]).generate(Clip(notes=notes)))
        self.assertEqual(changed[2].length, third_note.length * 0.5)

        stuttered = notes_only(AutoRatchet([1, 1, 2]).generate(Clip(notes=notes)))
        self.assertEqual(stuttered[2].length, third_note.length / 2)
        self.assertEqual(stuttered[3], stuttered[2])

        swapped = notes_only(MixUp2([0, 0, 1, 0, 0, 0]).generate(Clip(notes=notes)))
        self.assertEqual(swapped[2], notes_only(Clip(notes=notes))[3])

        filled = notes_only(Backfill([0, 0, 1, 0, 0, 0], scale=C_MAJOR).generate(Clip(notes=notes)))
        self.assertEqual(len(filled), len(PITCHES) + 1)
        self.assertEqual(filled[2], third_note)
        self.assertEqual(filled[3].name, 'E')


if __name__ == '__main__':
    unittest.main()
