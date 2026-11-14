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

"""Grab steps, which take notes from another track."""

import unittest
from fractions import Fraction

from llamatron.composition.clip_slot import morph_style_name
from llamatron.generators.blend import BlendMode
from llamatron.exporters.timing import timed_events
from rendering import render_data, song_from_data
from llamatron.composition.file_format import ChordSymbol, ClipSlotSetting, GeneratorKind, PatternSetting, Row, Section, SongSetting, TrackSetting
from llamatron.composition.generator_settings import ArpSetting
from llamatron.composition.song_file_error import SongFileError
from llamatron.music.chord import Chord
from llamatron.music.midi import MAX_MIDI_NUMBER
from llamatron.music.note import MAX_OCTAVE, NoteName
from llamatron.strings.errors import ERR_NO_SCALE, ERR_WHERE_PATTERN
from song_testing import LEAD, X, clip, pat, pitches, with_parts

QUARTER = '1/4'
HALF = '1/2'
EIGHTH = '1/8'
NOPE = 'nope'
YES = 'yes'
KICK = 'kick'
RIFF = 'riff'
BASS = 'bass'
UP = 'up'
PAD = 'pad'
TOP = 'top'
NOTES_FROM = 'notes_from'
# The scale chord of four notes as a file holds it, a number.
SCALE_SEVENTH = int(ChordSymbol.SCALE_SEVENTH)
SCALE_TRIAD = int(ChordSymbol.SCALE_TRIAD)
SHARP = '#'


class TestGrab(unittest.TestCase):
    """A clip's grab steps play what another track most recently started, like the Cirklon."""

    def song(self, riff=None, bass=None, lead_clip_slot=None, kick_clip_slot=None, **parts):
        riff = riff or pat(*[[1, QUARTER]] * 4, grab=[True, False, True, False])
        bass = bass or pat([1, QUARTER], [2, QUARTER], [3, QUARTER], [None, QUARTER], octave=[5, 5, 5, None])
        data = with_parts(patterns={RIFF: riff, BASS: bass, **parts.pop(Section.PATTERNS, {})}, scenes=[{Section.TRACKS: {
            LEAD: {ClipSlotSetting.PATTERN: RIFF, ClipSlotSetting.GRAB_TRACK: KICK, **(lead_clip_slot or {})},
            KICK: {ClipSlotSetting.PATTERN: BASS, **(kick_clip_slot or {})},
        }}], **parts)
        return render_data(data)

    def lead(self, **parts):
        return clip(song=self.song(**parts), scene=1, track=LEAD)

    def test_marked_steps_play_what_the_other_track_plays_at_that_moment(self):
        self.assertEqual(pitches(self.lead()), [60, 48, 64, 48])

    def test_a_silent_track_gives_the_last_note_it_played(self):
        riff = pat(*[[1, QUARTER]] * 4, grab=[False, False, False, True])
        self.assertEqual(pitches(self.lead(riff=riff)), [48, 48, 48, 64])

    def test_nothing_played_yet_leaves_the_note_alone(self):
        bass = pat([None, HALF], [5, HALF], octave=[None, 5])
        self.assertEqual(pitches(self.lead(bass=bass)), [48, 48, 67, 48])

    def test_it_grabs_what_the_track_sounds_like_after_its_chain(self):
        bass = pat([1, 1], chord=['M'], octave=[5])
        found = self.lead(bass=bass, kick_clip_slot={ClipSlotSetting.CHAIN: X}, arps={UP: {ArpSetting.STEP: QUARTER}}, chains={X: [{GeneratorKind.ARP: UP}]})
        self.assertEqual(pitches(found), [60, 48, 67, 48])

    def test_a_chord_gives_its_lowest_note(self):
        bass = pat([1, 1], chord=['M'], octave=[5])
        found = self.lead(bass=bass).get_notes()[0]
        self.assertEqual(found.get_midi_number(), 60)

    def sounding(self, position):
        """Return the MIDI numbers a position of a clip sounds, lowest first: a chord's notes, or a note's one."""
        notes = position.get_notes() if isinstance(position, Chord) else [position]
        return sorted(note.get_midi_number() for note in notes)

    def test_a_grab_step_builds_its_named_chord_on_the_grabbed_note(self):
        # The user asked for this on 2026-11-09: the bass plays C, so the step's m7 is C, Eb, G and Bb, the root and three more.
        riff = pat([1, QUARTER], grab=[True], chord=[ChordSymbol.MINOR7])
        self.assertEqual(self.sounding(self.lead(riff=riff).get_notes()[0]), [60, 63, 67, 70])

    def test_a_grab_step_builds_its_scale_chord_from_the_clips_scale_on_the_grabbed_note(self):
        # The bass plays D on the second quarter, so the step's 7 in C major is D, F, A and C.
        riff = pat([1, QUARTER], [1, QUARTER], grab=[False, True], chord=[None, SCALE_SEVENTH])
        self.assertEqual(self.sounding(self.lead(riff=riff).get_notes()[1]), [62, 65, 69, 72])

    def test_a_scale_chord_on_a_grabbed_note_outside_the_scale_keeps_the_notes_distance_from_the_scale(self):
        # The bass plays C sharp, a half step above C, so each note of the triad is a half step above C, E and G.
        bass = pat([1, 1], octave=[5], accidental=[SHARP])
        riff = pat([1, QUARTER], grab=[True], chord=[SCALE_TRIAD])
        self.assertEqual(self.sounding(self.lead(riff=riff, bass=bass).get_notes()[0]), [61, 65, 68])

    def test_a_grab_step_with_no_chord_still_plays_one_note(self):
        riff = pat([1, QUARTER], [1, QUARTER], grab=[True, False], chord=[None, ChordSymbol.MAJOR])
        found = self.lead(riff=riff).get_notes()
        self.assertEqual(self.sounding(found[0]), [60])
        self.assertEqual(self.sounding(found[1]), [48, 52, 55])

    def test_with_nothing_grabbed_yet_the_step_plays_its_own_chord_on_its_own_note(self):
        bass = pat([None, HALF], [5, HALF], octave=[None, 5])
        riff = pat([1, HALF], [1, HALF], grab=[True, True], chord=[ChordSymbol.MAJOR, ChordSymbol.MAJOR])
        found = self.lead(riff=riff, bass=bass).get_notes()
        self.assertEqual(self.sounding(found[0]), [48, 52, 55])
        self.assertEqual(self.sounding(found[1]), [67, 71, 74])

    def test_every_ratchet_slice_of_a_grab_step_is_the_chord(self):
        riff = pat([1, QUARTER], grab=[True], chord=[ChordSymbol.MAJOR], ratchet=[2])
        found = self.lead(riff=riff).get_notes()
        self.assertEqual([self.sounding(position) for position in found], [[60, 64, 67], [60, 64, 67]])
        self.assertEqual(self.lead(riff=riff).total_length(), Fraction(1, 4))

    def test_a_note_of_the_chord_above_the_midi_range_is_left_out(self):
        # The bass plays the highest note there is, so the chord has nothing to add.
        bass = pat([5, 1], octave=[MAX_OCTAVE])
        riff = pat([1, QUARTER], grab=[True], chord=[ChordSymbol.MAJOR])
        self.assertEqual(self.sounding(self.lead(riff=riff, bass=bass).get_notes()[0]), [MAX_MIDI_NUMBER])

    def song_with_no_scale(self, chord):
        """Return the data of a song with no scale, where a step with no note of its own grabs from a drum track and holds a chord."""
        riff = {PatternSetting.STEPS: 1, Row.GRAB: [True], Row.CHORD: [chord]}
        drums = pat([NoteName.C, QUARTER], drum=True, octave=[5])
        data = with_parts(patterns={RIFF: riff, BASS: drums}, scenes=[{Section.TRACKS: {
            LEAD: {ClipSlotSetting.PATTERN: RIFF, ClipSlotSetting.GRAB_TRACK: KICK}, KICK: {ClipSlotSetting.PATTERN: BASS},
        }}])
        del data[SongSetting.SCALE]
        return data

    def test_without_a_scale_a_named_chord_is_built_on_the_grabbed_note(self):
        found = clip(song=render_data(self.song_with_no_scale(ChordSymbol.MAJOR)), scene=1, track=LEAD)
        self.assertEqual(self.sounding(found.get_notes()[0]), [60, 64, 67])

    def test_without_a_scale_a_scale_chord_on_a_grab_step_is_refused_as_a_degree_is(self):
        with self.assertRaises(SongFileError) as refused:
            render_data(self.song_with_no_scale(SCALE_TRIAD))
        self.assertIn(ERR_NO_SCALE.format(where=ERR_WHERE_PATTERN.format(name=RIFF), scene=1), str(refused.exception))

    def test_the_clip_keeps_its_rhythm_velocity_and_other_settings(self):
        riff = pat([1, EIGHTH], grab=[True], velocity=[33], ratchet=[2])
        found = self.lead(riff=riff)
        self.assertEqual(found.total_length(), Fraction(1, 8))
        events, _ = timed_events(clip=found, scale=None)
        self.assertEqual([event[2:] for event in events], [(60, 33), (60, 33)])

    def test_a_marked_step_with_no_note_of_its_own_plays_the_grabbed_note(self):
        # The user decided on 2026-11-08 that a grab works on an empty step, so a file can mark one with no degree.
        riff = pat([None, QUARTER], [1, QUARTER], grab=[True, False])
        self.assertEqual(pitches(self.lead(riff=riff)), [60, 48])

    def test_a_marked_step_with_no_note_of_its_own_is_silent_until_the_other_track_has_played(self):
        riff = pat([None, QUARTER], [1, QUARTER], grab=[True, False])
        bass = pat([None, QUARTER], [2, QUARTER], [3, QUARTER], [None, QUARTER], octave=[None, 5, 5, None])
        self.assertEqual(pitches(self.lead(riff=riff, bass=bass)), [48])

    def test_a_tie_on_a_marked_step_is_refused_like_a_tie_on_a_note(self):
        riff = pat([None, QUARTER], [None, QUARTER], **{Row.GRAB: [False, True], Row.TIE: [False, True]})
        data = with_parts(patterns={RIFF: riff}, scenes=[{Section.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: RIFF}}}])
        with self.assertRaises(SongFileError):
            song_from_data(data)

    def test_the_grab_track_must_be_a_real_track(self):
        data = with_parts(patterns={RIFF: pat([1, QUARTER])}, scenes=[{Section.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: RIFF, ClipSlotSetting.GRAB_TRACK: NOPE}}}])
        with self.assertRaises(SongFileError):
            song_from_data(data)

    def test_marks_without_a_grab_track_do_nothing(self):
        data = with_parts(patterns={RIFF: pat([1, QUARTER], grab=[True])}, scenes=[{Section.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: RIFF}}}])
        self.assertEqual(pitches(clip(song=render_data(data), scene=1, track=LEAD)), [48])

    def test_it_follows_the_other_track_across_repeats(self):
        found = self.lead(lead_clip_slot={ClipSlotSetting.REPEAT: 2}, kick_clip_slot={ClipSlotSetting.LOOP: True})
        self.assertEqual(pitches(found), [60, 48, 64, 48, 60, 48, 64, 48])

    def test_it_can_grab_from_a_track_that_loops_to_fill_the_scene(self):
        bass = pat([5, HALF], octave=[5])
        found = self.lead(bass=bass, lead_clip_slot={ClipSlotSetting.REPEAT: 2}, kick_clip_slot={ClipSlotSetting.LOOP: True})
        self.assertEqual(pitches(found), [67, 48, 67, 48, 67, 48, 67, 48])

    def test_a_grab_follows_a_grab(self):
        data = with_parts(
            tracks={LEAD: {}, KICK: {}, PAD: {}},
            patterns={RIFF: pat([1, QUARTER], grab=[True]), TOP: pat([5, QUARTER], octave=[5])},
            scenes=[{Section.TRACKS: {
                LEAD: {ClipSlotSetting.PATTERN: RIFF, ClipSlotSetting.GRAB_TRACK: KICK},
                KICK: {ClipSlotSetting.PATTERN: RIFF, ClipSlotSetting.GRAB_TRACK: PAD},
                PAD: {ClipSlotSetting.PATTERN: TOP},
            }}],
        )
        self.assertEqual(pitches(clip(song=render_data(data), scene=1, track=LEAD)), [67])

    def test_grabbing_in_a_circle_stops_with_a_message(self):
        with self.assertRaises(SongFileError) as raised:
            self.song(kick_clip_slot={ClipSlotSetting.GRAB_TRACK: LEAD})
        self.assertIn('go round in a circle (lead → kick → lead)', str(raised.exception))

    def test_a_muted_track_can_still_be_grabbed_from(self):
        song = self.song(tracks={LEAD: {}, KICK: {TrackSetting.MUTE: True}})
        self.assertEqual([track.get_mute() for track in song.get_columns()], [False, True])
        self.assertEqual(pitches(clip(song=song, scene=1, track=LEAD)), [60, 48, 64, 48])

    def test_mute_must_be_true_or_false(self):
        with self.assertRaisesRegex(SongFileError, 'mute must be true or false'):
            self.song(tracks={LEAD: {}, KICK: {TrackSetting.MUTE: YES}})

    def test_transpose_moves_a_grabbed_note_along_this_tracks_scale(self):
        found = self.lead(tracks={LEAD: {TrackSetting.TRANSPOSE: 1}, KICK: {}})
        self.assertEqual(pitches(found)[:2], [62, 50])

    def test_a_morph_target_does_not_grab(self):
        riff = pat([1, QUARTER], grab=[True])
        found = self.lead(riff=riff, lead_clip_slot={ClipSlotSetting.REPEAT: 2, ClipSlotSetting.MORPH_TO: RIFF, ClipSlotSetting.MORPH_STYLE: morph_style_name(BlendMode.LEFT)}, kick_clip_slot={ClipSlotSetting.LOOP: True})
        self.assertEqual(pitches(found), [60, 48])

    def test_the_track_must_exist_and_be_another_one(self):
        for other in [NOPE, LEAD]:
            with self.subTest(other=other), self.assertRaises(SongFileError):
                self.song(lead_clip_slot={ClipSlotSetting.GRAB_TRACK: other})

    def test_notes_from_is_gone(self):
        with self.assertRaises(SongFileError):
            self.song(lead_clip_slot={NOTES_FROM: BASS})

    def test_grab_must_be_true_or_false(self):
        with self.assertRaises(SongFileError):
            song_from_data(with_parts(patterns={X: pat([1, 1], grab=[YES])}))
