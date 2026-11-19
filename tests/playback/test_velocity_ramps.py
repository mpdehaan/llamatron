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
"""How loud a scene and a clip play: the velocity that holds, the ramp in and the ramp out.

The lead plays a bar of sixteen sixteenth notes, each written at a velocity of 100, so that a
percentage is the velocity heard. Where a scene has to be longer than the lead's clip, a second
track plays two bars.
"""

import unittest

from llamatron.composition import limits
from llamatron.composition.file_format import ClipSlotSetting, GeneratorKind, PatternSetting, Row, SceneSetting, Section, VelocitySetting
from llamatron.composition.generator_settings import ShapeSetting
from llamatron.composition.song_file_error import SongFileError
from llamatron.composition import velocity_ramps
from llamatron.composition.velocity_ramps import Velocity, VelocityRamp, velocity_of
from llamatron.exporters.timing import timed_events
from llamatron.music import midi
from llamatron.playback.shapes import PlacedRamp, PlacedVelocity, velocity_percent_at
from llamatron.support.rational import Rational
from tests.playback import test_registers
from tests.playback import test_shapes
from tests.playback.test_shapes import bar_of_sixteenths, one_scene
from tests.support.rendering import render_data, setlist_from_data

WRITTEN = 100
HALF = 50
QUARTER = 25
LOW = 20
# A bar of sixteenths from 20% to 100% rises 5 a note, and two bars from 36% rise 2 a note.
A_NOTE_OF_ONE_BAR = 5
TWO_BAR_START = 36
A_NOTE_OF_TWO_BARS = 2
ONE_BAR = 1
TWO_BARS = 2
LONG = 'long'
ROWS = {Row.VELOCITY: [WRITTEN] * test_shapes.STEPS}
RISING = [LOW + A_NOTE_OF_ONE_BAR * note for note in range(test_shapes.STEPS)]
FALLING = [WRITTEN - A_NOTE_OF_ONE_BAR * note for note in range(test_shapes.STEPS)]
HELD = [WRITTEN] * test_shapes.STEPS
# A setting a scene and a clip held before their velocity took its place.
OLD_SWELL_START = 'swell_start'


def played(data, *, row=0):
    """Return the velocity of every note the lead plays in one written-out scene, in time order."""
    grid = render_data(data)
    clip = grid.get_clip(row=grid.get_rows()[row], column=grid.get_columns()[0])
    return [velocity for start, end, pitch, velocity in sorted(timed_events(clip=clip, scale=clip.get_scale())[0])]


def lead_of(*, scene=None, clip=None, repeat=1, scene_repeat=1):
    """Return a song whose lead plays its bar so many times, in a scene played so many times, with settings for the scene and the clip."""
    return one_scene(rows=ROWS, scene={SceneSetting.REPEAT: scene_repeat, **(scene or {})}, clip=clip, repeat=repeat)


def beside_two_bars(*, scene=None, clip=None):
    """Return a song whose lead plays its one bar in a scene that another track makes two bars long."""
    data = one_scene(rows=ROWS, scene=scene, clip=clip)
    data[Section.TRACKS][test_shapes.OTHER_TRACK] = {}
    data[Section.PATTERNS][LONG] = dict(bar_of_sixteenths(), **{PatternSetting.STEPS: test_shapes.STEPS})
    data[Section.SCENES][0][SceneSetting.TRACKS][test_shapes.OTHER_TRACK] = {ClipSlotSetting.PATTERN: LONG, ClipSlotSetting.REPEAT: TWO_BARS}
    return data


class TestTheVelocityThatHolds(unittest.TestCase):

    def test_a_scenes_velocity_scales_every_note(self):
        self.assertEqual(set(played(lead_of(scene={VelocitySetting.LEVEL: HALF}))), {HALF})

    def test_nothing_set_plays_as_written(self):
        self.assertEqual(played(lead_of()), HELD)

    def test_a_clips_velocity_wins_over_its_scenes(self):
        self.assertEqual(set(played(lead_of(scene={VelocitySetting.LEVEL: HALF}, clip={VelocitySetting.LEVEL: QUARTER}))), {QUARTER})

    def test_a_note_stops_at_the_loudest_and_the_softest_velocity(self):
        self.assertEqual(set(played(lead_of(scene={VelocitySetting.LEVEL: limits.MAX_VELOCITY_PERCENT}))), {midi.MAX_VELOCITY})
        self.assertEqual(set(played(lead_of(scene={VelocitySetting.LEVEL: limits.MIN_VELOCITY_PERCENT}))), {midi.MIN_VELOCITY})

    def test_a_swell_generator_scales_what_the_scene_already_scaled(self):
        data = one_scene(rows=ROWS, scene={VelocitySetting.LEVEL: HALF}, chain=[{GeneratorKind.SWELL: test_shapes.SHAPED}],
                         generators={Section.SWELLS: {test_shapes.SHAPED: {ShapeSetting.START: HALF, ShapeSetting.END: HALF}}})
        self.assertEqual(set(played(data)), {QUARTER})


class TestTheRampIn(unittest.TestCase):

    def test_it_climbs_from_its_start_to_the_velocity_over_its_bars_and_then_holds(self):
        data = lead_of(scene={VelocitySetting.IN_START: LOW, VelocitySetting.IN_OVER: ONE_BAR}, repeat=TWO_BARS)
        self.assertEqual(played(data), RISING + HELD)

    def test_a_blank_start_is_the_velocity_and_an_end_is_where_it_arrives(self):
        data = lead_of(scene={VelocitySetting.LEVEL: LOW, VelocitySetting.IN_END: WRITTEN, VelocitySetting.IN_OVER: ONE_BAR}, repeat=TWO_BARS)
        self.assertEqual(played(data), RISING + [LOW] * test_shapes.STEPS)

    def test_it_needs_its_bars(self):
        self.assertEqual(played(lead_of(scene={VelocitySetting.IN_START: LOW})), HELD)

    def test_bars_alone_change_nothing(self):
        self.assertEqual(played(lead_of(scene={VelocitySetting.IN_OVER: ONE_BAR})), HELD)

    def test_a_scenes_ramp_goes_on_through_the_scenes_repeats(self):
        data = lead_of(scene={VelocitySetting.IN_START: TWO_BAR_START, VelocitySetting.IN_OVER: TWO_BARS}, scene_repeat=TWO_BARS)
        self.assertEqual(played(data, row=0), [TWO_BAR_START + A_NOTE_OF_TWO_BARS * note for note in range(test_shapes.STEPS)])
        self.assertEqual(played(data, row=1), [TWO_BAR_START + A_NOTE_OF_TWO_BARS * (test_shapes.STEPS + note) for note in range(test_shapes.STEPS)])

    def test_a_ramp_whose_bars_the_clip_gives_starts_again_with_the_clip(self):
        data = lead_of(clip={VelocitySetting.IN_START: LOW, VelocitySetting.IN_OVER: ONE_BAR}, scene_repeat=TWO_BARS)
        self.assertEqual((played(data, row=0), played(data, row=1)), (RISING, RISING))


class TestTheRampOut(unittest.TestCase):

    def test_it_falls_from_the_velocity_to_its_end_over_the_last_bars(self):
        data = lead_of(scene={VelocitySetting.OUT_END: LOW, VelocitySetting.OUT_OVER: ONE_BAR}, repeat=TWO_BARS)
        self.assertEqual(played(data), HELD + FALLING)

    def test_the_ramp_in_wins_where_the_two_overlap(self):
        scene = {VelocitySetting.IN_START: LOW, VelocitySetting.IN_OVER: ONE_BAR, VelocitySetting.OUT_END: LOW, VelocitySetting.OUT_OVER: ONE_BAR}
        self.assertEqual(played(lead_of(scene=scene)), RISING)

    def test_a_scenes_ramp_out_is_counted_back_from_the_scenes_end(self):
        # The lead's one bar is over before the scene's last bar, where the scene's ramp out is.
        data = beside_two_bars(scene={VelocitySetting.OUT_END: LOW, VelocitySetting.OUT_OVER: ONE_BAR})
        self.assertEqual(played(data), HELD)

    def test_a_ramp_out_whose_bars_the_clip_gives_is_counted_back_from_the_clips_end(self):
        data = beside_two_bars(clip={VelocitySetting.OUT_END: LOW, VelocitySetting.OUT_OVER: ONE_BAR})
        self.assertEqual(played(data), FALLING)

    def test_a_looping_clips_own_ramp_out_is_counted_back_from_its_scenes_end(self):
        data = beside_two_bars(clip={ClipSlotSetting.LOOP: True, VelocitySetting.OUT_END: LOW, VelocitySetting.OUT_OVER: ONE_BAR})
        self.assertEqual(played(data), HELD + FALLING)


class TestAClipOverItsScene(unittest.TestCase):
    """A clip's own settings win over its scene's one field at a time, and whoever gives a ramp its bars says what the bars are counted over."""

    def test_a_clip_takes_each_blank_field_from_its_scene(self):
        scene = {VelocitySetting.LEVEL: HALF, VelocitySetting.IN_START: LOW, VelocitySetting.IN_OVER: ONE_BAR}
        self.assertEqual(velocity_of(scene_settings=scene, clip_settings={VelocitySetting.IN_START: QUARTER}), Velocity(HALF, VelocityRamp(QUARTER, HALF, ONE_BAR, False), None))

    def test_a_clips_own_bars_make_the_ramp_the_clips(self):
        scene = {VelocitySetting.IN_START: LOW, VelocitySetting.IN_OVER: ONE_BAR}
        self.assertEqual(velocity_of(scene_settings=scene, clip_settings={VelocitySetting.IN_OVER: TWO_BARS}).ramp_in, VelocityRamp(LOW, velocity_ramps.AS_WRITTEN, TWO_BARS, True))

    def test_a_clips_velocity_is_where_its_scenes_ramp_ends(self):
        scene = {VelocitySetting.IN_START: LOW, VelocitySetting.IN_OVER: ONE_BAR}
        data = lead_of(scene=scene, clip={VelocitySetting.LEVEL: HALF}, repeat=TWO_BARS)
        self.assertEqual(played(data)[test_shapes.STEPS:], [HALF] * test_shapes.STEPS)
        self.assertEqual(played(data)[0], LOW)

    def test_a_scene_alone_says_how_its_clips_play_and_what_stands_for_it(self):
        still = velocity_of(scene_settings={})
        self.assertTrue(still.changes_nothing())
        self.assertEqual(still.typical(), velocity_ramps.AS_WRITTEN)
        ramped = velocity_of(scene_settings={VelocitySetting.LEVEL: WRITTEN, VelocitySetting.IN_START: HALF, VelocitySetting.IN_OVER: ONE_BAR})
        self.assertFalse(ramped.changes_nothing())
        self.assertEqual(ramped.typical(), (HALF + WRITTEN) / 2)


class TestThePercentageAtATime(unittest.TestCase):

    def test_inside_and_outside_the_ramps(self):
        velocity = PlacedVelocity(HALF, PlacedRamp(LOW, HALF, Rational(1), Rational(0)), PlacedRamp(HALF, WRITTEN, Rational(1), Rational(3)))
        self.assertEqual(velocity_percent_at(velocity=velocity, time=Rational(0)), LOW)
        self.assertEqual(velocity_percent_at(velocity=velocity, time=Rational(1, 2)), (LOW + HALF) / 2)
        self.assertEqual(velocity_percent_at(velocity=velocity, time=Rational(2)), HALF)
        self.assertEqual(velocity_percent_at(velocity=velocity, time=Rational(7, 2)), (HALF + WRITTEN) / 2)
        self.assertEqual(velocity_percent_at(velocity=velocity, time=Rational(5)), WRITTEN)


class TestVelocitySettingsInAFile(unittest.TestCase):

    def test_a_percentage_out_of_range_is_refused(self):
        for name in (VelocitySetting.LEVEL, VelocitySetting.IN_START, VelocitySetting.OUT_END):
            with self.subTest(name=name), self.assertRaises(SongFileError):
                setlist_from_data(lead_of(scene={name: limits.MAX_VELOCITY_PERCENT + 1}))

    def test_bars_out_of_range_are_refused_on_a_scene_and_on_a_clip(self):
        with self.assertRaises(SongFileError):
            setlist_from_data(lead_of(scene={VelocitySetting.IN_OVER: limits.MIN_RAMP_BARS - 1}))
        with self.assertRaises(SongFileError):
            setlist_from_data(lead_of(clip={VelocitySetting.OUT_OVER: limits.MAX_RAMP_BARS + 1}))

    def test_a_scenes_or_a_clips_swell_is_no_longer_a_setting(self):
        with self.assertRaises(SongFileError):
            setlist_from_data(lead_of(scene={OLD_SWELL_START: HALF}))

    def test_they_are_written_back_as_read(self):
        scene = {VelocitySetting.LEVEL: HALF, VelocitySetting.IN_START: LOW, VelocitySetting.IN_OVER: ONE_BAR}
        clip = {VelocitySetting.OUT_END: QUARTER, VelocitySetting.OUT_OVER: TWO_BARS}
        written = next(iter(setlist_from_data(lead_of(scene=scene, clip=clip)).to_data()[Section.SONGS].values()))[Section.SCENES][0]
        self.assertEqual({name: written[name] for name in scene}, scene)
        self.assertEqual({name: written[SceneSetting.TRACKS][test_registers.LEAD][name] for name in clip}, clip)

    def test_the_setters_refuse_what_a_file_refuses(self):
        song = next(iter(setlist_from_data(lead_of()).get_songs()))
        scene = song.get_scenes()[0]
        with self.assertRaises(ValueError):
            scene.set_velocity_setting(name=VelocitySetting.LEVEL, value=limits.MAX_VELOCITY_PERCENT + 1)
        with self.assertRaises(ValueError):
            scene.get_clip_slot(test_registers.LEAD).set_velocity_setting(name=VelocitySetting.IN_OVER, value=limits.MIN_RAMP_BARS - 1)
        scene.set_velocity_setting(name=VelocitySetting.LEVEL, value=HALF)
        scene.set_velocity_setting(name=VelocitySetting.LEVEL, value=None)
        self.assertTrue(scene.get_velocity().changes_nothing())

