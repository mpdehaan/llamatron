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
"""The genre library's analyzer, on songs written note by note so that each measure has a known answer: roles, keys and chords,
grooves and swing, melodic motion and expectation, hooks, the sawtooth of unprepared jumps, and a demo measured end to end
from its render."""

import os
import unittest

from llamatron.composition.setlist import Setlist
from llamatron.genres.hearing.harmony import MAJOR, Key, chord_of, chromatic_of, fifths_between, travel_of
from llamatron.genres.hearing.lines import bass_of, bottom_line, expectation_of, is_pentatonic, melody_of, phrases_of, top_line, vocal_of
from llamatron.genres.hearing.transitions import Sign
from llamatron.genres.hearing.performance import Performance, PlayedNote, PlayedTrack, performance_of
from llamatron.genres.hearing.profile import LOW_REGISTER, bass_track, profile_of_performance
from llamatron.genres.hearing.rhythm import ghosts_of, swing_of, track_voices
from llamatron.genres.measures.drum_patterns import Voice
from llamatron.genres.hearing.roles import roles_of
from llamatron.genres.hearing.shape import bar_energy, shape_of, span_of
from llamatron.genres.hearing.sonorities import BAR_SPAN, CHORDAL, PLANING, RICH, WHOLE_TONE, sonorities_of
from llamatron.genres.measures.traits import TRAITS, BassMotion, Role, Trait

BEATS = 4
TEMPO = 120
METER = '4/4'
VELOCITY = 100
QUIET = 20
C = 60
C_MAJOR_SCALE = (60, 62, 64, 65, 67, 69, 71, 72)
KICK = 36
SNARE = 38
HAT = 42
BASS_NOTE = 36
SWUNG = 2 / 3
EXAMPLES = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, 'examples')
DEMO = os.path.join(EXAMPLES, 'by_genre', 'rock', 'green_men.yml')
SONG = 'test'
POWER_CHORD = '5'
# A gap between two keys struck as one chord by a person, in beats.
HAIR = 0.02
TRIAD = (0, 4, 7)
MINOR_TRIAD = (0, 3, 7)
SEVENTH = (0, 4, 7, 10)
WHOLE_TONE_NOTES = 6
OCTAVE = 12
# A left-hand note just below middle C, high enough that a line of it and a high tune averages above the low register.
LEFT_HAND_NOTE = 57
FIGURE = (0, 2, 4, 2)
SCALE_UP = (60, 62, 64, 65, 67, 69, 71, 72)
# A tune on the anhemitonic pentatonic scale, C D E G A, moving by its steps, minor thirds among them.
PENTATONIC = (60, 62, 64, 67, 69, 72, 69, 67, 64, 62)
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

    def test_roles_are_found_from_notes_alone(self):
        song = performance(tracks=[track(name='a', notes=rock_drums(4), drum=True), track(name='b', notes=root_bass(4)), track(name='c', notes=scale_tune(4))], bars=4)
        roles = {each.name: role for each, role in roles_of(song).items()}
        self.assertEqual(roles, {'a': Role.DRUMS, 'b': Role.BASS, 'c': Role.LEAD})

    def test_a_stepwise_tune_moves_by_step_and_arches(self):
        line = scale_tune(4)
        melody, phrases = melody_of(line=line, beats_per_bar=BEATS)
        self.assertEqual(melody.steps, 1.0)
        self.assertEqual(len(phrases), 4)
        self.assertEqual(melody.arches, 1.0)

    def test_a_leap_that_turns_back_counts_as_a_reversal(self):
        line = [note(start=0, pitch=C), note(start=0.5, pitch=C + 7), note(start=1, pitch=C + 5), note(start=1.5, pitch=C + 4)]
        melody, _ = melody_of(line=line, beats_per_bar=BEATS)
        self.assertEqual(melody.reversals, 1.0)

    def test_a_figure_repeated_grows_more_predictable(self):
        line = [note(start=bar * BEATS + place * 0.5, pitch=C + step) for bar in range(8) for place, step in enumerate(FIGURE)]
        phrases = phrases_of(line)
        expectation = expectation_of(phrases=phrases, line=line, bars_heard=0.9)
        random_line = [note(start=place * 0.5, pitch=C + (place * 7) % 19) for place in range(32)]
        surprised = expectation_of(phrases=phrases_of(random_line), line=random_line, bars_heard=0.0)
        self.assertLess(expectation.surprise, surprised.surprise)

    def test_offbeats_at_two_thirds_of_the_beat_swing(self):
        swung = [note(start=beat + place, pitch=C) for beat in range(8) for place in (0, SWUNG)]
        self.assertAlmostEqual(swing_of(performance(tracks=[track(name='a', notes=swung)], bars=2)), SWUNG, places=2)

    def test_a_jump_with_nothing_preparing_it_is_found(self):
        quiet = [note(start=bar * BEATS, length=4, pitch=C, velocity=QUIET) for bar in range(4)]
        loud = [note(start=bar * BEATS + place, pitch=C + place, velocity=VELOCITY) for bar in range(4, 8) for place in range(4)]
        drums = [note(start=bar * BEATS + place, pitch=KICK) for bar in range(4, 8) for place in range(4)]
        song = performance(tracks=[track(name='a', notes=quiet + loud), track(name='b', notes=drums, drum=True)], bars=8)
        levels, _ = bar_energy(performance=song)
        self.assertIn(4, shape_of(levels=levels, performance=song).jumps)

    def test_spacing_finds_the_bass_an_octave_or_more_below_and_mud_down_low(self):
        song = performance(tracks=[track(name='b', notes=root_bass(4)), track(name='c', notes=scale_tune(4))], bars=4)
        spacing = profile_of_performance(performance=song, name=SONG).spacing
        self.assertGreaterEqual(spacing.bass_to_lead, 12)
        self.assertEqual(spacing.mud, 0.0)
        muddy = [note(start=beat, length=1, pitch=BASS_NOTE + 2) for beat in range(16)]
        crowded = performance(tracks=[track(name='b', notes=root_bass(4)), track(name='m', notes=muddy), track(name='c', notes=scale_tune(4))], bars=4)
        self.assertGreater(profile_of_performance(performance=crowded, name=SONG).spacing.mud, 0.5)
        high = [note(start=beat, length=1, pitch=BASS_NOTE + 40) for beat in range(16)]
        hollow = performance(tracks=[track(name='b', notes=root_bass(4)), track(name='h', notes=high)], bars=4)
        self.assertEqual(profile_of_performance(performance=hollow, name=SONG).spacing.hollow, 1.0)

    def test_a_song_written_note_by_note_is_measured_in_every_trait(self):
        song = performance(tracks=[track(name='a', notes=rock_drums(8), drum=True), track(name='b', notes=root_bass(8)), track(name='c', notes=scale_tune(8))], bars=8)
        profile = profile_of_performance(performance=song, name=SONG)
        for trait in TRAITS:
            if trait not in UNMEASURED_TRAITS:
                self.assertIsNotNone(profile.trait(trait), trait)
        self.assertEqual(profile.trait(Trait.BASS).motion, BassMotion.ROOTS)
        self.assertGreater(profile.trait(Trait.HOOK).strength, 0.5)
        self.assertTrue(profile.trait(Trait.DRUMS).main().has_backbeat())


class TestGhostsAndLoneNotes(unittest.TestCase):

    def test_a_snares_quiet_notes_between_its_backbeats_are_ghosts(self):
        notes = rock_drums(4) + [note(start=bar * BEATS + 1.5, pitch=SNARE, velocity=QUIET) for bar in range(4)]
        played = performance(tracks=[track(name='kit', notes=notes, drum=True)], bars=4)
        self.assertGreater(ghosts_of(played), 0.0)

    def test_a_voice_softer_than_another_and_a_quiet_bar_are_not_ghosts(self):
        notes = [each for each in rock_drums(2) if each.pitch != HAT]
        notes += [note(start=place * 0.5, pitch=HAT, velocity=QUIET) for place in range(16)]
        notes += [note(start=2 * BEATS + beat, pitch=KICK, velocity=QUIET) for beat in range(BEATS)]
        played = performance(tracks=[track(name='kit', notes=notes, drum=True)], bars=3)
        self.assertEqual(ghosts_of(played), 0.0)

    def test_one_note_alone_is_no_chord_and_two_are(self):
        alone = [0.0] * 12
        alone[7] = 1.0
        self.assertIsNone(chord_of(alone))
        fifth = list(alone)
        fifth[2] = 1.0
        self.assertEqual(chord_of(fifth), (7, POWER_CHORD))


class TestSonorities(unittest.TestCase):
    """What sounds together: rich chords, chords moved in parallel, whole-tone time, chords struck at once and the left hand's reach."""

    def chords(self, *shapes):
        return [note(start=place * BEATS, length=BEATS, pitch=root + step) for place, (root, steps) in enumerate(shapes) for step in steps]

    def heard(self, notes, *, bars):
        return sonorities_of(performance(tracks=[track(name='piano', notes=notes)], bars=bars))

    def test_a_song_with_no_pitched_notes_has_none(self):
        self.assertEqual(sonorities_of(performance(tracks=[], bars=1)), {})

    def test_triads_are_not_rich_and_sevenths_are(self):
        self.assertEqual(self.heard(self.chords((C, TRIAD), (C + 5, TRIAD)), bars=2)[RICH], 0.0)
        self.assertEqual(self.heard(self.chords((C, SEVENTH), (C + 5, SEVENTH)), bars=2)[RICH], 1.0)

    def test_the_same_chord_carried_to_another_pitch_is_planing_and_a_changed_or_repeated_chord_is_not(self):
        self.assertEqual(self.heard(self.chords((C, TRIAD), (C + 2, TRIAD), (C + 4, TRIAD)), bars=3)[PLANING], 1.0)
        self.assertEqual(self.heard(self.chords((C, TRIAD), (C + 2, MINOR_TRIAD), (C + 2, MINOR_TRIAD)), bars=3)[PLANING], 0.0)
        self.assertIsNone(self.heard(scale_tune(2), bars=2)[PLANING])

    def test_a_whole_tone_stretch_is_found_and_a_major_scale_is_not(self):
        whole = [note(start=beat, pitch=C + 2 * (beat % WHOLE_TONE_NOTES)) for beat in range(2 * BEATS)]
        self.assertEqual(self.heard(whole, bars=2)[WHOLE_TONE], 1.0)
        self.assertEqual(self.heard(scale_tune(2), bars=2)[WHOLE_TONE], 0.0)

    def test_chords_struck_at_once_are_counted_against_single_notes(self):
        self.assertEqual(self.heard(self.chords((C, TRIAD), (C + 5, TRIAD)), bars=2)[CHORDAL], 1.0)
        self.assertEqual(self.heard(scale_tune(2), bars=2)[CHORDAL], 0.0)

    def test_the_left_hand_reaches_as_far_as_its_notes_in_a_bar_and_nothing_with_one_note_a_bar(self):
        wide = [note(start=bar * BEATS + beat, pitch=BASS_NOTE + (OCTAVE if beat else 0)) for bar in range(2) for beat in range(2)]
        self.assertEqual(self.heard(wide, bars=2)[BAR_SPAN], OCTAVE)
        self.assertIsNone(self.heard([note(start=0, pitch=BASS_NOTE), note(start=BEATS, pitch=BASS_NOTE + 2)], bars=2)[BAR_SPAN])

    def test_a_profile_carries_them_on_its_harmony_bass_and_texture(self):
        notes = self.chords((C, SEVENTH), (C + 2, SEVENTH)) + [note(start=bar * BEATS + beat, pitch=BASS_NOTE + (OCTAVE if beat else 0)) for bar in range(2) for beat in range(2)]
        profile = profile_of_performance(performance=performance(tracks=[track(name='piano', notes=notes)], bars=2), name=SONG)
        self.assertEqual(profile.trait(Trait.HARMONY).rich, 1.0)
        self.assertEqual(profile.trait(Trait.HARMONY).whole_tone, 0.0)
        self.assertIsNotNone(profile.trait(Trait.TEXTURE).chordal)


class TestOuterLines(unittest.TestCase):
    """A part's top and bottom lines as the skyline of what sounds."""

    def test_a_tune_over_an_accompaniment_in_one_part_is_its_top_line_and_the_left_hand_its_bottom(self):
        tune = [note(start=bar * BEATS, length=BEATS, pitch=C + OCTAVE + bar) for bar in range(2)]
        left = [note(start=bar * BEATS + beat, length=0.5, pitch=BASS_NOTE + beat) for bar in range(2) for beat in range(BEATS)]
        part = track(name='piano', notes=tune + left)
        self.assertEqual([each.pitch for each in top_line(part)], [each.pitch for each in tune])
        self.assertEqual([each.pitch for each in bottom_line(part)], [each.pitch for each in left])

    def test_notes_struck_a_hair_apart_start_together_as_a_person_plays_them(self):
        played = [note(start=0, pitch=C), note(start=HAIR, pitch=C + 4), note(start=2 * HAIR, pitch=C + 7), note(start=1, pitch=C + 2)]
        part = track(name='piano', notes=played)
        self.assertEqual([each.pitch for each in top_line(part)], [C + 7, C + 2])
        self.assertEqual([each.pitch for each in bottom_line(part)], [C, C + 2])

    def test_a_line_alone_is_itself(self):
        part = track(name='tune', notes=scale_tune(2))
        self.assertEqual(top_line(part), list(part.notes))


class TestWhatThePeriodsDifferIn(unittest.TestCase):
    """The measures the classical periods differ in: notes outside the key, how far the keys wander, the bass's range and the
    range of all the notes."""

    def test_a_tune_in_its_key_has_no_note_outside_it_and_one_with_sharps_has(self):
        plain = performance(tracks=[track(name='tune', notes=scale_tune(8))], bars=8)
        keys = [Key(tonic=0, mode=MAJOR)]
        self.assertEqual(chromatic_of(performance=plain, keys=keys), 0.0)
        sharps = [note(start=bar * BEATS + 3.5, pitch=C + 1) for bar in range(8)]
        coloured = performance(tracks=[track(name='tune', notes=scale_tune(8) + sharps)], bars=8)
        self.assertGreater(chromatic_of(performance=coloured, keys=keys), 0.0)
        self.assertIsNone(chromatic_of(performance=performance(tracks=[], bars=1), keys=keys))

    def test_keys_a_fifth_apart_travel_one_and_keys_a_third_apart_further(self):
        self.assertEqual(fifths_between(old=0, new=7), 1)
        self.assertEqual(fifths_between(old=0, new=5), 1)
        self.assertEqual(fifths_between(old=0, new=4), 4)
        home = Key(tonic=0, mode=MAJOR)
        self.assertEqual(travel_of([home, home, home]), 0.0)
        self.assertEqual(travel_of([home, Key(tonic=7, mode=MAJOR), Key(tonic=11, mode=MAJOR)]), 2.5)

    def test_a_bass_on_one_note_reaches_nothing_and_one_over_an_octave_twelve(self):
        still = performance(tracks=[track(name='tune', notes=scale_tune(4)), track(name='low', notes=root_bass(4))], bars=4)
        self.assertEqual(profile_of_performance(performance=still, name=SONG).trait(Trait.BASS).reach, 0)
        leaping = [note(start=bar * BEATS + beat, length=1, pitch=BASS_NOTE + (OCTAVE if beat % 2 else 0)) for bar in range(4) for beat in range(BEATS)]
        wide = performance(tracks=[track(name='tune', notes=scale_tune(4)), track(name='low', notes=leaping)], bars=4)
        self.assertEqual(profile_of_performance(performance=wide, name=SONG).trait(Trait.BASS).reach, OCTAVE)

    def test_the_span_of_a_songs_notes_leaves_out_a_stray_one(self):
        tune = scale_tune(8)
        played = performance(tracks=[track(name='tune', notes=tune + [note(start=0, pitch=C + 4 * OCTAVE)])], bars=8)
        self.assertLess(span_of(played), 2 * OCTAVE)
        self.assertIsNone(span_of(performance(tracks=[], bars=1)))


class TestSceneChanges(unittest.TestCase):
    """At each scene's start: how abrupt the change is, and what prepares it."""

    def song(self, *, pickup):
        quiet = [note(start=bar * BEATS, length=4, pitch=C, velocity=QUIET) for bar in range(4)]
        loud = [note(start=bar * BEATS + place, pitch=C + 12 + place, velocity=VELOCITY) for bar in range(4, 8) for place in range(4)]
        lead_in = [note(start=15.5, length=0.5, pitch=C + 11)] if pickup else []
        drums = [note(start=bar * BEATS + place, pitch=KICK) for bar in range(4, 8) for place in range(4)]
        return Performance(tracks=(track(name='a', notes=quiet + loud + lead_in), track(name='b', notes=drums, drum=True)), tempo=TEMPO, meter=METER,
                           beats_per_bar=BEATS, length=8 * BEATS, scene_starts=(0.0, 16.0))

    def test_a_jump_with_nothing_preparing_it_is_unprepared(self):
        changes = profile_of_performance(performance=self.song(pickup=False), name=SONG).transitions
        self.assertEqual(len(changes), 1)
        self.assertTrue(changes[0].is_unprepared_jump())

    def test_a_pickup_stepping_across_the_bar_line_prepares_it(self):
        change = profile_of_performance(performance=self.song(pickup=True), name=SONG).transitions[0]
        self.assertIn(Sign.PICKUP, change.signs)
        self.assertFalse(change.is_unprepared_jump())


class TestVoiceLeading(unittest.TestCase):

    def test_lines_moving_apart_are_contrary_and_power_chords_are_parallel_fifths(self):
        rising = [note(start=place, pitch=C + place) for place in range(12)]
        falling = [note(start=place, pitch=C - 12 - place) for place in range(12)]
        fifths = [note(start=place, pitch=C - 7 + place) for place in range(12)]
        apart = profile_of_performance(performance=performance(tracks=[track(name='a', notes=rising), track(name='b', notes=falling)], bars=3), name=SONG)
        together = profile_of_performance(performance=performance(tracks=[track(name='a', notes=rising), track(name='b', notes=fifths)], bars=3), name=SONG)
        self.assertEqual(apart.trait(Trait.VOICE_LEADING).contrary, 1.0)
        self.assertEqual(together.trait(Trait.VOICE_LEADING).parallels, 100.0)


class TestBassMotion(unittest.TestCase):

    def test_a_note_held_through_bars_is_a_pedal_and_one_moving_with_the_chords_a_root_bass(self):
        pedal = [note(start=place * 0.5, pitch=BASS_NOTE) for place in range(64)]
        roots = [note(start=bar * BEATS + place * 0.5, pitch=BASS_NOTE + (5 if bar % 2 else 0)) for bar in range(8) for place in range(8)]
        song = performance(tracks=[track(name='p', notes=pedal)], bars=8)
        self.assertEqual(bass_of(track=song.tracks[0], performance=song).motion, BassMotion.PEDAL)
        moving = performance(tracks=[track(name='r', notes=roots)], bars=8)
        self.assertEqual(bass_of(track=moving.tracks[0], performance=moving).motion, BassMotion.ROOTS)


class TestDrumVoices(unittest.TestCase):
    """A drum track may play any note, so its voice is found from its name, then from General MIDI's notes, then its rhythm."""

    def test_a_track_named_for_its_voice_plays_that_voice_whatever_its_note(self):
        named = track(name='Kick 1', notes=[note(start=beat, pitch=C) for beat in range(8)], drum=True)
        self.assertEqual(track_voices(track=named, beats_per_bar=BEATS)(C), Voice.KICK)

    def test_a_kit_on_general_midi_notes_is_sorted_by_note(self):
        kit = track(name='drums', notes=rock_drums(2), drum=True)
        voice_of = track_voices(track=kit, beats_per_bar=BEATS)
        self.assertEqual((voice_of(KICK), voice_of(SNARE), voice_of(HAT)), (Voice.KICK, Voice.SNARE, Voice.HATS))

    def test_an_unnamed_one_voice_track_is_judged_by_where_it_hits(self):
        backbeat = track(name='perc', notes=[note(start=bar * BEATS + beat, pitch=C) for bar in range(4) for beat in (1, 3)], drum=True)
        downbeat = track(name='perc', notes=[note(start=bar * BEATS + beat, pitch=C) for bar in range(4) for beat in (0, 2)], drum=True)
        offbeat = track(name='perc', notes=[note(start=place * 0.5, pitch=C) for place in range(32)], drum=True)
        self.assertEqual(track_voices(track=backbeat, beats_per_bar=BEATS)(C), Voice.SNARE)
        self.assertEqual(track_voices(track=downbeat, beats_per_bar=BEATS)(C), Voice.KICK)
        self.assertEqual(track_voices(track=offbeat, beats_per_bar=BEATS)(C), Voice.HATS)


class TestDemoMeasured(unittest.TestCase):

    def test_a_demo_is_measured_from_its_render(self):
        setlist = Setlist.read_file(DEMO)
        name = setlist.get_song_names()[0]
        profile = profile_of_performance(performance=performance_of(setlist.get_song(name)), name=name)
        self.assertEqual(profile.trait(Trait.TEMPO).low, setlist.get_song(name).get_tempo())
        self.assertIn(Role.LEAD, profile.roles.values())
        self.assertIsNotNone(profile.trait(Trait.DRUMS))



class TestLeftHandBass(unittest.TestCase):
    """A piano's left hand heard as the bass when no part plays one, and an oom-pah line read as one."""

    def left_hand(self, bars):
        notes = []
        for beat in range(bars * BEATS):
            notes.append(note(start=beat, length=0.5, pitch=BASS_NOTE + (7 if beat % 2 else 0)))
            notes += [note(start=beat + 0.5, length=0.5, pitch=pitch) for pitch in (BASS_NOTE + 16, BASS_NOTE + 19, BASS_NOTE + 24)]
        return notes

    def test_an_oom_pah_left_hand_is_heard_as_an_oom_pah_bass(self):
        piano = performance(tracks=[track(name='right', notes=scale_tune(4)), track(name='left', notes=self.left_hand(4))], bars=4)
        profile = profile_of_performance(performance=piano, name=SONG)
        self.assertEqual(profile.trait(Trait.BASS).motion, BassMotion.OOM_PAH)

    def test_the_lowest_line_of_the_lowest_part_stands_in_for_a_missing_bass(self):
        piano = performance(tracks=[track(name='right', notes=scale_tune(4)), track(name='left', notes=self.left_hand(4))], bars=4)
        roles = profile_of_performance(performance=piano, name=SONG).roles
        found = bass_track(roles=roles, performance=piano)
        self.assertIsNotNone(found)
        self.assertEqual(min(note.pitch for note in found.notes), BASS_NOTE)
        self.assertEqual(len(bottom_line(track(name='left', notes=self.left_hand(1)))), BEATS * 2)

    def test_two_hands_written_in_one_part_give_their_notes_below_middle_c_as_the_bass(self):
        high_tune = [note(start=bar * BEATS + place + 0.5, pitch=C + OCTAVE + place) for bar in range(4) for place in range(BEATS)]
        left = [note(start=bar * BEATS + beat, length=0.5, pitch=LEFT_HAND_NOTE) for bar in range(4) for beat in (0, 2)]
        piano = performance(tracks=[track(name='piano', notes=high_tune + left)], bars=4)
        self.assertGreaterEqual(sum(each.pitch for each in bottom_line(piano.tracks[0])) / len(bottom_line(piano.tracks[0])), LOW_REGISTER)
        found = bass_track(roles=profile_of_performance(performance=piano, name=SONG).roles, performance=piano)
        self.assertEqual({each.pitch for each in found.notes}, {LEFT_HAND_NOTE})

    def test_nothing_low_means_no_stand_in(self):
        high = performance(tracks=[track(name='a', notes=scale_tune(4)), track(name='b', notes=[note(start=beat, length=1, pitch=C + 12) for beat in range(16)])], bars=4)
        self.assertIsNone(bass_track(roles=profile_of_performance(performance=high, name=SONG).roles, performance=high))



class TestPhrasesAndSinging(unittest.TestCase):
    """Phrases end where a player breathes, fitted to experts' marks, and a pentatonic tune is heard by a singer's steps."""

    def test_an_eighth_rest_inside_a_bar_does_not_end_a_phrase_but_one_before_a_bar_does(self):
        inside = [note(start=place * 0.5, pitch=SCALE_UP[place % len(SCALE_UP)]) for place in range(16) if place != 3]
        self.assertEqual(len(phrases_of(inside, beats_per_bar=BEATS)), 1)
        self.assertEqual(len(phrases_of(scale_tune(4), beats_per_bar=BEATS)), 4)

    def test_a_rest_of_a_beat_ends_a_phrase_anywhere(self):
        line = [note(start=0, pitch=C), note(start=0.5, pitch=C + 2), note(start=2.5, pitch=C + 4), note(start=3, pitch=C + 5)]
        self.assertEqual(len(phrases_of(line, beats_per_bar=BEATS)), 2)

    def test_a_pentatonic_tune_is_heard_by_its_scales_steps(self):
        pentatonic = [note(start=place, length=1, pitch=PENTATONIC[place % len(PENTATONIC)]) for place in range(16)]
        self.assertTrue(is_pentatonic(pentatonic))
        self.assertFalse(is_pentatonic(scale_tune(4)))
        melody, phrases = melody_of(line=pentatonic, beats_per_bar=BEATS)
        heard = vocal_of(line=pentatonic, melody=melody, phrases=phrases, sound=None, beats_per_bar=BEATS)
        self.assertLess(melody.steps, 1.0)
        self.assertGreater(heard.singable, 0.5)


if __name__ == '__main__':
    unittest.main()
