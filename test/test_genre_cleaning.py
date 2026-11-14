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

"""The tidying of a song that came from anywhere, on tracks made up here: notes written twice, a note left sounding, a track
of a few notes, sound effects, percussion on ordinary channels joined to the drums, what is doubtful about a kit, and a MIDI
file's length by every tempo it passes through, with the time signature it holds longest."""

import tempfile
import unittest
from pathlib import Path

import mido

from llamatron.genres.hearing.cleaning import (
    COWBELL, DRUM_HIT_BEATS, EFFECT_PROGRAMS, ENOUGH_HITS, JUNK_NOTES, KICK, PERCUSSION_PROGRAMS, SNARE, STUCK_BARS, WORTH_SAYING, drum_named, is_percussion, tidied,
)
from llamatron.genres.hearing.midi_file import performance_of_midi, seconds_at
from llamatron.genres.hearing.performance import PlayedNote, PlayedTrack
from llamatron.strings.genres import MSG_DOUBT_NO_KICK, MSG_DOUBT_ONE_DRUM, MSG_DOUBT_STUCK

BEATS_PER_BAR = 4
BARS = 16
VELOCITY = 90
LEAD_PROGRAM = 81
BASS_PROGRAM = 34
HIGH = 76
LOW = 36
SCALE = (60, 62, 64, 65, 67, 69, 71, 72)
HAT = 42
TICKS = 480
FAST = 120
SLOW = 60
LEAD = 'lead'
SNARE_NAME = 'Snare'
BASS_DRUM_NAME = 'Bass Drum'
BASS_NAME = 'Bass'
DRUMS = 'Drums'
EFFECT_NAME = 'shout'
CREDIT = 'credit'
WALTZ = (3, 4)
COMMON = (4, 4)
WALTZ_TEXT = '3/4'


def note(*, start, pitch, length=0.5):
    return PlayedNote(start=start, end=start + length, pitch=pitch, velocity=VELOCITY)


def melody(*, name=LEAD, sound=LEAD_PROGRAM):
    return PlayedTrack(name=name, drum=False, sound=sound, notes=tuple(note(start=float(beat), pitch=SCALE[beat % len(SCALE)]) for beat in range(BARS * BEATS_PER_BAR)))


def one_pitch(*, name, pitch, sound=LEAD_PROGRAM, drum=False):
    return PlayedTrack(name=name, drum=drum, sound=sound, notes=tuple(note(start=float(beat), pitch=pitch) for beat in range(BARS * BEATS_PER_BAR)))


def tidy(*tracks):
    return tidied(tracks=tracks, beats_per_bar=BEATS_PER_BAR)


def drums_of(tracks):
    return next(track for track in tracks if track.drum)


class TestTidying(unittest.TestCase):
    __slots__ = ()

    def test_a_clean_song_is_left_as_it_is_with_no_doubts(self):
        kit = PlayedTrack(name=DRUMS, drum=True, sound=None, notes=tuple(note(start=float(beat), pitch=(KICK, HAT)[beat % 2]) for beat in range(BARS * BEATS_PER_BAR)))
        tracks, doubts = tidy(melody(), kit)
        self.assertEqual(doubts, ())
        self.assertEqual([len(track.notes) for track in tracks], [len(melody().notes), len(kit.notes)])

    def test_notes_written_twice_are_counted_once_and_said_when_many(self):
        doubled = PlayedTrack(name=LEAD, drum=False, sound=LEAD_PROGRAM, notes=tuple(sorted(melody().notes + melody().notes, key=lambda each: each.begins)))
        tracks, doubts = tidy(doubled)
        self.assertEqual(len(tracks[0].notes), len(melody().notes))
        self.assertGreaterEqual(len(melody().notes), WORTH_SAYING)
        self.assertEqual(len(doubts), 1)

    def test_a_note_left_sounding_is_cut_and_a_long_held_note_is_kept(self):
        too_long = (STUCK_BARS + 1) * BEATS_PER_BAR
        held = STUCK_BARS * BEATS_PER_BAR
        stuck = PlayedTrack(name=LEAD, drum=False, sound=LEAD_PROGRAM, notes=melody().notes + (note(start=0.0, pitch=HIGH, length=too_long), note(start=0.0, pitch=HIGH + 1, length=held)))
        tracks, doubts = tidy(stuck)
        lengths = sorted(each.length() for each in tracks[0].notes)
        self.assertEqual(lengths[-1], held)
        self.assertEqual(lengths[-2], BEATS_PER_BAR)
        self.assertEqual(doubts, (MSG_DOUBT_STUCK.format(count=1),))

    def test_a_short_pieces_small_parts_are_kept(self):
        small = PlayedTrack(name=CREDIT, drum=False, sound=LEAD_PROGRAM, notes=tuple(note(start=float(beat), pitch=HIGH) for beat in range(JUNK_NOTES)))
        other = PlayedTrack(name=LEAD, drum=False, sound=BASS_PROGRAM, notes=tuple(note(start=float(beat), pitch=LOW) for beat in range(JUNK_NOTES * 2)))
        tracks, doubts = tidy(small, other)
        self.assertEqual(len(tracks), 2)
        self.assertEqual(doubts, ())

    def test_a_drum_hit_left_sounding_is_held_to_a_beat(self):
        kit = one_pitch(name=DRUMS, pitch=KICK, drum=True)
        kit = PlayedTrack(name=DRUMS, drum=True, sound=None, notes=kit.notes + (note(start=1.0, pitch=SNARE, length=BARS * BEATS_PER_BAR),))
        tracks, _ = tidy(melody(), kit)
        self.assertEqual(max(each.length() for each in drums_of(tracks).notes), DRUM_HIT_BEATS)

    def test_a_track_of_a_few_notes_and_a_sound_effect_are_left_out(self):
        credit = PlayedTrack(name=CREDIT, drum=False, sound=LEAD_PROGRAM, notes=tuple(note(start=float(beat), pitch=HIGH) for beat in range(JUNK_NOTES)))
        effect = melody(name=EFFECT_NAME, sound=EFFECT_PROGRAMS[0])
        tracks, doubts = tidy(melody(), credit, effect)
        self.assertEqual([track.name for track in tracks], [LEAD])
        self.assertEqual(len(doubts), 2)
        self.assertIn(EFFECT_NAME, doubts[1])

    def test_drums_on_ordinary_tracks_named_for_drums_become_one_kit(self):
        tracks, doubts = tidy(melody(), one_pitch(name=SNARE_NAME, pitch=HIGH), one_pitch(name=BASS_DRUM_NAME, pitch=HIGH - 1))
        self.assertEqual([track.name for track in tracks if not track.drum], [LEAD])
        self.assertEqual({each.pitch for each in drums_of(tracks).notes}, {SNARE, KICK})
        self.assertEqual(len(doubts), 1)
        self.assertIn(SNARE_NAME, doubts[0])

    def test_a_percussive_program_and_one_high_pitch_struck_often_are_percussion(self):
        self.assertTrue(is_percussion(melody(sound=PERCUSSION_PROGRAMS[0])))
        self.assertTrue(is_percussion(one_pitch(name=LEAD, pitch=HIGH)))
        self.assertGreaterEqual(len(one_pitch(name=LEAD, pitch=HIGH).notes), ENOUGH_HITS)
        tracks, _ = tidy(melody(), one_pitch(name=LEAD, pitch=HIGH))
        self.assertEqual({each.pitch for each in drums_of(tracks).notes}, {COWBELL})

    def test_a_bass_on_one_low_note_and_a_track_named_bass_stay_parts(self):
        pedal = one_pitch(name=BASS_NAME, pitch=LOW, sound=BASS_PROGRAM)
        self.assertFalse(is_percussion(pedal))
        self.assertFalse(is_percussion(melody(name=BASS_NAME, sound=BASS_PROGRAM)))
        self.assertIsNone(drum_named(LEAD))
        self.assertEqual(drum_named(BASS_DRUM_NAME), KICK)

    def test_a_kit_of_one_drum_and_a_kit_with_no_kick_are_doubted(self):
        _, one = tidy(melody(), one_pitch(name=DRUMS, pitch=HAT, drum=True))
        self.assertEqual(one, (MSG_DOUBT_ONE_DRUM,))
        kickless = PlayedTrack(name=DRUMS, drum=True, sound=None, notes=tuple(note(start=float(beat), pitch=(SNARE, HAT)[beat % 2]) for beat in range(BARS)))
        _, none = tidy(melody(), kickless)
        self.assertEqual(none, (MSG_DOUBT_NO_KICK,))


def changing_midi(path):
    """Write a MIDI file whose tempo halves halfway and whose time signature is 4/4 for a bar before a waltz for the rest."""
    song = mido.MidiFile(ticks_per_beat=TICKS)
    track = mido.MidiTrack()
    song.tracks.append(track)
    beats = BARS * BEATS_PER_BAR
    track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(FAST), time=0))
    track.append(mido.MetaMessage('time_signature', numerator=COMMON[0], denominator=COMMON[1], time=0))
    track.append(mido.Message('program_change', program=LEAD_PROGRAM - 1, channel=0, time=0))
    for beat in range(beats):
        if beat == BEATS_PER_BAR:
            track.append(mido.MetaMessage('time_signature', numerator=WALTZ[0], denominator=WALTZ[1], time=0))
        if beat == beats // 2:
            track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(SLOW), time=0))
        track.append(mido.Message('note_on', note=SCALE[beat % len(SCALE)], velocity=VELOCITY, channel=0, time=0))
        track.append(mido.Message('note_off', note=SCALE[beat % len(SCALE)], velocity=0, channel=0, time=TICKS))
    song.save(str(path))


class TestAMidiFileThatChanges(unittest.TestCase):
    __slots__ = ()

    def test_the_length_follows_every_tempo_and_the_time_signature_is_the_one_held_longest(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'changing.mid'
            changing_midi(path)
            performance = performance_of_midi(path)
        half = BARS * BEATS_PER_BAR // 2
        self.assertAlmostEqual(performance.seconds, half * 60 / FAST + half * 60 / SLOW)
        self.assertEqual(performance.meter, WALTZ_TEXT)
        self.assertEqual(len(performance.doubts), 2)
        self.assertIn(WALTZ_TEXT, performance.doubts[1])

    def test_seconds_before_any_tempo_are_counted_at_the_default(self):
        self.assertAlmostEqual(seconds_at(tempos=[], tick=TICKS * 2, ticks=TICKS), 1.0)
        self.assertAlmostEqual(seconds_at(tempos=[(TICKS, SLOW)], tick=TICKS * 2, ticks=TICKS), 1.5)


if __name__ == '__main__':
    unittest.main()
