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
"""The Voice leading generator, the user's design of 2026-11-11: each chord voiced nearest the chord before, within a range, the root kept in the bass when asked.

The tests play a C major triad, written in root position, through the progression I V vi IV, a
chord a bar, and voice it.
"""

import unittest

from llamatron.composition.file_format import GeneratorKind, Row, Section
from llamatron.composition.generator_settings import VoiceLeadingSetting
from llamatron.composition.song_file_error import SongFileError
from rendering import setlist_from_data
from test_progression import through
from test_shapes import notes

VOICING = 'smooth'
TRIAD = '3'
BARS = 4
POP = [1, 5, 6, 4]
# I V vi IV in root position, and voiced nearest each chord before.
ROOT_POSITION = [[60, 64, 67], [67, 71, 74], [69, 72, 76], [65, 69, 72]]
VOICE_LED = [[60, 64, 67], [59, 62, 67], [60, 64, 69], [60, 65, 69]]


def voiced(*, voicing=None, chords=POP):
    """Return the pitches of each bar's chord, through a progression and, when given, a voice leading after it."""
    data = through({'chords': chords}, rows={Row.CHORD: [TRIAD, None, None, None]}, repeat=BARS)
    if voicing is not None:
        data[Section.VOICE_LEADINGS] = {VOICING: voicing}
        data[Section.CHAINS]['chords'].append({GeneratorKind.VOICE_LEADING: VOICING})
    return [sorted(pitch for start, _, pitch, _ in notes(data) if start == bar) for bar in range(BARS)]


class TestVoiceLeading(unittest.TestCase):

    def test_without_it_every_chord_is_in_root_position(self):
        self.assertEqual(voiced(), ROOT_POSITION)

    def test_each_chord_moves_as_little_as_it_can(self):
        self.assertEqual(voiced(voicing={}), VOICE_LED)

    def test_the_first_chord_plays_as_written(self):
        self.assertEqual(voiced(voicing={})[0], ROOT_POSITION[0])

    def test_a_range_keeps_every_note_within_it(self):
        found = voiced(voicing={VoiceLeadingSetting.LOWEST_OCTAVE: 5, VoiceLeadingSetting.HIGHEST_OCTAVE: 5})
        for chord in found[1:]:
            self.assertTrue(all(60 <= pitch < 72 for pitch in chord), chord)

    def test_the_root_kept_in_the_bass_stays_where_it_was_written(self):
        found = voiced(voicing={VoiceLeadingSetting.ROOT_IN_BASS: True})
        self.assertEqual([chord[0] for chord in found], [chord[0] for chord in ROOT_POSITION])
        for chord in found:
            self.assertEqual(chord[0], min(chord))

    def test_a_range_no_voicing_fits_leaves_the_chord_as_written(self):
        # Octave 10, from MIDI 120, is further than the four octaves a voicing is tried from where its chord was written.
        found = voiced(voicing={VoiceLeadingSetting.LOWEST_OCTAVE: 10, VoiceLeadingSetting.HIGHEST_OCTAVE: 10})
        self.assertEqual(found, ROOT_POSITION)

    def test_a_lowest_octave_above_the_highest_is_refused(self):
        data = through({'chords': POP})
        data[Section.VOICE_LEADINGS] = {VOICING: {VoiceLeadingSetting.LOWEST_OCTAVE: 6, VoiceLeadingSetting.HIGHEST_OCTAVE: 5}}
        with self.assertRaises(SongFileError):
            setlist_from_data(data)
