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
"""Opening a set file that holds values that can't be used, in the tracker: the Corrections dialog, from the Open page and when the tracker starts on such a file.

Yes opens the set with each value changed to the allowed value nearest it and marks the set
unsaved, since the file still holds what it did. No opens nothing. The dialog lists only the
first few corrections and cuts a long one short, so that it always fits an 80 by 24 console.
The two sets opened here are in test/sample_sets.
"""

import io
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr
from unittest import mock

from textual.widgets import Static

from ui_testing import UITest, a_song
from llamatron.composition.file_format import PatternSetting, Row, Section, SetlistSetting
from llamatron.composition.limits import MAX_OCTAVE, MIN_OCTAVE
from llamatron.composition.setlist import Setlist
from llamatron.composition.setlist_writer import dump_setlist
from llamatron.composition.song_file_error import SongFileError
from llamatron.music.midi import MAX_VELOCITY
from llamatron.strings.errors import ERR_CANT_OPEN_TITLE, ERR_PRINTED
from llamatron.strings.labels import MSG_NO_FILE_CRUMB, MSG_PROTECTED_LABEL, MSG_SET_CRUMB, MSG_SONG_CRUMB
from llamatron.strings.marks import MSG_UNSAVED_CHANGES_MARK, MSG_UNSAVED_MARK
from llamatron.strings.messages import (
    MSG_CORRECTIONS_INTRO, MSG_CORRECTIONS_MORE, MSG_CORRECTIONS_QUESTION, MSG_CORRECTIONS_TITLE, MSG_CORRECTIONS_WARNING, MSG_OPENED, MSG_SAVED,
)
from llamatron.tui import app as tui_app
from llamatron.tui import keybindings
from llamatron.tui.app import LlamatronApp
from llamatron.tui.dialogs.corrections_dialog import MOST_SHOWN, CorrectionsDialog
from llamatron.tui.dialogs.dialog import DIALOG_MARGIN, DIALOG_VIEW_SELECTOR, DIALOG_WIDTH
from llamatron.tui.dialogs.message_dialog import MessageDialog
from llamatron.tui.document import Document
from llamatron.tui.drawing import ELLIPSIS, Box, fit
from llamatron.tui.keys import Key
from llamatron.tui.screens.main_page import MainPage
from llamatron.tui.screens.open_page import OpenPage

# The two sets made for these tests, and the names their copies go by in a test's own folder.
SAMPLE_SETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sample_sets')
SAMPLE = 'out_of_range.yml'
BROKEN = 'out_of_range_and_broken.yml'
FINE = 'fine.yml'
ONE_WRONG = 'one wrong.yml'
LONG_NAMES = 'long names.yml'
READ_BYTES = 'rb'
WRITE_TEXT = 'w'
# The console every page and dialog has to fit.
CONSOLE = (80, 24)
# A pattern's name too long for one line of the dialog.
A_LONG_NAME = 'the tune that the lead plays in the last chorus before the long quiet ending'
STEPS = 2
A_DEGREE = 1
SPACE = ' '
# The keyword the tracker's app takes the corrections by.
CORRECTIONS_ARGUMENT = 'corrections'
DOCUMENT_ARGUMENT = 'document'
RUN = 'run'


def copy_of(name):
    """Copy one of the sample sets into the working directory, which is the test's own folder, and return its name there."""
    shutil.copy(os.path.join(SAMPLE_SETS, name), name)
    return name


def file_bytes(path):
    with open(path, READ_BYTES) as file:
        return file.read()


def write_set(*, path, data):
    with open(path, WRITE_TEXT) as file:
        file.write(dump_setlist(data))


def corrections_of(path):
    """Return the line that describes each correction a file needs, in the order the dialog lists them."""
    return [correction.described() for correction in Setlist.read_file_corrected(path)[1]]


class CorrectionsTest(UITest):
    """What the tests of the dialog share: choosing a file on the Open page, and reading what the dialog says."""

    SIZE = CONSOLE

    async def choose(self, name):
        """Show the Open page from the page on screen and press Enter on a file."""
        await self.press(Key.CTRL_O)
        rows = [row[0] for row in self.app.screen.rows()]
        self.app.screen.place = rows.index(name)
        await self.press(Key.ENTER)

    def inner_width(self):
        """Return how wide a line inside a dialog can be on this console."""
        columns, _ = self.SIZE
        return min(columns - DIALOG_MARGIN, DIALOG_WIDTH) - DIALOG_MARGIN

    def said(self):
        """Return what the dialog on screen drew as one run of words, so that a sentence the dialog wrapped over two lines can be looked for."""
        drawn = self.app.screen.query_one(DIALOG_VIEW_SELECTOR, Static).content.plain
        return SPACE.join(drawn.replace(Box.HEAVY_BAR, SPACE).split())


class TestCorrectionsDialog(CorrectionsTest):

    async def test_a_file_with_values_out_of_range_asks_before_anything_opens(self):
        before = self.app.get_document()
        await self.choose(copy_of(SAMPLE))
        self.assertIsInstance(self.app.screen, CorrectionsDialog)
        self.assertIs(self.app.get_document(), before)
        said = self.said()
        for sentence in [MSG_CORRECTIONS_TITLE, MSG_CORRECTIONS_INTRO.format(file=SAMPLE), MSG_CORRECTIONS_WARNING, MSG_CORRECTIONS_QUESTION]:
            self.assertIn(sentence, said)

    async def test_only_the_first_few_are_listed_with_a_count_of_the_rest(self):
        await self.choose(copy_of(SAMPLE))
        lines = corrections_of(SAMPLE)
        self.assertGreater(len(lines), MOST_SHOWN)
        text = self.text()
        for line in lines[:MOST_SHOWN]:
            self.assertIn(fit(text=line, width=self.inner_width()).rstrip(), text)
        for line in lines[MOST_SHOWN:]:
            self.assertNotIn(line, text)
        self.assertIn(MSG_CORRECTIONS_MORE.format(count=len(lines) - MOST_SHOWN), text)

    async def test_a_few_are_all_listed_with_no_count(self):
        write_set(path=ONE_WRONG, data={SetlistSetting.DEFAULT_OCTAVE: MAX_OCTAVE + 1})
        await self.choose(ONE_WRONG)
        (line,) = corrections_of(ONE_WRONG)
        self.assertIn(line, self.text())
        self.assertNotIn(MSG_CORRECTIONS_MORE.format(count=0), self.text())

    async def test_a_line_wider_than_the_dialog_is_cut_short_with_an_ellipsis(self):
        pattern = {PatternSetting.STEPS: STEPS, Row.DEGREE: [A_DEGREE] * STEPS, Row.VELOCITY: [MAX_VELOCITY + 1] * STEPS}
        write_set(path=LONG_NAMES, data={Section.PATTERNS: {A_LONG_NAME: pattern}})
        await self.choose(LONG_NAMES)
        (line,) = corrections_of(LONG_NAMES)
        self.assertGreater(len(line), self.inner_width())
        cut = fit(text=line, width=self.inner_width())
        self.assertTrue(cut.endswith(ELLIPSIS))
        self.assertIn(cut, self.text())
        self.assertNotIn(line, self.text())

    async def test_the_whole_dialog_is_on_an_80_by_24_console_however_many_corrections_there_are(self):
        await self.choose(copy_of(SAMPLE))
        columns, rows = CONSOLE
        lines = self.text().splitlines()
        self.assertLessEqual(len(lines), rows)
        self.assertTrue(any(Box.HEAVY_TOP_LEFT in line for line in lines))
        self.assertTrue(any(Box.HEAVY_BOTTOM_LEFT in line for line in lines))
        self.assertIn(MSG_CORRECTIONS_QUESTION, self.text())

    async def test_yes_opens_the_set_corrected_and_unsaved_and_leaves_the_file_alone(self):
        before = file_bytes(copy_of(SAMPLE))
        await self.choose(SAMPLE)
        await self.press(keybindings.CorrectionsDialog.YES)
        self.assertIsInstance(self.app.screen, MainPage)
        document = self.app.get_document()
        self.assertEqual(document.get_path(), SAMPLE)
        self.assertEqual(document.setlist().get_default_octave(), MIN_OCTAVE)
        self.assertTrue(document.is_dirty())
        self.assertIn(MSG_UNSAVED_CHANGES_MARK, self.title_line())
        self.assertIn(MSG_OPENED.format(path=SAMPLE), self.text())
        self.assertEqual(file_bytes(SAMPLE), before)

    async def test_enter_presses_yes_which_the_dialog_opens_on(self):
        await self.choose(copy_of(SAMPLE))
        await self.press(keybindings.CorrectionsDialog.ANSWER)
        self.assertEqual(self.app.get_document().get_path(), SAMPLE)

    async def test_no_opens_nothing_and_stays_on_the_open_page(self):
        before = self.app.get_document()
        contents = file_bytes(copy_of(SAMPLE))
        await self.choose(SAMPLE)
        await self.press(keybindings.CorrectionsDialog.NO)
        self.assertIsInstance(self.app.screen, OpenPage)
        self.assertIs(self.app.get_document(), before)
        self.assertEqual(file_bytes(SAMPLE), contents)

    async def test_esc_and_the_no_button_open_nothing_either(self):
        before = self.app.get_document()
        await self.choose(copy_of(SAMPLE))
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, OpenPage)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, CorrectionsDialog)
        await self.press(Key.RIGHT, keybindings.CorrectionsDialog.ANSWER)
        self.assertIsInstance(self.app.screen, OpenPage)
        self.assertIs(self.app.get_document(), before)

    async def test_saving_the_opened_set_writes_the_corrected_values_to_the_file(self):
        await self.choose(copy_of(SAMPLE))
        await self.press(keybindings.CorrectionsDialog.YES, keybindings.Page.SAVE)
        self.assertIn(MSG_SAVED.format(path=SAMPLE), self.text())
        self.assertFalse(self.app.get_document().is_dirty())
        self.assertEqual(Setlist.read_file(SAMPLE).get_default_octave(), MIN_OCTAVE)
        self.assertEqual(Document.load_or_correct(SAMPLE)[1], [])

    async def test_undoing_an_edit_made_after_opening_leaves_the_set_unsaved(self):
        await self.choose(copy_of(SAMPLE))
        await self.press(keybindings.CorrectionsDialog.YES, keybindings.MainPage.FILE)
        await self.select_field(MSG_PROTECTED_LABEL)
        await self.press(Key.ENTER, keybindings.Page.UNDO)
        self.assertFalse(self.app.get_document().setlist().is_protected())
        self.assertTrue(self.app.get_document().is_dirty())

    async def test_a_file_with_a_problem_nothing_can_correct_is_refused_in_a_message_as_before(self):
        before = self.app.get_document()
        await self.choose(copy_of(BROKEN))
        self.assertIs(type(self.app.screen), MessageDialog)
        self.assertIn(ERR_CANT_OPEN_TITLE, self.text())
        self.assertIs(self.app.get_document(), before)

    async def test_a_file_with_nothing_wrong_opens_without_asking(self):
        a_song().save(path=FINE)
        await self.choose(FINE)
        self.assertIsInstance(self.app.screen, MainPage)
        self.assertEqual(self.app.get_document().get_path(), FINE)
        self.assertFalse(self.app.get_document().is_dirty())


class TestStartingTheTrackerOnSuchAFile(CorrectionsTest):
    """`llamatron out_of_range.yml` asks the same question over the main screen, with a new set behind it until the answer is yes."""

    def make_app(self):
        self.offered, corrections = Document.load_or_correct(copy_of(SAMPLE))
        return LlamatronApp(document=self.offered, corrections=corrections)

    async def test_the_dialog_is_asked_over_the_main_screen_before_the_set_is_opened(self):
        self.assertIsInstance(self.app.screen, CorrectionsDialog)
        self.assertIsNot(self.app.get_document(), self.offered)
        self.assertIsNone(self.app.get_document().get_path())
        self.assertIn(MSG_CORRECTIONS_INTRO.format(file=SAMPLE), self.said())

    async def test_yes_opens_the_set_corrected_and_unsaved(self):
        await self.press(keybindings.CorrectionsDialog.YES)
        self.assertIsInstance(self.app.screen, MainPage)
        self.assertIs(self.app.get_document(), self.offered)
        self.assertTrue(self.app.get_document().is_dirty())
        header = self.title_line()
        self.assertIn(MSG_SET_CRUMB.format(file=SAMPLE), header)
        self.assertIn(MSG_SONG_CRUMB.format(song=self.offered.current_song_name()), self.song_line())
        self.assertIn(MSG_UNSAVED_CHANGES_MARK, header)

    async def test_no_leaves_a_new_set_with_no_file(self):
        await self.press(keybindings.CorrectionsDialog.NO)
        self.assertIsInstance(self.app.screen, MainPage)
        document = self.app.get_document()
        self.assertIsNone(document.get_path())
        self.assertFalse(document.is_dirty())
        header = self.title_line()
        self.assertIn(MSG_NO_FILE_CRUMB, header)
        # A set that has no file is unsaved, whether or not anything was changed.
        self.assertIn(MSG_UNSAVED_MARK, header)
        self.assertNotIn(MSG_UNSAVED_CHANGES_MARK, header)


class TestTheDocumentOfSuchAFile(unittest.TestCase):
    """Document.load_or_correct, which the Open page and the tracker's start both read a file with."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(temporary.name)

    def test_a_file_with_nothing_wrong_has_no_corrections_and_nothing_unsaved(self):
        a_song().save(path=FINE)
        document, corrections = Document.load_or_correct(FINE)
        self.assertEqual(corrections, [])
        self.assertFalse(document.is_dirty())

    def test_a_corrected_set_is_unsaved_has_nothing_to_undo_and_its_file_is_not_said_to_have_changed(self):
        document, corrections = Document.load_or_correct(copy_of(SAMPLE))
        self.assertEqual([correction.described() for correction in corrections], corrections_of(SAMPLE))
        self.assertTrue(document.is_dirty())
        self.assertFalse(document.can_undo())
        self.assertFalse(document.file_changed_elsewhere())
        self.assertFalse(document.file_holds_this_set())

    def test_saving_it_makes_the_file_one_that_reads_strictly(self):
        document, _ = Document.load_or_correct(copy_of(SAMPLE))
        document.save()
        self.assertFalse(document.is_dirty())
        self.assertTrue(document.file_holds_this_set())
        Setlist.read_file(SAMPLE)

    def test_a_problem_nothing_can_correct_is_raised(self):
        with self.assertRaises(SongFileError) as refused:
            Document.load_or_correct(copy_of(BROKEN))
        self.assertIsNone(refused.exception.get_correction())

    def test_loading_stays_strict(self):
        with self.assertRaises(SongFileError):
            Document.load(copy_of(SAMPLE))


class TestTheTrackersCommand(unittest.TestCase):
    """The tracker's main, with only the app's run patched out, so that the real call into the app is checked."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(temporary.name)

    def start(self, path):
        """Run the tracker's main on a file and return its exit code, what it printed as errors and how the app was made."""
        errors = io.StringIO()
        with mock.patch.object(LlamatronApp, RUN) as run, mock.patch.object(tui_app, LlamatronApp.__name__, wraps=LlamatronApp) as made:
            with redirect_stderr(errors):
                code = tui_app.main(argv=[path])
        return code, errors.getvalue(), made, run

    def test_a_file_with_values_out_of_range_starts_the_tracker_with_the_corrections_to_ask_about(self):
        code, errors, made, run = self.start(copy_of(SAMPLE))
        self.assertEqual(code, 0)
        self.assertEqual(errors, '')
        run.assert_called_once()
        described = [correction.described() for correction in made.call_args.kwargs[CORRECTIONS_ARGUMENT]]
        self.assertEqual(described, corrections_of(SAMPLE))
        self.assertEqual(made.call_args.kwargs[DOCUMENT_ARGUMENT].get_path(), SAMPLE)

    def test_a_file_with_nothing_wrong_starts_it_with_none(self):
        a_song().save(path=FINE)
        code, errors, made, run = self.start(FINE)
        self.assertEqual(code, 0)
        self.assertFalse(made.call_args.kwargs[CORRECTIONS_ARGUMENT])

    def test_a_file_nothing_can_correct_is_explained_and_the_tracker_does_not_start(self):
        code, errors, made, run = self.start(copy_of(BROKEN))
        self.assertEqual(code, 1)
        run.assert_not_called()
        with self.assertRaises(SongFileError) as refused:
            Setlist.read_file_corrected(BROKEN)
        self.assertIn(ERR_PRINTED.format(problem=refused.exception), errors)


if __name__ == '__main__':
    unittest.main()
