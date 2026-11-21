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

"""The MIDI cleaning of internal_tools/analysis_and_generation/, one quick check of its main path: a clean song is left as it is with no doubts. A research tool fails loudly when it is run, so one check is enough (.claude/TESTING.md)."""

from measuring.hearing.cleaning import KICK, tidied
from measuring.hearing.performance import PlayedNote, PlayedTrack
import unittest

BEATS_PER_BAR = 4
BARS = 16
VELOCITY = 90
LEAD_PROGRAM = 81
SCALE = (60, 62, 64, 65, 67, 69, 71, 72)
HAT = 42
LEAD = 'lead'
DRUMS = 'Drums'


def note(*, start, pitch, length=0.5):
    return PlayedNote(start=start, end=start + length, pitch=pitch, velocity=VELOCITY)


def melody(*, name=LEAD, sound=LEAD_PROGRAM):
    return PlayedTrack(name=name, drum=False, sound=sound, notes=tuple(note(start=float(beat), pitch=SCALE[beat % len(SCALE)]) for beat in range(BARS * BEATS_PER_BAR)))


def tidy(*tracks):
    return tidied(tracks=tracks, beats_per_bar=BEATS_PER_BAR)


class TestTidying(unittest.TestCase):
    __slots__ = ()

    def test_a_clean_song_is_left_as_it_is_with_no_doubts(self):
        kit = PlayedTrack(name=DRUMS, drum=True, sound=None, notes=tuple(note(start=float(beat), pitch=(KICK, HAT)[beat % 2]) for beat in range(BARS * BEATS_PER_BAR)))
        tracks, doubts = tidy(melody(), kit)
        self.assertEqual(doubts, ())
        self.assertEqual([len(track.notes) for track in tracks], [len(melody().notes), len(kit.notes)])

if __name__ == '__main__':
    unittest.main()
