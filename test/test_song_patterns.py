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

"""Patterns in song files: steps, rows, gates, chords and drum patterns, and what they play."""

import os
import tempfile
import unittest
from fractions import Fraction

import mido

from llamatron.music.chord import Chord
from llamatron.music.note import Note, NoteName, Rest
from llamatron.playback.song_renderer import SongRenderer
from llamatron.exporters.clip_tree import ClipTree
from llamatron.exporters.midi_messages import NOTE_ON_MESSAGE
from llamatron.exporters.timing import GLIDE_OVERLAP, timed_events
from rendering import render_data, song_from_data
from llamatron.composition.file_format import (
    CHORD_SYMBOLS,
    FIXED_CHORDS,
    SCALE_CHORDS,
    ClipSlotSetting,
    ChordSymbol,
    GateModifier,
    LIVE_OCTAVE_OFFSET,
    LLAMATRON_OCTAVES_SINCE,
    OctaveLabels,
    PatternSetting,
    Row,
    Section,
    SetlistSetting,
)
from llamatron.composition.limits import MAX_OCTAVE, MAX_PROBABILITY, MIN_PROBABILITY
from llamatron.support.version import VERSION
from llamatron.composition.song_file_error import SongFileError
from song_testing import BASIC, LEAD, ROWS, X, build, clip, lead, lead_data, lead_song, pat, pitches, with_parts

QUARTER = '1/4'
HALF = '1/2'
EIGHTH = '1/8'
NOPE = 'nope'
YES = 'yes'
B = 'b'
SIXTEENTH = '1/16'
DOM = 'dom'
# A probability that keeps a note on about half the takes, and how many seeds a test tries.
EVEN_CHANCE = 50
SEEDS_TRIED = 20
M5 = 'M5'
MAJ7 = 'maj7'
C_MINOR = 'C minor'
KICK = 'kick'
# A version from before song files numbered octaves from C0.
OLD_VERSION = '1.0.24'


class TestPatterns(unittest.TestCase):

    def test_degrees_and_rests_and_lengths(self):
        found = clip(song=build(BASIC), scene=1, track=LEAD).get_notes()
        # Each empty step is a rest of one step.
        self.assertEqual(found, [Note(name=NoteName.C, octave_number=4, length=Fraction(1, 4)), Note(name=NoteName.E, octave_number=4, length=Fraction(1, 4)), Rest(Fraction(1, 4)), Rest(Fraction(1, 4))])

    def test_octaves_are_absolute_and_numbered_from_c0(self):
        found = lead([1, HALF], [1, HALF], rows={Row.OCTAVE: [5, 3]})
        self.assertEqual(pitches(found), [60, 36])

    def test_a_note_without_an_octave_uses_the_song_default(self):
        self.assertEqual(pitches(lead([1, HALF], default_octave=5)), [60])

    def test_a_default_song_octave_is_middle_c(self):
        data = with_parts(patterns={X: pat([1, HALF])}, scenes=[{Section.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: X}}}])
        del data[SetlistSetting.DEFAULT_OCTAVE]
        self.assertEqual(pitches(clip(song=render_data(data), scene=1, track=LEAD)), [60])

    def test_a_file_saved_before_the_numbering_changed_has_its_octaves_moved_up(self):
        # Older files numbered octaves as Live labels them, two lower, so an old 3 and a new 5 are both middle C.
        data = with_parts(patterns={X: pat([1, HALF], octave=[3])}, scenes=[{Section.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: X}}}])
        data[SetlistSetting.DEFAULT_OCTAVE] = 3
        data[SetlistSetting.DEFAULT_DRUM_OCTAVE] = 1
        data[SetlistSetting.VERSION] = OLD_VERSION
        song = song_from_data(data)
        self.assertEqual((song.get_default_octave(), song.get_default_drum_octave()), (3 + LIVE_OCTAVE_OFFSET, 1 + LIVE_OCTAVE_OFFSET))
        self.assertEqual(pitches(clip(song=render_data(data), scene=1, track=LEAD)), [60])

    def test_a_file_saved_since_the_numbering_changed_or_without_a_version_is_read_as_it_is(self):
        for version in [LLAMATRON_OCTAVES_SINCE, VERSION, None]:
            with self.subTest(version=version):
                data = with_parts(patterns={X: pat([1, HALF], octave=[3])}, scenes=[{Section.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: X}}}])
                if version is not None:
                    data[SetlistSetting.VERSION] = version
                self.assertEqual(pitches(clip(song=render_data(data), scene=1, track=LEAD)), [36])

    def test_an_old_file_still_refuses_octaves_that_are_not_numbers(self):
        data = with_parts(patterns={X: pat([1, HALF], octave=[YES])})
        data[SetlistSetting.VERSION] = OLD_VERSION
        with self.assertRaises(SongFileError):
            song_from_data(data)

    def test_octave_labels_are_a_song_setting_with_lives_as_the_default(self):
        self.assertEqual(song_from_data(with_parts()).get_octave_labels(), OctaveLabels.LIVE)
        song = song_from_data(with_parts(octave_labels=OctaveLabels.LLAMATRON))
        self.assertEqual(song.get_octave_labels(), OctaveLabels.LLAMATRON)
        self.assertEqual((song.shown_octave(MAX_OCTAVE), song.stored_octave(MAX_OCTAVE)), (MAX_OCTAVE, MAX_OCTAVE))
        with self.assertRaises(SongFileError):
            song_from_data(with_parts(octave_labels=X))

    def test_a_degree_past_the_scale_wraps_up_an_octave(self):
        self.assertEqual(pitches(lead([8, HALF])), [60])

    def test_accidentals(self):
        found = lead([3, QUARTER], [3, QUARTER], [3, QUARTER], rows={Row.ACCIDENTAL: [None, B, '#']})
        self.assertEqual(pitches(found), [52, 51, 53])

    def test_a_step_with_nothing_set_is_a_rest_of_the_default_length(self):
        found = lead([1, QUARTER], [None, None], [3, QUARTER])
        self.assertEqual(found.total_length(), Fraction(9, 16))
        self.assertEqual(pitches(found), [48, 52])

    def test_a_step_with_only_a_duration_is_a_rest(self):
        found = lead([1, QUARTER], [None, QUARTER], [3, QUARTER])
        self.assertEqual(found.total_length(), Fraction(3, 4))

    def test_a_note_without_a_gate_lasts_one_step(self):
        found = lead([1, EIGHTH], [None, EIGHTH])
        self.assertEqual(found.get_notes()[0], Note(name=NoteName.C, octave_number=4, length=Fraction(1, 8)))

    def test_the_song_step_size_is_used_unless_the_pattern_has_its_own(self):
        data = with_parts(patterns={X: {PatternSetting.STEPS: 2, Row.DEGREE: [1, 1]}}, scenes=[{Section.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: X}}}], step_size=EIGHTH)
        self.assertEqual(clip(song=render_data(data), scene=1, track=LEAD).total_length(), Fraction(1, 4))
        data[Section.PATTERNS][X][PatternSetting.STEP_SIZE] = QUARTER
        self.assertEqual(clip(song=render_data(data), scene=1, track=LEAD).total_length(), Fraction(1, 2))

    def test_a_gate_can_run_past_later_steps_but_not_past_the_end_of_the_pattern(self):
        pattern = {PatternSetting.STEPS: 8, Row.DEGREE: [1, 3, None, 5, None, None, None, None], Row.GATE: [HALF, None, None, '1', None, None, None, None]}
        data = with_parts(patterns={X: pattern}, scenes=[{Section.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: X, ClipSlotSetting.REPEAT: 2}}}])
        events, _ = timed_events(clip=clip(song=render_data(data), scene=1, track=LEAD), scale=None)
        starts_and_ends = sorted((start, end) for start, end, _, _ in events)
        # The first note sounds right through the next two, and the last is cut at the end of the pattern.
        self.assertEqual(starts_and_ends[:3], [(0, Fraction(1, 2)), (Fraction(1, 16), Fraction(1, 8)), (Fraction(3, 16), Fraction(1, 2))])
        self.assertEqual(starts_and_ends[3][0], Fraction(1, 2))

    def test_dotted_and_triplet_gates(self):
        found = lead([1, QUARTER], [1, QUARTER], rows={Row.GATE: [SIXTEENTH, SIXTEENTH], Row.DOT: [GateModifier.DOTTED, GateModifier.TRIPLET]})
        self.assertEqual([note.get_length() for note in found.get_notes() if isinstance(note, Note)], [Fraction(3, 32), Fraction(1, 24)])

    def test_a_pattern_needs_at_least_one_step(self):
        with self.assertRaises(SongFileError):
            lead()

    def test_rows_must_match_the_step_count(self):
        with self.assertRaises(SongFileError):
            lead([1, QUARTER], rows={Row.VELOCITY: [1, 2]})

    def test_values_are_checked(self):
        for row, value in [
            (Row.GATE, 0), (Row.GATE, '0.25'), (Row.GATE, 0.25), (Row.GATE, 5), (Row.DOT, X),
            (Row.ACCIDENTAL, X), (Row.OCTAVE, MAX_OCTAVE + 1), (Row.CHORD, NOPE), (Row.VELOCITY, 0),
            (Row.VELOCITY, 128), (Row.PROBABILITY, 101), (Row.RATCHET, 0), (Row.GLIDE, YES),
        ]:
            with self.subTest(row=row, value=value), self.assertRaises(SongFileError):
                lead([1, QUARTER], rows={row: [value]})


class TestChordRow(unittest.TestCase):

    def chord(self, symbol, degree=1, **rows):
        return lead([degree, 1], rows={Row.CHORD: [symbol], **rows}).get_notes()[0]

    def test_fixed_chords(self):
        # Half steps above C for each symbol, written out rather than read from ChordType.
        expected = {
            'M': [0, 4, 7], 'm': [0, 3, 7], ChordSymbol.DIMINISHED: [0, 3, 6], ChordSymbol.AUGMENTED: [0, 4, 8], ChordSymbol.SUS2: [0, 2, 7], ChordSymbol.SUS4: [0, 5, 7],
            ChordSymbol.POWER: [0, 7], ChordSymbol.MAJOR6: [0, 4, 7, 9], ChordSymbol.MINOR6: [0, 3, 7, 9],
            ChordSymbol.DOMINANT7: [0, 4, 7, 10], ChordSymbol.MAJOR7: [0, 4, 7, 11], ChordSymbol.MINOR7: [0, 3, 7, 10], ChordSymbol.MINOR_MAJOR7: [0, 3, 7, 11],
            ChordSymbol.DIMINISHED7: [0, 3, 6, 9], ChordSymbol.HALF_DIMINISHED7: [0, 3, 6, 10], ChordSymbol.AUGMENTED7: [0, 4, 8, 10], ChordSymbol.AUGMENTED_MAJOR7: [0, 4, 8, 11],
            ChordSymbol.DOMINANT7_SUS4: [0, 5, 7, 10], ChordSymbol.ADD9: [0, 4, 7, 14], ChordSymbol.MINOR_ADD9: [0, 3, 7, 14],
            ChordSymbol.DOMINANT9: [0, 4, 7, 10, 14], ChordSymbol.MAJOR9: [0, 4, 7, 11, 14], ChordSymbol.MINOR9: [0, 3, 7, 10, 14],
            ChordSymbol.DOMINANT11: [0, 4, 7, 10, 14, 17], ChordSymbol.MAJOR11: [0, 4, 7, 11, 14, 17], ChordSymbol.MINOR11: [0, 3, 7, 10, 14, 17],
            ChordSymbol.DOMINANT13: [0, 4, 7, 10, 14, 17, 21], ChordSymbol.MAJOR13: [0, 4, 7, 11, 14, 17, 21], ChordSymbol.MINOR13: [0, 3, 7, 10, 14, 17, 21],
        }
        self.assertEqual(set(expected), set(FIXED_CHORDS))
        for symbol, steps in expected.items():
            with self.subTest(symbol=symbol):
                self.assertEqual(sorted(n.get_midi_number() for n in self.chord(symbol).get_notes()), [48 + s for s in steps])

    def test_a_fixed_chord_can_leave_the_scale(self):
        # E major on degree 3 of C major has a G#, which isn't in the scale.
        self.assertEqual(sorted(n.get_midi_number() for n in self.chord('M', degree=3).get_notes()), [52, 56, 59])

    def test_every_chord_fits_a_pattern_cell(self):
        for symbol in CHORD_SYMBOLS:
            self.assertLessEqual(len(symbol), 5)

    def test_a_fixed_chord_stays_the_same_in_any_scale(self):
        found = lead([1, 1], scale=C_MINOR, rows={Row.CHORD: ['M']}).get_notes()[0]
        self.assertEqual(sorted(n.get_midi_number() for n in found.get_notes()), [48, 52, 55])

    def test_chords_from_the_scale_follow_the_scale(self):
        major = lead([1, 1], rows={Row.CHORD: [3]}).get_notes()[0]
        minor = lead([1, 1], scale=C_MINOR, rows={Row.CHORD: [3]}).get_notes()[0]
        self.assertEqual(sorted(n.get_midi_number() for n in major.get_notes()), [48, 52, 55])
        self.assertEqual(sorted(n.get_midi_number() for n in minor.get_notes()), [48, 51, 55])

    def test_a_seventh_from_the_scale_has_four_notes(self):
        self.assertEqual(sorted(n.get_midi_number() for n in self.chord(7).get_notes()), [48, 52, 55, 59])

    def test_every_chord_from_the_scale(self):
        expected = {
            5: [48, 55], 3: [48, 52, 55], 7: [48, 52, 55, 59], 9: [48, 52, 55, 59, 62],
            11: [48, 52, 55, 59, 62, 65], 13: [48, 52, 55, 59, 62, 65, 69],
        }
        self.assertEqual({str(symbol) for symbol in expected}, set(SCALE_CHORDS))
        for symbol, notes in expected.items():
            with self.subTest(symbol=symbol):
                self.assertEqual(sorted(n.get_midi_number() for n in self.chord(symbol).get_notes()), notes)

    def test_chords_from_the_scale_stay_in_it(self):
        # On degree 7 of C major, the 5 is F, a diminished fifth, and the 9 is C, a flat ninth.
        self.assertEqual(sorted(n.get_midi_number() for n in self.chord(5, degree=7).get_notes()), [59, 65])
        self.assertEqual(sorted(n.get_midi_number() for n in self.chord(9, degree=7).get_notes()), [59, 62, 65, 69, 72])

    def test_an_unknown_chord_is_refused(self):
        for symbol in [DOM, M5, 6, MAJ7]:
            with self.subTest(symbol=symbol), self.assertRaises(SongFileError):
                self.chord(symbol)

    def test_a_chord_uses_the_octave_and_accidental(self):
        found = self.chord('M', octave=[5], accidental=['#'])
        self.assertEqual(sorted(n.get_midi_number() for n in found.get_notes()), [61, 65, 68])


class TestDrumPatterns(unittest.TestCase):

    def test_letters_ignore_the_scale_and_use_the_drum_octave(self):
        self.assertEqual(set(pitches(clip(song=build(BASIC), scene=1, track=KICK))), {36})

    def test_a_drum_step_can_have_an_accidental_and_octave(self):
        found = lead([NoteName.F, QUARTER], rows={PatternSetting.DRUM: True, Row.ACCIDENTAL: ['#'], Row.OCTAVE: [4]})
        self.assertEqual(pitches(found), [54])

    def test_a_drum_pattern_needs_no_scale(self):
        found = lead([NoteName.C, QUARTER], rows={PatternSetting.DRUM: True}, scale=None)
        self.assertEqual(pitches(found), [36])

    def test_a_drum_pattern_only_takes_letters(self):
        with self.assertRaises(SongFileError):
            lead([1, QUARTER], rows={PatternSetting.DRUM: True})

    def test_a_scale_pattern_only_takes_numbers(self):
        with self.assertRaises(SongFileError):
            lead([NoteName.C, QUARTER])

    def test_a_drum_pattern_has_no_chords(self):
        with self.assertRaises(SongFileError):
            lead([NoteName.C, QUARTER], rows={PatternSetting.DRUM: True, Row.CHORD: ['M']})


class TestStepRows(unittest.TestCase):

    def test_velocity_defaults_to_127(self):
        events, _ = timed_events(clip=lead([1, QUARTER]), scale=None)
        self.assertEqual(events[0][3], 127)

    def test_velocity_reaches_the_note(self):
        events, _ = timed_events(clip=lead([1, QUARTER], rows={Row.VELOCITY: [40]}), scale=None)
        self.assertEqual(events[0][3], 40)

    def test_velocity_reaches_every_chord_note(self):
        events, _ = timed_events(clip=lead([1, QUARTER], rows={Row.VELOCITY: [40], Row.CHORD: ['M']}), scale=None)
        self.assertEqual({event[3] for event in events}, {40})

    def test_velocity_reaches_a_midi_file(self):
        with tempfile.TemporaryDirectory() as directory:
            ClipTree(directory=directory, grid=lead_song([1, QUARTER], rows={Row.VELOCITY: [40]})).export()
            played = mido.MidiFile(os.path.join(directory, os.listdir(directory)[0]))
        self.assertEqual([m.velocity for m in played.tracks[0] if m.type == NOTE_ON_MESSAGE], [40])

    def test_ratchet_slices_a_note_in_the_same_time(self):
        found = lead([1, SIXTEENTH], rows={Row.RATCHET: [2]})
        self.assertEqual(found.get_notes(), [Note(name=NoteName.C, octave_number=4, length=Fraction(1, 32))] * 2)

    def test_ratchet_slices_a_chord(self):
        found = lead([1, QUARTER], rows={Row.RATCHET: [3], Row.CHORD: ['M']})
        self.assertEqual(len(found.get_notes()), 3)
        self.assertIsInstance(found.get_notes()[0], Chord)
        self.assertEqual(found.total_length(), Fraction(1, 4))

    def test_probability_of_zero_is_always_silent_but_keeps_the_time(self):
        found = lead([1, QUARTER], rows={Row.PROBABILITY: [0]})
        self.assertEqual(found.get_notes(), [Rest(Fraction(1, 4))])

    def long_note_over_the_next(self, *, probability, **parts):
        """Return the clip of four sixteenth steps where the note on step 1 has a gate of a quarter, reaching over the note on step 2, and a probability."""
        pattern = {
            PatternSetting.STEPS: 4, Row.DEGREE: [1, 3, None, None], Row.GATE: [QUARTER, None, None, None],
            Row.PROBABILITY: [probability, None, None, None], **parts.pop(ROWS, {}),
        }
        data = with_parts(patterns={X: pattern}, scenes=[{Section.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: X}}}], **parts)
        return clip(song=render_data(data), scene=1, track=LEAD)

    def starts_and_ends(self, found):
        """Return when each note of a clip starts and ends, in time order."""
        events, _ = timed_events(clip=found, scale=None)
        return sorted((start, end) for start, end, _, _ in events)

    def test_a_long_note_that_probability_keeps_sounds_over_the_next_note(self):
        found = self.long_note_over_the_next(probability=MAX_PROBABILITY)
        self.assertEqual(self.starts_and_ends(found), [(0, Fraction(1, 4)), (Fraction(1, 16), Fraction(1, 8))])
        self.assertEqual(found.total_length(), Fraction(1, 4))

    def test_a_long_note_that_probability_drops_is_silent_and_the_next_note_plays(self):
        found = self.long_note_over_the_next(probability=MIN_PROBABILITY)
        self.assertEqual(self.starts_and_ends(found), [(Fraction(1, 16), Fraction(1, 8))])
        sixteenth = Fraction(1, 16)
        self.assertEqual(found.get_notes(), [Rest(sixteenth), Note(name=NoteName.E, octave_number=4, length=sixteenth), Rest(sixteenth), Rest(sixteenth)])
        self.assertEqual(found.total_length(), Fraction(1, 4))

    def test_a_long_ratcheted_note_that_probability_drops_is_silent_and_the_next_note_plays(self):
        found = self.long_note_over_the_next(probability=MIN_PROBABILITY, rows={Row.RATCHET: [2, None, None, None]})
        self.assertEqual(self.starts_and_ends(found), [(Fraction(1, 16), Fraction(1, 8))])
        self.assertEqual(found.total_length(), Fraction(1, 4))

    def test_a_long_note_with_a_chance_renders_on_every_seed_with_or_without_the_note(self):
        kept = 0
        dropped = 0
        for seed in range(SEEDS_TRIED):
            with self.subTest(seed=seed):
                found = self.starts_and_ends(self.long_note_over_the_next(probability=EVEN_CHANCE, seed=seed))
                self.assertIn(found, [[(0, Fraction(1, 4)), (Fraction(1, 16), Fraction(1, 8))], [(Fraction(1, 16), Fraction(1, 8))]])
                kept += len(found) == 2
                dropped += len(found) == 1
        # Both sides are tested: takes that keep the long note and takes that drop it.
        self.assertGreater(kept, 0)
        self.assertGreater(dropped, 0)

    def many(self, **parts):
        steps = [[1, SIXTEENTH]] * 200
        return lead(*steps, rows={Row.PROBABILITY: [50] * 200}, **parts)

    def test_probability_is_rolled_once_at_render_from_the_seed(self):
        self.assertEqual(self.many(seed=5).get_notes(), self.many(seed=5).get_notes())

    def test_probability_changes_with_the_seed(self):
        self.assertNotEqual(self.many(seed=5).get_notes(), self.many(seed=6).get_notes())

    def test_probability_drops_about_the_right_share(self):
        sounding = [n for n in self.many(seed=5).get_notes() if isinstance(n, Note)]
        self.assertTrue(70 < len(sounding) < 130)

    def test_without_a_seed_every_render_is_a_new_take(self):
        self.assertIsNone(song_from_data(with_parts()).get_seed())
        self.assertNotEqual(self.many().get_notes(), self.many().get_notes())

    def test_a_seed_given_to_the_renderer_replaces_the_songs(self):
        data = lead_data(*[[1, SIXTEENTH]] * 200, rows={Row.PROBABILITY: [50] * 200}, seed=6)
        rendered = SongRenderer(song_from_data(data), seed=5).render()
        self.assertEqual(clip(song=rendered, scene=1, track=LEAD).get_notes(), self.many(seed=5).get_notes())

    def test_a_seed_in_the_file_must_be_an_integer_or_null(self):
        self.assertIsNone(song_from_data(with_parts(seed=None)).get_seed())
        with self.assertRaises(SongFileError):
            song_from_data(with_parts(seed=X))

    def test_each_repeat_rolls_again(self):
        found = lead(*[[1, SIXTEENTH]] * 100, clip_slot={ClipSlotSetting.REPEAT: 2}, rows={Row.PROBABILITY: [50] * 100})
        self.assertNotEqual(found.get_notes()[:100], found.get_notes()[100:])

    def test_each_ratchet_slice_rolls_again(self):
        found = lead(*[[1, SIXTEENTH]] * 50, rows={Row.PROBABILITY: [50] * 50, Row.RATCHET: [2] * 50})
        pairs = zip(found.get_notes()[::2], found.get_notes()[1::2])
        self.assertTrue(any(isinstance(a, Note) != isinstance(b, Note) for a, b in pairs))

    def test_glide_runs_into_the_next_note(self):
        events, _ = timed_events(clip=lead([1, QUARTER], [3, QUARTER], rows={Row.GLIDE: [True, False]}), scale=None)
        self.assertEqual(events[0][1], Fraction(1, 4) + GLIDE_OVERLAP)
        self.assertEqual(events[1][1], Fraction(1, 2))

    def test_glide_to_a_rest_or_the_same_pitch_or_the_end_does_nothing(self):
        for steps, glide in [
            ([[1, QUARTER], [None, QUARTER]], [True, False]),
            ([[1, QUARTER], [1, QUARTER]], [True, False]),
            ([[1, QUARTER]], [True]),
        ]:
            with self.subTest(steps=steps):
                events, _ = timed_events(clip=lead(*steps, rows={Row.GLIDE: glide}), scale=None)
                self.assertEqual(events[0][1], Fraction(1, 4))

    def test_only_the_last_ratchet_slice_glides(self):
        events, _ = timed_events(clip=lead([1, QUARTER], [3, QUARTER], rows={Row.RATCHET: [2, None], Row.GLIDE: [True, False]}), scale=None)
        self.assertEqual(events[0][1], Fraction(1, 8))
        self.assertEqual(events[1][1], Fraction(1, 4) + GLIDE_OVERLAP)
