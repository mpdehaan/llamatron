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

"""The Tracks, Scales, Generators and Chains pages and their editors."""

from ui_testing import SWAY, fixed_text, KEY_SHOWN, UITest, key_of, key_name
from llamatron.tui.drawing import NOTHING
from llamatron.strings.marks import MSG_MOVING_CLOSE, MSG_MOVING_OPEN
from llamatron.tui.screens.patterns_page import PatternsPage
from llamatron.composition.file_format import (
    TIME_CHOICES,
    DRIFT_DIRECTIONS, NAMED_GENERATORS, REGISTER_NAMES, ClipSlotSetting, Direction, DriftValue, DriftVersion, GeneratorKind, Section,
)
from llamatron.composition.generator_settings import ArpSetting, written_name
from llamatron.composition.named_scale import scale_type_name
from llamatron.generators.arp import ChordOrder, MAX_OFFSETS, OctaveJump
from llamatron.music.note import NoteName, SHARP_NAMES
from llamatron.tui.components.keyboard import Keyboard, KEY_WIDTH as KEYBOARD_KEY_WIDTH
from llamatron.music.scale import ScaleType
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.dialogs.grid_choice_dialog import GridChoiceDialog
from llamatron.tui.dialogs.message_dialog import MessageDialog
from llamatron.composition.setlist import DEFAULT_SCALE, Setlist
from llamatron.strings.marks import MSG_GENERATOR_KIND_SHOWN
from llamatron.tui.screens.generator_pages import generator_page_of_kind
from llamatron.tui.keys import Key
from llamatron.tui.screens.arp_editor import ArpEditor
from llamatron.tui.screens.drift_editor import DriftEditor
from llamatron.tui.screens.auto_ratchet_editor import AutoRatchetEditor
from llamatron.tui.screens.chain_editor import ChainEditor
from llamatron.tui.screens.chains_page import ChainsPage
from llamatron.tui.screens.offsets_editor import OffsetsEditor
from llamatron.tui.screens.scale_page import ScalePage
from llamatron.tui.screens.scales_page import ScalesPage
from llamatron.strings.labels import (
    MSG_DRIFT_DIRECTION_LABEL, MSG_DRIFT_VALUE_LABELS, MSG_EVERY_LABEL, MSG_ARP_NOTE_ADD_LABEL, MSG_STEP_ADD_ROW_LABEL,
    MSG_COUNTS_LABEL, MSG_KIND_LABEL, MSG_NAME_LABEL, MSG_OCTAVE_JUMP_LABEL, MSG_OCTAVE_RANGE_LABEL, MSG_OFFSETS_LABEL, MSG_ORDER_LABEL,
    MSG_ROOT_LABEL, MSG_SCALE_LABEL, MSG_SEED_LABEL, MSG_STEP_LABEL,
)
from llamatron.strings.legends import MSG_LEGEND_WHAT, What, KeyName
from llamatron.strings.marks import (
    MSG_CURSOR_STEP_MARKS, MSG_CURSOR_VALUE_MARKS, MSG_GAUGE_BAR, MSG_KEY_IN_SCALE, MSG_KEY_OUT_OF_SCALE,
    MSG_MORE_AFTER, MSG_MORE_BEFORE, MSG_NEXT_PAGE_MARK, MSG_OTHER_VALUE, MSG_OVER_THE_TOP_MARK, MSG_POSITIVE_VALUE, MSG_PREVIOUS_PAGE_MARK,
    MSG_STEPS_SHOWN, MSG_UNDER_THE_BOTTOM_MARK, MSG_ROOT_KEY_NAME,
)
from llamatron.strings.messages import MSG_ROOT_TITLE, MSG_SCALE_USES_NOTE
from llamatron.tui import keybindings
from llamatron.tui.screens.chain_editor import step_shown
from llamatron.strings.marks import MSG_CHAIN_STEP_AGAIN, MSG_CHAIN_STEP_SHOWN
from llamatron.strings.messages import MSG_NEW_GENERATOR_CHOICE, MSG_NEW_GENERATOR_NAMED
from llamatron.strings.labels import MSG_ARP_LABEL, MSG_OPENED_ITEM_CRUMB
from rendering import render_song

# Names the tests give to their own things, and other values they use.
LEAD = 'lead'
DRUMS = 'drums'
MAIN = 'main'
THE_SONG = 'song untitled'
MODES = 'MODES'
SYMMETRIC = 'SYMMETRIC'
WHOLE_HALF_DIM = 'whole half dim'
IONIAN = 'ionian'
DIMINISHED = 'diminished'
D_DORIAN_NOTES = 'D dorian: D E F G A B C'
D_MAJOR = 'D Major'
# The two-octave keyboard under a scale's fields.
WHITE_KEYS_ON_THE_KEYBOARD = 14
BLACK_KEYS_ON_THE_KEYBOARD = 10
D_DORIAN = 'D Dorian'
D_MINOR = 'D Minor'
D_HIRAJOSHI = 'D Hirajoshi'
C_MAJOR_2 = 'C Major 2'
OTHER_PAGE = 'other page'
# The key that added on a list before A did, which adds nothing now.
OLD_ADD_KEY = Key.PLUS
MELODIC_MINOR = 'MELODIC MINOR'
EAST_ASIA = 'EAST ASIA'
INDIA = 'INDIA'
JAZZ = 'JAZZ'
PHRYGIAN_DOM = 'phrygian dom'
MIXOLYDIAN_FLAT6 = 'mixolydian flat6'
NATURAL_MINOR = 'natural minor'
LYDIAN_AUGMENTED = 'lydian augmented'
CHANGE = 'Change '
C_MAJOR = 'C Major'
A_VERY_LONG_SCALE_NAME = 'a very long scale name '
C_MAJOR_COPY = 'C Major 2'
AFTER_EACH_NOTE = 'after each note'
UP = 'up'
# How many levels the offsets gauge draws either side of its zero line on the tests' tall console, and on an 80 by 24 one, where the legend takes one line.
GAUGE_LEVELS_ON_A_TALL_CONSOLE = 7
GAUGE_LEVELS_ON_A_USUAL_CONSOLE = 5
ARPEGGIATORS = 'Arpeggiators'
AUTORATCHETS = 'AutoRatchets'
QUARTER = '1/4'
INTEGERS = 'integers'
EMPTY = 'empty'
ROLLS = 'rolls'
CHAIN_EMPTY = 'chain empty'
CHAIN_NAMED = 'chain named'
GENERATORS = 'Generators'
FAST = 'fast'
RISE = 'rise'
CLIMB = 'climb'
ROLLS_COPY = 'rolls 2'
NAMED = 'named'
AFTER_CHORD = 'after chord'
BRIGHT = 'bright'
TRACK_LEAD = 'track lead'
LIFT = 'lift'
RISE_COPY = 'rise 2'
NOTHING_TO_ADD = 'Nothing to add'


class TestScalesPage(UITest):
    """The Scales page: the list of the set's scales."""

    async def test_the_default_scale_must_be_unset_before_deleting_it(self):
        await self.press(keybindings.MainPage.SCALES, Key.BACKSPACE)
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn(THE_SONG, self.text())
        await self.press(Key.ENTER, Key.ESCAPE, keybindings.MainPage.SONGS, Key.ENTER)
        await self.select_field(MSG_SCALE_LABEL)
        await self.press(Key.BACKSPACE, Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.SCALES, Key.BACKSPACE, keybindings.ConfirmDialog.YES)
        self.assertEqual(self.document.song().get_scale_names(), [])

    async def test_a_is_the_add_key_and_plus_adds_only_from_its_row(self):
        """A adds on every list page, the user's choice of 2026-11-09, since + needs Shift; the + row at the bottom still adds with Enter."""
        await self.press(keybindings.MainPage.SCALES, OLD_ADD_KEY)
        self.assertIsInstance(self.app.screen, ScalesPage)
        self.assertEqual(self.document.song().get_scale_names(), [C_MAJOR])
        self.assertIn(KEY_SHOWN.format(label=key_name(keybindings.ScalesPage.ADD)) + MSG_LEGEND_WHAT.format(what=What.ADD), self.text())
        await self.press(Key.DOWN, Key.ENTER)
        self.assertIsInstance(self.app.screen, ScalePage)
        self.assertEqual(self.document.song().get_scale_names(), [C_MAJOR, C_MAJOR_2])

    async def test_adding_a_scale_makes_c_major_and_opens_its_page(self):
        await self.press(keybindings.MainPage.SCALES, keybindings.ScalesPage.ADD)
        self.assertIsInstance(self.app.screen, ScalePage)
        self.assertEqual(self.document.song().get_scale_names(), [C_MAJOR, C_MAJOR_2])
        self.assertEqual(self.root_and_kind(C_MAJOR_2), (NoteName.C, scale_type_name(ScaleType.MAJOR)))
        self.assertIn(C_MAJOR_2, self.crumbs_line())
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, ScalesPage)
        self.assertEqual(self.app.screen.current(), C_MAJOR_2)

    async def test_two_scales_can_be_the_same_notes(self):
        await self.press(keybindings.MainPage.SCALES, keybindings.ScalesPage.COPY)
        self.assertEqual(self.root_and_kind(C_MAJOR_COPY), (NoteName.C, scale_type_name(ScaleType.MAJOR)))

    async def test_renaming_a_scale_updates_what_uses_it(self):
        self.document.set_scene_scale(index=0, name=DEFAULT_SCALE)
        await self.press(keybindings.MainPage.SCALES, keybindings.ScalesPage.RENAME)
        self.app.screen.value = MAIN
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song().get_scale_name(), MAIN)
        self.assertEqual(self.document.song().get_scenes()[0].get_scale_name(), MAIN)
        render_song(self.document.song())


class TestScalePage(UITest):
    """One scale's page, and the root and kind pickers on it."""

    async def test_the_scale_page_steps_the_root_and_kind_and_shows_the_notes(self):
        await self.press(keybindings.MainPage.SCALES, Key.ENTER)
        self.assertIsInstance(self.app.screen, ScalePage)
        await self.select_field(MSG_ROOT_LABEL)
        await self.press(Key.RIGHT, Key.RIGHT)
        # A scale still named after its root and kind follows them, on the page and in the song.
        self.assertEqual(self.root_and_kind(D_MAJOR), (NoteName.D, scale_type_name(ScaleType.MAJOR)))
        self.assertIn(D_MAJOR, self.crumbs_line())
        await self.select_field(MSG_KIND_LABEL)
        await self.press(key_of(binding=keybindings.ScalePage.MORE, key=Key.RIGHT_BRACKET), key_of(binding=keybindings.ScalePage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.root_and_kind(D_DORIAN), (NoteName.D, scale_type_name(ScaleType.DORIAN)))
        self.assertIn(D_DORIAN_NOTES, self.text())
        self.assertIn(MSG_SCALE_USES_NOTE.format(count=1), self.text())
        self.assertEqual(self.document.song().get_scale_names(), [D_DORIAN])
        self.assertEqual(self.document.song().get_scale_name(), D_DORIAN)
        render_song(self.document.song())

    async def test_the_keyboard_fills_the_scales_keys_and_brackets_the_root(self):
        await self.press(keybindings.MainPage.SCALES, Key.ENTER)
        text = self.text()
        # C major: every white key of both octaves and no black key.
        self.assertEqual(text.count(MSG_KEY_IN_SCALE), WHITE_KEYS_ON_THE_KEYBOARD)
        self.assertEqual(text.count(MSG_KEY_OUT_OF_SCALE), BLACK_KEYS_ON_THE_KEYBOARD)
        self.assertIn(MSG_ROOT_KEY_NAME.format(name=NoteName.C), text)
        await self.select_field(MSG_ROOT_LABEL)
        await self.press(Key.RIGHT)
        text = self.text()
        # C# major: five black keys and two white keys an octave, with the root's name under its black key.
        self.assertEqual(text.count(MSG_KEY_IN_SCALE), WHITE_KEYS_ON_THE_KEYBOARD)
        self.assertIn(MSG_ROOT_KEY_NAME.format(name=NoteName.C_SHARP), text)
        self.assertNotIn(MSG_ROOT_KEY_NAME.format(name=NoteName.C), text)
        lines = Keyboard(root=NoteName.C_SHARP, half_steps=ScaleType.MAJOR.value).lines()
        self.assertEqual(lines[0].count(MSG_KEY_IN_SCALE), 10)
        self.assertEqual(lines[1].count(MSG_KEY_IN_SCALE), 4)
        self.assertNotIn(SHARP_NAMES[0].center(KEYBOARD_KEY_WIDTH), lines[2])
        self.assertNotIn(SHARP_NAMES[2].center(KEYBOARD_KEY_WIDTH), lines[2])
        self.assertIn(SHARP_NAMES[4].center(KEYBOARD_KEY_WIDTH), lines[2])

    async def test_the_scale_page_renames_the_scale_and_what_uses_it(self):
        self.document.set_scene_scale(index=0, name=DEFAULT_SCALE)
        await self.press(keybindings.MainPage.SCALES, Key.ENTER)
        await self.select_field(MSG_NAME_LABEL)
        await self.press(Key.ENTER)
        self.app.screen.value = MAIN
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song().get_scale_name(), MAIN)
        self.assertEqual(self.document.song().get_scenes()[0].get_scale_name(), MAIN)
        self.assertIn(MAIN, self.crumbs_line())
        await self.select_field(MSG_ROOT_LABEL)
        await self.press(Key.RIGHT)
        self.assertEqual(self.root_and_kind(MAIN), (NoteName.C_SHARP, scale_type_name(ScaleType.MAJOR)))
        render_song(self.document.song())

    async def open_root_keyboard(self):
        await self.press(keybindings.MainPage.SCALES, Key.ENTER)
        await self.select_field(MSG_ROOT_LABEL)
        await self.press(Key.ENTER)
        return self.app.screen

    async def open_scale_kinds(self):
        self.assertEqual(self.document.set_scale_root(name=DEFAULT_SCALE, root=NoteName.D), D_MAJOR)
        await self.press(keybindings.MainPage.SCALES, Key.ENTER)
        await self.select_field(MSG_KIND_LABEL)
        await self.press(Key.ENTER)
        return self.app.screen

    def dialog_text(self):
        return str(self.app.screen.query_one('#dialog-view').render())

    async def test_roots_are_laid_out_like_a_keyboard(self):
        dialog = await self.open_root_keyboard()
        self.assertIsInstance(dialog, GridChoiceDialog)
        self.assertIn(MSG_ROOT_TITLE, self.dialog_text())
        lines = self.dialog_text().splitlines()
        self.assertIn('C   C#   D   D#   E   F   F#   G   G#   A   A#   B', '\n'.join(lines))
        dialog.place = dialog.options.index(NoteName.C)
        await self.press(Key.RIGHT)
        self.assertEqual(dialog.options[dialog.place], NoteName.C_SHARP)
        await self.press(Key.DOWN)
        self.assertEqual(dialog.options[dialog.place], NoteName.D_FLAT)
        await self.press(Key.RIGHT)
        self.assertEqual(dialog.options[dialog.place], NoteName.D)
        await self.press(Key.ENTER)
        self.assertEqual(self.root_and_kind(D_MAJOR), (NoteName.D, scale_type_name(ScaleType.MAJOR)))

    async def test_scales_are_grouped_and_show_their_notes(self):
        dialog = await self.open_scale_kinds()
        text = self.dialog_text()
        for word in [MODES, 'MINOR & MAJOR', SYMMETRIC, 'PENTATONIC & BLUES', WHOLE_HALF_DIM, IONIAN, scale_type_name(ScaleType.EGYPTIAN)]:
            self.assertIn(word, text)
        self.assertNotIn(DIMINISHED, text)
        self.assertNotIn(scale_type_name(ScaleType.HIRAJOSHI), text)
        self.assertLessEqual(len(text.splitlines()), 22)
        dialog.place = dialog.options.index(scale_type_name(ScaleType.DORIAN))
        await self.press(Key.DOWN)
        self.assertEqual(dialog.options[dialog.place], scale_type_name(ScaleType.PHRYGIAN))
        await self.press(Key.UP)
        self.assertIn(D_DORIAN_NOTES, self.dialog_text())
        await self.press(Key.ENTER)
        self.assertEqual(self.root_and_kind(D_DORIAN), (NoteName.D, scale_type_name(ScaleType.DORIAN)))

    async def test_the_scale_picker_shows_its_other_page(self):
        dialog = await self.open_scale_kinds()
        dialog.place = dialog.options.index(scale_type_name(ScaleType.DORIAN))
        first = self.dialog_text().splitlines()
        for word in [' COMMON ', ' JAZZ & WORLD ', MSG_NEXT_PAGE_MARK, KeyName.TAB_SHIFT_TAB, OTHER_PAGE]:
            self.assertIn(word, '\n'.join(first))
        self.assertNotIn(MSG_PREVIOUS_PAGE_MARK, '\n'.join(first))
        await self.press(Key.TAB)
        text = self.dialog_text()
        for word in [MELODIC_MINOR, 'MIDDLE EAST & EUROPE', EAST_ASIA, INDIA, JAZZ, PHRYGIAN_DOM, MIXOLYDIAN_FLAT6, MSG_PREVIOUS_PAGE_MARK]:
            self.assertIn(word, text)
        self.assertNotIn(MSG_NEXT_PAGE_MARK, text)
        self.assertNotIn(NATURAL_MINOR, text)
        lines = text.splitlines()
        self.assertLessEqual(len(lines), 22)
        self.assertLessEqual(max(len(line) for line in lines), 76)
        # The cursor stays in its column, on the nearest row.
        self.assertEqual(dialog.options[dialog.place], LYDIAN_AUGMENTED)
        await self.press(Key.TAB)
        self.assertEqual(dialog.page, 1)
        await self.press(Key.SHIFT_TAB, Key.SHIFT_TAB)
        self.assertEqual(dialog.page, 0)

    async def test_both_scale_pages_are_the_same_size(self):
        dialog = await self.open_scale_kinds()
        sizes = []
        for page in range(len(dialog.pages)):
            dialog.page = page
            dialog.place = next(cell for row in dialog.grid() for cell in row if isinstance(cell, int))
            dialog.draw()
            lines = self.dialog_text().splitlines()
            sizes.append((len(lines), {len(line) for line in lines}))
        self.assertEqual(len(set(map(str, sizes))), 1, sizes)
        self.assertEqual(len(sizes[0][1]), 1)

    async def test_a_long_title_does_not_widen_the_scale_picker(self):
        dialog = await self.open_scale_kinds()
        width = len(self.dialog_text().splitlines()[0])
        dialog.title = CHANGE + A_VERY_LONG_SCALE_NAME * 4
        dialog.draw()
        self.assertEqual({len(line) for line in self.dialog_text().splitlines()}, {width})
        self.assertIn('JAZZ & WORLD', self.dialog_text())

    async def test_arrows_cross_to_the_other_page(self):
        dialog = await self.open_scale_kinds()
        dialog.place = dialog.options.index(scale_type_name(ScaleType.BLUES))
        await self.press(Key.RIGHT)
        self.assertEqual(dialog.page, 1)
        self.assertEqual(dialog.options[dialog.place], LYDIAN_AUGMENTED)
        await self.press(Key.LEFT)
        self.assertEqual(dialog.page, 0)
        self.assertEqual(dialog.options[dialog.place], scale_type_name(ScaleType.BLUES))
        await self.press(Key.LEFT, Key.LEFT, Key.LEFT)
        # The first page doesn't go round to the last.
        self.assertEqual(dialog.page, 0)
        self.assertEqual(dialog.options[dialog.place], scale_type_name(ScaleType.DORIAN))
        await self.press(Key.TAB, Key.RIGHT, Key.RIGHT, Key.RIGHT)
        self.assertEqual(dialog.page, 1)
        self.assertEqual(dialog.options[dialog.place], scale_type_name(ScaleType.IWATO))

    async def test_picking_a_world_scale(self):
        dialog = await self.open_scale_kinds()
        dialog.place = dialog.options.index(scale_type_name(ScaleType.MAJOR))
        await self.press(Key.TAB, Key.RIGHT, Key.RIGHT)
        self.assertEqual(dialog.options[dialog.place], scale_type_name(ScaleType.HIRAJOSHI))
        self.assertIn('D hirajoshi: D E F A A#', self.dialog_text())
        await self.press(Key.ENTER)
        self.assertEqual(self.root_and_kind(D_HIRAJOSHI), (NoteName.D, scale_type_name(ScaleType.HIRAJOSHI)))
        render_song(self.document.song())

class TestGeneratorsPage(UITest):
    """The Generators page: every generator on one list, its kind beside its name, in an order of the user's own, the user's design."""

    async def test_it_lists_every_generator_with_its_kind_and_enter_opens_its_editor(self):
        await self.press(keybindings.MainPage.GENERATORS)
        page = self.app.screen
        self.assertEqual(len(page.rows()), sum(len(self.document.song().get_generator_names(kind)) for kind in NAMED_GENERATORS))
        self.assertIn(MSG_GENERATOR_KIND_SHOWN.format(kind=generator_page_of_kind(GeneratorKind.AUTO_RATCHET).label), self.text())
        self.assertEqual(page.current(), (GeneratorKind.ARP, UP))
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ArpEditor)

    async def test_adding_asks_the_kind_names_it_and_opens_it(self):
        name = await self.add_generator(Section.ARPS)
        self.assertIsInstance(self.app.screen, ArpEditor)
        self.assertEqual(self.arp(name).get_order(), written_name(ChordOrder.UP))
        await self.press(Key.ESCAPE)
        self.assertEqual(self.app.screen.current(), (GeneratorKind.ARP, name))

    async def test_a_generator_in_a_chain_cannot_be_deleted_and_an_unused_one_can(self):
        await self.press(keybindings.MainPage.GENERATORS, Key.BACKSPACE)
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn(CHAIN_NAMED, self.text())
        await self.press(Key.ENTER, Key.ESCAPE)
        name = await self.add_generator(Section.ARPS)
        await self.press(Key.ESCAPE, Key.BACKSPACE, keybindings.ConfirmDialog.YES)
        self.assertNotIn(name, self.document.song().get_generator_names(GeneratorKind.ARP))

    async def test_renaming_updates_its_chains(self):
        await self.press(keybindings.MainPage.GENERATORS, keybindings.GeneratorsPage.RENAME)
        self.app.screen.value = CLIMB
        await self.press(Key.ENTER)
        self.assertEqual(self.chain_steps(NAMED)[0], (GeneratorKind.ARP, CLIMB))

    async def test_a_copy_comes_after_what_it_copies_and_moving_keeps_the_order_in_the_set(self):
        await self.press(keybindings.MainPage.GENERATORS, Key.DOWN, keybindings.GeneratorsPage.COPY)
        self.assertEqual(self.auto_ratchet(ROLLS_COPY).get_counts(), [1, 4])
        page = self.app.screen
        self.assertEqual(page.current(), (GeneratorKind.AUTO_RATCHET, ROLLS_COPY))
        # Move mode carries the copy above the arpeggiator, across kinds, and the set keeps the order.
        await self.press(keybindings.GeneratorsPage.MOVE, Key.UP, Key.UP, Key.ENTER)
        self.assertEqual(page.generators()[:3], [(GeneratorKind.AUTO_RATCHET, ROLLS_COPY), (GeneratorKind.ARP, UP), (GeneratorKind.AUTO_RATCHET, ROLLS)])
        kept = Setlist.from_data(data=self.document.setlist().to_data())
        self.assertEqual(kept.ordered_generators()[:3], page.generators()[:3])


class TestArpEditor(UITest):
    """An arpeggiator's settings page, reached from the main screen."""

    async def test_editing_an_arps_offsets_and_octaves(self):
        await self.open_generator(section=Section.ARPS)
        self.assertIsInstance(self.app.screen, ArpEditor)
        await self.select_field(MSG_OCTAVE_RANGE_LABEL)
        await self.press(key_of(binding=keybindings.ArpEditor.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.arp(UP).get_octave_range(), 2)
        await self.select_field(MSG_OCTAVE_JUMP_LABEL)
        await self.press(key_of(binding=keybindings.ArpEditor.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.arp(UP).get_octave_jump(), written_name(OctaveJump.AFTER_EACH_NOTE))
        self.assertIn(AFTER_EACH_NOTE, self.text())
        await self.select_field(MSG_OFFSETS_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, OffsetsEditor)
        self.assertEqual(self.arp(UP).get_offsets(), [0] * 8)
        await self.press(Key.RIGHT, '7', Key.RIGHT, Key.SPACE, Key.RIGHT, keybindings.OffsetsEditor.LESS, keybindings.OffsetsEditor.LESS, keybindings.OffsetsEditor.REMOVE_STEP, keybindings.OffsetsEditor.INSERT_STEP)
        self.assertEqual(self.arp(UP).get_offsets(), [0, 7, None, 0, 0, 0, 0, 0])
        # Enter silences a step and plays it again, like Space.
        await self.press(Key.ENTER)
        self.assertEqual(self.arp(UP).get_offsets(), [0, 7, None, None, 0, 0, 0, 0])
        await self.press(Key.ENTER)
        self.assertEqual(self.arp(UP).get_offsets(), [0, 7, None, 0, 0, 0, 0, 0])
        await self.press(Key.ESCAPE)
        self.assertIn('0 7 - 0 0 0 0 0', self.text())
        await self.press(Key.BACKSPACE)
        self.assertIsNone(self.arp(UP).get_offsets())
        render_song(self.document.song())

    async def test_editing_an_arp(self):
        await self.open_generator(section=Section.ARPS)
        self.assertIsInstance(self.app.screen, ArpEditor)
        await self.select_field(MSG_STEP_LABEL)
        before = self.arp(UP).get_step()
        await self.press(key_of(binding=keybindings.ArpEditor.MORE, key=Key.RIGHT_BRACKET))
        # ] (inc) steps to the next value of the one list of times that every time setting shares.
        self.assertEqual(self.arp(UP).get_step(), TIME_CHOICES[TIME_CHOICES.index(before) + 1])
        await self.press(Key.DOWN, key_of(binding=keybindings.ArpEditor.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.arp(UP).get_order(), written_name(ChordOrder.DOWN))

class TestArpEditorFields(UITest):
    """Each field of the arpeggiator editor, with the editor already open."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.open_generator(section=Section.ARPS)
        self.assertIsInstance(self.app.screen, ArpEditor)

    def up(self):
        return self.arp(UP)

    async def test_each_registers_add_per_note_steps_and_clears(self):
        for register in REGISTER_NAMES:
            with self.subTest(register=register):
                await self.select_field(MSG_ARP_NOTE_ADD_LABEL.format(name=register))
                await self.press(key_of(binding=keybindings.ArpEditor.MORE, key=Key.RIGHT_BRACKET))
                self.assertEqual(self.up().get_note_add(register), 1)
                await self.press(Key.BACKSPACE)
                self.assertIsNone(self.up().get_note_add(register))

    async def test_the_name_field_renames_the_arpeggiator_and_its_chains(self):
        await self.select_field(MSG_NAME_LABEL)
        await self.press(Key.ENTER)
        self.app.screen.value = RISE
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song().get_generator_names(GeneratorKind.ARP), [RISE])
        self.assertEqual(self.chain_steps(NAMED)[0], (GeneratorKind.ARP, RISE))
        self.assertIn(RISE, self.crumbs_line())
        await self.select_field(MSG_ORDER_LABEL)
        await self.press(key_of(binding=keybindings.ArpEditor.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.arp(RISE).get_order(), written_name(ChordOrder.DOWN))

    async def test_choosing_a_step_and_an_order(self):
        await self.select_field(MSG_STEP_LABEL)
        await self.press(Key.ENTER)
        self.app.screen.place = self.app.screen.options.index(QUARTER)
        await self.press(Key.ENTER, Key.DOWN, Key.ENTER)
        self.app.screen.place = self.app.screen.options.index(Direction.RANDOM)
        await self.press(Key.ENTER)
        self.assertEqual((self.up().get_step(), self.up().get_order()), (QUARTER, written_name(ChordOrder.RANDOM)))

    async def test_typing_an_octave_range_and_going_back_to_one(self):
        await self.select_field(MSG_OCTAVE_RANGE_LABEL)
        await self.press(Key.ENTER)
        self.app.screen.value = '3'
        await self.press(Key.ENTER)
        self.assertEqual(self.up().get_octave_range(), 3)
        await self.press(Key.ENTER)
        self.app.screen.value = '1'
        await self.press(Key.ENTER)
        self.assertIsNone(self.up().get_octave_range())

    async def test_choosing_an_octave_jump(self):
        await self.select_field(MSG_OCTAVE_JUMP_LABEL)
        await self.press(Key.ENTER)
        self.assertEqual(self.app.screen.options, [AFTER_CHORD, AFTER_EACH_NOTE])
        self.app.screen.place = 1
        await self.press(Key.ENTER)
        self.assertEqual(self.up().get_octave_jump(), written_name(OctaveJump.AFTER_EACH_NOTE))
        await self.press(Key.ENTER)
        self.app.screen.place = 0
        await self.press(Key.ENTER)
        self.assertIsNone(self.up().get_octave_jump())

    async def test_a_seed_of_its_own_and_back_to_the_songs(self):
        await self.select_field(MSG_SEED_LABEL)
        await self.press(key_of(binding=keybindings.ArpEditor.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.up().get_seed(), 1)
        await self.press(Key.BACKSPACE)
        self.assertIsNone(self.up().get_seed())
        self.assertIn('(song)', self.text())

    async def test_typing_an_offset_too_big_starts_a_new_number(self):
        self.document.set_generator_setting(section=Section.ARPS, name=UP, setting=ArpSetting.OFFSETS, value=[0, -3])
        await self.select_field(MSG_OFFSETS_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, OffsetsEditor)
        await self.press('2', '5')
        self.assertEqual(self.up().get_offsets()[0], 5)
        await self.press(Key.RIGHT, '4')
        self.assertEqual(self.up().get_offsets()[1], -4)


# What a test names the drift it adds.
NEW_DRIFT = 'tide'


class TestDriftAdded(UITest):

    async def test_a_new_one_does_nothing_until_given_values(self):
        name = await self.add_generator(Section.DRIFTS)
        self.assertEqual(self.document.song().get_generator_settings(kind=GeneratorKind.DRIFT, name=name).to_data(), {})


class TestDriftEditor(UITest):
    """A drift's editor: its own settings, then each value for both versions, Left and Right picking one."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.open_generator(section=Section.DRIFTS)
        self.assertIsInstance(self.app.screen, DriftEditor)

    def drift(self):
        return self.document.song().get_generator_settings(kind=GeneratorKind.DRIFT, name=SWAY)

    async def test_left_and_right_pick_a_version_and_the_brackets_change_only_that_one(self):
        await self.select_field(MSG_DRIFT_VALUE_LABELS[DriftValue.DEGREE])
        await self.press(keybindings.DriftEditor.MORE)
        self.assertEqual(self.drift().get_value(version=DriftVersion.A, value=DriftValue.DEGREE), 1)
        await self.press(Key.RIGHT, keybindings.DriftEditor.LESS, keybindings.DriftEditor.LESS)
        self.assertEqual(self.drift().get_value(version=DriftVersion.B, value=DriftValue.DEGREE), -2)
        self.assertEqual(self.drift().get_value(version=DriftVersion.A, value=DriftValue.DEGREE), 1)
        await self.press(Key.BACKSPACE)
        self.assertIsNone(self.drift().get_value(version=DriftVersion.B, value=DriftValue.DEGREE))

    async def test_a_scale_override_is_picked_from_the_songs_scales(self):
        await self.select_field(MSG_DRIFT_VALUE_LABELS[DriftValue.SCALE])
        await self.press(keybindings.DriftEditor.MORE)
        self.assertEqual(self.drift().get_value(version=DriftVersion.A, value=DriftValue.SCALE), sorted(self.document.song().get_scale_names())[0])

    async def test_its_own_settings_step_and_go_back_to_their_defaults(self):
        await self.select_field(MSG_DRIFT_DIRECTION_LABEL)
        await self.press(keybindings.DriftEditor.MORE)
        self.assertEqual(self.drift().get_direction(), DRIFT_DIRECTIONS[1])
        await self.select_field(MSG_EVERY_LABEL)
        await self.press(keybindings.DriftEditor.MORE)
        self.assertIsNotNone(self.drift().get_every())


class TestOffsetsEditor(UITest):
    """The editor of an arpeggiator's offsets: a gauge of bars either side of a zero line."""

    async def open_offsets(self, offsets):
        self.document.set_generator_setting(section=Section.ARPS, name=UP, setting=ArpSetting.OFFSETS, value=offsets)
        await self.open_generator(section=Section.ARPS)
        await self.select_field(MSG_OFFSETS_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, OffsetsEditor)

    async def test_tab_moves_to_a_registers_add_row_where_steps_add_within_its_limit(self):
        await self.open_offsets([0, 2])
        self.assertNotIn(MSG_STEP_ADD_ROW_LABEL.format(name=REGISTER_NAMES[0]), self.text())
        await self.press(keybindings.OffsetsEditor.NEXT_ROW)
        self.assertIn(MSG_STEP_ADD_ROW_LABEL.format(name=REGISTER_NAMES[0]), self.text())
        await self.press(keybindings.OffsetsEditor.MORE, Key.RIGHT, keybindings.OffsetsEditor.LESS)
        self.assertEqual(self.arp(UP).get_step_adds(REGISTER_NAMES[0]), [1, -1])
        self.assertEqual(self.app.screen.offsets(), [0, 2])
        most = self.document.song().get_register(REGISTER_NAMES[0]).get_allowed_inc_max()
        for _ in range(most + 1):
            await self.press(keybindings.OffsetsEditor.LESS)
        self.assertEqual(self.arp(UP).get_step_adds(REGISTER_NAMES[0])[1], -most)
        for _ in REGISTER_NAMES:
            await self.press(keybindings.OffsetsEditor.NEXT_ROW)
        self.assertIsNone(self.app.screen.register_edited())

    async def test_up_and_down_nudge_the_offset_like_plus_and_minus(self):
        await self.open_offsets([0, 2])
        await self.press(Key.UP, Key.UP, Key.UP)
        self.assertEqual(self.app.screen.offsets(), [3, 2])
        await self.press(Key.DOWN, Key.RIGHT, Key.DOWN, key_of(binding=keybindings.OffsetsEditor.LESS, key=Key.MINUS), key_of(binding=keybindings.OffsetsEditor.MORE, key=Key.PLUS))
        self.assertEqual(self.app.screen.offsets(), [2, 1])

    async def test_the_brackets_nudge_the_offset_too(self):
        await self.open_offsets([0, 2])
        await self.press(keybindings.OffsetsEditor.MORE, keybindings.OffsetsEditor.MORE, Key.RIGHT, keybindings.OffsetsEditor.LESS)
        self.assertEqual(self.app.screen.offsets(), [2, 1])

    async def test_each_offset_is_a_bar_from_the_zero_line_with_its_value_beneath(self):
        await self.open_offsets([3, -2, None, 9, 0])
        text = self.text()
        # A tall console gives seven levels either side, so 9 fills its column and is marked.
        self.assertEqual(text.count(MSG_GAUGE_BAR), 3 + 2 + GAUGE_LEVELS_ON_A_TALL_CONSOLE)
        self.assertIn(MSG_POSITIVE_VALUE.format(value=9, mark=MSG_OVER_THE_TOP_MARK), text)
        self.assertIn(MSG_OTHER_VALUE.format(value=-2, mark=NOTHING), text)
        self.assertIn(MSG_OTHER_VALUE.format(value=0, mark=NOTHING), text)
        self.assertNotIn(MSG_POSITIVE_VALUE.format(value=0, mark=NOTHING), text)

    async def test_the_cursors_column_is_marked_at_both_ends(self):
        await self.open_offsets([3, -9])
        text = self.text()
        self.assertIn(MSG_CURSOR_STEP_MARKS.format(text=1), text)
        self.assertIn(MSG_CURSOR_VALUE_MARKS.format(text=MSG_POSITIVE_VALUE.format(value=3, mark=NOTHING)), text)
        await self.press(Key.RIGHT)
        text = self.text()
        self.assertIn(MSG_CURSOR_STEP_MARKS.format(text=2), text)
        self.assertIn(MSG_CURSOR_VALUE_MARKS.format(text=MSG_OTHER_VALUE.format(value=-9, mark=MSG_UNDER_THE_BOTTOM_MARK)), text)
        self.assertNotIn(MSG_CURSOR_STEP_MARKS.format(text=1), text)

    async def test_offsets_have_one_to_sixteen_steps(self):
        self.document.set_generator_setting(section=Section.ARPS, name=UP, setting=ArpSetting.OFFSETS, value=[0] * 16)
        await self.open_generator(section=Section.ARPS)
        await self.select_field(MSG_OFFSETS_LABEL)
        await self.press(Key.ENTER)
        self.assertNotIn('« I »', self.text())
        self.document.set_generator_setting(section=Section.ARPS, name=UP, setting=ArpSetting.OFFSETS, value=[3])
        await self.press(Key.RIGHT)
        self.assertNotIn('« D »', self.text())

class TestOffsetsEditorOnAUsualConsole(UITest):
    SIZE = (80, 24)

    async def test_five_levels_fit_with_the_keys_and_the_row_scrolls_sideways(self):
        self.document.set_generator_setting(section=Section.ARPS, name=UP, setting=ArpSetting.OFFSETS, value=[7] + [0] * 15)
        await self.open_generator(section=Section.ARPS)
        await self.select_field(MSG_OFFSETS_LABEL)
        await self.press(Key.ENTER)
        text = self.text()
        self.assertEqual(text.count(MSG_GAUGE_BAR), GAUGE_LEVELS_ON_A_USUAL_CONSOLE)
        self.assertIn(MSG_POSITIVE_VALUE.format(value=7, mark=MSG_OVER_THE_TOP_MARK), text)
        for item in self.app.screen.shown_keys():
            self.assertIn(KEY_SHOWN.format(label=item.shown_label()), text)
        self.assertIn(fixed_text(MSG_STEPS_SHOWN) + '1-9' + MSG_MORE_AFTER, text)
        # Left on the first step stays there, since no cursor goes round, and Right to the last step scrolls the row.
        await self.press(Key.LEFT)
        self.assertIn(MSG_CURSOR_STEP_MARKS.format(text=1), self.text())
        await self.press(*[Key.RIGHT] * (MAX_OFFSETS - 1))
        self.assertIn(MSG_MORE_BEFORE + fixed_text(MSG_STEPS_SHOWN) + '8-16', self.text())
        self.assertIn(MSG_CURSOR_STEP_MARKS.format(text=16), self.text())


class TestAutoRatchetAdded(UITest):

    async def test_an_auto_ratchet_can_be_made_edited_and_added_to_a_chain(self):
        name = await self.add_generator(Section.AUTO_RATCHETS)
        self.assertIsInstance(self.app.screen, AutoRatchetEditor)
        self.assertEqual(self.auto_ratchet(name).get_counts(), [2])
        await self.select_field(MSG_COUNTS_LABEL)
        await self.press(Key.ENTER)
        self.app.screen.value = '1 1 4'
        await self.press(Key.ENTER)
        self.assertEqual(self.auto_ratchet(name).get_counts(), [1, 1, 4])
        await self.press(Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.CHAINS, Key.DOWN, Key.ENTER, keybindings.ChainEditor.ADD)
        await self.pick(step_shown(kind=GeneratorKind.AUTO_RATCHET, name=name))
        self.assertEqual(self.chain_steps(EMPTY), [(GeneratorKind.AUTO_RATCHET, name)])
        render_song(self.document.song())


class TestAutoRatchetEditor(UITest):
    """An AutoRatchet's settings page."""

    async def test_the_name_field_renames_the_auto_ratchet_and_its_chains(self):
        await self.open_generator(section=Section.AUTO_RATCHETS)
        self.assertIsInstance(self.app.screen, AutoRatchetEditor)
        await self.select_field(MSG_NAME_LABEL)
        await self.press(Key.ENTER)
        self.app.screen.value = FAST
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song().get_generator_names(GeneratorKind.AUTO_RATCHET), [FAST])
        self.assertEqual(self.chain_steps(NAMED)[1], (GeneratorKind.AUTO_RATCHET, FAST))
        self.assertIn(FAST, self.crumbs_line())

    async def test_bad_counts_are_refused(self):
        await self.open_generator(section=Section.AUTO_RATCHETS)
        await self.select_field(MSG_COUNTS_LABEL)
        await self.press(Key.ENTER)
        self.app.screen.value = '1 x'
        await self.press(Key.ENTER)
        self.assertEqual(self.auto_ratchet(ROLLS).get_counts(), [1, 4])
        self.assertIn(INTEGERS, self.text())

class TestChainsPage(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.CHAINS)
        self.assertIsInstance(self.app.screen, ChainsPage)

    def chains(self):
        return self.document.song().get_chain_names()

    async def test_adding_renaming_copying_and_moving(self):
        await self.press(keybindings.ChainsPage.ADD)
        await self.type('lift')
        await self.press(Key.ENTER)
        self.assertEqual(self.chains(), [NAMED, EMPTY, LIFT])
        await self.press(keybindings.ChainsPage.RENAME)
        self.app.screen.value = RISE
        await self.press(Key.ENTER)
        self.assertEqual(self.chains(), [NAMED, EMPTY, RISE])
        await self.press(keybindings.ChainsPage.COPY)
        self.assertEqual(self.chains(), [NAMED, EMPTY, RISE, RISE_COPY])
        await self.press(keybindings.ChainsPage.MOVE, Key.UP, Key.ENTER)
        self.assertEqual(self.chains(), [NAMED, EMPTY, RISE_COPY, RISE])

    async def test_renaming_a_chain_updates_the_clips_that_use_it(self):
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.CHAIN, value=NAMED)
        await self.press(keybindings.ChainsPage.RENAME)
        self.app.screen.value = BRIGHT
        await self.press(Key.ENTER)
        self.assertEqual(self.document.clip_slot(index=0, track=LEAD).get_chain_names(), [BRIGHT])

    async def test_deleting_an_unused_chain_asks_first(self):
        await self.press(Key.DOWN, Key.BACKSPACE)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertEqual(self.chains(), [NAMED])

    async def test_a_chain_in_use_cannot_be_deleted(self):
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.CHAIN, value=NAMED)
        await self.press(Key.BACKSPACE)
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn(TRACK_LEAD, self.text())
        self.assertIn(NAMED, self.chains())


EMPTY_CHAIN = 'x'


class TestChainEditor(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.CHAINS, Key.ENTER)
        self.assertIsInstance(self.app.screen, ChainEditor)

    def steps(self):
        return self.chain_steps(NAMED)

    async def test_changing_copying_moving_and_removing_steps(self):
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options[0], MSG_NEW_GENERATOR_CHOICE)
        self.assertEqual(self.app.screen.options[1:], [step_shown(kind='arp', name='up'), step_shown(kind='auto_ratchet', name='rolls'), step_shown(kind='drift', name='sway'), step_shown(kind='progression', name='pop'), step_shown(kind='voice_leading', name='smooth'), step_shown(kind='strum', name='folk'), step_shown(kind='euclid', name='clave'), step_shown(kind='density', name='thin'), step_shown(kind='swell', name='fade'), step_shown(kind='articulate', name='clipped'), step_shown(kind='glide', name='slides'), step_shown(kind='shorten', name='clips'), step_shown(kind='rush', name='push'), step_shown(kind='drag', name='lazy'), step_shown(kind='hocket', name='trade')])
        self.app.screen.place = 2
        await self.press(Key.ENTER)
        self.assertEqual(self.steps(), [(GeneratorKind.AUTO_RATCHET, ROLLS), (GeneratorKind.AUTO_RATCHET, ROLLS)])
        await self.press(Key.DOWN, Key.ENTER)
        self.app.screen.place = 1
        await self.press(Key.ENTER)
        self.assertEqual(self.steps(), [(GeneratorKind.AUTO_RATCHET, ROLLS), (GeneratorKind.ARP, UP)])
        await self.press(keybindings.ChainEditor.COPY)
        self.assertEqual(self.steps(), [(GeneratorKind.AUTO_RATCHET, ROLLS), (GeneratorKind.ARP, UP), (GeneratorKind.ARP, UP)])
        await self.press(Key.UP, Key.UP, keybindings.ChainEditor.MOVE, Key.DOWN, Key.ENTER)
        self.assertEqual(self.steps(), [(GeneratorKind.ARP, UP), (GeneratorKind.AUTO_RATCHET, ROLLS), (GeneratorKind.ARP, UP)])
        await self.press(Key.BACKSPACE, Key.BACKSPACE)
        self.assertEqual(self.steps(), [(GeneratorKind.ARP, UP)])
        render_song(self.document.song())

    async def test_n_renames_the_chain_and_the_clips_using_it(self):
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.CHAIN, value=NAMED)
        await self.press(keybindings.ChainEditor.RENAME)
        self.app.screen.value = BRIGHT
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song().get_chain_names(), [BRIGHT, EMPTY])
        self.assertEqual(self.document.clip_slot(index=0, track=LEAD).get_chain_names(), [BRIGHT])
        self.assertIn(BRIGHT, self.crumbs_line())
        render_song(self.document.song())

    async def test_a_step_cannot_move_past_the_ends(self):
        await self.press(keybindings.ChainEditor.MOVE, Key.UP, Key.ENTER)
        self.assertEqual(self.steps(), [(GeneratorKind.ARP, UP), (GeneratorKind.AUTO_RATCHET, ROLLS)])

    async def test_each_step_shows_its_generators_name_then_its_kind_and_a_repeat_is_numbered_on_screen_only(self):
        self.document.add_chain_step(chain=NAMED, kind=GeneratorKind.ARP, name=UP)
        self.document.record_edit()
        await self.press(Key.DOWN)
        texts = [row[1][0] for row in self.app.screen.rows()]
        self.assertEqual(texts[-1], MSG_CHAIN_STEP_AGAIN.format(name=UP, number=2, kind=MSG_ARP_LABEL))
        self.assertEqual(texts[0], MSG_CHAIN_STEP_SHOWN.format(name=UP, kind=MSG_ARP_LABEL))
        self.assertEqual(self.steps()[-1], (GeneratorKind.ARP, UP))

    async def test_with_no_generators_the_picker_offers_a_new_one_alone(self):
        # The chain's own steps go first, since a generator a chain uses can't be deleted.
        await self.press(Key.BACKSPACE, Key.BACKSPACE)
        self.delete_every_generator()
        await self.press(keybindings.ChainEditor.ADD)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options, [MSG_NEW_GENERATOR_CHOICE])
class TestChainEditorAdding(UITest):
    """Adding steps to a chain, from the main screen."""

    async def test_a_chain_can_add_a_named_arp(self):
        await self.press(keybindings.MainPage.CHAINS, Key.DOWN, Key.ENTER)
        self.assertIsInstance(self.app.screen, ChainEditor)
        await self.press(keybindings.ChainEditor.ADD, Key.DOWN, Key.ENTER)
        self.assertEqual(self.chain_steps(EMPTY), [(GeneratorKind.ARP, UP)])
        self.document.song()

    async def test_a_new_generator_is_made_of_the_kind_picked_added_to_the_chain_and_opened(self):
        await self.press(keybindings.MainPage.CHAINS, Key.DOWN, Key.ENTER)
        await self.press(keybindings.ChainEditor.ADD, Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options[0], MSG_ARP_LABEL)
        await self.press(Key.ENTER)
        name = MSG_NEW_GENERATOR_NAMED.format(kind=MSG_ARP_LABEL)
        self.assertEqual(self.chain_steps(EMPTY), [(GeneratorKind.ARP, name)])
        self.assertIsInstance(self.app.screen, ArpEditor)
        self.assertEqual(self.app.screen.crumb_trail()[-1], MSG_OPENED_ITEM_CRUMB.format(word=MSG_ARP_LABEL, name=name))
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, ChainEditor)




class TestMoveModeOnALists(UITest):
    """Move mode on a list page, the user's design: M picks up the row, Up and Down carry it, and Enter, Esc or M drops it."""

    def names(self):
        return self.document.setlist().get_pattern_names()

    def carried_line(self):
        return next(line for line in self.text().splitlines() if MSG_MOVING_OPEN in line and MSG_MOVING_CLOSE in line)

    async def test_the_carried_name_is_marked_without_moving_the_columns_and_one_move_is_one_undo_step(self):
        await self.press(keybindings.MainPage.PATTERNS)
        first = self.names()[0]
        still = next(line for line in self.text().splitlines() if first in line)
        await self.press(keybindings.PatternsPage.MOVE)
        carried = self.carried_line()
        self.assertIn(MSG_MOVING_OPEN + first + MSG_MOVING_CLOSE, carried)
        # The marks take the places of the spaces beside the name, so every column after it stays where it was.
        self.assertEqual(len(carried.rstrip()), len(still.rstrip()))
        self.assertEqual(carried.index(MSG_MOVING_OPEN + first) + 1, still.index(first))
        await self.press(*[Key.DOWN] * len(self.names()))
        self.assertEqual(self.names()[-1], first)
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, PatternsPage)
        self.assertFalse(self.app.screen.moving)
        await self.press(keybindings.Page.UNDO)
        self.assertEqual(self.names()[0], first)

    async def test_m_or_enter_drops_it_too(self):
        await self.press(keybindings.MainPage.PATTERNS, keybindings.PatternsPage.MOVE, keybindings.PatternsPage.MOVE)
        self.assertFalse(self.app.screen.moving)
        await self.press(keybindings.PatternsPage.MOVE, Key.ENTER)
        self.assertFalse(self.app.screen.moving)
        self.assertIsInstance(self.app.screen, PatternsPage)
