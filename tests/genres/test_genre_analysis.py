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
"""The genre analysis of internal_tools/analysis_and_generation/, one quick check of its main path: a song written note by note is measured in every trait. A research tool fails loudly when it is run, so one check is enough (.claude/TESTING.md)."""

from measuring.hearing.performance import Performance, PlayedNote, PlayedTrack
from measuring.hearing.profile import profile_of_performance
from measuring.measures.traits import BassMotion, Trait, TRAITS
import unittest


BEATS = 4
TEMPO = 120
METER = '4/4'
VELOCITY = 100
C = 60
C_MAJOR_SCALE = (60, 62, 64, 65, 67, 69, 71, 72)
KICK = 36
SNARE = 38
HAT = 42
BASS_NOTE = 36
SONG = 'test'
# The traits the analyzer cannot yet measure from notes: form, since how to split a song is not known, and solos, which it cannot yet find.
UNMEASURED_TRAITS = (Trait.FORM, Trait.SOLOS)


def note(*, start, length=0.5, pitch=C, velocity=VELOCITY):
    return PlayedNote(start=start, end=start + length, pitch=pitch, velocity=velocity)


def track(*, name, notes, drum=False, sound=None):
    return PlayedTrack(name=name, drum=drum, sound=sound, notes=tuple(sorted(notes, key=lambda each: (each.start, each.pitch))))


def performance(*, tracks, bars):
    return Performance(tracks=tuple(tracks), tempo=TEMPO, meter=METER, beats_per_bar=BEATS, length=bars * BEATS)


def scale_tune(bars):
    """Return a lead walking up and down the C major scale in eighths, a rest at the end of each bar."""
    notes = []
    for bar in range(bars):
        pitches = C_MAJOR_SCALE[:4] + tuple(reversed(C_MAJOR_SCALE[:3])) if bar % 2 == 0 else C_MAJOR_SCALE[3:7] + tuple(reversed(C_MAJOR_SCALE[4:7]))
        for place, pitch in enumerate(pitches):
            notes.append(note(start=bar * BEATS + place * 0.5, pitch=pitch))
    return notes


def rock_drums(bars):
    notes = []
    for bar in range(bars):
        start = bar * BEATS
        notes += [note(start=start, pitch=KICK), note(start=start + 2, pitch=KICK), note(start=start + 1, pitch=SNARE), note(start=start + 3, pitch=SNARE)]
        notes += [note(start=start + place * 0.5, pitch=HAT) for place in range(8)]
    return notes


def root_bass(bars):
    return [note(start=bar * BEATS + beat, length=1, pitch=BASS_NOTE) for bar in range(bars) for beat in range(BEATS)]


class TestAnalysis(unittest.TestCase):

    def test_a_song_written_note_by_note_is_measured_in_every_trait(self):
        song = performance(tracks=[track(name='a', notes=rock_drums(8), drum=True), track(name='b', notes=root_bass(8)), track(name='c', notes=scale_tune(8))], bars=8)
        profile = profile_of_performance(performance=song, name=SONG)
        for trait in TRAITS:
            if trait not in UNMEASURED_TRAITS:
                self.assertIsNotNone(profile.trait(trait), trait)
        self.assertEqual(profile.trait(Trait.BASS).motion, BassMotion.ROOTS)
        self.assertGreater(profile.trait(Trait.HOOK).strength, 0.5)
        self.assertTrue(profile.trait(Trait.DRUMS).main().has_backbeat())


if __name__ == '__main__':
    unittest.main()
