# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The editors of steps (tui/screens/shared/step_editor.py) and of one row of numbers (tui/screens/shared/one_row_editor.py).

The offsets editor and the groove editor are each a OneRowEditor, so one set of checks runs on
both: the cursor stops at both ends, digits type a number as one edit and keep the sign, Up and
Down stop at the largest number either side of zero, I and D keep the row within its shortest
and longest, and a row wider than the screen scrolls sideways and says which steps are shown.
The pattern editor shares StepEditor with them, and its own tests cover its scrolling.
"""

import unittest

from llamatron.model.objects.generator_settings import ArpSetting
from llamatron.model.objects.groove import FactoryGroove
from llamatron.model.vocabulary.file_format import Section
from llamatron.tui import drawing, keybindings
from llamatron.tui.drawing import Box
from llamatron.tui.keys import Key
from llamatron.tui.screens.generators.chords_editor import ChordsEditor
from llamatron.tui.screens.generators.drag_steps_editor import DragStepsEditor
from llamatron.tui.screens.generators.glide_steps_editor import GlideStepsEditor
from llamatron.tui.screens.generators.guitar_bar_editor import GuitarBarEditor
from llamatron.tui.screens.generators.offsets_editor import OffsetsEditor
from llamatron.tui.screens.generators.rush_steps_editor import RushStepsEditor
from llamatron.tui.screens.generators.shorten_steps_editor import ShortenStepsEditor
from llamatron.tui.screens.pattern.pattern_editor import PatternEditor
from llamatron.tui.screens.set.groove_editor import GrooveEditor
from llamatron.tui.screens.shared.one_row_editor import OneRowEditor
from llamatron.tui.screens.shared.step_editor import StepEditor
from llamatron.user_strings import legends, marks
from tests.support import ui_testing
from tests.support.ui_testing import key_name, leaf_pages, UITest

A_GROOVE = 'shuffle'
SOME_OFFSETS = [0, 0, 0, 0]
ONE = '1'
TWO = '2'
NINE = '9'
TWELVE = 12
# A count that is more presses than any row has steps or any number has room to move.
MORE_THAN_ENOUGH = 3
FIRST_STEP = 0


def legend_entry(binding):
    """Return a binding as the legend shows it: the key's name and what the key does."""
    return ui_testing.KEY_SHOWN.format(label=key_name(binding)) + legends.MSG_LEGEND_WHAT.format(what=binding.what)


class OneRowChecks:
    """What every editor of one row of numbers does, checked on the page a test class names.

    A test class gives PAGE, the name of the thing the page opens on as FIRST, and how the page
    words which steps are shown as SHOWN.
    """

    __slots__ = ()

    PAGE = None
    FIRST = None
    SHOWN = None

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.prepare()
        self.document.record_edit()
        self.app.screen.show_page(self.PAGE(holder=self.app.screen.holder, name=self.FIRST))
        await self.pilot.pause()
        self.assertIsInstance(self.app.screen, self.PAGE)
        self.page = self.app.screen

    def prepare(self):
        """Give the set the row the page edits before the page opens."""

    def values(self):
        return self.page.values()

    async def fill_the_row(self):
        """Insert steps until the row is as long as a row can be."""
        await self.press(*[self.PAGE.INSERT] * (self.PAGE.MOST_STEPS - len(self.values())))
        self.assertEqual(len(self.values()), self.PAGE.MOST_STEPS)

    async def test_the_cursor_stops_at_both_ends_of_the_row(self):
        await self.press(Key.LEFT)
        self.assertEqual(self.page.step, FIRST_STEP)
        await self.press(*[Key.RIGHT] * (len(self.values()) + MORE_THAN_ENOUGH))
        self.assertEqual(self.page.step, len(self.values()) - 1)

    async def test_digits_build_one_number_which_one_undo_takes_away(self):
        before = self.values()[FIRST_STEP]
        await self.press(ONE, TWO)
        self.assertEqual(self.values()[FIRST_STEP], TWELVE)
        await self.press(keybindings.Page.UNDO)
        self.assertEqual(self.values()[FIRST_STEP], before)

    async def test_a_digit_that_would_take_the_number_out_of_range_starts_a_new_number(self):
        await self.press(ONE, TWO, NINE)
        self.assertGreater(int(ONE + TWO + NINE), self.PAGE.MOST)
        self.assertEqual(self.values()[FIRST_STEP], int(NINE))

    async def test_moving_the_cursor_ends_the_number_being_typed(self):
        await self.press(ONE, Key.RIGHT, Key.LEFT, TWO)
        self.assertEqual(self.values()[FIRST_STEP], int(TWO))

    async def test_typing_into_a_number_below_zero_keeps_the_sign(self):
        await self.press(self.PAGE.KEYS.LESS, ONE, TWO)
        self.assertEqual(self.values()[FIRST_STEP], -TWELVE)

    async def test_up_and_down_stop_at_the_largest_number_either_side_of_zero(self):
        await self.press(*[self.PAGE.KEYS.MORE] * (self.PAGE.MOST + MORE_THAN_ENOUGH))
        self.assertEqual(self.values()[FIRST_STEP], self.PAGE.MOST)
        await self.press(*[self.PAGE.KEYS.LESS] * (2 * self.PAGE.MOST + MORE_THAN_ENOUGH))
        self.assertEqual(self.values()[FIRST_STEP], -self.PAGE.MOST)

    async def test_a_full_row_takes_no_more_steps_and_the_legend_stops_offering_one(self):
        self.assertIn(legend_entry(self.PAGE.INSERT), self.text())
        await self.fill_the_row()
        self.assertNotIn(legend_entry(self.PAGE.INSERT), self.text())
        await self.press(self.PAGE.INSERT)
        self.assertEqual(len(self.values()), self.PAGE.MOST_STEPS)

    async def test_the_shortest_row_gives_up_no_step_and_the_legend_stops_offering_to_remove_one(self):
        self.assertIn(legend_entry(self.PAGE.REMOVE), self.text())
        await self.press(*[self.PAGE.REMOVE] * (len(self.values()) - self.PAGE.FEWEST_STEPS))
        self.assertEqual(len(self.values()), self.PAGE.FEWEST_STEPS)
        self.assertNotIn(legend_entry(self.PAGE.REMOVE), self.text())
        await self.press(self.PAGE.REMOVE)
        self.assertEqual(len(self.values()), self.PAGE.FEWEST_STEPS)

    async def test_removing_the_last_step_leaves_the_cursor_on_the_new_last_step(self):
        await self.press(*[Key.RIGHT] * len(self.values()))
        await self.press(self.PAGE.REMOVE)
        self.assertEqual(self.page.step, len(self.values()) - 1)

    async def test_a_row_that_fits_the_screen_says_nothing_of_which_steps_are_shown(self):
        width, _ = self.SIZE
        fits = self.page.steps_shown(width)
        await self.press(*[self.PAGE.REMOVE] * max(len(self.values()) - fits, 0))
        self.assertLessEqual(len(self.values()), fits)
        self.assertGreater(len(self.values()), self.PAGE.FEWEST_STEPS)
        self.assertNotIn(self.SHOWN.format(before=drawing.NOTHING, first=1, last=len(self.values()), after=drawing.NOTHING), self.text())
        self.assertEqual(self.text().count(Box.TOP_LEFT), 1)

    async def test_a_row_wider_than_the_screen_scrolls_sideways_and_says_which_steps_are_shown(self):
        await self.fill_the_row()
        width, _ = self.SIZE
        shown = self.page.steps_shown(width)
        count = self.PAGE.MOST_STEPS
        self.assertLess(shown, count)
        self.assertEqual(self.page.first_step, FIRST_STEP)
        self.assertIn(self.SHOWN.format(before=drawing.NOTHING, first=1, last=shown, after=marks.MSG_MORE_AFTER), self.text())
        # The grid is one block however long the row is: it scrolls, and never wraps onto a second block.
        self.assertEqual(self.text().count(Box.TOP_LEFT), 1)
        await self.press(*[Key.RIGHT] * shown)
        self.assertEqual(self.page.first_step, 1)
        self.assertIn(self.SHOWN.format(before=marks.MSG_MORE_BEFORE, first=2, last=shown + 1, after=marks.MSG_MORE_AFTER), self.text())
        await self.press(*[Key.RIGHT] * count)
        self.assertEqual(self.page.step, count - 1)
        self.assertEqual(self.page.first_step, count - shown)
        self.assertIn(self.SHOWN.format(before=marks.MSG_MORE_BEFORE, first=count - shown + 1, last=count, after=drawing.NOTHING), self.text())
        await self.press(*[Key.LEFT] * count)
        self.assertEqual(self.page.first_step, FIRST_STEP)

    async def test_a_row_made_shorter_elsewhere_keeps_the_cursor_and_the_window_on_it(self):
        await self.fill_the_row()
        await self.press(*[Key.RIGHT] * self.PAGE.MOST_STEPS)
        for _ in range(self.PAGE.MOST_STEPS - self.PAGE.FEWEST_STEPS):
            self.page.remove_step_here()
            self.page.step -= 1
        self.page.step = self.PAGE.MOST_STEPS
        await self.press(Key.RIGHT)
        self.assertEqual(self.page.step, len(self.values()) - 1)
        self.assertEqual(self.page.first_step, FIRST_STEP)


class TestGrooveEditorIsOneRow(OneRowChecks, UITest):

    PAGE = GrooveEditor
    FIRST = A_GROOVE
    SHOWN = marks.MSG_CELLS_SHOWN

    def prepare(self):
        self.document.add_groove(A_GROOVE)

    async def test_a_factory_groove_can_be_moved_along_and_not_changed(self):
        self.app.pop_screen()
        self.app.screen.show_page(GrooveEditor(holder=self.app.screen.holder, name=FactoryGroove.SWING_58))
        await self.pilot.pause()
        page = self.app.screen
        before = list(page.values())
        self.assertNotIn(legend_entry(GrooveEditor.KEYS.LESS), self.text())
        self.assertNotIn(legend_entry(GrooveEditor.KEYS.MORE), self.text())
        await self.press(Key.RIGHT, ONE, GrooveEditor.KEYS.MORE, GrooveEditor.INSERT, GrooveEditor.REMOVE)
        self.assertEqual(page.step, 1)
        self.assertEqual(page.values(), before)


class TestOffsetsEditorIsOneRow(OneRowChecks, UITest):

    PAGE = OffsetsEditor
    FIRST = ui_testing.UP_ARP
    SHOWN = marks.MSG_STEPS_SHOWN

    def prepare(self):
        self.document.change(self.document.generator(section=Section.ARPS, name=ui_testing.UP_ARP).set_setting, name=ArpSetting.OFFSETS, value=SOME_OFFSETS)

    async def test_a_silent_step_is_stepped_and_typed_from_nothing(self):
        await self.press(OffsetsEditor.KEYS.SILENT)
        self.assertIsNone(self.values()[FIRST_STEP])
        await self.press(OffsetsEditor.KEYS.MORE)
        self.assertEqual(self.values()[FIRST_STEP], 1)
        await self.press(OffsetsEditor.KEYS.SILENT, ONE, TWO)
        self.assertEqual(self.values()[FIRST_STEP], TWELVE)


# The test class of each editor of one row, which the rule below reads.
CHECKED = [TestGrooveEditorIsOneRow, TestOffsetsEditorIsOneRow]
# What every editor of one row takes from OneRowEditor, and every editor of steps from StepEditor, without a way of its own.
SHARED_BY_ONE_ROW_EDITORS = (OneRowEditor.keys, OneRowEditor.move_cursor, OneRowEditor.type_digit, OneRowEditor.nudge, OneRowEditor.insert, OneRowEditor.remove_step, OneRowEditor.scroll_to_cursor)
SHARED_BY_STEP_EDITORS = (StepEditor.on_key, StepEditor.typed_number, StepEditor.window_of_steps, StepEditor.steps_shown_text, StepEditor.keep_step)


class TestEveryStepEditorIsChecked(unittest.TestCase):

    def test_every_editor_of_one_row_has_the_checks(self):
        pages = [page for page in leaf_pages() if issubclass(page, OneRowEditor)]
        self.assertEqual(sorted(page.__name__ for page in pages), sorted(checks.PAGE.__name__ for checks in CHECKED))

    def test_the_editors_of_steps_are_the_pattern_editor_the_chord_editor_and_the_editors_of_one_row(self):
        # The chord editor has three rows, which Up and Down move between, and degrees from 1 to 7, a Guitarify's bar holds strokes over accents, and the steps pages of Glide, Shorten, Rush and Drag hold toggles, so none is an editor of one row of numbers either side of zero; test_tui_progressions.py and test_tui_step_rows.py test them.
        pages = [page for page in leaf_pages() if issubclass(page, StepEditor)]
        self.assertEqual(sorted(page.__name__ for page in pages), sorted(page.__name__ for page in (PatternEditor, ChordsEditor, GuitarBarEditor, GlideStepsEditor, ShortenStepsEditor, RushStepsEditor, DragStepsEditor, *[checks.PAGE for checks in CHECKED])))

    def test_every_editor_of_one_row_says_what_the_row_holds(self):
        for checks in CHECKED:
            page = checks.PAGE
            for said in (page.CELL_WIDTH, page.MOST, page.MOST_STEPS, page.FEWEST_STEPS, page.INSERT, page.REMOVE):
                self.assertIsNotNone(said, page.__name__)
            self.assertLessEqual(page.FEWEST_STEPS, page.MOST_STEPS, page.__name__)

    def test_no_editor_keeps_a_way_of_its_own(self):
        for checks in CHECKED:
            for method in (*SHARED_BY_ONE_ROW_EDITORS, *SHARED_BY_STEP_EDITORS):
                self.assertIs(getattr(checks.PAGE, method.__name__), method, checks.PAGE.__name__)
        for method in SHARED_BY_STEP_EDITORS:
            self.assertIs(getattr(PatternEditor, method.__name__), method)
            self.assertIs(getattr(ChordsEditor, method.__name__), method)


if __name__ == '__main__':
    unittest.main()
