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
"""The descriptions of settings (composition/setting.py): each kind's check, the allowed value
nearest a wrong one, and the rules that every setting a file can hold is described once and that
reading a file and calling a setter refuse a value in the same words."""

import inspect
import unittest

from llamatron.composition import clip_slot, file_format, generator_settings, groove, instrument, named_scale, pattern, register, scene, setlist, song, track
from llamatron.composition.clip_slot import FIRST_MORPH_STYLE, MORPH_STYLES, ClipSlot
from llamatron.composition.checks import listed
from llamatron.composition.file_format import (
    DIRECTIONS, OCTAVE_LABEL_CHOICES, ClipSlotSetting, GrooveSetting, InstrumentSetting, PatternSetting, RegisterSetting, ScaleSetting, SceneSetting, Section,
    SetlistSetting, SongSetting, TrackSetting,
)
from llamatron.composition.file_format import DRIFT_VERSIONS, DriftValue
from llamatron.composition.generator_settings import HocketSetting, HocketSettings, DriftSetting, DriftSettings, ProgressionSetting, ProgressionSettings, ShapeSetting, VoiceLeadingSetting, VoiceLeadingSettings, StepRowSetting, GlideSettings, ShortenSettings, RushSettings, SwellSettings, versioned, ArpSetting, ArpSettings, AutoRatchetSetting, AutoRatchetSettings
from llamatron.composition.groove import Groove, new_groove
from llamatron.composition.instrument import Instrument
from llamatron.music.midi import MAX_CHANNEL
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.limits import MAX_OCTAVE, MAX_REGISTER_VALUE, MAX_TRANSPOSE, MIN_OCTAVE, MIN_REPEAT
from llamatron.composition.named_scale import NamedScale, scale_type_name
from llamatron.composition.pattern import Pattern
from llamatron.composition.register import Register
from llamatron.composition.scene import Scene
from llamatron.composition.setlist import Setlist
from llamatron.composition.corrections import LEFT_OUT, NO_NEAREST_VALUE
from llamatron.composition.setting import Checked, Choice, Flag, Setting, Text, WholeNumber, check_settings, described
from llamatron.composition.song_file_error import SongFileError
from llamatron.composition.track import Track
from llamatron.generators.arp import MAX_OCTAVE_RANGE
from llamatron.music.note import NoteName
from llamatron.music.scale import ScaleType
from llamatron.strings.names import MSG_NEW_PATTERN_NAME, MSG_NEW_TRACK_NAME

# The settings the tests of each kind describe, and the messages they refuse with.
SPEED = 'speed'
COLOUR = 'colour'
BAD_FLAG = '{name} must be true or false, got {value!r}'
BAD_NUMBER = '{name} must be an integer from {lowest} to {highest}, got {value!r}'
BAD_CHOICE = '{name} must be one of: {choices}, got {value!r}'
BAD_TEXT = '{name} must be text, got {value!r}'
ODD = 'odd numbers are refused'
LOWEST = 1
HIGHEST = 10
BELOW = -5
ABOVE = 99
INSIDE = 4
NOT_A_NUMBER = 'four'
HALF = 1.5
# Values that are neither true nor false, and values that aren't whole numbers, though Python counts some of them as such.
NOT_FLAGS = (1, 0, None, 'true')
NOT_WHOLE_NUMBERS = (NOT_A_NUMBER, True, None, HALF)
NOT_TEXT = (3, None, ['red'])
NO_TEXT = ''
# A step size, as a file writes one.
EIGHTH = '1/8'
RED = 'red'
BLUE = 'blue'
GREEN = 'green'
COLOURS = [RED, BLUE]
ODD_NUMBER = 3
EVEN_NUMBER = 4
A_SONG = 'the song'
# Where the tests say a file's value is.
HERE = 'here'
# A pattern's size, for the tests that need one.
STEPS = 4
FIRST_SCENE = 0
NOT_A_NAME = 'nothing'
NOT_A_DIRECTION = 'sideways'
NOT_OCTAVE_LABELS = 'roman'
NOT_A_ROOT = 'H'
NOT_A_LENGTH = 'long'
# The names a file gives a new set's first pattern and track.
FIRST = 1
PATTERN_ONE = MSG_NEW_PATTERN_NAME.format(number=FIRST)
TRACK_ONE = MSG_NEW_TRACK_NAME.format(number=FIRST)
# The modules that hold classes of setting names.
NAMING_MODULES = [file_format, generator_settings]
SETTING_CLASS_ENDING = 'Setting'
# Each class of setting names, the descriptions of those settings, and the names that aren't settings with a
# value of their own to check: a pattern's steps are its size, and a scene's tracks are its clips.
DESCRIBED = [
    (SetlistSetting, setlist.SETTINGS, ()),
    (SongSetting, song.SETTINGS, ()),
    (ScaleSetting, named_scale.SETTINGS, ()),
    (GrooveSetting, groove.SETTINGS, ()),
    (InstrumentSetting, instrument.SETTINGS, ()),
    (TrackSetting, track.SETTINGS, ()),
    (PatternSetting, pattern.SETTINGS, (PatternSetting.STEPS,)),
    # chain is only read, from a file saved before a clip held a list of chains.
    (ClipSlotSetting, clip_slot.SETTINGS, (ClipSlotSetting.CHAIN,)),
    (SceneSetting, scene.SETTINGS, (SceneSetting.TRACKS,)),
    # wrap is only read, from a file saved before at_limit came.
    (RegisterSetting, register.SETTINGS, (RegisterSetting.WRAP,)),
    (ArpSetting, ArpSettings.SETTINGS, ()),
    (AutoRatchetSetting, AutoRatchetSettings.SETTINGS, ()),
    # A drift's own settings; each version's values are named from DriftValue, which the test below holds them to.
    (DriftSetting, {name: setting for name, setting in DriftSettings.SETTINGS.items() if name in vars(DriftSetting).values()}, ()),
    # A Swell's settings are every shape generator's, and an accent besides.
    (ShapeSetting, SwellSettings.SETTINGS, ()),
    (ProgressionSetting, ProgressionSettings.SETTINGS, ()),
    (VoiceLeadingSetting, VoiceLeadingSettings.SETTINGS, ()),
    # A Glide's, a Shorten's, a Rush's and a Drag's settings share one class of names.
    (StepRowSetting, {**GlideSettings.SETTINGS, **ShortenSettings.SETTINGS, **RushSettings.SETTINGS}, ()),
    (HocketSetting, HocketSettings.SETTINGS, ()),
]


def names_in(holder):
    """Return the names a class of constants holds."""
    return {value for name, value in vars(holder).items() if not name.startswith('_')}


def setting_classes():
    """Return every class of setting names the program defines."""
    return {
        member for module in NAMING_MODULES for name, member in vars(module).items()
        if inspect.isclass(member) and name.endswith(SETTING_CLASS_ENDING) and member.__module__ == module.__name__
    }


def refuse_odd(value):
    if value % 2:
        raise InvalidValue(ODD)


def refuse_unless_the_song(*, value, song):
    if song != A_SONG:
        raise InvalidValue(ODD)


class TestFlag(unittest.TestCase):

    def setUp(self):
        self.flag = Flag(name=SPEED, error=BAD_FLAG)

    def test_it_takes_true_and_false(self):
        self.flag.check(True)
        self.flag.check(False)

    def test_it_refuses_anything_else_in_its_own_words(self):
        for value in NOT_FLAGS:
            with self.subTest(value=value), self.assertRaises(InvalidValue) as refused:
                self.flag.check(value)
            self.assertEqual(str(refused.exception), BAD_FLAG.format(name=SPEED, value=value))

    def test_nothing_is_near_a_wrong_value(self):
        self.assertIs(self.flag.nearest(1), NO_NEAREST_VALUE)


class TestWholeNumber(unittest.TestCase):

    def setUp(self):
        self.number = WholeNumber(name=SPEED, lowest=LOWEST, highest=HIGHEST, error=BAD_NUMBER)

    def test_it_takes_its_range_and_both_ends(self):
        for value in (LOWEST, INSIDE, HIGHEST):
            self.number.check(value)

    def test_it_refuses_what_is_outside_or_not_a_whole_number(self):
        for value in (BELOW, ABOVE, *NOT_WHOLE_NUMBERS):
            with self.subTest(value=value), self.assertRaises(InvalidValue) as refused:
                self.number.check(value)
            self.assertEqual(str(refused.exception), BAD_NUMBER.format(name=SPEED, lowest=LOWEST, highest=HIGHEST, value=value))

    def test_the_nearest_value_is_the_nearest_end(self):
        self.assertEqual(self.number.nearest(BELOW), LOWEST)
        self.assertEqual(self.number.nearest(ABOVE), HIGHEST)
        self.assertEqual(self.number.nearest(INSIDE), INSIDE)

    def test_nothing_is_near_what_is_not_a_whole_number(self):
        for value in NOT_WHOLE_NUMBERS:
            with self.subTest(value=value):
                self.assertIs(self.number.nearest(value), NO_NEAREST_VALUE)

    def test_a_range_with_no_highest_has_only_a_lowest_end(self):
        number = WholeNumber(name=SPEED, lowest=LOWEST, error=BAD_NUMBER)
        number.check(ABOVE)
        self.assertEqual(number.nearest(BELOW), LOWEST)
        self.assertEqual(number.nearest(ABOVE), ABOVE)
        with self.assertRaises(InvalidValue):
            number.check(BELOW)

    def test_a_range_with_no_ends_takes_any_whole_number(self):
        number = WholeNumber(name=SPEED, error=BAD_NUMBER)
        number.check(BELOW)
        number.check(ABOVE)
        with self.assertRaises(InvalidValue):
            number.check(NOT_A_NUMBER)


class TestChoice(unittest.TestCase):

    def setUp(self):
        self.choice = Choice(name=COLOUR, choices=COLOURS, default=RED, error=BAD_CHOICE)

    def test_it_takes_its_choices(self):
        for value in COLOURS:
            self.choice.check(value)

    def test_it_refuses_anything_else_and_lists_the_choices(self):
        for value in (GREEN, *NOT_TEXT):
            with self.subTest(value=value), self.assertRaises(InvalidValue) as refused:
                self.choice.check(value)
            self.assertEqual(str(refused.exception), BAD_CHOICE.format(name=COLOUR, choices=listed(COLOURS), value=value))

    def test_the_nearest_value_is_the_default(self):
        self.assertEqual(self.choice.nearest(GREEN), RED)

    def test_a_default_can_be_to_leave_the_setting_out(self):
        self.assertIs(Choice(name=COLOUR, choices=COLOURS, default=LEFT_OUT, error=BAD_CHOICE).nearest(GREEN), LEFT_OUT)


class TestText(unittest.TestCase):

    def test_it_takes_text_and_refuses_the_rest(self):
        text = Text(name=COLOUR, error=BAD_TEXT)
        text.check(RED)
        text.check(NO_TEXT)
        for value in NOT_TEXT:
            with self.subTest(value=value), self.assertRaises(InvalidValue) as refused:
                text.check(value)
            self.assertEqual(str(refused.exception), BAD_TEXT.format(name=COLOUR, value=value))
        self.assertIs(text.nearest(ODD_NUMBER), NO_NEAREST_VALUE)


class TestChecked(unittest.TestCase):

    def test_its_function_decides(self):
        checked = Checked(name=SPEED, check=refuse_odd)
        checked.check(EVEN_NUMBER)
        with self.assertRaisesRegex(InvalidValue, ODD):
            checked.check(ODD_NUMBER)
        self.assertIs(checked.nearest(ODD_NUMBER), NO_NEAREST_VALUE)

    def test_a_function_that_needs_the_song_is_given_it(self):
        checked = Checked(name=SPEED, check=refuse_unless_the_song, needs_song=True)
        checked.check(EVEN_NUMBER, song=A_SONG)
        with self.assertRaisesRegex(InvalidValue, ODD):
            checked.check(EVEN_NUMBER, song=None)


class TestSettingsOfAFile(unittest.TestCase):
    """Settings described together, and checked in the data a file holds."""

    def setUp(self):
        self.settings = described(
            WholeNumber(name=SPEED, lowest=LOWEST, highest=HIGHEST, error=BAD_NUMBER),
            Choice(name=COLOUR, choices=COLOURS, default=RED, error=BAD_CHOICE),
        )

    def test_they_are_kept_by_name_in_the_order_given(self):
        self.assertEqual(list(self.settings), [SPEED, COLOUR])
        self.assertEqual(self.settings[SPEED].get_name(), SPEED)

    def test_a_setting_the_data_leaves_out_is_not_checked(self):
        check_settings(settings=self.settings, data={})

    def test_a_setting_the_data_holds_is_checked(self):
        check_settings(settings=self.settings, data={SPEED: INSIDE, COLOUR: BLUE})
        with self.assertRaises(InvalidValue):
            check_settings(settings=self.settings, data={SPEED: ABOVE})
        with self.assertRaises(InvalidValue):
            check_settings(settings=self.settings, data={COLOUR: None})

    def test_the_first_wrong_setting_the_data_holds_is_the_one_refused(self):
        with self.assertRaises(InvalidValue) as refused:
            check_settings(settings=self.settings, data={COLOUR: GREEN, SPEED: ABOVE})
        self.assertIn(COLOUR, str(refused.exception))

    def test_a_name_that_is_not_a_setting_is_left_to_the_class(self):
        check_settings(settings=self.settings, data={SPEED: INSIDE, NOT_A_NAME: ABOVE})

    def test_settings_can_be_left_to_the_class(self):
        check_settings(settings=self.settings, data={SPEED: ABOVE}, leaving_out=(SPEED,))

    def test_a_plain_setting_has_no_check_of_its_own(self):
        with self.assertRaises(NotImplementedError):
            Setting(name=SPEED).check(INSIDE)


class TestEverySettingIsDescribedOnce(unittest.TestCase):
    """The rule: every setting a file can hold has one description, which reading the file and the setter both ask."""

    def test_every_class_of_setting_names_is_listed_here(self):
        self.assertEqual(setting_classes(), {names for names, settings, others in DESCRIBED})

    def test_every_setting_name_has_a_description_and_nothing_else_does(self):
        for names, settings, others in DESCRIBED:
            with self.subTest(names=names.__name__):
                self.assertEqual(set(settings), names_in(names) - set(others))

    def test_a_drifts_other_settings_are_each_version_of_each_value(self):
        own = {value for name, value in vars(DriftSetting).items() if not name.startswith('_')}
        versions = {versioned(version=version, value=value) for version in DRIFT_VERSIONS for value in names_in(DriftValue)}
        self.assertEqual(set(DriftSettings.SETTINGS) - own, versions)

    def test_every_description_is_a_setting_under_its_own_name(self):
        for names, settings, others in DESCRIBED:
            for name, setting in settings.items():
                with self.subTest(names=names.__name__, name=name):
                    self.assertIsInstance(setting, Setting)
                    self.assertEqual(setting.get_name(), name)


class TestReadingAndSettingAgree(unittest.TestCase):
    """A value a setter refuses is refused in the same words when a file holds it, after the place in the file."""

    def setUp(self):
        self.setlist = Setlist.new()
        self.song = self.setlist.get_song(self.setlist.first_song_name())

    def assert_same_refusal(self, *, read, change):
        """Check that reading and changing both refuse, and that the file's message is the setter's with a place in front."""
        with self.assertRaises(InvalidValue) as refused:
            change()
        with self.assertRaises(SongFileError) as unreadable:
            read()
        self.assertTrue(str(unreadable.exception).endswith(str(refused.exception)), (str(unreadable.exception), str(refused.exception)))

    def test_a_track(self):
        for name, value, change in [
            (TrackSetting.TRANSPOSE, MAX_TRANSPOSE + 1, lambda: Track().set_transpose(MAX_TRANSPOSE + 1)),
            (TrackSetting.DRUM, 1, lambda: Track().set_drum(1)),
            (TrackSetting.MUTE, None, lambda: Track().set_mute(None)),
            (TrackSetting.LOWEST_OCTAVE, MIN_OCTAVE - 1, lambda: Track().set_lowest_octave(MIN_OCTAVE - 1)),
            (TrackSetting.HIGHEST_OCTAVE, MAX_OCTAVE + 1, lambda: Track().set_highest_octave(MAX_OCTAVE + 1)),
            (TrackSetting.GROOVE, NOT_A_NAME, lambda: Track().set_groove_choice(choice=NOT_A_NAME, song=self.song)),
        ]:
            with self.subTest(name=name):
                self.assert_same_refusal(read=lambda: Track.from_data(data={name: value}, where=HERE, song=self.song), change=change)

    def test_a_clip(self):
        clip = ClipSlot(pattern=PATTERN_ONE)
        for name, value, change in [
            (ClipSlotSetting.REPEAT, MIN_REPEAT - 1, lambda: clip.set_repeat(MIN_REPEAT - 1)),
            (ClipSlotSetting.LOOP, 1, lambda: clip.set_loop(1)),
            (ClipSlotSetting.DIRECTION, NOT_A_DIRECTION, lambda: clip.set_direction(NOT_A_DIRECTION)),
            (ClipSlotSetting.PATTERN, NOT_A_NAME, lambda: clip.set_pattern_name(name=NOT_A_NAME, song=self.song)),
            (ClipSlotSetting.CHAINS, [NOT_A_NAME], lambda: clip.set_chain_names(names=[NOT_A_NAME], song=self.song)),
            (ClipSlotSetting.GRAB_TRACK, NOT_A_NAME, lambda: clip.set_grab_track(name=NOT_A_NAME, song=self.song, own_track=TRACK_ONE)),
            (ClipSlotSetting.NAME, ODD_NUMBER, lambda: clip.set_name(ODD_NUMBER)),
        ]:
            with self.subTest(name=name):
                data = {ClipSlotSetting.PATTERN: PATTERN_ONE, name: value}
                self.assert_same_refusal(read=lambda: ClipSlot.from_data(data=data, where=HERE, song=self.song, track=TRACK_ONE), change=change)

    def test_a_scene(self):
        scene_one = self.song.get_scene(FIRST_SCENE)
        for name, value, change in [
            (SceneSetting.REPEAT, MIN_REPEAT - 1, lambda: scene_one.set_repeat(MIN_REPEAT - 1)),
            (SceneSetting.SCALE, NOT_A_NAME, lambda: scene_one.set_scale_name(name=NOT_A_NAME, song=self.song)),
            (SceneSetting.TEMPO, NOT_A_LENGTH, lambda: scene_one.set_tempo(NOT_A_LENGTH)),
            (SceneSetting.GROOVE, NOT_A_NAME, lambda: scene_one.set_groove_choice(choice=NOT_A_NAME, song=self.song)),
        ]:
            with self.subTest(name=name):
                self.assert_same_refusal(read=lambda: Scene.from_data(data={name: value, SceneSetting.TRACKS: {}}, where=HERE, song=self.song), change=change)

    def test_a_song(self):
        for name, value, change in [
            (SongSetting.TEMPO, NOT_A_LENGTH, lambda: self.song.set_tempo(NOT_A_LENGTH)),
            (SongSetting.TIME_SIGNATURE, NOT_A_LENGTH, lambda: self.song.set_time_signature(NOT_A_LENGTH)),
            (SongSetting.ENTRY_SIZE, NOT_A_LENGTH, lambda: self.song.set_entry_size(NOT_A_LENGTH)),
            (SongSetting.SCALE, NOT_A_NAME, lambda: self.song.set_scale_name(NOT_A_NAME)),
            (SongSetting.SEED, NOT_A_NUMBER, lambda: self.song.set_seed(NOT_A_NUMBER)),
            (SongSetting.GROOVE, NOT_A_NAME, lambda: self.song.set_groove_name(NOT_A_NAME)),
        ]:
            with self.subTest(name=name):
                data = {Section.SONGS: {A_SONG: {name: value}}}
                self.assert_same_refusal(read=lambda: Setlist.from_data(data=data), change=change)

    def test_a_set(self):
        for name, value, change in [
            (SetlistSetting.DEFAULT_OCTAVE, MAX_OCTAVE + 1, lambda: self.setlist.set_default_octave(MAX_OCTAVE + 1)),
            (SetlistSetting.DEFAULT_DRUM_OCTAVE, MIN_OCTAVE - 1, lambda: self.setlist.set_default_drum_octave(MIN_OCTAVE - 1)),
            (SetlistSetting.OCTAVE_LABELS, NOT_OCTAVE_LABELS, lambda: self.setlist.set_octave_labels(NOT_OCTAVE_LABELS)),
            (SetlistSetting.PROTECTED, 1, lambda: self.setlist.set_protected(1)),
            (SetlistSetting.STEP_SIZE, NOT_A_LENGTH, lambda: self.setlist.set_step_size(NOT_A_LENGTH)),
            (SetlistSetting.VERSION, NOT_A_LENGTH, lambda: self.setlist.set_version(NOT_A_LENGTH)),
        ]:
            with self.subTest(name=name):
                self.assert_same_refusal(read=lambda: Setlist.from_data(data={name: value}), change=change)

    def test_a_pattern(self):
        tune = Pattern.from_data(data={PatternSetting.STEPS: STEPS}, where=HERE)
        for name, value, change in [
            (PatternSetting.DIRECTION, NOT_A_DIRECTION, lambda: tune.set_direction(NOT_A_DIRECTION)),
            (PatternSetting.DRUM, 1, lambda: tune.set_drum(1)),
            (PatternSetting.STEP_SIZE, NOT_A_LENGTH, lambda: tune.set_step_size(NOT_A_LENGTH)),
            (PatternSetting.TIME_SIGNATURE, NOT_A_LENGTH, lambda: tune.set_time_signature(NOT_A_LENGTH)),
            (PatternSetting.ENTRY_SIZE, NOT_A_LENGTH, lambda: tune.set_entry_size(NOT_A_LENGTH)),
        ]:
            with self.subTest(name=name):
                self.assert_same_refusal(read=lambda: Pattern.from_data(data={PatternSetting.STEPS: STEPS, name: value}, where=HERE), change=change)

    def test_a_register(self):
        for name, value in [(RegisterSetting.MAXIMUM, MAX_REGISTER_VALUE + 1), (RegisterSetting.RESET_EACH_SCENE, 1)]:
            with self.subTest(name=name):
                self.assert_same_refusal(
                    read=lambda: Register.from_data(data={name: value}, where=HERE),
                    change=lambda: Register().set_setting(name=name, value=value),
                )

    def test_a_scale(self):
        scale = NamedScale(root=NoteName.C, kind=scale_type_name(ScaleType.MAJOR))
        self.assert_same_refusal(
            read=lambda: NamedScale.from_data(data={ScaleSetting.ROOT: NOT_A_ROOT, ScaleSetting.TYPE: scale_type_name(ScaleType.MAJOR)}, where=HERE),
            change=lambda: scale.set_root(NOT_A_ROOT),
        )
        self.assert_same_refusal(
            read=lambda: NamedScale.from_data(data={ScaleSetting.ROOT: NoteName.C, ScaleSetting.TYPE: NOT_A_NAME}, where=HERE),
            change=lambda: scale.set_kind(NOT_A_NAME),
        )

    def test_a_groove(self):
        swing = new_groove()
        self.assert_same_refusal(
            read=lambda: Groove.from_data(data={GrooveSetting.CELLS: swing.get_cells(), GrooveSetting.CELL_LENGTH: NOT_A_LENGTH}, where=HERE),
            change=lambda: swing.set_cell_length(NOT_A_LENGTH),
        )

    def test_an_instrument(self):
        synth = Instrument()
        self.assert_same_refusal(
            read=lambda: Instrument.from_data(data={InstrumentSetting.CHANNEL: MAX_CHANNEL + 1}, where=HERE),
            change=lambda: synth.set_channel(MAX_CHANNEL + 1),
        )
        self.assert_same_refusal(
            read=lambda: Instrument.from_data(data={InstrumentSetting.DEVICE: NOT_TEXT}, where=HERE),
            change=lambda: synth.set_device(NOT_TEXT),
        )

    def test_a_generator(self):
        for name, value in [(ArpSetting.OCTAVE_RANGE, MAX_OCTAVE_RANGE + 1), (ArpSetting.ORDER, NOT_A_DIRECTION), (ArpSetting.SEED, NOT_A_NUMBER)]:
            with self.subTest(name=name):
                self.assert_same_refusal(
                    read=lambda: ArpSettings.from_data(data={ArpSetting.STEP: EIGHTH, name: value}, where=HERE),
                    change=lambda: ArpSettings.new().set_setting(name=name, value=value),
                )
        self.assert_same_refusal(
            read=lambda: AutoRatchetSettings.from_data(data={AutoRatchetSetting.COUNTS: FIRST}, where=HERE),
            change=lambda: AutoRatchetSettings.new().set_setting(name=AutoRatchetSetting.COUNTS, value=FIRST),
        )


class TestAChoiceKeepsItsFileNames(unittest.TestCase):
    """The choices a description lists are the names a file writes, so a right value is taken as it always was."""

    def test_every_direction_is_taken_by_a_pattern_and_a_clip(self):
        for direction in DIRECTIONS:
            with self.subTest(direction=direction):
                pattern.SETTINGS[PatternSetting.DIRECTION].check(direction)
                clip_slot.SETTINGS[ClipSlotSetting.DIRECTION].check(direction)

    def test_every_morph_style_and_octave_label_is_taken(self):
        for style in MORPH_STYLES:
            clip_slot.SETTINGS[ClipSlotSetting.MORPH_STYLE].check(style)
        for labels in OCTAVE_LABEL_CHOICES:
            setlist.SETTINGS[SetlistSetting.OCTAVE_LABELS].check(labels)

    def test_a_wrong_choice_falls_back_to_the_default(self):
        self.assertIs(pattern.SETTINGS[PatternSetting.DIRECTION].nearest(NOT_A_DIRECTION), LEFT_OUT)
        self.assertIs(clip_slot.SETTINGS[ClipSlotSetting.DIRECTION].nearest(NOT_A_DIRECTION), LEFT_OUT)
        self.assertIs(setlist.SETTINGS[SetlistSetting.OCTAVE_LABELS].nearest(NOT_OCTAVE_LABELS), LEFT_OUT)
        self.assertEqual(clip_slot.SETTINGS[ClipSlotSetting.MORPH_STYLE].nearest(NOT_A_NAME), FIRST_MORPH_STYLE)

    def test_a_number_out_of_range_has_the_nearest_end(self):
        self.assertEqual(track.SETTINGS[TrackSetting.TRANSPOSE].nearest(MAX_TRANSPOSE + 1), MAX_TRANSPOSE)
        self.assertEqual(track.SETTINGS[TrackSetting.TRANSPOSE].nearest(-MAX_TRANSPOSE - 1), -MAX_TRANSPOSE)
        self.assertEqual(track.SETTINGS[TrackSetting.HIGHEST_OCTAVE].nearest(MAX_OCTAVE + 1), MAX_OCTAVE)
        self.assertEqual(clip_slot.SETTINGS[ClipSlotSetting.REPEAT].nearest(MIN_REPEAT - 1), MIN_REPEAT)
        self.assertEqual(scene.SETTINGS[SceneSetting.REPEAT].nearest(MIN_REPEAT - 1), MIN_REPEAT)
        self.assertEqual(setlist.SETTINGS[SetlistSetting.DEFAULT_OCTAVE].nearest(MAX_OCTAVE + 1), MAX_OCTAVE)
        self.assertEqual(register.SETTINGS[RegisterSetting.MAXIMUM].nearest(MAX_REGISTER_VALUE + 1), MAX_REGISTER_VALUE)
        self.assertEqual(ArpSettings.SETTINGS[ArpSetting.OCTAVE_RANGE].nearest(MAX_OCTAVE_RANGE + 1), MAX_OCTAVE_RANGE)


if __name__ == '__main__':
    unittest.main()
