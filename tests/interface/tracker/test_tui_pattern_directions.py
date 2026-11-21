# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A pattern's direction and its Grab row, in the pattern editor."""

from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.keys import Key, RowSection
from llamatron.interface.tracker.screens.pattern.pattern_editor import Reconfigure
from llamatron.model.objects.naming import words
from llamatron.model.schema import limits
from llamatron.model.schema.file_format import ClipSlotSetting, Direction, Row
from llamatron.user_strings import labels, marks, messages
from tests.support import ui_testing
from tests.support.pattern_editor_testing import open_section
from tests.support.rendering import render_song
from tests.support.ui_testing import UITest

TUNE = 'tune'
LEAD = 'lead'
# The step of tune that holds nothing.
EMPTY_STEP = 2
DIRECTION_PENDULUM = 'Direction pendulum'
TUNE_D = 'tune d'
DIRECTION = labels.MSG_DIRECTION_LABEL


class TestDirectionsAndGrab(UITest):

    async def test_a_pattern_chooses_a_direction(self):
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER)
        await self.reconfigure(Reconfigure.DIRECTION)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options[0], 'forward    first step to last')
        self.assertEqual(self.app.screen.options[1], 'reverse a  step 1, then backward from the last')
        self.app.screen.cursor.set_place(4)
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song().get_setlist().get_pattern(TUNE).get_direction(), Direction.PENDULUM)
        self.assertIn(DIRECTION_PENDULUM, self.text())
        render_song(self.document.song())

    async def clip_page(self):
        await self.press(keybindings.MainPage.ARRANGE, Key.RIGHT, Key.ENTER)
        return self.app.screen

    async def go_to(self, page, label):
        page.cursor.set_place([field.label for field in page.fields()].index(label))
        page.draw()
        await self.pilot.pause()

    async def test_a_clip_shows_the_patterns_direction_until_it_overrides_it(self):
        self.document.change_pattern(self.document.pattern(TUNE).set_direction, Direction.ALTERNATE)
        page = await self.clip_page()
        self.assertIn(marks.MSG_PATTERN_DIRECTION_SHOWN.format(direction=words(Direction.ALTERNATE)), self.text())
        await self.go_to(page, DIRECTION)
        await self.press(Key.RIGHT)
        self.assertEqual(self.document.clip_slot(index=0, track=LEAD).get_direction(), Direction.FORWARD)
        await self.press(Key.RIGHT)
        self.assertEqual(self.document.clip_slot(index=0, track=LEAD).get_direction(), Direction.REVERSE_A)
        await self.press(Key.BACKSPACE)
        self.assertIsNone(self.document.clip_slot(index=0, track=LEAD).get_direction())

    async def test_a_clip_direction_can_be_chosen_from_a_list(self):
        page = await self.clip_page()
        await self.go_to(page, DIRECTION)
        await self.press(Key.ENTER)
        self.assertEqual(self.app.screen.options[0], "(pattern)  use each pattern's direction")
        self.assertEqual(self.app.screen.options[1], 'forward    first step to last')
        self.app.screen.cursor.set_place(self.app.screen.options.index('brownian   on 50%, back 25%, stay 25%'))
        await self.press(Key.ENTER)
        self.assertEqual(self.document.clip_slot(index=0, track=LEAD).get_direction(), Direction.BROWNIAN)

    async def test_the_grid_marks_a_clip_with_its_own_direction(self):
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.DIRECTION, value=Direction.RANDOM)
        await self.press(keybindings.MainPage.ARRANGE)
        self.assertIn(TUNE_D, self.text())

    async def test_the_grab_row_is_in_the_advanced_section_whose_hint_the_header_shows(self):
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER, keybindings.PatternEditor.TO_EDITOR)
        self.assertNotIn(ui_testing.ROW_SHOWN.format(label=labels.MSG_ROW_LABELS[Row.GRAB]), self.text())
        await open_section(test=self, section=RowSection.ADVANCED)
        while self.app.screen.row_name() != Row.GRAB:
            await self.press(Key.DOWN)
        self.assertIn(ui_testing.ROW_SHOWN.format(label=labels.MSG_ROW_LABELS[Row.GRAB]), self.text())
        self.assertIn(labels.MSG_SECTION_HINTS[RowSection.ADVANCED], self.text())

    async def test_marking_an_empty_step_gives_it_the_root_as_its_own_note_and_opens_the_note_rows_chord_among_them(self):
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER, keybindings.PatternEditor.TO_EDITOR)
        await open_section(test=self, section=RowSection.ADVANCED)
        await self.press(Key.RIGHT, Key.RIGHT)
        editor = self.app.screen
        self.assertFalse(editor.is_note())
        while editor.row_name() != Row.GRAB:
            await self.press(Key.DOWN)
        await self.press(Key.SPACE)
        self.assertTrue(self.document.step_value(name=TUNE, row=Row.GRAB, step=EMPTY_STEP))
        self.assertEqual(self.document.step_value(name=TUNE, row=Row.DEGREE, step=EMPTY_STEP), limits.MIN_DEGREE)
        self.assertEqual(self.document.step_value(name=TUNE, row=Row.OCTAVE, step=EMPTY_STEP), self.document.song().get_setlist().get_default_octave())
        self.assertTrue(editor.is_note())
        # The description names no note, since what a grab step plays is whatever the other track played.
        self.assertIn(messages.MSG_GRABBED_SOUND, self.text())
        # Velocity takes a value on the step now, and so does Chord, which is built on the grabbed note.
        self.assertTrue(editor.row_for(Row.VELOCITY).editable())
        self.assertTrue(editor.row_for(Row.CHORD).editable())
        await self.press(Key.SPACE)
        self.assertFalse(self.document.step_value(name=TUNE, row=Row.GRAB, step=EMPTY_STEP))
        self.assertNotIn(messages.MSG_GRABBED_SOUND, self.text())
        self.assertTrue(editor.row_for(Row.CHORD).editable())
        render_song(self.document.song())

    async def test_a_grab_step_takes_a_chord_and_the_description_names_the_chord_and_no_note(self):
        # A grab step holds a chord, built on the grabbed note.
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER, keybindings.PatternEditor.TO_EDITOR)
        self.document.change_pattern(self.document.pattern(TUNE).set_value, row=Row.GRAB, step=0, value=True)
        self.document.changed()
        editor = self.app.screen
        await open_section(test=self, section=RowSection.CHORD)
        await self.press(Key.DOWN)
        self.assertEqual(editor.row_name(), Row.CHORD)
        self.assertTrue(editor.row_for(Row.CHORD).editable())
        await self.press(keybindings.ChordRow.NEXT)
        chord = self.document.step_value(name=TUNE, row=Row.CHORD, step=0)
        self.assertIsNotNone(chord)
        self.assertEqual(editor.row_for(Row.CHORD).cell_lines(step=0), [str(chord)])
        self.assertIn(messages.MSG_GRABBED_SOUND, self.text())
        self.assertIn(messages.MSG_DESCRIBE_CHORD.format(chord=chord), self.text())
        render_song(self.document.song())

    async def test_marking_a_step_with_space(self):
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER, keybindings.PatternEditor.TO_EDITOR)
        await open_section(test=self, section=RowSection.ADVANCED)
        while self.app.screen.row_name() != Row.GRAB:
            await self.press(Key.DOWN)
        await self.press(Key.SPACE)
        self.assertTrue(self.document.step_value(name=TUNE, row=Row.GRAB, step=0))
        self.assertEqual(self.app.screen.cell_text(name=Row.GRAB, step=0), marks.MSG_TOGGLE_ON)
        render_song(self.document.song())


class TestDirectionsAndGrabOnAUsualConsole(UITest):
    SIZE = (80, 24)

    async def test_everything_still_fits_with_the_grab_row(self):
        # Grab is the last advanced row, so on a short console the rows scroll down to it as the cursor arrives.
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER, keybindings.PatternEditor.TO_EDITOR)
        await open_section(test=self, section=RowSection.ADVANCED)
        while self.app.screen.row_name() != Row.GRAB:
            await self.press(Key.DOWN)
        text = self.text()
        self.assertIn(ui_testing.ROW_SHOWN.format(label=labels.MSG_ROW_LABELS[Row.GRAB]), text)
        self.assertIn('Step 1:', text)
        for item in self.app.screen.shown_keys():
            self.assertIn(f'« {item.shown_label()} »', text)
