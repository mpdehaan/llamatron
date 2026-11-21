# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for the Guitarify generator: Shape, which holds a chord as a hand does, and Strokes, which plays a bar of strokes on whatever sounds.

Each test plays C major from one pattern at 120 beats a minute, where a whole note lasts two
seconds, so 8 milliseconds between strings is 1/250 of a whole note.
"""

import unittest

from llamatron.engine.generators import guitarify as guitarify_plugin
from llamatron.engine.generators.guitarify import bars as guitar_bars, generator as guitarify, model as guitarify_settings
from llamatron.engine.generators.guitarify.bars import ready_bar_matching
from llamatron.engine.generators.guitarify.model import GuitarifySettings
from llamatron.engine.realizer.song_realizer import SongRealizer
from llamatron.engine.timing.timing import timed_events
from llamatron.math.rational import Rational
from llamatron.model.file.song_file_error import SongFileError
from llamatron.model.schema import file_format
from llamatron.model.schema.file_format import Approach, ChordColor, ClipSlotSetting, GuitarifySetting, PatternSetting, ReadyBar, Restart, Row, SceneSetting, Section, SingleNotes, SongSetting, Stroke, Tuning
from llamatron.model.values import midi
from tests.engine.realizer import test_registers
from tests.engine.realizer.test_registers import pattern, song
from tests.support.rendering import render_data, setlist_from_data, song_from_data

TRIAD = '3'
MAJOR = 'M'
TEMPO = 120
VELOCITY = 100
PLAYED = 'played'
PLAYED_CHAIN = 'played chain'
WHOLE = '1'
HALF = '1/2'
NO_SUCH_CHOICE = 'blue'
HALF_NOTE = Rational(1, 2)
D = 62
C_CLASS = 0
D_CLASS = 2
F_CLASS = 5
G_CLASS = 7
QUARTER = '1/4'
QUARTER_NOTE = Rational(1, 4)
WHOLE_NOTE = Rational(1)
MILLISECONDS_PER_WHOLE_NOTE_AT_ONE_BEAT_A_MINUTE = 240000


def delay(*, spread, strings):
    """Return how long after a stroke its string that many strings on starts, at the tests' tempo, on the grid a strum's strings start on."""
    return Rational(round(Rational(spread * strings * TEMPO, MILLISECONDS_PER_WHOLE_NOTE_AT_ONE_BEAT_A_MINUTE) * guitarify.STRUM_TICKS), guitarify.STRUM_TICKS)


# How long after a stroke its second and its third string start, with the spread a Guitarify has unless set.
GAP = delay(spread=guitarify_settings.DEFAULT_GUITAR_SPREAD, strings=1)
TWO_GAPS = delay(spread=guitarify_settings.DEFAULT_GUITAR_SPREAD, strings=2)
WIDE_SPREAD = 16
C = 60
E = 64
G = 67
C_MAJOR = {0, 4, 7}
D_MINOR = {2, 5, 9}
# C major as a hand holds it in the open position of a standard guitar: C3 E3 G3 C4 E4.
OPEN_C = [48, 52, 55, 60, 64]
LOW_D = 38
SEED = 7
OTHER_SEED = 8
EVEN = 0
NO_FADE = 0
NO_SPREAD = 0
# Settings that leave the notes' loudness and timing plain, for the tests of which strings a stroke plays.
PLAIN = {GuitarifySetting.FADE: NO_FADE, GuitarifySetting.LOOSE_TIMING: EVEN}
SHAPE_ONLY = {GuitarifySetting.STROKES: False}
STROKES_ONLY = {GuitarifySetting.SHAPE: False, **PLAIN}


def guitar(*, settings=None, rows=None, steps=1, step_size=WHOLE, repeat=1):
    """Return a song whose lead plays C major triads, one a step, through a Guitarify with these settings."""
    made = dict(pattern(steps, **{Row.CHORD: [TRIAD] * steps, Row.VELOCITY: [VELOCITY] * steps, **(rows or {})}), **{PatternSetting.STEP_SIZE: step_size})
    clip_slot = {ClipSlotSetting.PATTERN: test_registers.X, ClipSlotSetting.CHAINS: [PLAYED_CHAIN], ClipSlotSetting.REPEAT: repeat}
    data = song(patterns={test_registers.X: made}, scenes=[{SceneSetting.TRACKS: {test_registers.LEAD: clip_slot}}])
    data[SongSetting.TEMPO] = TEMPO
    data[guitarify_plugin.SECTION] = {PLAYED: dict(settings or {})}
    data[Section.CHAINS] = {PLAYED_CHAIN: [{guitarify_plugin.NAME: PLAYED}]}
    return data


def bar(strokes, *, accents=None, cell=QUARTER, **more):
    """Return the settings of a bar of strokes with nothing shaped, even and unfaded, and whatever else is given."""
    settings = {**STROKES_ONLY, GuitarifySetting.BAR: list(strokes), GuitarifySetting.CELL: cell, **more}
    if accents is not None:
        settings[GuitarifySetting.ACCENTS] = list(accents)
    return settings


def events(data, *, seed=None):
    grid = render_data(data) if seed is None else SongRealizer(song_from_data(data), seed=seed).render()
    clip = grid.get_clip(row=grid.get_rows()[0], column=grid.get_columns()[0])
    return sorted(timed_events(clip=clip, scale=clip.get_scale())[0])


def pitches(data):
    return [event.midi_number for event in events(data)]


def classes(data):
    return {pitch % midi.HALF_STEPS_PER_OCTAVE for pitch in pitches(data)}


def starting(data, *, start, before):
    """Return the notes that start from one time up to another, in the order they sound."""
    return [event for event in events(data) if start <= event.start < before]


class TestShape(unittest.TestCase):

    def test_a_chord_is_held_as_a_hand_holds_it_one_note_a_string(self):
        self.assertEqual(pitches(guitar(settings=SHAPE_ONLY)), OPEN_C)

    def test_with_shape_off_a_chord_stays_as_written(self):
        self.assertEqual(pitches(guitar(settings={GuitarifySetting.SHAPE: False, GuitarifySetting.STROKES: False})), [C, E, G])

    def test_every_note_keeps_the_chords_velocity_and_length(self):
        for event in events(guitar(settings=SHAPE_ONLY)):
            self.assertEqual((event.start, event.velocity), (Rational(0), VELOCITY))

    def test_a_position_keeps_every_string_within_reach_of_its_fret(self):
        for position in (5, 7, 9, 12):
            with self.subTest(position=position):
                played = pitches(guitar(settings={**SHAPE_ONLY, GuitarifySetting.POSITION: position}))
                self.assertEqual({pitch % midi.HALF_STEPS_PER_OCTAVE for pitch in played}, C_MAJOR)
                for pitch in played:
                    self.assertTrue(any(position <= pitch - string < position + guitarify.REACH for string in guitarify.OPEN_STRINGS[Tuning.STANDARD]), pitch)

    def test_a_capo_raises_the_open_strings(self):
        capo = 3
        played = pitches(guitar(settings={**SHAPE_ONLY, GuitarifySetting.CAPO: capo}))
        self.assertEqual({pitch % midi.HALF_STEPS_PER_OCTAVE for pitch in played}, C_MAJOR)
        self.assertGreaterEqual(min(played), guitarify.OPEN_STRINGS[Tuning.STANDARD][0] + capo)

    def test_fewer_strings_are_the_highest_ones(self):
        played = pitches(guitar(settings={**SHAPE_ONLY, GuitarifySetting.STRINGS: guitarify_settings.MIN_GUITAR_STRINGS}))
        self.assertLessEqual(len(played), guitarify_settings.MIN_GUITAR_STRINGS)
        self.assertGreaterEqual(min(played), guitarify.OPEN_STRINGS[Tuning.STANDARD][-guitarify_settings.MIN_GUITAR_STRINGS])
        self.assertEqual({pitch % midi.HALF_STEPS_PER_OCTAVE for pitch in played}, C_MAJOR)

    def test_a_tuning_changes_the_strings(self):
        # D major, the second degree made major, reaches the low D string only in drop D.
        rows = {Row.DEGREE: [2], Row.CHORD: [MAJOR]}
        self.assertEqual(min(pitches(guitar(settings={**SHAPE_ONLY, GuitarifySetting.TUNING: Tuning.DROP_D}, rows=rows))), LOW_D)
        self.assertGreater(min(pitches(guitar(settings=SHAPE_ONLY, rows=rows))), LOW_D)

    def test_every_tuning_plays_the_whole_chord_one_note_a_string(self):
        for tuning, strings in guitarify.OPEN_STRINGS.items():
            with self.subTest(tuning=tuning):
                played = pitches(guitar(settings={**SHAPE_ONLY, GuitarifySetting.TUNING: tuning}))
                self.assertEqual({pitch % midi.HALF_STEPS_PER_OCTAVE for pitch in played}, C_MAJOR)
                self.assertLessEqual(len(played), len(strings))
                self.assertGreaterEqual(min(played), strings[0])

    def test_the_root_is_in_the_bass_where_a_string_can_reach_it(self):
        played = pitches(guitar(settings={**SHAPE_ONLY, GuitarifySetting.TUNING: Tuning.STANDARD}))
        self.assertEqual(min(played) % midi.HALF_STEPS_PER_OCTAVE, C % midi.HALF_STEPS_PER_OCTAVE)

    def test_a_hand_short_of_strings_leaves_the_fifth_out_before_the_root(self):
        # A seventh chord has four notes, and three strings hold three of them: the root, the third and the seventh.
        played = pitches(guitar(settings={**SHAPE_ONLY, GuitarifySetting.STRINGS: guitarify_settings.MIN_GUITAR_STRINGS, GuitarifySetting.POSITION: 5}, rows={Row.CHORD: ['dom7']}))
        self.assertEqual(played, [C, E, 70])

    def test_a_note_outside_the_scale_builds_no_chord(self):
        played = pitches(guitar(settings={**SHAPE_ONLY, GuitarifySetting.SINGLE_NOTES: SingleNotes.SCALE_CHORD}, rows={Row.CHORD: [None], Row.ACCIDENTAL: ['#']}))
        self.assertEqual(played, [C + 1])

    def test_an_inverted_chord_keeps_its_lowest_note_in_the_bass(self):
        played = pitches(guitar(settings=SHAPE_ONLY, rows={Row.INVERSION: [1]}))
        self.assertEqual(min(played) % midi.HALF_STEPS_PER_OCTAVE, E % midi.HALF_STEPS_PER_OCTAVE)

    def test_a_single_note_is_left_alone_unless_asked(self):
        self.assertEqual(pitches(guitar(settings=SHAPE_ONLY, rows={Row.CHORD: [None]})), [C])

    def test_a_single_note_becomes_a_power_chord_on_the_low_strings(self):
        played = pitches(guitar(settings={**SHAPE_ONLY, GuitarifySetting.SINGLE_NOTES: SingleNotes.POWER_CHORD}, rows={Row.CHORD: [None]}))
        self.assertEqual(played, [48, 55, 60])

    def test_a_single_note_becomes_the_chord_its_degree_builds(self):
        played = classes(guitar(settings={**SHAPE_ONLY, GuitarifySetting.SINGLE_NOTES: SingleNotes.SCALE_CHORD}, rows={Row.DEGREE: [2], Row.CHORD: [None]}))
        self.assertEqual(played, D_MINOR)

    def test_a_rest_stays_silent(self):
        data = guitar(rows={Row.DEGREE: [1, None], Row.CHORD: [TRIAD, None], Row.VELOCITY: [VELOCITY, None]}, steps=2, step_size='1/2')
        self.assertEqual(starting(data, start=Rational(1, 2), before=WHOLE_NOTE), [])


class TestStrokes(unittest.TestCase):

    def test_a_down_stroke_plays_low_to_high_and_an_up_stroke_high_to_low(self):
        data = guitar(settings=bar([Stroke.DOWN, Stroke.NOTHING, Stroke.UP, Stroke.NOTHING]))
        down = starting(data, start=Rational(0), before=QUARTER_NOTE)
        up = starting(data, start=Rational(1, 2), before=Rational(3, 4))
        self.assertEqual([(event.start, event.midi_number) for event in down], [(Rational(0), C), (GAP, E), (TWO_GAPS, G)])
        self.assertEqual([(event.start, event.midi_number) for event in up], [(Rational(1, 2), G), (Rational(1, 2) + GAP, E), (Rational(1, 2) + TWO_GAPS, C)])
        self.assertEqual(len(events(data)), 6)

    def test_an_upstroke_catches_only_its_top_strings(self):
        data = guitar(settings=bar([Stroke.UP], cell=WHOLE, **{GuitarifySetting.UPSTROKE: 2}))
        self.assertEqual(pitches(data), [G, E])
        every = guitar(settings=bar([Stroke.UP], cell=WHOLE, **{GuitarifySetting.UPSTROKE: guitarify_settings.EVERY_STRING}))
        self.assertEqual(pitches(every), [G, E, C])

    def test_a_muted_stroke_is_short_and_quiet(self):
        played = events(guitar(settings=bar([Stroke.MUTE], cell=WHOLE, **{GuitarifySetting.SPREAD: NO_SPREAD})))
        self.assertEqual([(event.end - event.start, event.velocity) for event in played], [(WHOLE_NOTE * guitarify.MUTE_LENGTH, round(VELOCITY * guitarify.MUTE_VELOCITY))] * 3)

    def test_a_stab_is_every_string_at_full_loudness_and_stops_short_even_when_left_to_ring(self):
        for let_ring in (False, True):
            with self.subTest(let_ring=let_ring):
                played = events(guitar(settings=bar([Stroke.STAB], cell=WHOLE, **{GuitarifySetting.SPREAD: NO_SPREAD, GuitarifySetting.LET_RING: let_ring})))
                self.assertEqual([(event.end - event.start, event.velocity) for event in played], [(WHOLE_NOTE * guitarify.SHORT_LENGTH, VELOCITY)] * 3)

    def test_a_muted_bass_is_the_lowest_string_short_and_a_little_soft(self):
        played = events(guitar(settings=bar([Stroke.MUTED_BASS], cell=WHOLE, **{GuitarifySetting.LET_RING: True})))
        self.assertEqual([(event.midi_number, event.end - event.start, event.velocity) for event in played], [(C, WHOLE_NOTE * guitarify.SHORT_LENGTH, round(VELOCITY * guitarify.MUTED_BASS_VELOCITY))])

    def test_an_accented_muted_bass_is_at_full_loudness_and_the_others_no_softer_for_the_accent(self):
        played = events(guitar(settings=bar([Stroke.MUTED_BASS, Stroke.MUTED_BASS], accents=[True, False], cell=HALF)))
        self.assertEqual([event.velocity for event in played], [VELOCITY, round(VELOCITY * guitarify.MUTED_BASS_VELOCITY)])

    def test_a_squeal_is_one_high_note_short_and_never_softened(self):
        played = events(guitar(settings=bar([Stroke.DOWN, Stroke.SQUEAL], accents=[True, False], cell=HALF, **{GuitarifySetting.SPREAD: NO_SPREAD})))
        squeal = played[-1]
        self.assertEqual((squeal.midi_number, squeal.end - squeal.start, squeal.velocity), (C + guitarify.SQUEAL_ABOVE, HALF_NOTE * guitarify.SHORT_LENGTH, VELOCITY))

    def test_the_bass_the_alternate_bass_and_single_strings(self):
        data = guitar(settings=bar([Stroke.BASS, Stroke.ALT_BASS, Stroke.STRING_1, Stroke.STRING_2]))
        self.assertEqual([(event.start, event.midi_number) for event in events(data)], [(Rational(0), C), (QUARTER_NOTE, G), (Rational(1, 2), G), (Rational(3, 4), E)])

    def test_a_string_the_chord_lacks_is_the_nearest_it_has(self):
        self.assertEqual(pitches(guitar(settings=bar([Stroke.STRING_4], cell=WHOLE))), [C])

    def test_nothing_lets_the_stroke_before_sound_on(self):
        played = events(guitar(settings=bar([Stroke.BASS, Stroke.NOTHING, Stroke.NOTHING, Stroke.STRING_1])))
        self.assertEqual([(event.start, event.end) for event in played], [(Rational(0), Rational(3, 4)), (Rational(3, 4), WHOLE_NOTE)])

    def test_let_ring_holds_a_string_until_it_is_struck_again_or_the_chord_ends(self):
        strokes = [Stroke.BASS, Stroke.STRING_1, Stroke.BASS, Stroke.STRING_2]
        ringing = events(guitar(settings=bar(strokes, **{GuitarifySetting.LET_RING: True})))
        self.assertEqual([(event.start, event.end, event.midi_number) for event in ringing], [
            (Rational(0), Rational(1, 2), C), (QUARTER_NOTE, WHOLE_NOTE, G), (Rational(1, 2), WHOLE_NOTE, C), (Rational(3, 4), WHOLE_NOTE, E),
        ])
        damped = events(guitar(settings=bar(strokes)))
        self.assertEqual([event.end - event.start for event in damped], [QUARTER_NOTE] * 4)

    def test_let_ring_never_rings_into_the_next_chord(self):
        data = guitar(settings=bar([Stroke.DOWN, Stroke.NOTHING], cell='1/2', **{GuitarifySetting.LET_RING: True, GuitarifySetting.SPREAD: NO_SPREAD}), steps=2, step_size='1/2')
        self.assertEqual({event.end for event in starting(data, start=Rational(0), before=Rational(1, 2))}, {Rational(1, 2)})

    def test_where_a_bar_has_accents_the_other_strokes_are_softer(self):
        data = guitar(settings=bar([Stroke.BASS, Stroke.BASS], accents=[True, False], cell='1/2'))
        self.assertEqual([event.velocity for event in events(data)], [VELOCITY, round(VELOCITY * guitarify.UNACCENTED_VELOCITY)])
        plain = guitar(settings=bar([Stroke.BASS, Stroke.BASS], cell='1/2'))
        self.assertEqual([event.velocity for event in events(plain)], [VELOCITY, VELOCITY])

    def test_fade_makes_each_later_string_quieter(self):
        data = guitar(settings=bar([Stroke.DOWN], cell=WHOLE, **{GuitarifySetting.FADE: 20}))
        self.assertEqual([event.velocity for event in events(data)], [100, 90, 80])

    def test_spread_is_the_time_between_strings_and_none_strikes_them_together(self):
        wide = events(guitar(settings=bar([Stroke.DOWN], cell=WHOLE, **{GuitarifySetting.SPREAD: WIDE_SPREAD})))
        self.assertEqual([event.start for event in wide], [Rational(0), delay(spread=WIDE_SPREAD, strings=1), delay(spread=WIDE_SPREAD, strings=2)])
        together = events(guitar(settings=bar([Stroke.DOWN], cell=WHOLE, **{GuitarifySetting.SPREAD: NO_SPREAD})))
        self.assertEqual({event.start for event in together}, {Rational(0)})

    def test_a_strum_never_takes_more_than_half_the_time_to_the_next_stroke(self):
        played = events(guitar(settings=bar([Stroke.DOWN], cell='1/64', **{GuitarifySetting.SPREAD: guitarify_settings.MAX_GUITAR_SPREAD})))
        first = [event for event in played if event.start < Rational(1, 64)]
        self.assertLessEqual(max(event.start for event in first), Rational(1, 128))

    def test_loose_timing_is_uneven_and_the_same_for_the_same_seed(self):
        data = guitar(settings=bar([Stroke.DOWN], cell=WHOLE, **{GuitarifySetting.LOOSE_TIMING: guitarify_settings.MAX_GUITAR_PERCENT, GuitarifySetting.SPREAD: guitarify_settings.MAX_GUITAR_SPREAD}), rows={Row.CHORD: ['M9']})
        starts = [event.start for event in events(data, seed=SEED)]
        self.assertEqual(starts, [event.start for event in events(data, seed=SEED)])
        self.assertNotEqual(starts, [event.start for event in events(data, seed=OTHER_SEED)])
        self.assertEqual(starts, sorted(starts))

    def test_a_single_note_is_played_by_every_stroke(self):
        data = guitar(settings=bar([Stroke.DOWN, Stroke.UP, Stroke.MUTE, Stroke.STRING_3]), rows={Row.CHORD: [None]})
        self.assertEqual([(event.start, event.midi_number) for event in events(data)], [(QUARTER_NOTE * place, C) for place in range(4)])

    def test_the_bar_goes_round_under_a_long_chord_and_across_chords(self):
        data = guitar(settings=bar([Stroke.BASS, Stroke.STRING_1]), steps=2, step_size='1/2', rows={Row.DEGREE: [1, 4]})
        self.assertEqual([event.midi_number for event in events(data)], [C, G, 65, 72])

    def test_with_strokes_off_and_a_bar_written_nothing_is_struck(self):
        data = guitar(settings={**bar([Stroke.BASS] * 4), GuitarifySetting.STROKES: False})
        self.assertEqual(pitches(data), [C, E, G])

    def test_shape_and_strokes_together_strum_the_held_chord(self):
        data = guitar(settings={**PLAIN, GuitarifySetting.BAR: [Stroke.DOWN], GuitarifySetting.CELL: WHOLE})
        self.assertEqual([event.midi_number for event in events(data)], OPEN_C)

    def test_a_new_guitarify_plays_the_default_bar_on_the_held_chord(self):
        played = events(guitar())
        strokes = guitar_bars.READY_BARS[guitar_bars.DEFAULT_BAR].strokes
        struck = [place for place, stroke in enumerate(strokes) if stroke != Stroke.NOTHING]
        cell = Rational(1, 8)
        self.assertEqual(sorted({event.start // cell for event in played}), struck)
        self.assertEqual({event.midi_number for event in played}, set(OPEN_C))


class TestTheBarFollowsTheSongsBars(unittest.TestCase):

    def data(self, restart):
        # A clip of three quarter notes played twice: one bar and a half of 4/4.
        settings = bar([Stroke.BASS, Stroke.STRING_1, Stroke.STRING_1, Stroke.STRING_1])
        if restart is not None:
            settings[file_format.GENERATOR_RESTART] = restart
        data = guitar(settings=settings, steps=3, step_size=QUARTER)
        data[Section.SCENES].append({SceneSetting.TRACKS: {test_registers.LEAD: dict(data[Section.SCENES][0][SceneSetting.TRACKS][test_registers.LEAD])}})
        return data

    def second_clip(self, data):
        grid = render_data(data)
        clip = grid.get_clip(row=grid.get_rows()[1], column=grid.get_columns()[0])
        return [event.midi_number for event in sorted(timed_events(clip=clip, scale=clip.get_scale())[0])]

    def test_every_clip_starts_the_bar_again(self):
        self.assertEqual(self.second_clip(self.data(None)), [C, G, G])

    def test_whole_song_carries_the_bar_on_from_the_clip_before(self):
        self.assertEqual(self.second_clip(self.data(Restart.WHOLE_SONG)), [G, C, G])


class TestSingleNoteChoices(unittest.TestCase):

    def single(self, choice):
        settings = {GuitarifySetting.STROKES: False, GuitarifySetting.SINGLE_NOTES: choice}
        return pitches(guitar(settings=settings, rows={Row.CHORD: [None]}))

    def test_an_octave_a_third_above_and_a_double_stop(self):
        self.assertEqual(self.single(SingleNotes.OCTAVE), [C, C + midi.HALF_STEPS_PER_OCTAVE])
        self.assertEqual(self.single(SingleNotes.THIRD_ABOVE), [C, E])
        self.assertEqual(self.single(SingleNotes.DOUBLE_STOP), [C - guitarify.FOURTH_BELOW, C])


class TestChordColor(unittest.TestCase):

    def classes(self, color):
        return {pitch % midi.HALF_STEPS_PER_OCTAVE for pitch in pitches(guitar(settings={GuitarifySetting.STROKES: False, GuitarifySetting.COLOR: color}))}

    def test_each_color_of_a_c_major_chord(self):
        self.assertEqual(self.classes(ChordColor.AS_WRITTEN), C_MAJOR)
        self.assertEqual(self.classes(ChordColor.ADD_9), C_MAJOR | {D_CLASS})
        self.assertEqual(self.classes(ChordColor.SUS_2), {C_CLASS, D_CLASS, G_CLASS})
        self.assertEqual(self.classes(ChordColor.SUS_4), {C_CLASS, F_CLASS, G_CLASS})
        self.assertEqual(self.classes(ChordColor.NO_THIRD), {C_CLASS, G_CLASS})

    def test_a_color_is_one_of_the_colors(self):
        with self.assertRaises(SongFileError):
            setlist_from_data(guitar(settings={GuitarifySetting.COLOR: NO_SUCH_CHOICE}))


class TestApproach(unittest.TestCase):

    def played(self, approach):
        settings = bar([Stroke.DOWN], cell=WHOLE, **{GuitarifySetting.SPREAD: NO_SPREAD, GuitarifySetting.APPROACH: approach})
        data = guitar(settings=settings, rows={Row.CHORD: [None, None], Row.DEGREE: [1, 2]}, steps=2)
        return [(event.start, event.midi_number, event.end - event.start) for event in events(data)]

    def test_off_plays_each_note_where_it_is_written(self):
        self.assertEqual(self.played(Approach.OFF), [(Rational(0), C, WHOLE_NOTE), (WHOLE_NOTE, D, WHOLE_NOTE)])

    def test_a_new_note_is_reached_from_a_fret_below_and_the_first_is_not(self):
        self.assertEqual(self.played(Approach.FROM_BELOW), [(Rational(0), C, WHOLE_NOTE), (WHOLE_NOTE, D - 1, guitarify.APPROACH_LENGTH), (WHOLE_NOTE + guitarify.APPROACH_LENGTH, D, WHOLE_NOTE - guitarify.APPROACH_LENGTH)])

    def test_from_above(self):
        self.assertEqual(self.played(Approach.FROM_ABOVE)[1], (WHOLE_NOTE, D + 1, guitarify.APPROACH_LENGTH))


class TestReadyMadeBars(unittest.TestCase):

    def test_every_ready_made_bar_is_strokes_and_accents_of_one_length_within_the_limit(self):
        for name, ready in guitar_bars.READY_BARS.items():
            with self.subTest(bar=name):
                self.assertEqual(len(ready.strokes), len(ready.accents))
                self.assertLessEqual(len(ready.strokes), guitarify_settings.MAX_GUITAR_BAR)
                self.assertTrue(all(stroke in file_format.STROKES for stroke in ready.strokes))
                GuitarifySettings.check_data({GuitarifySetting.BAR: list(ready.strokes), GuitarifySetting.ACCENTS: list(ready.accents), GuitarifySetting.CELL: ready.cell})

    def test_every_ready_made_bar_has_a_name_and_no_two_are_the_same(self):
        names = [getattr(ReadyBar, name) for name in vars(ReadyBar) if not name.startswith('_')]
        self.assertEqual(sorted(names), sorted(guitar_bars.READY_BARS))
        self.assertEqual(len({(ready.cell, ready.strokes, ready.accents) for ready in guitar_bars.READY_BARS.values()}), len(guitar_bars.READY_BARS))

    def test_a_bar_is_matched_to_its_ready_made_name(self):
        ready = guitar_bars.READY_BARS[ReadyBar.CHUG]
        self.assertEqual(ready_bar_matching(cell=ready.cell, strokes=list(ready.strokes), accents=list(ready.accents)), ReadyBar.CHUG)
        self.assertIsNone(ready_bar_matching(cell=ready.cell, strokes=[Stroke.DOWN], accents=[False]))

    def test_new_settings_hold_the_default_bar(self):
        settings = GuitarifySettings.new()
        ready = guitar_bars.READY_BARS[guitar_bars.DEFAULT_BAR]
        self.assertEqual((settings.get_cell(), settings.get_bar(), settings.get_accents()), (ready.cell, list(ready.strokes), list(ready.accents)))
        self.assertEqual(settings.to_data(), {})

    def test_a_written_bar_with_no_accents_has_none(self):
        settings = GuitarifySettings({GuitarifySetting.BAR: [Stroke.DOWN, Stroke.UP]})
        self.assertEqual(settings.get_accents(), [False, False])


class TestWhatAFileRefuses(unittest.TestCase):

    def refused(self, settings):
        with self.assertRaises(SongFileError):
            setlist_from_data(guitar(settings=settings))

    def test_an_unknown_stroke_is_refused(self):
        self.refused({GuitarifySetting.BAR: [Stroke.DOWN, 'sideways']})

    def test_an_empty_bar_and_one_too_long_are_refused(self):
        self.refused({GuitarifySetting.BAR: []})
        self.refused({GuitarifySetting.BAR: [Stroke.DOWN] * (guitarify_settings.MAX_GUITAR_BAR + 1)})

    def test_accents_that_are_not_true_or_false_are_refused(self):
        self.refused({GuitarifySetting.ACCENTS: [1, 0]})

    def test_a_cell_that_is_no_length_is_refused(self):
        self.refused({GuitarifySetting.CELL: 'short'})


if __name__ == '__main__':
    unittest.main()
