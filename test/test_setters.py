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

"""The composition objects' setters: each checks a value the way reading a file does, raises
InvalidValue when it's wrong, and leaves the object as it was."""

import unittest

from llamatron.composition.clip_slot import ClipSlot, MORPH_STYLES
from llamatron.composition.chain import Chain
from llamatron.composition.defaults import DEFAULT_TRANSPOSE
from llamatron.composition.file_format import (
    CC_ROWS, REGISTER_NAMES, ClipSlotSetting, Direction, GeneratorKind, PatternSetting, RegisterName, RegisterSetting, Row,
    SceneSetting, Section, TrackSetting,
)
from llamatron.composition.generator_settings import ArpSetting, ArpSettings, AutoRatchetSetting, AutoRatchetSettings, NO_OFFSET
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.limits import MAX_GATE, MAX_REGISTER_VALUE, MAX_TRANSPOSE, MIN_REPEAT, MIN_STEPS
from llamatron.music.midi import MAX_CC_NUMBER
from llamatron.composition.named_scale import NamedScale, scale_type_name
from llamatron.composition.pattern import Pattern
from llamatron.composition.register import Register
from llamatron.composition.scene import Scene
from llamatron.composition.setlist import NO_TEXT, Setlist
from llamatron.composition.song import Song
from llamatron.composition.track import Track
from llamatron.music.note import NoteName
from llamatron.music.scale import ScaleType

# The song the tests build: two patterns, two tracks, a scale, an arp, an AutoRatchet and a chain.
TUNE = 'tune'
ANSWER = 'answer'
LEAD = 'lead'
BASS = 'bass'
MAIN = 'main'
UP = 'up'
ROLLS = 'rolls'
NAMED = 'named'
VERSE = 'verse'
NOT_A_NAME = 'nothing'
STEPS = 4
FIRST = 0
LAST = STEPS - 1
PAST_THE_END = STEPS
TEMPO = 100
FASTER = 140
STEP_SIZE = '1/8'
MAJOR = scale_type_name(ScaleType.MAJOR)
MINOR = scale_type_name(ScaleType.MINOR)
NOT_A_SCALE_TYPE = 'wobbly'
# A degree, a velocity and a gate that the file accepts, and values it refuses.
DEGREE = 3
VELOCITY = 90
GATE = '1/4'
TOO_LONG_A_GATE = MAX_GATE + 1
NOT_A_ROW = 'colour'
A_MOD_WHEEL = 1
A_CC_VALUE = 64
TWO_REPEATS = 2
FOUR_REPEATS = 4
NEW_OCTAVE_RANGE = 2
A_STEP_VALUE = 7
TOO_FAR = MAX_TRANSPOSE + 1
NOT_A_CC_NUMBER = MAX_CC_NUMBER + 1
NO_SUCH_LANE = len(CC_ROWS)
FIRST_LANE = 0
# Register settings in and out of order.
LOW = 2
HIGH = 5
TOO_HIGH = MAX_REGISTER_VALUE + 1
AN_OFFSET = 1
ANOTHER_OFFSET = -1
PAST_THE_OFFSETS = 2
# Moving things up and down a list.
ONE_UP = -1
ONE_DOWN = 1
TWO_DOWN = 2
FIRST_STYLE = next(iter(MORPH_STYLES))
TEXT = '  Title  '


def song_with_everything():
    """Return a song with one of each kind of object, built through the set's and the song's own methods."""
    setlist = Setlist()
    setlist.add_item(section=Section.SCALES, name=MAIN, item=NamedScale(root=NoteName.C, kind=MAJOR))
    setlist.add_item(section=Section.PATTERNS, name=TUNE, item=Pattern(steps=STEPS, rows={Row.DEGREE: [DEGREE] * STEPS}))
    setlist.add_item(section=Section.PATTERNS, name=ANSWER, item=Pattern(steps=STEPS, rows={}))
    setlist.add_item(section=Section.ARPS, name=UP, item=ArpSettings.new())
    setlist.add_item(section=Section.AUTO_RATCHETS, name=ROLLS, item=AutoRatchetSettings.new())
    chain = Chain([])
    chain.add_step(kind=GeneratorKind.ARP, name=UP, setlist=setlist)
    chain.add_step(kind=GeneratorKind.AUTO_RATCHET, name=ROLLS, setlist=setlist)
    setlist.add_item(section=Section.CHAINS, name=NAMED, item=chain)
    song = Song.new(setlist=setlist)
    setlist.add_item(section=Section.SONGS, name=VERSE, item=song)
    song.set_scale_name(MAIN)
    song.set_tempo(TEMPO)
    song.add_item(section=Section.TRACKS, name=LEAD, item=Track())
    song.add_item(section=Section.TRACKS, name=BASS, item=Track())
    scene = Scene(clip_slots={}, name=VERSE)
    lead = ClipSlot()
    lead.set_pattern_name(name=TUNE, song=song)
    lead.set_chain_names(names=[NAMED], song=song)
    scene.set_clip_slot(track=LEAD, clip_slot=lead, song=song)
    bass = ClipSlot()
    bass.set_pattern_name(name=TUNE, song=song)
    bass.set_grab_track(name=LEAD, song=song, own_track=BASS)
    scene.set_clip_slot(track=BASS, clip_slot=bass, song=song)
    song.add_scene(index=FIRST, scene=scene)
    return song


class SetterTestCase(unittest.TestCase):
    """Checks that a refused change raises InvalidValue and leaves the object's data as it was."""

    def assertRefused(self, thing, method, *arguments, **named):
        before = thing.to_data()
        with self.assertRaises(InvalidValue):
            method(*arguments, **named)
        self.assertEqual(thing.to_data(), before)


class TestPattern(SetterTestCase):

    def setUp(self):
        self.pattern = Pattern(steps=STEPS, rows={})

    def test_a_value_is_set_on_a_step_and_a_blank_one_leaves_the_row_out_of_the_file(self):
        self.pattern.set_value(row=Row.VELOCITY, step=FIRST, value=VELOCITY)
        self.assertEqual(self.pattern.get_value(row=Row.VELOCITY, step=FIRST), VELOCITY)
        self.assertIn(Row.VELOCITY, self.pattern.to_data())
        self.pattern.set_value(row=Row.VELOCITY, step=FIRST, value=None)
        self.assertNotIn(Row.VELOCITY, self.pattern.to_data())
        self.assertIsNotNone(self.pattern.get_row(Row.VELOCITY))

    def test_toggle_rows_are_written_as_true_and_false(self):
        self.pattern.set_value(row=Row.GLIDE, step=FIRST, value=True)
        self.assertEqual(self.pattern.to_data()[Row.GLIDE], [True] + [False] * (STEPS - 1))

    def test_values_the_file_refuses_are_refused(self):
        self.assertRefused(self.pattern, self.pattern.set_value, row=Row.GATE, step=FIRST, value=TOO_LONG_A_GATE)
        self.assertRefused(self.pattern, self.pattern.set_value, row=NOT_A_ROW, step=FIRST, value=A_STEP_VALUE)
        self.assertRefused(self.pattern, self.pattern.set_value, row=Row.DEGREE, step=PAST_THE_END, value=DEGREE)

    def test_steps_grow_with_blanks_and_are_cut_from_the_end(self):
        self.pattern.set_value(row=Row.DEGREE, step=LAST, value=DEGREE)
        self.pattern.set_steps(STEPS + 1)
        self.assertEqual(self.pattern.get_row(Row.DEGREE), [None] * LAST + [DEGREE, None])
        self.pattern.set_steps(LAST)
        self.assertEqual(self.pattern.get_row(Row.DEGREE), [None] * LAST)
        self.assertRefused(self.pattern, self.pattern.set_steps, MIN_STEPS - 1)

    def test_a_step_is_inserted_and_removed_but_the_last_step_stays(self):
        self.pattern.set_value(row=Row.DEGREE, step=FIRST, value=DEGREE)
        self.pattern.insert_step(FIRST)
        self.assertEqual(self.pattern.get_steps(), STEPS + 1)
        self.assertEqual(self.pattern.get_value(row=Row.DEGREE, step=FIRST + 1), DEGREE)
        self.pattern.remove_step(FIRST)
        self.assertEqual(self.pattern.get_value(row=Row.DEGREE, step=FIRST), DEGREE)
        self.pattern.set_steps(MIN_STEPS)
        self.assertRefused(self.pattern, self.pattern.remove_step, FIRST)

    def test_clearing_a_steps_sound_keeps_what_a_rest_can_hold(self):
        self.pattern.set_value(row=Row.DEGREE, step=FIRST, value=DEGREE)
        self.pattern.set_value(row=Row.CC1, step=FIRST, value=A_CC_VALUE)
        self.pattern.clear_sound(FIRST)
        self.assertIsNone(self.pattern.get_value(row=Row.DEGREE, step=FIRST))
        self.assertEqual(self.pattern.get_value(row=Row.CC1, step=FIRST), A_CC_VALUE)
        self.assertTrue(self.pattern.holds_anything(FIRST))

    def test_clearing_a_steps_sound_keeps_every_register_row_and_takes_what_only_a_note_holds(self):
        register_rows = [Row.AX_NOTE, Row.BX_VELOCITY]
        self.pattern.set_value(row=Row.DEGREE, step=FIRST, value=DEGREE)
        self.pattern.set_value(row=Row.VELOCITY, step=FIRST, value=VELOCITY)
        self.pattern.set_value(row=Row.CX_ADD, step=FIRST, value=1)
        for row in register_rows:
            self.pattern.set_value(row=row, step=FIRST, value=True)
        self.pattern.clear_sound(FIRST)
        self.assertIsNone(self.pattern.get_value(row=Row.DEGREE, step=FIRST))
        self.assertIsNone(self.pattern.get_value(row=Row.VELOCITY, step=FIRST))
        self.assertEqual(self.pattern.get_value(row=Row.CX_ADD, step=FIRST), 1)
        for row in register_rows:
            self.assertTrue(self.pattern.get_value(row=row, step=FIRST), row)
        self.assertFalse(self.pattern.holds_anything(LAST))

    def test_becoming_a_drum_pattern_clears_the_notes(self):
        self.pattern.set_value(row=Row.DEGREE, step=FIRST, value=DEGREE)
        self.pattern.set_drum(True)
        self.assertTrue(self.pattern.is_drum())
        self.assertFalse(self.pattern.has_notes())
        self.pattern.set_drum(False)
        self.assertNotIn(PatternSetting.DRUM, self.pattern.to_data())

    def test_forward_is_the_direction_the_file_leaves_out(self):
        self.pattern.set_direction(Direction.REVERSE_B)
        self.assertEqual(self.pattern.to_data()[PatternSetting.DIRECTION], Direction.REVERSE_B)
        self.pattern.set_direction(Direction.FORWARD)
        self.assertNotIn(PatternSetting.DIRECTION, self.pattern.to_data())
        self.assertRefused(self.pattern, self.pattern.set_direction, NOT_A_NAME)

    def test_flipping_and_swapping_undo_themselves(self):
        self.pattern.set_value(row=Row.DEGREE, step=LAST, value=DEGREE)
        before = self.pattern.to_data()
        self.pattern.reverse_after(FIRST)
        self.assertEqual(self.pattern.get_value(row=Row.DEGREE, step=FIRST + 1), DEGREE)
        self.pattern.reverse_after(FIRST)
        self.assertEqual(self.pattern.to_data(), before)
        # Swapping around step 1 puts the last two steps first, so the note on the last step lands on step 1.
        place = self.pattern.pivot_around(FIRST + 1)
        self.assertEqual(self.pattern.get_value(row=Row.DEGREE, step=FIRST + 1), DEGREE)
        self.pattern.pivot_around(place)
        self.assertEqual(self.pattern.to_data(), before)

    def test_a_copy_has_lists_of_its_own(self):
        copy = self.pattern.copy()
        copy.set_value(row=Row.DEGREE, step=FIRST, value=DEGREE)
        self.assertFalse(self.pattern.has_notes())


class TestClipSlot(SetterTestCase):

    def setUp(self):
        self.song = song_with_everything()
        self.clip_slot = self.song.get_scene(FIRST).get_clip_slot(LEAD)

    def test_names_have_to_exist(self):
        self.assertRefused(self.clip_slot, self.clip_slot.set_pattern_name, name=NOT_A_NAME, song=self.song)
        self.assertRefused(self.clip_slot, self.clip_slot.set_chain_names, names=[NOT_A_NAME], song=self.song)
        self.assertRefused(self.clip_slot, self.clip_slot.set_grab_track, name=NOT_A_NAME, song=self.song, own_track=LEAD)
        self.assertRefused(self.clip_slot, self.clip_slot.set_grab_track, name=LEAD, song=self.song, own_track=LEAD)
        self.clip_slot.set_chain_names(names=[], song=self.song)
        self.assertEqual(self.clip_slot.get_chain_names(), [])

    def test_a_morph_needs_repeats_and_goes_when_they_do(self):
        self.assertRefused(self.clip_slot, self.clip_slot.set_morph, target=ANSWER, style=FIRST_STYLE, song=self.song)
        self.clip_slot.set_repeat(TWO_REPEATS)
        self.clip_slot.set_morph(target=ANSWER, style=FIRST_STYLE, song=self.song)
        self.assertEqual(self.clip_slot.get_morph_target(), ANSWER)
        self.assertRefused(self.clip_slot, self.clip_slot.set_morph_style, NOT_A_NAME)
        self.clip_slot.set_repeat(MIN_REPEAT)
        self.assertIsNone(self.clip_slot.get_morph_target())
        self.assertNotIn(ClipSlotSetting.REPEAT, self.clip_slot.to_data())
        self.assertRefused(self.clip_slot, self.clip_slot.set_morph_style, FIRST_STYLE)

    def test_loop_is_only_written_when_on(self):
        self.clip_slot.set_loop(True)
        self.assertTrue(self.clip_slot.loops())
        self.clip_slot.set_loop(False)
        self.assertNotIn(ClipSlotSetting.LOOP, self.clip_slot.to_data())
        self.assertRefused(self.clip_slot, self.clip_slot.set_loop, NOT_A_NAME)


class TestScene(SetterTestCase):

    def setUp(self):
        self.song = song_with_everything()
        self.scene = self.song.get_scene(FIRST)

    def test_settings_are_checked(self):
        self.assertRefused(self.scene, self.scene.set_scale_name, name=NOT_A_NAME, song=self.song)
        self.assertRefused(self.scene, self.scene.set_repeat, MIN_REPEAT - 1)
        self.assertRefused(self.scene, self.scene.set_reset, register=NOT_A_NAME, on=True)
        self.assertRefused(self.scene, self.scene.set_clip_slot, track=NOT_A_NAME, clip_slot=ClipSlot(), song=self.song)
        self.assertRefused(self.scene, self.scene.remove_clip_slot, NOT_A_NAME)
        self.scene.set_repeat(MIN_REPEAT)
        self.assertNotIn(SceneSetting.REPEAT, self.scene.to_data())

    def test_a_tempo_ramp_replaces_a_tempo_and_leaves_its_start_behind(self):
        self.scene.set_tempo(TEMPO)
        self.scene.set_tempo_ramp(start=TEMPO, end=FASTER)
        self.assertEqual((self.scene.get_tempo_setting(), self.scene.get_tempo_start(), self.scene.get_tempo_end()), (None, TEMPO, FASTER))
        self.scene.set_tempo(FASTER)
        self.assertEqual(self.scene.get_tempo_start(), FASTER)
        self.scene.clear_tempo_ramp()
        self.assertEqual((self.scene.get_tempo_setting(), self.scene.get_tempo_end()), (FASTER, None))
        self.scene.clear_tempo()
        self.assertNotIn(SceneSetting.TEMPO, self.scene.to_data())

    def test_resets_stay_in_register_order(self):
        self.scene.set_reset(register=RegisterName.DX, on=True)
        self.scene.set_reset(register=RegisterName.AX, on=True)
        self.assertEqual(self.scene.get_reset_names(), [RegisterName.AX, RegisterName.DX])
        self.scene.set_reset(register=RegisterName.AX, on=False)
        self.scene.set_reset(register=RegisterName.DX, on=False)
        self.assertNotIn(SceneSetting.RESET, self.scene.to_data())

    def test_a_grab_circle_is_found(self):
        self.assertEqual(self.scene.grab_circle(track=LEAD, other=BASS), [LEAD, BASS, LEAD])
        self.assertIsNone(self.scene.grab_circle(track=BASS, other=LEAD))

    def test_a_copy_has_clip_slots_of_its_own(self):
        copy = self.scene.copy()
        copy.remove_clip_slot(LEAD)
        self.assertTrue(self.scene.has_clip_slot(LEAD))


class TestTrack(SetterTestCase):

    def setUp(self):
        self.track = Track()

    def test_defaults_are_left_out_of_the_file(self):
        self.track.set_drum(True)
        self.track.set_mute(True)
        self.track.set_transpose(MAX_TRANSPOSE)
        self.track.set_cc_number(lane=FIRST_LANE, number=A_MOD_WHEEL)
        self.assertEqual(self.track.get_cc_numbers(), [A_MOD_WHEEL] + [None] * (len(CC_ROWS) - 1))
        self.track.set_drum(False)
        self.track.set_mute(False)
        self.track.set_transpose(DEFAULT_TRANSPOSE)
        self.track.set_cc_number(lane=FIRST_LANE, number=None)
        self.assertEqual(self.track.to_data(), {})

    def test_bad_values_are_refused(self):
        self.assertRefused(self.track, self.track.set_transpose, TOO_FAR)
        self.assertRefused(self.track, self.track.set_cc_number, lane=FIRST_LANE, number=NOT_A_CC_NUMBER)
        self.assertRefused(self.track, self.track.set_cc_number, lane=NO_SUCH_LANE, number=A_MOD_WHEEL)
        self.assertRefused(self.track, self.track.set_drum, NOT_A_NAME)
        self.assertNotIn(TrackSetting.CC, self.track.to_data())


class TestNamedScale(SetterTestCase):

    def test_root_and_kind_are_checked(self):
        scale = NamedScale(root=NoteName.C, kind=MAJOR)
        scale.set_root(NoteName.F)
        scale.set_kind(MINOR)
        self.assertEqual((scale.get_root(), scale.get_kind()), (NoteName.F, MINOR))
        self.assertRefused(scale, scale.set_root, NOT_A_NAME)
        self.assertRefused(scale, scale.set_kind, NOT_A_SCALE_TYPE)
        self.assertEqual(scale.get_size(), len(ScaleType.MINOR.value))


class TestChain(SetterTestCase):

    def setUp(self):
        self.song = song_with_everything()
        self.chain = self.song.get_chain(NAMED)

    def test_steps_name_generators_the_song_has(self):
        self.assertRefused(self.chain, self.chain.add_step, kind=GeneratorKind.ARP, name=NOT_A_NAME, setlist=self.song.get_setlist())
        self.assertRefused(self.chain, self.chain.set_step, place=FIRST, kind=NOT_A_NAME, name=UP, setlist=self.song.get_setlist())
        self.assertRefused(self.chain, self.chain.remove_step, len(self.chain.get_steps()))

    def test_steps_are_copied_moved_and_removed(self):
        self.chain.copy_step(FIRST)
        self.assertEqual([step.name for step in self.chain.get_steps()], [UP, UP, ROLLS])
        self.assertFalse(self.chain.move_step(place=FIRST, offset=ONE_UP))
        self.assertTrue(self.chain.move_step(place=FIRST, offset=TWO_DOWN))
        self.assertEqual([step.name for step in self.chain.get_steps()], [UP, ROLLS, UP])
        self.chain.remove_step(FIRST)
        self.chain.set_step(place=FIRST, kind=GeneratorKind.ARP, name=UP, setlist=self.song.get_setlist())
        self.assertEqual([step.name for step in self.chain.get_steps()], [UP, UP])
        self.assertTrue(self.chain.names_item(section=Section.ARPS, name=UP))
        self.assertFalse(self.chain.names_item(section=Section.AUTO_RATCHETS, name=ROLLS))


class TestRegister(SetterTestCase):

    def test_settings_are_checked_together(self):
        register = Register()
        self.assertTrue(register.is_default())
        register.set_setting(name=RegisterSetting.MAXIMUM, value=HIGH)
        register.set_setting(name=RegisterSetting.DEFAULT, value=LOW)
        self.assertFalse(register.is_default())
        self.assertRefused(register, register.set_setting, name=RegisterSetting.DEFAULT, value=HIGH + 1)
        self.assertRefused(register, register.set_setting, name=RegisterSetting.MAXIMUM, value=TOO_HIGH)
        self.assertRefused(register, register.set_setting, name=RegisterSetting.AT_LIMIT, value=NOT_A_NAME)
        self.assertRefused(register, register.set_setting, name=NOT_A_NAME, value=LOW)
        register.set_setting(name=RegisterSetting.MAXIMUM, value=None)
        register.set_setting(name=RegisterSetting.DEFAULT, value=None)
        self.assertTrue(register.is_default())


class TestGeneratorSettings(SetterTestCase):

    def setUp(self):
        self.arp = ArpSettings.new()

    def test_a_setting_is_checked_as_a_chain_would_and_none_leaves_it_out(self):
        self.arp.set_setting(name=ArpSetting.OCTAVE_RANGE, value=NEW_OCTAVE_RANGE)
        self.assertEqual(self.arp.get_octave_range(), NEW_OCTAVE_RANGE)
        self.assertRefused(self.arp, self.arp.set_setting, name=ArpSetting.OCTAVE_RANGE, value=NOT_A_NAME)
        self.assertRefused(self.arp, self.arp.set_setting, name=NOT_A_NAME, value=NEW_OCTAVE_RANGE)
        self.arp.set_setting(name=ArpSetting.OCTAVE_RANGE, value=None)
        self.assertNotIn(ArpSetting.OCTAVE_RANGE, self.arp.to_data())

    def test_offsets_are_edited_a_step_at_a_time(self):
        self.assertRefused(self.arp, self.arp.set_offset, step=FIRST, offset=AN_OFFSET)
        self.arp.set_setting(name=ArpSetting.OFFSETS, value=[AN_OFFSET])
        self.arp.insert_offset(FIRST)
        self.assertEqual(self.arp.get_offsets(), [NO_OFFSET, AN_OFFSET])
        self.arp.set_offset(step=FIRST, offset=ANOTHER_OFFSET)
        self.assertRefused(self.arp, self.arp.set_offset, step=PAST_THE_OFFSETS, offset=AN_OFFSET)
        self.arp.remove_offset(FIRST)
        self.arp.remove_offset(FIRST)
        self.assertIsNone(self.arp.get_offsets())

    def test_auto_ratchet_counts_are_checked(self):
        rolls = AutoRatchetSettings.new()
        self.assertRefused(rolls, rolls.set_setting, name=AutoRatchetSetting.COUNTS, value=NOT_A_NAME)


class TestSong(SetterTestCase):

    def setUp(self):
        self.song = song_with_everything()

    def test_settings_are_checked(self):
        setlist = self.song.get_setlist()
        self.assertRefused(self.song, self.song.set_scale_name, NOT_A_NAME)
        self.assertRefused(self.song, self.song.set_tempo, NOT_A_NAME)
        self.assertRefused(self.song, self.song.set_seed, NOT_A_NAME)
        self.assertRefused(self.song, self.song.set_time_signature, NOT_A_NAME)
        self.assertRefused(setlist.get_pattern(TUNE), setlist.get_pattern(TUNE).set_time_signature, NOT_A_NAME)
        self.assertRefused(setlist, setlist.set_step_size, NOT_A_NAME)
        self.assertRefused(setlist, setlist.set_default_octave, NOT_A_NAME)
        self.assertRefused(setlist, setlist.set_version, NOT_A_NAME)
        setlist.set_title(TEXT)
        self.assertEqual(setlist.get_title(), TEXT.strip())
        setlist.set_title(NO_TEXT)
        self.assertEqual(setlist.get_title(), NO_TEXT)

    def test_names_are_unique_within_a_section_and_have_to_exist(self):
        setlist = self.song.get_setlist()
        self.assertRefused(setlist, setlist.add_item, section=Section.PATTERNS, name=TUNE, item=Pattern(steps=STEPS, rows={}))
        self.assertRefused(setlist, setlist.rename_item, section=Section.PATTERNS, old=TUNE, new=ANSWER)
        self.assertRefused(setlist, setlist.rename_item, section=Section.PATTERNS, old=NOT_A_NAME, new=NAMED)
        self.assertRefused(setlist, setlist.remove_item, section=Section.PATTERNS, name=NOT_A_NAME)
        self.assertRefused(setlist, setlist.add_item, section=Section.PATTERNS, name=None, item=Pattern(steps=STEPS, rows={}))
        self.assertRefused(self.song, self.song.add_item, section=Section.TRACKS, name=LEAD, item=Track())
        self.assertRefused(self.song, self.song.rename_item, section=Section.TRACKS, old=NOT_A_NAME, new=NAMED)

    def test_removing_a_track_removes_its_clip_slots_and_the_grabs_from_it(self):
        self.song.remove_item(section=Section.TRACKS, name=LEAD)
        scene = self.song.get_scene(FIRST)
        self.assertFalse(scene.has_clip_slot(LEAD))
        self.assertIsNone(scene.get_clip_slot(BASS).get_grab_track())

    def test_items_move_within_their_section_and_sort(self):
        setlist = self.song.get_setlist()
        self.assertTrue(setlist.move_item(section=Section.PATTERNS, place=FIRST, offset=ONE_DOWN))
        self.assertEqual(self.song.get_pattern_names(), [ANSWER, TUNE])
        self.assertFalse(setlist.move_item(section=Section.PATTERNS, place=FIRST, offset=ONE_UP))
        setlist.sort_items(Section.PATTERNS)
        self.assertEqual(self.song.get_pattern_names(), sorted([ANSWER, TUNE]))
        self.assertTrue(self.song.move_item(section=Section.TRACKS, place=FIRST, offset=ONE_DOWN))
        self.assertEqual(self.song.get_track_names(), [BASS, LEAD])

    def test_a_copied_track_follows_its_original_with_its_clip_slots(self):
        self.song.copy_track(name=LEAD, new=NAMED)
        self.assertEqual(self.song.get_track_names(), [LEAD, NAMED, BASS])
        self.assertEqual(self.song.get_scene(FIRST).get_clip_slot(NAMED).get_pattern_name(), TUNE)
        self.song.get_setlist().copy_item(section=Section.PATTERNS, name=TUNE, new=NOT_A_NAME)
        self.assertEqual(self.song.get_pattern_names()[-1], NOT_A_NAME)

    def test_registers_are_written_in_order_and_only_when_changed(self):
        self.song.set_register_setting(name=RegisterName.DX, setting=RegisterSetting.MAXIMUM, value=HIGH)
        self.song.set_register_setting(name=RegisterName.AX, setting=RegisterSetting.MAXIMUM, value=HIGH)
        self.assertEqual(list(self.song.to_data()[Section.REGISTERS]), [RegisterName.AX, RegisterName.DX])
        self.assertEqual(self.song.get_register(RegisterName.DX).get_maximum(), HIGH)
        self.assertRefused(self.song, self.song.set_register_setting, name=RegisterName.AX, setting=RegisterSetting.DEFAULT, value=TOO_HIGH)
        self.assertRefused(self.song, self.song.set_register_setting, name=NOT_A_NAME, setting=RegisterSetting.DEFAULT, value=LOW)
        for name in REGISTER_NAMES:
            self.song.set_register_setting(name=name, setting=RegisterSetting.MAXIMUM, value=None)
        self.assertNotIn(Section.REGISTERS, self.song.to_data())

    def test_scenes_are_added_copied_moved_and_removed_within_bounds(self):
        self.song.copy_scene(index=FIRST, name=NOT_A_NAME)
        self.assertEqual([scene.get_name() for scene in self.song.get_scenes()], [VERSE, NOT_A_NAME])
        self.assertFalse(self.song.move_scene(index=FIRST, offset=ONE_UP))
        self.assertTrue(self.song.move_scene(index=FIRST, offset=ONE_DOWN))
        self.assertEqual(self.song.get_scene(FIRST).get_name(), NOT_A_NAME)
        self.assertRefused(self.song, self.song.add_scene, index=len(self.song.get_scenes()) + 1, scene=Scene())
        self.assertRefused(self.song, self.song.remove_scene, len(self.song.get_scenes()))
        self.song.remove_scene(FIRST)
        self.assertEqual(len(self.song.get_scenes()), 1)

    def test_every_change_still_reads_back_as_a_file(self):
        self.song.set_register_setting(name=RegisterName.AX, setting=RegisterSetting.MAXIMUM, value=HIGH)
        self.song.copy_track(name=LEAD, new=NOT_A_NAME)
        self.song.get_scene(FIRST).get_clip_slot(LEAD).set_repeat(FOUR_REPEATS)
        data = self.song.get_setlist().to_data()
        self.assertEqual(Setlist.from_data(data=data).to_data(), data)


if __name__ == '__main__':
    unittest.main()
