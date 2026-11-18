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

"""The sections of the pattern editor's rows view, which open and close."""

from tests.support.ui_testing import KEY_SHOWN, QUIET_VALUE, REVERSED, ROW_SHOWN, UITest, back_key, forward_key, key_name, key_of
from llamatron.composition.file_format import REGISTER_ADD_ROWS, REGISTER_NOTE_ROWS, REGISTER_VELOCITY_ROWS, RegisterName, RegisterUse, Row
from llamatron.composition import limits
from llamatron.strings import labels as labels_text, legends, marks
from llamatron.music.note import NoteName
from llamatron.tui.drawing import Box, SPACE, fit
from llamatron.tui.keys import Key, OPEN_AT_START, RowSection
from llamatron.tui.components.pattern_rows import SECTIONS
from llamatron.music import midi
from llamatron.tui import keybindings
from tests.support.rendering import render_song
from tests.support.pattern_editor_testing import open_section

BEAT = 'beat'
TUNE = 'tune'
OTHER = 'other'
LEAD = 'lead'
# Two CC numbers for a track's first lane, the mod wheel and brightness, and a second track added to play tune.
MOD_WHEEL = 1
BRIGHTNESS = 74
SECOND_TRACK = 'second'
# The step of tune that holds nothing.
EMPTY_STEP = 2


def section_label(section, *, open_):
    """Return a section's heading as the grid shows it, with its mark for open or closed."""
    return labels_text.MSG_SECTION_LABEL.format(mark=marks.MSG_SECTION_OPEN_MARK if open_ else marks.MSG_SECTION_CLOSED_MARK, name=labels_text.MSG_SECTION_NAMES[section])


class TestSections(UITest):
    """The rows under Octave come in sections headed by rows of the grid: Space or Enter opens and closes one, PgUp and PgDn jump between them, and Tab opens the roll over them."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER, keybindings.PatternEditor.TO_EDITOR)
        self.editor = self.app.screen

    def shown(self, row):
        return ROW_SHOWN.format(label=labels_text.MSG_ROW_LABELS[row])

    def heading_shown(self, section):
        """Return a section's heading as the screen shows it, after the bar, or after the reversed mark when the cursor is on it."""
        label = SPACE + section_label(section, open_=self.editor.rows_view.section_is_open(section))
        return REVERSED.format(text=fit(text=label, width=self.editor.drawing.label_width())) if self.editor.row_name() == section else Box.BAR + label

    def grid_lines_shown(self):
        """Return the screen's lines from the grid's top rule to its bottom rule."""
        lines = self.text().splitlines()
        top = next(number for number, line in enumerate(lines) if line.startswith(Box.TOP_LEFT))
        bottom = next(number for number, line in enumerate(lines) if line.startswith(Box.BOTTOM_LEFT))
        return lines[top:bottom + 1]

    def line_of_heading(self, section):
        lines = self.grid_lines_shown()
        return next(number for number, line in enumerate(lines) if self.heading_shown(section) in line), lines

    async def test_no_divider_crosses_a_heading_and_the_rules_around_it_close_and_reopen_the_dividers(self):
        """The dividers above a heading end in bottom tees, the ones below an open heading start in top tees, two closed headings share an unbroken rule, and a closed last heading sits on a plain bottom rule."""
        # Basics is open and under a row, Octave; Timing, open too, is under the closed Chord heading, whose rule it shares.
        self.assertIn(RowSection.BASICS, self.app.open_sections)
        at, lines = self.line_of_heading(RowSection.BASICS)
        heading = lines[at]
        self.assertEqual(heading.rstrip().count(Box.BAR), 2, heading)
        self.assertNotIn(Box.DOUBLE_BAR, heading)
        above = lines[at - 1]
        self.assertIn(Box.BOTTOM_TEE, above)
        self.assertIn(Box.DOUBLE_BOTTOM_TEE, above)
        for joint in (Box.CROSS, Box.DOUBLE_CROSS, Box.TOP_TEE):
            self.assertNotIn(joint, above)
        below = lines[at + 1]
        self.assertIn(Box.TOP_TEE, below)
        self.assertIn(Box.DOUBLE_TOP_TEE, below)
        self.assertNotIn(Box.CROSS, below)
        # Advanced and CCs are closed: their headings share a rule with no joints at all. Timing is closed first so that both headings fit on this screen.
        await self.press(*[forward_key(keybindings.PatternRows.SECTION)] * 3, keybindings.SectionRow.CLOSE)
        self.assertEqual(self.editor.row_name(), RowSection.TIMING)
        at, lines = self.line_of_heading(RowSection.ADVANCED)
        between = lines[at + 1]
        self.assertEqual(between.rstrip(), Box.LEFT_TEE + Box.RULE * (len(between.rstrip()) - 2) + Box.RIGHT_TEE)
        self.assertIn(self.heading_shown(RowSection.CC), lines[at + 2])
        # With Basics and Timing closed and the cursor on the last heading, the last row is the closed Mute When heading, so the bottom rule under it has no tees.
        await self.press(back_key(keybindings.PatternRows.SECTION), back_key(keybindings.PatternRows.SECTION), keybindings.SectionRow.CLOSE)
        self.assertEqual(self.editor.row_name(), RowSection.BASICS)
        await self.press(*[forward_key(keybindings.PatternRows.SECTION)] * len(SECTIONS))
        self.assertEqual(self.editor.row_name(), RowSection.MUTE_WHEN)
        _, lines = self.line_of_heading(RowSection.MUTE_WHEN)
        bottom = lines[-1].rstrip()
        self.assertIn(self.heading_shown(RowSection.MUTE_WHEN), lines[-2])
        self.assertEqual(bottom, Box.BOTTOM_LEFT + Box.RULE * (len(bottom) - 2) + Box.BOTTOM_RIGHT)

    async def test_the_sections_open_at_the_start_show_their_rows_and_the_rest_show_only_their_headings(self):
        self.assertEqual(self.app.open_sections, set(OPEN_AT_START))
        text = self.text()
        names = [row.name for row in self.editor.rows_view.reachable()]
        for section, rows in SECTIONS.items():
            self.assertIn(section, names)
            for row in rows:
                if section in OPEN_AT_START:
                    self.assertIn(row, names, row)
                else:
                    self.assertNotIn(row, names, row)
                    self.assertNotIn(self.shown(row), text, row)
        self.assertIn(self.heading_shown(RowSection.BASICS), text)

    async def test_page_down_goes_from_heading_to_heading_and_stops_at_the_last_and_page_up_goes_back_and_stops_at_the_first(self):
        for section in SECTIONS:
            await self.press(Key.PAGE_DOWN)
            self.assertEqual(self.editor.row_name(), section)
        await self.press(Key.PAGE_DOWN)
        self.assertEqual(self.editor.row_name(), list(SECTIONS)[-1])
        for section in reversed(list(SECTIONS)[:-1]):
            await self.press(Key.PAGE_UP)
            self.assertEqual(self.editor.row_name(), section)
        await self.press(Key.PAGE_UP)
        self.assertEqual(self.editor.row_name(), list(SECTIONS)[0])
        # From the Degree row, above every heading, PgUp stays put and PgDn reaches the first heading.
        await self.press(Key.UP, Key.UP, Key.PAGE_UP)
        self.assertEqual(self.editor.row_name(), Row.DEGREE)
        await self.press(Key.PAGE_DOWN)
        self.assertEqual(self.editor.row_name(), list(SECTIONS)[0])
        self.assertFalse(self.editor.on_roll())

    async def test_space_and_enter_open_and_close_a_section_and_the_cursor_stays_on_its_heading(self):
        await open_section(test=self, section=RowSection.ADVANCED)
        self.assertEqual(self.editor.row_name(), RowSection.ADVANCED)
        self.assertIn(RowSection.ADVANCED, self.app.open_sections)
        self.assertIn(self.heading_shown(RowSection.ADVANCED), self.text())
        await self.press(Key.DOWN)
        self.assertEqual(self.editor.row_name(), Row.PROBABILITY)
        await self.press(Key.UP, Key.ENTER)
        self.assertNotIn(RowSection.ADVANCED, self.app.open_sections)
        self.assertEqual(self.editor.row_name(), RowSection.ADVANCED)
        self.assertNotIn(self.shown(Row.PROBABILITY), self.text())
        await self.press(Key.DOWN)
        self.assertEqual(self.editor.row_name(), RowSection.CC)

    async def test_the_heading_shows_its_mark_and_the_cursor_on_it_reverses_the_label_and_keeps_the_step(self):
        await self.press(Key.RIGHT, Key.PAGE_DOWN)
        self.assertEqual((self.editor.row_name(), self.editor.step), (RowSection.BASICS, 1))
        self.assertIn(self.heading_shown(RowSection.BASICS), self.text())
        await self.press(Key.DOWN)
        self.assertEqual((self.editor.row_name(), self.editor.step), (Row.ACCIDENTAL, 1))
        self.assertIn(Box.BAR + SPACE + section_label(RowSection.BASICS, open_=True), self.text())
        await self.press(Key.PAGE_DOWN, Key.PAGE_DOWN, Key.PAGE_DOWN, Key.PAGE_DOWN)
        self.assertIn(self.heading_shown(RowSection.CC), self.text())

    async def test_the_label_column_is_as_wide_as_the_widest_row_whether_its_section_is_open_or_not(self):
        width = self.editor.drawing.label_width()
        await open_section(test=self, section=RowSection.ADVANCED)
        self.assertEqual(self.editor.drawing.label_width(), width)
        self.assertEqual(width, len(labels_text.MSG_ROW_LABELS[Row.RATCHET_OFFSET]) + 2)

    async def test_the_open_sections_stay_for_other_patterns_and_under_the_roll(self):
        await open_section(test=self, section=RowSection.ADVANCED)
        await self.press(keybindings.PatternEditor.TO_ROLL)
        self.assertTrue(self.editor.on_roll())
        self.assertNotIn(Key.PAGE_DOWN, [name for item in self.editor.keys() for name in item.keys])
        await self.press(keybindings.PatternEditor.TO_EDITOR, Key.ESCAPE, Key.ENTER)
        self.assertIn(RowSection.ADVANCED, self.app.open_sections)
        self.assertIn(Row.RATCHET_OFFSET, [row.name for row in self.app.screen.rows_view.reachable()])

    async def test_cc_rows_take_values_even_on_a_rest(self):
        await open_section(test=self, section=RowSection.CC)
        rest = 2
        value = 100
        await self.press(Key.RIGHT, Key.RIGHT)
        while self.editor.row_name() != Row.CC1:
            await self.press(Key.DOWN)
        self.assertEqual(self.editor.cell_text(name=Row.CC1, step=rest), QUIET_VALUE)
        await self.press(*str(value))
        self.assertEqual(self.document.step_value(name=TUNE, row=Row.CC1, step=rest), value)
        await self.press(keybindings.CcRow.MORE)
        self.assertEqual(self.document.step_value(name=TUNE, row=Row.CC1, step=rest), value + 1)
        await self.press(Key.BACKSPACE)
        self.assertIsNone(self.document.step_value(name=TUNE, row=Row.CC1, step=rest))
        while self.editor.row_name() != Row.SLIDE:
            await self.press(Key.DOWN)
        await self.press(Key.SPACE)
        self.assertIs(self.document.step_value(name=TUNE, row=Row.SLIDE, step=rest), True)
        self.assertEqual(self.editor.cell_text(name=Row.SLIDE, step=rest), marks.MSG_TOGGLE_ON)
        render_song(self.document.song())

    async def test_a_cc_row_is_one_line_and_its_label_says_the_cc_number_the_tracks_playing_the_pattern_send(self):
        await open_section(test=self, section=RowSection.CC)
        row = self.editor.row_for(Row.CC1)
        cc_1 = labels_text.MSG_ROW_LABELS[Row.CC1]
        # tune is played by lead alone, whose lanes send nothing yet, so the lane is off; the value stays a one-line number.
        self.assertEqual(row.labels(), [labels_text.MSG_CC_ROW_LABEL.format(label=cc_1, number=marks.MSG_CC_LANE_OFF)])
        self.assertEqual(row.cell_lines(step=0), [QUIET_VALUE])
        self.document.set_step_value(name=TUNE, row=Row.CC1, step=0, value=midi.MAX_CC_VALUE)
        self.assertEqual(row.cell_lines(step=0), [str(midi.MAX_CC_VALUE)])
        # Giving lead a number puts it in the label, and a second track playing tune with another number makes the label say they differ.
        self.document.set_track_cc_number(name=LEAD, lane=0, number=BRIGHTNESS)
        self.assertEqual(row.label(), labels_text.MSG_CC_ROW_LABEL.format(label=cc_1, number=str(BRIGHTNESS)))
        while self.editor.row_name() != Row.CC1:
            await self.press(Key.DOWN)
        self.assertIn(ROW_SHOWN.format(label=row.label()), self.text())
        self.document.add_track(SECOND_TRACK)
        self.document.add_clip_slot(index=0, track=SECOND_TRACK, pattern=TUNE)
        self.document.set_track_cc_number(name=SECOND_TRACK, lane=0, number=MOD_WHEEL)
        self.assertEqual(row.label(), labels_text.MSG_CC_ROW_LABEL.format(label=cc_1, number=marks.MSG_CC_LANE_VARIES))
        self.document.set_track_cc_number(name=SECOND_TRACK, lane=0, number=BRIGHTNESS)
        self.assertEqual(row.label(), labels_text.MSG_CC_ROW_LABEL.format(label=cc_1, number=str(BRIGHTNESS)))
        # A pattern no track plays keeps the plain label.
        await self.press(Key.ESCAPE, Key.ESCAPE)
        await self.open_patterns_on(OTHER)
        await self.press(Key.ENTER, keybindings.PatternEditor.TO_ROLL)
        self.assertEqual(self.app.screen.item, OTHER)
        self.assertEqual(self.app.screen.row_for(Row.CC1).label(), cc_1)

    async def test_typing_a_ratchet_offset_and_going_negative(self):
        await open_section(test=self, section=RowSection.ADVANCED)
        while self.editor.row_name() != Row.RATCHET_OFFSET:
            await self.press(Key.DOWN)
        typed = 2
        await self.press(str(typed))
        self.assertEqual(self.document.step_value(name=TUNE, row=Row.RATCHET_OFFSET, step=0), typed)
        presses = typed + 1
        await self.press(*[keybindings.NumberRow.LESS] * presses)
        self.assertEqual(self.document.step_value(name=TUNE, row=Row.RATCHET_OFFSET, step=0), typed - presses)
        self.assertEqual(self.editor.cell_text(name=Row.RATCHET_OFFSET, step=0), str(typed - presses))

    async def test_unset_register_changes_show_a_dot(self):
        await open_section(test=self, section=RowSection.REGISTER_MOD)
        for row in REGISTER_ADD_ROWS.values():
            self.assertEqual(self.editor.cell_text(name=row, step=0), QUIET_VALUE)

    async def test_register_changes_take_typed_values_including_negative_ones_even_on_a_rest(self):
        await open_section(test=self, section=RowSection.REGISTER_MOD)
        rest = 2
        typed = -3
        row = REGISTER_ADD_ROWS[RegisterName.BX]
        await self.press(Key.RIGHT, Key.RIGHT)
        while self.editor.row_name() != row:
            await self.press(Key.DOWN)
        await self.press(Key.ENTER)
        self.app.screen.value = str(typed)
        await self.press(Key.ENTER)
        self.assertEqual(self.document.step_value(name=TUNE, row=row, step=rest), typed)
        await self.press(Key.ENTER)
        self.app.screen.value = str(limits.MAX_REGISTER_VALUE + 1)
        await self.press(Key.ENTER)
        self.assertEqual(self.document.step_value(name=TUNE, row=row, step=rest), typed)
        render_song(self.document.song())

    async def test_register_uses_cycle_add_subtract_and_off_on_notes_and_on_empty_steps_alike(self):
        # Space or Enter cycles +, - and blank, where the rows were toggles.
        await open_section(test=self, section=RowSection.REGISTER_APPLY)
        row = REGISTER_VELOCITY_ROWS[RegisterName.CX]
        while self.editor.row_name() != row:
            await self.press(Key.DOWN)
        self.assertEqual(self.editor.cell_text(name=row, step=0), marks.MSG_TOGGLE_OFF)
        await self.press(keybindings.RegisterRow.NEXT)
        self.assertEqual(self.document.step_value(name=TUNE, row=row, step=0), RegisterUse.ADD)
        self.assertEqual(self.editor.cell_text(name=row, step=0), marks.MSG_REGISTER_ADDS)
        await self.press(key_of(binding=keybindings.RegisterRow.NEXT, key=Key.ENTER))
        self.assertEqual(self.document.step_value(name=TUNE, row=row, step=0), RegisterUse.SUBTRACT)
        self.assertEqual(self.editor.cell_text(name=row, step=0), marks.MSG_REGISTER_SUBTRACTS)
        await self.press(keybindings.RegisterRow.NEXT)
        self.assertEqual(self.document.step_value(name=TUNE, row=row, step=0), RegisterUse.OFF)
        self.assertEqual(self.editor.cell_text(name=row, step=0), marks.MSG_TOGGLE_OFF)
        await self.press(keybindings.RegisterRow.LESS)
        self.assertEqual(self.document.step_value(name=TUNE, row=row, step=0), RegisterUse.SUBTRACT)
        await self.press(keybindings.RegisterRow.MORE, keybindings.RegisterRow.MORE)
        self.assertEqual(self.document.step_value(name=TUNE, row=row, step=0), RegisterUse.ADD)
        self.assertIn(KEY_SHOWN.format(label=legends.KeyName.LEFT_BRACKET) + legends.MSG_LEGEND_WHAT.format(what=legends.What.LESS), self.text())
        self.assertIn(KEY_SHOWN.format(label=legends.KeyName.RIGHT_BRACKET) + legends.MSG_LEGEND_WHAT.format(what=legends.What.MORE), self.text())
        await self.press(keybindings.RegisterRow.CLEAR)
        self.assertEqual(self.document.step_value(name=TUNE, row=row, step=0), RegisterUse.OFF)
        self.assertIn(f'« {key_name(keybindings.RegisterRow.NEXT)} »', self.text())
        # No register setting is locked out for want of a note: every register row works on an empty step, where the render has nothing to move.
        await self.press(*[Key.RIGHT] * EMPTY_STEP)
        for name in (*REGISTER_NOTE_ROWS.values(), *REGISTER_VELOCITY_ROWS.values()):
            self.assertTrue(self.editor.row_for(name).editable(), name)
            self.assertNotEqual(self.editor.row_for(name).cell_lines(step=EMPTY_STEP), [marks.MSG_BLOCKED_CELL], name)
        await self.press(keybindings.RegisterRow.NEXT)
        self.assertEqual(self.document.step_value(name=TUNE, row=row, step=EMPTY_STEP), RegisterUse.ADD)
        self.assertEqual(self.editor.cell_text(name=row, step=EMPTY_STEP), marks.MSG_REGISTER_ADDS)
        render_song(self.document.song())

    async def test_a_drum_pattern_has_no_rows_that_move_notes(self):
        await open_section(test=self, section=RowSection.REGISTER_APPLY)
        await self.press(Key.ESCAPE, Key.ESCAPE)
        await self.open_patterns_on(BEAT)
        await self.press(Key.ENTER)
        rows = [row.name for row in self.app.screen.rows_view.reachable()]
        for name in REGISTER_NOTE_ROWS.values():
            self.assertNotIn(name, rows)
        for name in REGISTER_VELOCITY_ROWS.values():
            self.assertIn(name, rows)

    async def test_on_a_drum_note_row_a_and_f_are_notes(self):
        await self.press(Key.ESCAPE, Key.ESCAPE)
        await self.open_patterns_on(BEAT)
        await self.press(Key.ENTER)
        editor = self.app.screen
        await self.press(Key.RIGHT, NoteName.A.lower())
        self.assertEqual(self.document.step_value(name=BEAT, row=Row.DEGREE, step=1), NoteName.A)
        await self.press(NoteName.F.lower())
        self.assertEqual(self.document.step_value(name=BEAT, row=Row.DEGREE, step=1), NoteName.F)
        labels = [item.shown_label() for item in editor.key_table()]
        self.assertNotIn(NoteName.F, labels)

    async def test_on_other_drum_rows_d_removes_a_step(self):
        await self.press(Key.ESCAPE, Key.ESCAPE)
        await self.open_patterns_on(BEAT)
        await self.press(Key.ENTER)
        labels = [item.shown_label() for item in self.app.screen.key_table()]
        self.assertNotIn(NoteName.D, labels)
        await self.press(Key.DOWN)
        labels = [item.shown_label() for item in self.app.screen.key_table()]
        self.assertIn(NoteName.D, labels)


class TestSectionsOnAUsualConsole(UITest):
    SIZE = (80, 24)

    def assert_fits(self):
        text = self.text()
        self.assertIn('Step 1:', text)
        for item in self.app.screen.shown_keys():
            self.assertIn(KEY_SHOWN.format(label=item.shown_label()), text)

    async def test_every_heading_and_every_row_fits_with_every_section_open(self):
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER)
        self.assert_fits()
        await self.press(keybindings.PatternEditor.TO_EDITOR)
        for section in SECTIONS:
            await open_section(test=self, section=section)
            self.assert_fits()
        # Down through every row: the rows scroll so that the cursor's row, its heading included, is always on screen.
        editor = self.app.screen
        for _ in editor.rows_view.reachable():
            await self.press(Key.DOWN)
            # The label follows the bar, or the reversed mark on a heading under the cursor.
            self.assertIn(SPACE + editor.rows_view.current_row().labels()[-1], self.text(), editor.row_name())
            self.assert_fits()
