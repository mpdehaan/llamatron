# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The tracker's Progression: the Progressions page, the progression editor and the chord editor, with the picker of named progressions."""

from llamatron.composition import file_format, generator_settings, limits
from llamatron.composition.file_format import Accidental, ChordSymbol, GeneratorKind, NamedProgression, Restart, Section, Tension
from llamatron.composition.named_scale import scale_type_name
from llamatron.composition.progressions import named_progression
from llamatron.music.scale import ScaleType
from llamatron.strings import labels, messages
from llamatron.tui import keybindings
from llamatron.tui.dialogs import chord_dialog
from llamatron.tui.dialogs.chord_dialog import ChordDialog
from llamatron.tui.dialogs.grid_choice_dialog import GridChoiceDialog
from llamatron.tui.keys import Key
from llamatron.tui.screens.generators import chords_editor
from llamatron.tui.screens.generators.chords_editor import ChordsEditor
from llamatron.tui.screens.generators.progression_editor import ProgressionEditor
from tests.support import ui_testing
from tests.support.ui_testing import UITest

# The test song's progression, pop, and what the chord editor shows for it in C major.
POP_CHORDS = [1, 5, 6, 4]
POP_NUMERALS = 'I V vi IV'
POP_NAMES = ['C', 'G', 'Am', 'F']
NEW_ONE = 'verse'
SIX = '6'
NINE = '9'
TWO = '2'
ZERO = '0'
MINOR = scale_type_name(ScaleType.MINOR)
# The third chord of Pop is vi, A minor in C major: named major it is A, and drawn from C minor it is A flat.
SIXTH_CHORD = 2
A_MAJOR = 'A'
A_FLAT_MAJOR = 'Ab Major'
A_MINOR = 'A Minor'
C_MINOR = 'C Minor'
C_MAJOR = 'C Major'
G_SEVEN_FLAT_NINE = 'G7(b9)'
A_FLAT_NOTES = 'Ab C Eb'


class TestProgressionAdded(UITest):

    async def test_a_new_one_has_one_chord_that_moves_nothing(self):
        name = await self.add_generator(Section.PROGRESSIONS)
        self.assertEqual(self.document.song().get_generator_settings(kind=GeneratorKind.PROGRESSION, name=name).get_chords(), [limits.MIN_PROGRESSION_DEGREE])


class TestProgressionEditor(UITest):
    """The progression editor: its Every from the one list of times, and its Chords field opening the chord editor."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.open_generator(section=Section.PROGRESSIONS)
        self.assertIsInstance(self.app.screen, ProgressionEditor)

    def progression(self):
        return self.document.song().get_generator_settings(kind=GeneratorKind.PROGRESSION, name=ui_testing.POP)

    async def test_every_starts_at_a_bar_and_steps_through_the_list(self):
        self.assertIn(file_format.ONE_BAR_WRITTEN, self.text())
        await self.select_field(labels.MSG_EVERY_LABEL)
        await self.press(keybindings.ProgressionEditor.MORE)
        self.assertEqual(self.progression().get_every(), [time for time in file_format.TIME_CHOICES if time != file_format.ONE_BAR_WRITTEN][0])

    async def test_the_chords_field_shows_the_numerals_and_opens_the_chord_editor(self):
        self.assertIn(POP_NUMERALS, self.text())
        await self.select_field(labels.MSG_CHORDS_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChordsEditor)


class TestChordsEditor(UITest):
    """The chord editor: degrees stepped and typed, the #/b and Inv. rows, chords inserted and removed, and H filling the chords."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.app.screen.show_page(ChordsEditor(holder=self.app.screen.holder, name=ui_testing.POP))
        await self.pilot.pause()
        self.page = self.app.screen

    def progression(self):
        return self.document.song().get_generator_settings(kind=GeneratorKind.PROGRESSION, name=ui_testing.POP)

    async def test_it_shows_each_chords_numeral_and_name_in_the_songs_scale(self):
        for name in POP_NAMES:
            self.assertIn(name, self.text())
        for numeral in POP_NUMERALS.split():
            self.assertIn(numeral, self.text())

    async def test_the_degree_steps_from_1_to_7_and_stops(self):
        await self.press(*[keybindings.ChordsEditor.MORE] * limits.MAX_PROGRESSION_DEGREE)
        self.assertEqual(self.progression().get_chords()[0], limits.MAX_PROGRESSION_DEGREE)
        await self.press(*[keybindings.ChordsEditor.LESS] * (limits.MAX_PROGRESSION_DEGREE + 1))
        self.assertEqual(self.progression().get_chords()[0], limits.MIN_PROGRESSION_DEGREE)

    async def test_digits_type_a_degree_and_one_out_of_range_types_nothing(self):
        await self.press(SIX)
        self.assertEqual(self.progression().get_chords()[0], int(SIX))
        await self.press(NINE)
        self.assertEqual(self.progression().get_chords()[0], int(SIX))

    async def test_up_and_down_reach_the_flat_and_inversion_rows_and_stop(self):
        await self.press(Key.UP)
        self.assertEqual(self.page.edited_row, chords_editor.CHORD_ROW)
        await self.press(Key.DOWN, keybindings.ChordsEditor.NEXT, keybindings.ChordsEditor.NEXT)
        self.assertEqual(self.page.edited_row, chords_editor.ACCIDENTAL_ROW)
        self.assertEqual(self.progression().get_accidentals()[0], Accidental.FLAT)
        await self.press(*[Key.DOWN] * (chords_editor.INVERSION_ROW - chords_editor.ACCIDENTAL_ROW + 1), TWO)
        self.assertEqual(self.page.edited_row, chords_editor.INVERSION_ROW)
        self.assertEqual(self.progression().get_inversions()[0], int(TWO))
        await self.press(ZERO)
        self.assertIsNone(self.progression().get_inversions()[0])

    async def go_to(self, *, row, chord=0):
        await self.press(*[Key.RIGHT] * chord, *[Key.DOWN] * row)
        self.assertEqual(self.page.edited_row, row)

    async def test_a_quality_is_stepped_and_cleared_and_names_the_chord(self):
        await self.go_to(row=chords_editor.QUALITY_ROW, chord=SIXTH_CHORD)
        await self.press(keybindings.ChordsEditor.NEXT_CHOICE)
        self.assertEqual(self.progression().get_qualities()[SIXTH_CHORD], ChordSymbol.MAJOR)
        self.assertIn(A_MAJOR + ' Major', self.text())
        self.assertIn(POP_NUMERALS.split()[SIXTH_CHORD].upper(), self.text())
        await self.press(keybindings.ChordsEditor.MORE, keybindings.ChordsEditor.LESS, keybindings.ChordsEditor.CLEAR)
        self.assertIsNone(self.progression().get_qualities()[SIXTH_CHORD])
        # A quality stops at the first choice and at the last, never going round.
        await self.press(keybindings.ChordsEditor.LESS)
        self.assertIsNone(self.progression().get_qualities()[SIXTH_CHORD])
        await self.press(*[keybindings.ChordsEditor.MORE] * (len(chords_editor.QUALITY_CYCLE) + 1))
        self.assertEqual(self.progression().get_qualities()[SIXTH_CHORD], chords_editor.QUALITY_CYCLE[-1])

    async def test_a_scale_borrows_the_chord_and_the_status_line_says_both_names_and_the_notes(self):
        await self.go_to(row=chords_editor.SCALE_ROW, chord=SIXTH_CHORD)
        await self.press(keybindings.ChordsEditor.CHOOSE)
        dialog = self.app.screen
        self.assertIsInstance(dialog, ChordDialog)
        self.assertEqual(dialog.part, chord_dialog.SCALE_LIST)
        dialog.set_kind(MINOR)
        await self.settle()
        dialog.draw()
        said = str(dialog.query_one('#dialog-view').render())
        self.assertIn(messages.MSG_CHORD_SENTENCE.format(scale=C_MINOR, degree=POP_CHORDS[SIXTH_CHORD], name=A_FLAT_MAJOR), said)
        self.assertIn(messages.MSG_CHORD_OWN_SENTENCE.format(scale=C_MAJOR, name=A_MINOR), said)
        self.assertIn(A_FLAT_NOTES, said)
        # Enter opens the flyout of the category that holds Minor, on Minor; Enter picks it; and Enter takes the chord.
        await self.press(keybindings.ChordDialog.OPEN, keybindings.ChordDialog.CHOOSE, keybindings.ChordDialog.CHOOSE)
        self.assertEqual(self.progression().get_scales()[SIXTH_CHORD], MINOR)
        resting = self.page.resting_status()
        self.assertTrue(resting.startswith(messages.MSG_RESTING_CHORD.format(chord=SIXTH_CHORD + 1)))
        for part in (C_MINOR, A_FLAT_MAJOR, A_FLAT_NOTES, C_MAJOR, A_MINOR):
            self.assertIn(part, resting)
        self.assertIn(resting[:20], self.text())

    async def test_tensions_are_toggled_in_the_dialog_and_tab_goes_round_its_lists(self):
        await self.go_to(row=chords_editor.TENSION_ROW, chord=1)
        await self.press(keybindings.ChordsEditor.CHOOSE)
        dialog = self.app.screen
        self.assertEqual(dialog.part, chord_dialog.TENSION_LIST)
        await self.press(keybindings.ChordDialog.FLIP, keybindings.ChordDialog.NEXT_LIST)
        self.assertEqual(dialog.part, chord_dialog.SCALE_LIST)
        await self.press(keybindings.ChordDialog.NEXT_LIST)
        self.assertEqual(dialog.part, chord_dialog.QUALITY_LIST)
        dialog.places[chord_dialog.QUALITY_LIST] = dialog.qualities.index(ChordSymbol.DOMINANT7)
        # Right stops at the scales, the last list, and Left goes back and stops at the qualities, the first.
        await self.press(*[Key.RIGHT] * chord_dialog.LISTS)
        self.assertEqual(dialog.part, chord_dialog.SCALE_LIST)
        await self.press(*[Key.LEFT] * chord_dialog.LISTS)
        self.assertEqual(dialog.part, chord_dialog.QUALITY_LIST)
        # The inversions come next, where Down picks the first inversion, and then the tensions.
        await self.press(Key.RIGHT, Key.DOWN)
        self.assertEqual(dialog.part, chord_dialog.INVERSION_LIST)
        await self.press(Key.RIGHT)
        self.assertEqual(dialog.part, chord_dialog.TENSION_LIST)
        await self.press(Key.ENTER)
        self.assertEqual(self.progression().get_tensions()[1], (Tension.FLAT_NINTH,))
        self.assertEqual(self.progression().get_qualities()[1], ChordSymbol.DOMINANT7)
        self.assertEqual(self.progression().get_inversions()[1], generator_settings.PROGRESSION_INVERSIONS[0])
        self.assertIn(G_SEVEN_FLAT_NINE, self.text())

    async def test_escape_in_the_dialog_changes_nothing(self):
        before = self.progression().to_data()
        await self.go_to(row=chords_editor.QUALITY_ROW)
        await self.press(keybindings.ChordsEditor.CHOOSE, Key.DOWN, Key.DOWN, keybindings.ChordDialog.CANCEL)
        self.assertIsInstance(self.app.screen, ChordsEditor)
        self.assertEqual(self.progression().to_data(), before)

    async def test_inserting_and_removing_a_chord_carries_every_row(self):
        await self.go_to(row=chords_editor.QUALITY_ROW, chord=1)
        await self.press(keybindings.ChordsEditor.NEXT_CHOICE, keybindings.ChordsEditor.INSERT_STEP)
        self.assertEqual(self.progression().get_qualities(), [None, None, ChordSymbol.MAJOR, None, None])
        await self.press(keybindings.ChordsEditor.REMOVE_STEP)
        self.assertEqual(self.progression().get_qualities(), [None, ChordSymbol.MAJOR, None, None])

    async def test_a_chord_is_inserted_before_the_cursor_and_removed_at_it(self):
        await self.press(Key.RIGHT, keybindings.ChordsEditor.INSERT_STEP)
        self.assertEqual(self.progression().get_chords(), [POP_CHORDS[0], limits.MIN_PROGRESSION_DEGREE, *POP_CHORDS[1:]])
        await self.press(keybindings.ChordsEditor.REMOVE_STEP)
        self.assertEqual(self.progression().get_chords(), POP_CHORDS)

    async def test_a_full_row_offers_no_insert_and_one_chord_no_remove(self):
        await self.press(*[keybindings.ChordsEditor.INSERT_STEP] * limits.MAX_PROGRESSION_CHORDS)
        self.assertEqual(len(self.progression().get_chords()), limits.MAX_PROGRESSION_CHORDS)
        # A row longer than the console follows the cursor to its last chord.
        await self.press(*[Key.RIGHT] * limits.MAX_PROGRESSION_CHORDS)
        self.assertIn(str(limits.MAX_PROGRESSION_CHORDS), self.text())
        await self.press(*[keybindings.ChordsEditor.REMOVE_STEP] * limits.MAX_PROGRESSION_CHORDS)
        self.assertEqual(len(self.progression().get_chords()), 1)

    async def test_h_fills_the_chords_with_a_named_progression_matched_to_the_scale(self):
        await self.press(keybindings.ChordsEditor.PICK)
        self.assertIsInstance(self.app.screen, GridChoiceDialog)
        self.assertIn(labels.MSG_PROGRESSION_NAMES[NamedProgression.ROCK], self.app.screen.options)
        self.app.screen.cursor.set_place(self.app.screen.options.index(labels.MSG_PROGRESSION_NAMES[NamedProgression.ROCK]))
        await self.press(Key.ENTER)
        self.assertEqual(len(self.progression().get_chords()), len(named_progression(NamedProgression.ROCK)))
        self.assertEqual(self.progression().get_accidentals(), [None, Accidental.FLAT, None])

    async def test_left_and_right_stop_at_the_ends(self):
        await self.press(Key.LEFT)
        self.assertEqual(self.page.step, 0)
        await self.press(*[Key.RIGHT] * (len(POP_CHORDS) + 1))
        self.assertEqual(self.page.step, len(POP_CHORDS) - 1)



class TestRestartField(UITest):
    """Every generator's editor ends its own settings with Restart: every clip, on new scene or whole song."""

    async def test_restart_steps_through_its_choices(self):
        await self.open_generator(section=Section.PROGRESSIONS)
        progression = self.document.song().get_generator_settings(kind=GeneratorKind.PROGRESSION, name=ui_testing.POP)
        self.assertEqual(progression.get_restart(), Restart.EVERY_CLIP)
        self.assertIn(labels.MSG_RESTART_NAMES[Restart.EVERY_CLIP], self.text())
        await self.select_field(labels.MSG_RESTART_LABEL)
        await self.press(keybindings.ProgressionEditor.MORE)
        self.assertEqual(self.document.song().get_generator_settings(kind=GeneratorKind.PROGRESSION, name=ui_testing.POP).get_restart(), Restart.ON_NEW_SCENE)
        await self.press(keybindings.ProgressionEditor.MORE)
        self.assertEqual(self.document.song().get_generator_settings(kind=GeneratorKind.PROGRESSION, name=ui_testing.POP).get_restart(), Restart.WHOLE_SONG)
