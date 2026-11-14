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
"""Density, Swell and Articulate: how a clip's notes are thinned, made louder or softer and made shorter or longer over time, set on a scene, a clip or a generator.

The user's design of 2026-11-11. Most tests play a bar of sixteen sixteenth-note Cs, so that every
strength of place in a 4/4 bar is there: the bar's start, its middle, the two other beats, the
eighths between and the sixteenths between those.
"""

import unittest

from llamatron.composition.file_format import (
    ClipSlotSetting, GeneratorKind, PatternSetting, Row, SceneSetting, Section, Shape, ShapePart, ShapeThen, shape_setting,
)
from llamatron.composition.generator_settings import ShapeSetting
from llamatron.composition.limits import MAX_DENSITY, MAX_SWELL, MIN_ARTICULATE
from llamatron.composition.shapes import ShapeValues
from llamatron.exporters.timing import timed_events
from llamatron.playback.shapes import BAR_MIDDLE, BAR_START, FINER, ON_A_BEAT, ON_AN_EIGHTH, ON_A_SIXTEENTH, percent_at, plays_at, strength
from llamatron.support.rational import Rational
from llamatron.composition.song_file_error import SongFileError
from rendering import render_data, setlist_from_data
from test_registers import LEAD, X, pattern, song

SIXTEENTH = '1/16'
STEPS = 16
BAR = Rational(1)
BEAT = Rational(1, 4)
CHORD = 'M'
VELOCITY = 100
SHAPED = 'shaped'
OTHER_TRACK = 'bass'
HALF = 50
QUARTER = 25
FULL = 100
DOUBLE = 200
ACCENT = 20
NO_NOTES = 0


def at(*, shape, part):
    return shape_setting(shape=shape, part=part)


def bar_of_sixteenths(**rows):
    return dict(pattern(STEPS, **rows), **{PatternSetting.STEP_SIZE: SIXTEENTH})


def one_scene(*, scene=None, clip=None, rows=None, repeat=1, chain=None, generators=None):
    """Return a song whose lead plays a bar of sixteenths, the scene and the clip given settings of their own, and the clip's chains naming generators."""
    clip_slot = {ClipSlotSetting.PATTERN: X, ClipSlotSetting.REPEAT: repeat, **(clip or {})}
    if chain:
        clip_slot[ClipSlotSetting.CHAINS] = [SHAPED]
    data = song(patterns={X: bar_of_sixteenths(**(rows or {}))}, scenes=[{**(scene or {}), SceneSetting.TRACKS: {LEAD: clip_slot}}])
    if chain:
        data[Section.CHAINS] = {SHAPED: chain}
    data.update(generators or {})
    return data


def notes(data):
    """Return (start, length, pitch, velocity) of every note the lead plays, in time order."""
    grid = render_data(data)
    clip = grid.get_clip(row=grid.get_rows()[0], column=grid.get_columns()[0])
    return [(start, end - start, pitch, velocity) for start, end, pitch, velocity in sorted(timed_events(clip=clip, scale=clip.get_scale())[0])]


def starts(data):
    return [start for start, _, _, _ in notes(data)]


def velocities(data):
    return [velocity for _, _, _, velocity in notes(data)]


def lengths(data):
    return [length for _, length, _, _ in notes(data)]


def steady(*, shape, percent):
    """Return a scene's or clip's settings holding a shape at one percentage."""
    return {at(shape=shape, part=ShapePart.START): percent, at(shape=shape, part=ShapePart.END): percent}


class TestPercentOverTime(unittest.TestCase):
    """percent_at: from start to end over the span or the over, then holding, repeating or bouncing."""

    def values(self, *, over=None, then=ShapeThen.HOLD):
        return ShapeValues(0, FULL, over, then, 0)

    def test_it_ramps_over_the_whole_span(self):
        self.assertEqual(percent_at(values=self.values(), time=Rational(1, 2), span=Rational(2)), QUARTER)

    def test_it_holds_at_the_end_after_its_over(self):
        self.assertEqual(percent_at(values=self.values(over=1), time=Rational(3, 2), span=Rational(4)), FULL)

    def test_repeat_starts_again(self):
        self.assertEqual(percent_at(values=self.values(over=1, then=ShapeThen.REPEAT), time=Rational(5, 4), span=Rational(4)), QUARTER)

    def test_bounce_ramps_back(self):
        self.assertEqual(percent_at(values=self.values(over=1, then=ShapeThen.BOUNCE), time=Rational(5, 4), span=Rational(4)), FULL - QUARTER)
        self.assertEqual(percent_at(values=self.values(over=1, then=ShapeThen.BOUNCE), time=Rational(9, 4), span=Rational(4)), QUARTER)


class TestStrength(unittest.TestCase):
    """How strong each place in a bar of 4/4 is."""

    def test_every_place_of_a_bar_of_sixteenths(self):
        found = [strength(time=Rational(step, STEPS), bar=BAR, beat=BEAT) for step in range(STEPS)]
        self.assertEqual(found[0], BAR_START)
        self.assertEqual(found[8], BAR_MIDDLE)
        self.assertEqual([found[4], found[12]], [ON_A_BEAT, ON_A_BEAT])
        self.assertEqual({found[step] for step in (2, 6, 10, 14)}, {ON_AN_EIGHTH})
        self.assertEqual({found[step] for step in range(1, STEPS, 2)}, {ON_A_SIXTEENTH})

    def test_a_triplet_is_finer_and_plays_only_at_full_density(self):
        self.assertEqual(strength(time=Rational(1, 12), bar=BAR, beat=BEAT), FINER)
        self.assertFalse(plays_at(density=FULL - 1, level=FINER))
        self.assertTrue(plays_at(density=FULL, level=FINER))

    def test_the_next_bar_starts_strong_again(self):
        self.assertEqual(strength(time=Rational(1), bar=BAR, beat=BEAT), BAR_START)


class TestDensity(unittest.TestCase):

    def test_nothing_set_plays_every_note(self):
        self.assertEqual(len(notes(one_scene())), STEPS)

    def test_the_strongest_places_keep_playing_longest(self):
        self.assertEqual(starts(one_scene(scene=steady(shape=Shape.DENSITY, percent=QUARTER))), [Rational(step, STEPS) for step in (0, 4, 8, 12)])
        self.assertEqual(len(notes(one_scene(scene=steady(shape=Shape.DENSITY, percent=HALF)))), STEPS // 2)
        self.assertEqual(starts(one_scene(scene=steady(shape=Shape.DENSITY, percent=10))), [0, Rational(1, 2)])
        self.assertEqual(starts(one_scene(scene=steady(shape=Shape.DENSITY, percent=1))), [0])

    def test_none_plays_nothing(self):
        self.assertEqual(len(notes(one_scene(scene=steady(shape=Shape.DENSITY, percent=NO_NOTES)))), NO_NOTES)

    def test_a_ramp_fills_in_across_the_repeats(self):
        played = notes(one_scene(repeat=4, scene={at(shape=Shape.DENSITY, part=ShapePart.START): QUARTER, at(shape=Shape.DENSITY, part=ShapePart.END): MAX_DENSITY}))
        first_bar = [note for note in played if note[0] < 1]
        last_bar = [note for note in played if note[0] >= 3]
        self.assertLess(len(first_bar), len(last_bar))

    def test_a_chord_is_kept_or_dropped_whole(self):
        played = notes(one_scene(rows={Row.CHORD: [CHORD] * STEPS}, scene=steady(shape=Shape.DENSITY, percent=QUARTER)))
        self.assertEqual(len(played), 4 * 3)

    def test_a_drum_pattern_is_thinned_too(self):
        data = one_scene(scene=steady(shape=Shape.DENSITY, percent=QUARTER))
        data[Section.PATTERNS][X].update({PatternSetting.DRUM: True, Row.DEGREE: ['C'] * STEPS})
        self.assertEqual(len(notes(data)), 4)

    def test_a_dropped_note_keeps_its_place(self):
        self.assertEqual(starts(one_scene(scene=steady(shape=Shape.DENSITY, percent=QUARTER)))[-1], Rational(12, 16))


class TestSwell(unittest.TestCase):

    def test_it_scales_the_velocity(self):
        rows = {Row.VELOCITY: [VELOCITY] * STEPS}
        self.assertEqual(set(velocities(one_scene(rows=rows, scene=steady(shape=Shape.SWELL, percent=HALF)))), {VELOCITY // 2})

    def test_it_is_held_from_1_to_127(self):
        self.assertEqual(set(velocities(one_scene(scene=steady(shape=Shape.SWELL, percent=MAX_SWELL)))), {127})
        self.assertEqual(set(velocities(one_scene(scene=steady(shape=Shape.SWELL, percent=NO_NOTES)))), {1})

    def test_a_crescendo_across_the_clip(self):
        found = velocities(one_scene(rows={Row.VELOCITY: [VELOCITY] * STEPS}, scene={at(shape=Shape.SWELL, part=ShapePart.START): HALF, at(shape=Shape.SWELL, part=ShapePart.END): FULL}))
        self.assertEqual(found, sorted(found))
        self.assertLess(found[0], found[-1])

    def test_a_generators_accent_lifts_the_beats(self):
        generators = {Section.SWELLS: {SHAPED: {ShapeSetting.START: FULL - ACCENT, ShapeSetting.END: FULL - ACCENT, ShapeSetting.ACCENT: ACCENT}}}
        found = velocities(one_scene(rows={Row.VELOCITY: [VELOCITY] * STEPS}, chain=[{GeneratorKind.SWELL: SHAPED}], generators=generators))
        self.assertGreater(found[4], found[1])
        self.assertEqual(found[1], VELOCITY * (FULL - ACCENT) // FULL)


class TestArticulate(unittest.TestCase):

    def test_it_shortens_each_note(self):
        self.assertEqual(set(lengths(one_scene(scene=steady(shape=Shape.ARTICULATE, percent=HALF)))), {Rational(1, 32)})

    def test_a_longer_note_stops_where_the_next_starts(self):
        self.assertEqual(set(lengths(one_scene(scene=steady(shape=Shape.ARTICULATE, percent=DOUBLE)))), {Rational(1, 16)})

    def test_a_longer_note_before_a_rest_is_held_into_it(self):
        rows = {Row.DEGREE: [1, None] * (STEPS // 2), Row.OCTAVE: [5, None] * (STEPS // 2)}
        self.assertEqual(set(lengths(one_scene(rows=rows, scene=steady(shape=Shape.ARTICULATE, percent=DOUBLE)))), {Rational(1, 8)})

    def test_the_last_note_never_runs_past_the_clip(self):
        rows = {Row.DEGREE: [None] * (STEPS - 1) + [1]}
        self.assertEqual(lengths(one_scene(rows=rows, scene=steady(shape=Shape.ARTICULATE, percent=DOUBLE))), [Rational(1, 16)])


class TestWhichShapeWins(unittest.TestCase):
    """A generator a clip's chains name beats the clip's own, which beats its scene's."""

    def test_the_clip_beats_the_scene(self):
        data = one_scene(scene=steady(shape=Shape.DENSITY, percent=QUARTER), clip=steady(shape=Shape.DENSITY, percent=HALF))
        self.assertEqual(len(notes(data)), STEPS // 2)

    def test_the_generator_beats_the_clip(self):
        generators = {Section.DENSITIES: {SHAPED: {ShapeSetting.START: QUARTER, ShapeSetting.END: QUARTER}}}
        data = one_scene(clip=steady(shape=Shape.DENSITY, percent=HALF), chain=[{GeneratorKind.DENSITY: SHAPED}], generators=generators)
        self.assertEqual(len(notes(data)), 4)

    def test_a_scenes_ramp_runs_over_the_whole_scene_and_a_clips_over_the_clip(self):
        ramp = {at(shape=Shape.DENSITY, part=ShapePart.START): QUARTER, at(shape=Shape.DENSITY, part=ShapePart.END): FULL}
        data = one_scene(scene=ramp)
        data[Section.TRACKS][OTHER_TRACK] = {}
        data[Section.PATTERNS]['long'] = dict(bar_of_sixteenths(), **{PatternSetting.STEPS: STEPS})
        data[Section.SCENES][0][SceneSetting.TRACKS][OTHER_TRACK] = {ClipSlotSetting.PATTERN: 'long', ClipSlotSetting.REPEAT: 2}
        # The lead's one bar is the first half of a two-bar scene, so it reaches only halfway up the ramp.
        self.assertLess(len(notes(data)), STEPS)


class TestShapeSettingsInAFile(unittest.TestCase):

    def test_a_percentage_outside_its_range_is_refused(self):
        data = one_scene(scene=steady(shape=Shape.ARTICULATE, percent=MIN_ARTICULATE - 1))
        with self.assertRaises(SongFileError):
            setlist_from_data(data)

    def test_an_unknown_then_is_refused(self):
        data = one_scene(scene={**steady(shape=Shape.SWELL, percent=HALF), at(shape=Shape.SWELL, part=ShapePart.THEN): 'sideways'})
        with self.assertRaises(SongFileError):
            setlist_from_data(data)

    def test_it_is_written_back_as_read(self):
        data = one_scene(scene={**steady(shape=Shape.SWELL, percent=HALF), at(shape=Shape.SWELL, part=ShapePart.OVER): '1/2', at(shape=Shape.SWELL, part=ShapePart.THEN): ShapeThen.BOUNCE})
        written = setlist_from_data(data).to_data()
        scene = next(iter(written[Section.SONGS].values()))[Section.SCENES][0]
        self.assertEqual(scene[at(shape=Shape.SWELL, part=ShapePart.THEN)], ShapeThen.BOUNCE)
        self.assertEqual(scene[at(shape=Shape.SWELL, part=ShapePart.START)], HALF)
