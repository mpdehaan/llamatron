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

"""Modulators as a song plays: a wave moving notes and velocities on the steps that read it, a step's set starting the wave again,
a modulator of one value staying a constant, a rate in hertz counted in seconds through the tempo, and a statement reading one."""

import unittest

from llamatron.composition.file_format import ClipSlotSetting, ModulatorName, ModulatorSetting, Operator, PatternSetting, RateIn, Row, SceneSetting, SongSetting, WaveShape
from llamatron.composition.modulator import Modulator
from tests.support import song_testing
from tests.support.rendering import render_data
from tests.support.song_testing import clip, pitches, with_parts

STEPS = 8
# The octave whose first degree is middle C.
OCTAVE = 5
EIGHTH = '1/8'
MIDDLE_C = 60
# The C major scale's notes from middle C, the degrees a wave from 0 to 4 moves a note to.
UP_THE_SCALE = [60, 62, 64, 65, 67]
TRIANGLE_OVER_A_BAR = [60, 62, 64, 65, 67, 65, 64, 62]
FOUR = 4
TWO = 2
FAST = 240
ONE_HERTZ = 1
TUNE = 'tune'


def played(*, rows, modulators, repeat=1, tempo=None):
    """Return the pitches the lead plays: a bar of eighths on middle C with the rows given, under the modulators given."""
    pattern = {PatternSetting.STEPS: STEPS, PatternSetting.STEP_SIZE: EIGHTH, Row.DEGREE: [1] * STEPS, Row.OCTAVE: [OCTAVE] * STEPS, **rows}
    data = with_parts(patterns={TUNE: pattern}, scenes=[{SceneSetting.TRACKS: {song_testing.LEAD: {ClipSlotSetting.PATTERN: TUNE, ClipSlotSetting.REPEAT: repeat}}}], modulators=modulators)
    if tempo is not None:
        data[SongSetting.TEMPO] = tempo
    return pitches(clip(song=render_data(data), scene=1, track=song_testing.LEAD))


def triangle(**more):
    return {ModulatorName.XMOD: {ModulatorSetting.SHAPE: WaveShape.TRIANGLE, ModulatorSetting.MAXIMUM: FOUR, **more}}


class TestModulatorsPlaying(unittest.TestCase):

    def test_a_wave_moves_the_notes_of_the_steps_that_read_it_and_goes_on_across_passes(self):
        self.assertEqual(played(rows={Row.XMOD_NOTE: [1] * STEPS}, modulators=triangle(), repeat=TWO), TRIANGLE_OVER_A_BAR * TWO)
        self.assertEqual(played(rows={Row.XMOD_NOTE: [1, 0, 0, 0, 1, 0, 0, 0]}, modulators=triangle()), [60, 60, 60, 60, 67, 60, 60, 60])

    def test_a_steps_set_starts_the_wave_again_from_its_value(self):
        sets = [None, None, None, None, 0, None, None, None]
        self.assertEqual(played(rows={Row.XMOD_NOTE: [1] * STEPS, Row.XMOD_SET: sets}, modulators=triangle()), [60, 62, 64, 65, 60, 62, 64, 65])

    def test_a_modulator_of_one_value_is_a_constant(self):
        flat = {ModulatorName.WMOD: {ModulatorSetting.SHAPE: WaveShape.SAW, ModulatorSetting.MINIMUM: TWO, ModulatorSetting.START: TWO, ModulatorSetting.MAXIMUM: TWO}}
        self.assertEqual(played(rows={Row.WMOD_NOTE: [1] * STEPS, Row.WMOD_SET: [None, 0, None, None, None, None, None, None]}, modulators=flat), [UP_THE_SCALE[TWO]] * STEPS)

    def test_a_rate_in_hertz_counts_seconds_whatever_the_tempo_and_bars_follow_it(self):
        # At 240 a bar of eighths takes one second, so one hertz is one cycle a bar, as one bar is.
        in_hertz = triangle(**{ModulatorSetting.RATE_IN: RateIn.HERTZ, ModulatorSetting.HERTZ: ONE_HERTZ})
        self.assertEqual(played(rows={Row.XMOD_NOTE: [1] * STEPS}, modulators=in_hertz, tempo=FAST), TRIANGLE_OVER_A_BAR)
        # At 120 the bar takes two seconds, so the wave in hertz goes round twice in it, and the one in bars still once.
        self.assertEqual(played(rows={Row.XMOD_NOTE: [1] * STEPS}, modulators=in_hertz), [60, 64, 67, 64, 60, 64, 67, 64])
        self.assertEqual(played(rows={Row.XMOD_NOTE: [1] * STEPS}, modulators=triangle()), TRIANGLE_OVER_A_BAR)

    def test_a_statement_reads_a_modulator_as_it_reads_a_register(self):
        mutes = {Row.MUTE_C1: [ModulatorName.XMOD] * STEPS, Row.MUTE_C2: [Operator.MORE] * STEPS, Row.MUTE_C3: [TWO] * STEPS}
        self.assertEqual(played(rows=mutes, modulators=triangle()), [MIDDLE_C] * 5)

    def test_a_default_modulator_reads_as_nothing(self):
        self.assertTrue(Modulator().is_default())
        self.assertEqual(played(rows={Row.YMOD_NOTE: [1] * STEPS}, modulators={}), [MIDDLE_C] * STEPS)


if __name__ == '__main__':
    unittest.main()
