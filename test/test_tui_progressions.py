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
"""The tracker's Progression: the Progressions page, the progression editor and the chord editor, with the picker of named progressions."""

from ui_testing import POP, UITest
from llamatron.composition.file_format import Section, ONE_BAR_WRITTEN, TIME_CHOICES, Accidental, ChordSymbol, GeneratorKind, NamedProgression, Restart, Tension
from llamatron.composition.named_scale import scale_type_name
from llamatron.music.scale import ScaleType
from llamatron.strings.messages import MSG_CHORD_OWN_SENTENCE, MSG_CHORD_SENTENCE, MSG_RESTING_CHORD
from llamatron.tui.dialogs.chord_dialog import QUALITY_LIST, SCALE_LIST, TENSION_LIST, ChordDialog
from llamatron.composition.limits import MAX_PROGRESSION_CHORDS, MAX_PROGRESSION_DEGREE, MIN_PROGRESSION_DEGREE
from llamatron.composition.progressions import named_progression
from llamatron.strings.labels import MSG_CHORDS_LABEL, MSG_EVERY_LABEL, MSG_PROGRESSION_NAMES, MSG_RESTART_LABEL, MSG_RESTART_NAMES
from llamatron.tui.dialogs.grid_choice_dialog import GridChoiceDialog
from llamatron.tui.keys import Key
from llamatron.tui.screens.chords_editor import ACCIDENTAL_ROW, CHORD_ROW, INVERSION_ROW, QUALITY_CYCLE, QUALITY_ROW, SCALE_ROW, TENSION_ROW, ChordsEditor
from llamatron.tui.screens.progression_editor import ProgressionEditor
from llamatron.tui import keybindings

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
        self.assertEqual(self.document.song().get_generator_settings(kind=GeneratorKind.PROGRESSION, name=name).get_chords(), [MIN_PROGRESSION_DEGREE])


class TestProgressionEditor(UITest):
    """The progression editor: its Every from the one list of times, and its Chords field opening the chord editor."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.open_generator(section=Section.PROGRESSIONS)
        self.assertIsInstance(self.app.screen, ProgressionEditor)

    def progression(self):
        return self.document.song().get_generator_settings(kind=GeneratorKind.PROGRESSION, name=POP)

    async def test_every_starts_at_a_bar_and_steps_through_the_list(self):
        self.assertIn(ONE_BAR_WRITTEN, self.text())
        await self.select_field(MSG_EVERY_LABEL)
        await self.press(keybindings.ProgressionEditor.MORE)
        self.assertEqual(self.progression().get_every(), [time for time in TIME_CHOICES if time != ONE_BAR_WRITTEN][0])

    async def test_the_chords_field_shows_the_numerals_and_opens_the_chord_editor(self):
        self.assertIn(POP_NUMERALS, self.text())
        await self.select_field(MSG_CHORDS_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChordsEditor)


class TestChordsEditor(UITest):
    """The chord editor: degrees stepped and typed, the #/b and Inv. rows, chords inserted and removed, and H filling the chords."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.app.screen.show_page(ChordsEditor(holder=self.app.screen.holder, name=POP))
        await self.pilot.pause()
        self.page = self.app.screen

    def progression(self):
        return self.document.song().get_generator_settings(kind=GeneratorKind.PROGRESSION, name=POP)

    async def test_it_shows_each_chords_numeral_and_name_in_the_songs_scale(self):
        for name in POP_NAMES:
            self.assertIn(name, self.text())
        for numeral in POP_NUMERALS.split():
            self.assertIn(numeral, self.text())

    async def test_the_degree_steps_from_1_to_7_and_stops(self):
        await self.press(*[keybindings.ChordsEditor.MORE] * MAX_PROGRESSION_DEGREE)
        self.assertEqual(self.progression().get_chords()[0], MAX_PROGRESSION_DEGREE)
        await self.press(*[keybindings.ChordsEditor.LESS] * (MAX_PROGRESSION_DEGREE + 1))
        self.assertEqual(self.progression().get_chords()[0], MIN_PROGRESSION_DEGREE)

    async def test_digits_type_a_degree_and_one_out_of_range_types_nothing(self):
        await self.press(SIX)
        self.assertEqual(self.progression().get_chords()[0], int(SIX))
        await self.press(NINE)
        self.assertEqual(self.progression().get_chords()[0], int(SIX))

    async def test_up_and_down_reach_the_flat_and_inversion_rows_and_stop(self):
        await self.press(Key.UP)
        self.assertEqual(self.page.edited_row, CHORD_ROW)
        await self.press(Key.DOWN, keybindings.ChordsEditor.NEXT, keybindings.ChordsEditor.NEXT)
        self.assertEqual(self.page.edited_row, ACCIDENTAL_ROW)
        self.assertEqual(self.progression().get_accidentals()[0], Accidental.FLAT)
        await self.press(*[Key.DOWN] * (INVERSION_ROW - ACCIDENTAL_ROW + 1), TWO)
        self.assertEqual(self.page.edited_row, INVERSION_ROW)
        self.assertEqual(self.progression().get_inversions()[0], int(TWO))
        await self.press(ZERO)
        self.assertIsNone(self.progression().get_inversions()[0])

    async def go_to(self, *, row, chord=0):
        await self.press(*[Key.RIGHT] * chord, *[Key.DOWN] * row)
        self.assertEqual(self.page.edited_row, row)

    async def test_a_quality_is_stepped_and_cleared_and_names_the_chord(self):
        await self.go_to(row=QUALITY_ROW, chord=SIXTH_CHORD)
        await self.press(keybindings.ChordsEditor.NEXT_CHOICE)
        self.assertEqual(self.progression().get_qualities()[SIXTH_CHORD], ChordSymbol.MAJOR)
        self.assertIn(A_MAJOR + ' Major', self.text())
        self.assertIn(POP_NUMERALS.split()[SIXTH_CHORD].upper(), self.text())
        await self.press(keybindings.ChordsEditor.MORE, keybindings.ChordsEditor.LESS, keybindings.ChordsEditor.CLEAR)
        self.assertIsNone(self.progression().get_qualities()[SIXTH_CHORD])
        # A quality stops at the first choice and at the last, never going round (the user's rule).
        await self.press(keybindings.ChordsEditor.LESS)
        self.assertIsNone(self.progression().get_qualities()[SIXTH_CHORD])
        await self.press(*[keybindings.ChordsEditor.MORE] * (len(QUALITY_CYCLE) + 1))
        self.assertEqual(self.progression().get_qualities()[SIXTH_CHORD], QUALITY_CYCLE[-1])

    async def test_a_scale_borrows_the_chord_and_the_status_line_says_both_names_and_the_notes(self):
        await self.go_to(row=SCALE_ROW, chord=SIXTH_CHORD)
        await self.press(keybindings.ChordsEditor.CHOOSE)
        dialog = self.app.screen
        self.assertIsInstance(dialog, ChordDialog)
        self.assertEqual(dialog.part, SCALE_LIST)
        dialog.set_kind(MINOR)
        await self.settle()
        dialog.draw()
        said = str(dialog.query_one('#dialog-view').render())
        self.assertIn(MSG_CHORD_SENTENCE.format(scale=C_MINOR, degree=POP_CHORDS[SIXTH_CHORD], name=A_FLAT_MAJOR), said)
        self.assertIn(MSG_CHORD_OWN_SENTENCE.format(scale=C_MAJOR, name=A_MINOR), said)
        self.assertIn(A_FLAT_NOTES, said)
        # Enter opens the flyout of the category that holds Minor, on Minor; Enter picks it; and Enter takes the chord.
        await self.press(keybindings.ChordDialog.OPEN, keybindings.ChordDialog.CHOOSE, keybindings.ChordDialog.CHOOSE)
        self.assertEqual(self.progression().get_scales()[SIXTH_CHORD], MINOR)
        resting = self.page.resting_status()
        self.assertTrue(resting.startswith(MSG_RESTING_CHORD.format(chord=SIXTH_CHORD + 1)))
        for part in (C_MINOR, A_FLAT_MAJOR, A_FLAT_NOTES, C_MAJOR, A_MINOR):
            self.assertIn(part, resting)
        self.assertIn(resting[:20], self.text())

    async def test_tensions_are_toggled_in_the_dialog_and_tab_goes_round_its_lists(self):
        await self.go_to(row=TENSION_ROW, chord=1)
        await self.press(keybindings.ChordsEditor.CHOOSE)
        dialog = self.app.screen
        self.assertEqual(dialog.part, TENSION_LIST)
        await self.press(keybindings.ChordDialog.FLIP, keybindings.ChordDialog.NEXT_LIST)
        self.assertEqual(dialog.part, SCALE_LIST)
        await self.press(keybindings.ChordDialog.NEXT_LIST)
        self.assertEqual(dialog.part, QUALITY_LIST)
        dialog.places[QUALITY_LIST] = dialog.qualities.index(ChordSymbol.DOMINANT7)
        # Right stops at the scales, the last list, and Left goes back and stops at the qualities, the first.
        await self.press(Key.RIGHT, Key.RIGHT, Key.RIGHT)
        self.assertEqual(dialog.part, SCALE_LIST)
        await self.press(Key.LEFT, Key.LEFT, Key.LEFT)
        self.assertEqual(dialog.part, QUALITY_LIST)
        await self.press(Key.RIGHT)
        self.assertEqual(dialog.part, TENSION_LIST)
        await self.press(Key.ENTER)
        self.assertEqual(self.progression().get_tensions()[1], (Tension.FLAT_NINTH,))
        self.assertEqual(self.progression().get_qualities()[1], ChordSymbol.DOMINANT7)
        self.assertIn(G_SEVEN_FLAT_NINE, self.text())

    async def test_escape_in_the_dialog_changes_nothing(self):
        before = self.progression().to_data()
        await self.go_to(row=QUALITY_ROW)
        await self.press(keybindings.ChordsEditor.CHOOSE, Key.DOWN, Key.DOWN, keybindings.ChordDialog.CANCEL)
        self.assertIsInstance(self.app.screen, ChordsEditor)
        self.assertEqual(self.progression().to_data(), before)

    async def test_inserting_and_removing_a_chord_carries_every_row(self):
        await self.go_to(row=QUALITY_ROW, chord=1)
        await self.press(keybindings.ChordsEditor.NEXT_CHOICE, keybindings.ChordsEditor.INSERT_STEP)
        self.assertEqual(self.progression().get_qualities(), [None, None, ChordSymbol.MAJOR, None, None])
        await self.press(keybindings.ChordsEditor.REMOVE_STEP)
        self.assertEqual(self.progression().get_qualities(), [None, ChordSymbol.MAJOR, None, None])

    async def test_a_chord_is_inserted_before_the_cursor_and_removed_at_it(self):
        await self.press(Key.RIGHT, keybindings.ChordsEditor.INSERT_STEP)
        self.assertEqual(self.progression().get_chords(), [POP_CHORDS[0], MIN_PROGRESSION_DEGREE, *POP_CHORDS[1:]])
        await self.press(keybindings.ChordsEditor.REMOVE_STEP)
        self.assertEqual(self.progression().get_chords(), POP_CHORDS)

    async def test_a_full_row_offers_no_insert_and_one_chord_no_remove(self):
        await self.press(*[keybindings.ChordsEditor.INSERT_STEP] * MAX_PROGRESSION_CHORDS)
        self.assertEqual(len(self.progression().get_chords()), MAX_PROGRESSION_CHORDS)
        await self.press(*[keybindings.ChordsEditor.REMOVE_STEP] * MAX_PROGRESSION_CHORDS)
        self.assertEqual(len(self.progression().get_chords()), 1)

    async def test_h_fills_the_chords_with_a_named_progression_matched_to_the_scale(self):
        await self.press(keybindings.ChordsEditor.PICK)
        self.assertIsInstance(self.app.screen, GridChoiceDialog)
        self.assertIn(MSG_PROGRESSION_NAMES[NamedProgression.ROCK], self.app.screen.options)
        self.app.screen.place = self.app.screen.options.index(MSG_PROGRESSION_NAMES[NamedProgression.ROCK])
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
        progression = self.document.song().get_generator_settings(kind=GeneratorKind.PROGRESSION, name=POP)
        self.assertEqual(progression.get_restart(), Restart.EVERY_CLIP)
        self.assertIn(MSG_RESTART_NAMES[Restart.EVERY_CLIP], self.text())
        await self.select_field(MSG_RESTART_LABEL)
        await self.press(keybindings.ProgressionEditor.MORE)
        self.assertEqual(self.document.song().get_generator_settings(kind=GeneratorKind.PROGRESSION, name=POP).get_restart(), Restart.ON_NEW_SCENE)
        await self.press(keybindings.ProgressionEditor.MORE)
        self.assertEqual(self.document.song().get_generator_settings(kind=GeneratorKind.PROGRESSION, name=POP).get_restart(), Restart.WHOLE_SONG)
