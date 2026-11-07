# llamatron: a Python language and framework for producing MIDI clips.
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

"""The main screen, the Song and Description pages, loading, the keys every page shows, help and the program's look."""

import os
import unittest
from fractions import Fraction
from unittest import mock

from textual.app import App
from textual.screen import Screen

from ui_testing import CHROMATIC_SCALE, UITest, a_song
from llamatron.composition.file_format import CellSetting, Direction, Row, STEP_SIZE_CHOICES
from llamatron.composition.named_scale import scale_type_name
from llamatron.composition.song import NO_TEXT
from llamatron.note import NoteName
from llamatron.scale import ScaleType
from llamatron.tui.app import LlamatronApp
from llamatron.tui.arrange import ArrangePage, ClipPage, ScenePage
from llamatron.tui.base import ChoiceDialog, ConfirmDialog, Dialog, GridChoiceDialog, MessageDialog, Page, PromptDialog
from llamatron.tui.document import DEFAULT_SCALE, Document, new_song
from llamatron.tui.lists import FieldPage, ListPage
from llamatron.tui.pages import (
    ArpEditor, ArpsPage, AutoRatchetEditor, AutoRatchetsPage, ChainEditor, ChainsPage, DescriptionPage, FilePage,
    GeneratorsPage, MainPage, PatternsPage, ScalesPage, SongPage, TracksPage,
)
from llamatron.tui.pattern_editor import PatternEditor
from llamatron.version import VERSION
from rendering import render_song


class TestMainScreen(UITest):

    async def test_opens_on_the_main_screen_with_every_page_listed(self):
        self.assertIsInstance(self.app.screen, MainPage)
        for label in ['S', 'P', 'T', 'C', 'G', 'Z', 'A', 'Q', 'H']:
            self.assertIn(f'« {label} »', self.text())

    async def test_each_key_opens_its_page(self):
        for name, page in [('s', SongPage), ('p', PatternsPage), ('t', TracksPage), ('c', ChainsPage), ('g', GeneratorsPage), ('z', ScalesPage), ('a', ArrangePage)]:
            await self.press(name)
            self.assertIsInstance(self.app.screen, page)
            await self.press('tab')
            self.assertIsInstance(self.app.screen, MainPage)

    async def test_upper_and_lower_case_are_the_same(self):
        await self.press('P')
        self.assertIsInstance(self.app.screen, PatternsPage)

    async def test_tab_never_quits(self):
        await self.press('tab', 'tab')
        self.assertIsInstance(self.app.screen, MainPage)
        self.assertTrue(self.app.is_running)

    async def test_quit_asks_only_if_there_are_unsaved_changes(self):
        self.document.changed()
        await self.press('q')
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press('n')
        self.assertIsInstance(self.app.screen, MainPage)
        self.assertTrue(self.app.is_running)
        await self.press('q', 'y')
        self.assertIsNotNone(self.app._exit)

    async def test_descriptions_start_with_a_capital_letter(self):
        for about in MainPage.ABOUT.values():
            self.assertTrue(about[0].isupper(), about)
        self.assertIn('Lists of generators used by clips', self.text())

    async def test_shows_the_length_of_the_song(self):
        self.assertIn('0:01', self.text())


class TestRealKeys(UITest):
    """Presses keys the slow way, through the same path that a terminal's keys take."""

    async def test_keys_arrive_with_the_names_the_screens_expect(self):
        await self.pilot.press('P')
        self.assertIsInstance(self.app.screen, PatternsPage)
        await self.pilot.press('enter')
        editor = self.app.screen
        self.assertIsInstance(editor, PatternEditor)
        await self.pilot.press('right', '5')
        self.assertEqual(self.document.step_value('tune', Row.DEGREE, 1), 5)
        await self.pilot.press('down', 'plus')
        self.assertEqual(self.document.step_value('tune', Row.GATE, 1), '1/2')
        await self.pilot.press('asterisk')
        self.assertEqual(self.document.step_value('tune', Row.GATE, 1), 1)
        await self.pilot.press('slash')
        self.assertEqual(self.document.step_value('tune', Row.GATE, 1), '1/2')
        await self.pilot.press('minus')
        self.assertEqual(self.document.step_value('tune', Row.GATE, 1), '1/4')
        await self.pilot.press('down', 'space')
        self.assertEqual(self.document.step_value('tune', Row.DOT, 1), 'd')
        await self.pilot.press('down', 'space')
        self.assertEqual(self.document.step_value('tune', Row.ACCIDENTAL, 1), '#')
        await self.pilot.press('backspace')
        self.assertIsNone(self.document.step_value('tune', Row.ACCIDENTAL, 1))
        await self.pilot.press('tab', 'tab')
        self.assertIsInstance(self.app.screen, MainPage)
        await self.pilot.press('p', 'escape')
        self.assertIsInstance(self.app.screen, PatternsPage)

    async def test_control_q_asks_too(self):
        self.document.changed()
        await self.pilot.press('ctrl+q')
        await self.pilot.pause()
        self.assertIsInstance(self.app.screen, ConfirmDialog)


class TestEveryKeyIsShown(UITest):

    async def visit(self):
        yield 'main'
        await self.press('s')
        yield 'song'
        for _ in range(6):
            await self.press('down')
            yield 'song field'
        await self.press('d')
        yield 'description'
        await self.press('e')
        yield 'description editing'
        await self.press('tab', 'tab', 'tab', 'p')
        yield 'patterns'
        await self.press('enter')
        yield 'pattern editor'
        for _ in range(8):
            await self.press('down')
            yield 'pattern row'
        await self.press('tab', 'tab', 't')
        yield 'tracks'
        await self.press('tab', 'c')
        yield 'chains'
        await self.press('enter')
        yield 'chain editor'
        await self.press('tab', 'tab', 'g')
        yield 'generators'
        await self.press('enter')
        yield 'arps'
        await self.press('enter')
        yield 'arp'
        await self.press('tab', 'tab', 'tab', 'z')
        yield 'scales'
        await self.press('tab', 'a')
        yield 'arrange'
        await self.press('right')
        yield 'arrange cell'
        await self.press('enter')
        yield 'clip'
        await self.press('tab', 'left', 'enter')
        yield 'scene'

    async def test_every_key_in_the_table_is_on_screen(self):
        async for where in self.visit():
            text = self.text()
            for item in self.app.screen.key_table():
                with self.subTest(where=where, label=item.shown_label()):
                    self.assertIn(f'« {item.shown_label()} »', text)

    async def test_a_key_that_is_not_shown_does_nothing(self):
        await self.press('p')
        before = self.text()
        await self.press('w', 'j', 'f5', 'escape')
        self.assertEqual(self.text(), before)

    async def test_no_key_table_is_empty(self):
        async for where in self.visit():
            with self.subTest(where=where):
                self.assertTrue(self.app.screen.keys())


class TestEveryKeyIsShownOnAUsualConsole(TestEveryKeyIsShown):
    SIZE = (80, 24)

    async def test_a_long_line_cannot_push_the_keys_off_the_screen(self):
        self.document.set_cell_setting(0, 'lead', CellSetting.LOOP, True)
        self.document.set_cell_setting(0, 'lead', CellSetting.GRAB_TRACK, 'drums')
        self.document.set_cell_setting(0, 'lead', CellSetting.DIRECTION, Direction.EITHERWAY)
        self.document.set_cell_setting(0, 'drums', CellSetting.LOOP, None)
        self.document.set_cell_setting(0, 'drums', CellSetting.PATTERN, 'other')
        await self.press('a', 'right', 'enter')
        self.assertIn('« Tab »', self.text())
        self.assertEqual(self.text().count('\n'), 23)


class TestSongPage(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        # Title and Author come first, so these start on Tempo.
        await self.press('s', 'down', 'down')

    async def test_title_and_author_come_first_and_start_blank(self):
        labels = [field.label for field in self.app.screen.fields()]
        self.assertEqual(labels[:3], ['Title', 'Author', 'Tempo'])
        self.assertEqual(self.document.song().get_title(), NO_TEXT)
        await self.press('up', 'up', 'enter')
        await self.type('Rain on the Bridge')
        await self.press('enter', 'down', 'enter')
        await self.type('Someone')
        await self.press('enter')
        song = self.document.song()
        self.assertEqual((song.get_title(), song.get_author()), ('Rain on the Bridge', 'Someone'))
        self.document.save('song.yml')
        with open('song.yml') as file:
            self.assertTrue(file.read().startswith(f'version: {VERSION}\ntitle: Rain on the Bridge\nauthor: Someone\ntempo: 120\n'))
        self.assertEqual(Document.load('song.yml').song().get_title(), 'Rain on the Bridge')
        await self.press('backspace')
        self.assertEqual(self.document.song().get_author(), NO_TEXT)

    async def test_plus_and_minus_change_the_tempo(self):
        await self.press('+', '+', '-')
        self.assertEqual(self.document.song().get_tempo(), 121)
        self.assertTrue(self.document.dirty)

    async def test_typing_a_tempo(self):
        await self.press('enter', 'backspace', 'backspace', 'backspace')
        await self.type('90')
        await self.press('enter')
        self.assertEqual(self.document.song().get_tempo(), 90)

    async def test_nonsense_is_refused(self):
        await self.press('enter', 'backspace', 'backspace', 'backspace')
        await self.type('xx')
        await self.press('enter')
        self.assertEqual(self.document.song().get_tempo(), 120)
        self.assertIn('not a whole number', self.text())

    async def test_step_size_offers_only_the_allowed_values(self):
        await self.select_field('Step size')
        await self.press('+')
        self.assertEqual(self.document.song().get_step_size(), Fraction(1, 8))
        await self.press('enter')
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options, STEP_SIZE_CHOICES)

    async def test_seed_can_be_set(self):
        await self.press('down', 'down', '+')
        self.assertEqual(self.document.song().get_seed(), 2)

    async def test_scale_can_be_none(self):
        await self.press('down', 'backspace')
        self.assertIsNone(self.document.song().get_scale_name())

    async def test_save_as_then_save(self):
        await self.press('w')
        self.assertIsInstance(self.app.screen, PromptDialog)
        self.app.screen.value = ''
        await self.type('tune')
        await self.press('enter')
        self.assertTrue(os.path.exists('tune.yml'))
        self.assertEqual(self.document.path, 'tune.yml')
        self.assertFalse(self.document.dirty)
        await self.press('+')
        self.assertTrue(self.document.dirty)
        with open('tune.yml') as file:
            before = file.read()
        await self.press('s')
        with open('tune.yml') as file:
            self.assertNotEqual(file.read(), before)
        self.assertFalse(self.document.dirty)

    async def test_save_as_asks_before_replacing_another_file(self):
        with open('taken.yml', 'w') as file:
            file.write('keep')
        await self.press('w')
        self.app.screen.value = 'taken.yml'
        await self.press('enter')
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press('n')
        with open('taken.yml') as file:
            self.assertEqual(file.read(), 'keep')

    async def test_new_asks_if_there_are_unsaved_changes(self):
        self.document.changed()
        await self.press('n')
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press('y')
        self.assertEqual(self.app.document.song().get_pattern_names(), [])
        self.assertEqual(self.app.document.song().get_scale_name(), DEFAULT_SCALE)

    async def test_render_asks_before_replacing_earlier_output(self):
        await self.press('r')
        self.assertTrue(os.path.exists('output/untitled/untitled.als'))
        await self.press('r')
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        self.assertIn('Replace', self.text())
        await self.press('tab', 'm')
        self.assertTrue(os.listdir('output/untitled'))

    async def test_changes_do_not_render_or_save_by_themselves(self):
        await self.press('+', '+')
        self.assertEqual(os.listdir(self.folder), [])

    async def test_every_clip_looping_is_a_popup_at_render(self):
        self.document.set_cell_setting(0, 'lead', CellSetting.LOOP, True)
        self.document.changed()
        await self.press('r')
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn('every clip is set to loop', self.text().replace('\n', ' ').replace('┃', ' ').replace('  ', ' '))
        self.assertFalse(os.path.exists('output/untitled/untitled.als'))


class TestSongPageEdges(UITest):

    async def test_saving_a_new_song_asks_for_a_name_and_an_empty_one_does_nothing(self):
        await self.press('s', 's')
        self.assertIsInstance(self.app.screen, PromptDialog)
        self.app.screen.value = '  '
        await self.press('enter')
        self.assertIsNone(self.document.path)

    async def test_a_save_that_fails_is_explained(self):
        os.mkdir('taken.yml')
        await self.press('s', 'w')
        self.app.screen.value = 'taken.yml'
        await self.press('enter')
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press('y')
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn("Can't save", self.text())

    async def test_new_and_load_ask_first_with_unsaved_changes(self):
        self.document.changed()
        await self.press('s', 'n')
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press('tab', 'l')
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press('y')
        self.assertNotIsInstance(self.app.screen, SongPage)

    async def test_choosing_a_scale_needs_one_first(self):
        self.document.set_scale_name(None)
        for name in self.document.song().get_scale_names():
            self.document.delete_scale(name)
        await self.press('s', 'down', 'down', 'down', 'enter')
        self.assertIn('Add a scale first', self.text())


class TestDescriptionPage(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press('s', 'd')

    async def test_it_opens_from_the_song_page_for_reading(self):
        self.assertIsInstance(self.app.screen, DescriptionPage)
        self.assertIn('No description yet', self.text())
        await self.press('tab')
        self.assertIsInstance(self.app.screen, SongPage)
        self.assertIn('not yet, D to write', self.text())

    async def test_typing_new_lines_and_erasing(self):
        await self.press('e')
        await self.type('Hi there')
        await self.press('enter')
        await self.type('ok')
        self.assertEqual(self.document.song().get_description(), 'Hi there\nok\n')
        await self.press('backspace', 'backspace', 'backspace')
        self.assertEqual(self.document.song().get_description(), 'Hi there\n')
        # Six steps left from the end of 'Hi there' is just after 'Hi'.
        await self.press(*['left'] * 6)
        await self.type('X')
        self.assertEqual(self.document.song().get_description(), 'HiX there\n')
        await self.press('tab')
        self.assertFalse(self.app.screen.editing)
        self.assertIn('HiX there', self.text())
        await self.press('tab')
        self.assertIn('1 line(s), D to read', self.text())

    async def test_h_is_text_while_editing_and_help_while_reading(self):
        await self.press('e', 'h')
        self.assertEqual(self.document.song().get_description(), 'h\n')
        await self.press('tab', 'h')
        self.assertIsInstance(self.app.screen, MessageDialog)

    async def test_erasing_at_the_start_of_a_line_joins_it_to_the_one_before(self):
        self.document.set_description('one\ntwo\n')
        await self.press('e', 'up', 'down')
        self.app.screen.column = 0
        await self.press('backspace')
        self.assertEqual(self.document.song().get_description(), 'onetwo\n')

    async def test_clearing_asks_first(self):
        self.document.set_description('one\n')
        await self.press('backspace')
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press('y')
        self.assertFalse(self.document.song().has_description())

    async def test_a_long_description_scrolls(self):
        self.document.set_description(''.join(f'line {n}\n' for n in range(100)))
        await self.press('down', 'down')
        self.assertNotIn('line 0\n', self.text().replace(' ', ''))
        self.assertIn('line 2', self.text())


class TestLoading(UITest):

    async def test_picks_a_file_and_opens_it(self):
        a_song().save('song one.yml')
        await self.press('s', 'l')
        rows = [row[0] for row in self.app.screen.rows()]
        self.assertIn('song one.yml', rows)
        self.app.screen.place = rows.index('song one.yml')
        await self.press('enter')
        self.assertIsInstance(self.app.screen, SongPage)
        self.assertEqual(self.app.document.path, 'song one.yml')

    async def test_a_bad_file_is_a_popup_and_keeps_the_song(self):
        with open('bad.yml', 'w') as file:
            file.write('tempo: [')
        before = self.app.document
        await self.press('s', 'l')
        rows = [row[0] for row in self.app.screen.rows()]
        self.app.screen.place = rows.index('bad.yml')
        await self.press('enter')
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIs(self.app.document, before)


class TestPlusRow(UITest):
    """Every list has a + at the bottom, where Enter does the same as pressing +."""

    async def test_tracks(self):
        await self.press('t', 'down', 'down')
        self.assertIsNone(self.app.screen.current())
        self.assertIn('«  +', self.text())
        self.assertNotIn('« Bksp »', self.text())
        await self.press('enter')
        self.assertIsInstance(self.app.screen, PromptDialog)
        await self.type('bass')
        await self.press('enter')
        self.assertEqual(self.document.song().get_track_names(), ['lead', 'drums', 'bass'])

    async def test_every_list_has_one(self):
        for keys, page in [
            (['p'], PatternsPage), (['t'], TracksPage), (['c'], ChainsPage), (['z'], ScalesPage),
        ]:
            await self.press(*keys)
            self.assertIsInstance(self.app.screen, page)
            self.assertEqual(self.app.screen.rows_with_plus()[-1][0], None, page)
            await self.press('tab')

    async def test_up_from_the_top_goes_to_it(self):
        await self.press('p', 'up')
        self.assertIsNone(self.app.screen.current())

    async def test_an_empty_list_starts_on_it(self):
        self.empty_the_arrangement()
        await self.press('t', 'enter')
        self.assertIsInstance(self.app.screen, PromptDialog)

    async def test_backspace_and_copy_do_nothing_on_it(self):
        await self.press('t', 'up', 'backspace', 'c', 'u', 'd')
        self.assertEqual(self.document.song().get_track_names(), ['lead', 'drums'])
        self.assertIsInstance(self.app.screen, TracksPage)

    async def test_lists_that_cannot_add_have_none(self):
        await self.press('g')
        self.assertEqual(len(self.app.screen.rows_with_plus()), 2)

    async def test_arrange_has_one_for_scenes(self):
        await self.press('a', 'down', 'down')
        self.assertTrue(self.app.screen.on_plus_row())
        self.assertNotIn('« Bksp »', self.text())
        await self.press('enter')
        self.assertEqual(len(self.document.song().get_scenes()), 3)
        self.assertEqual(self.app.screen.row, 2)
        self.assertEqual(self.document.song().get_scenes()[2].get_track_names(), [])

    async def test_arrange_with_no_scenes_starts_on_it(self):
        self.empty_the_arrangement()
        await self.press('a', 'enter')
        self.assertEqual(len(self.document.song().get_scenes()), 1)


class TestSettingArrows(UITest):

    async def test_left_and_right_do_the_same_as_minus_and_plus(self):
        await self.press('s', 'down', 'down', 'right', 'right', 'left')
        self.assertEqual(self.document.song().get_tempo(), 121)

    async def test_on_every_setting_with_a_value_to_step(self):
        await self.press('s', 'down', 'down', 'down', 'left')
        self.assertIsNone(self.document.song().get_scale_name())
        await self.press('right')
        self.assertEqual(self.document.song().get_scale_name(), 'C Major')
        await self.press('down', 'right')
        self.assertEqual(self.document.song().get_seed(), 2)
        await self.press('down', 'right')
        self.assertEqual(self.document.song().get_step_size(), Fraction(1, 8))
        await self.press('down', 'left')
        self.assertEqual(self.document.song().get_default_octave(), 2)
        await self.press('down', 'right')
        self.assertEqual(self.document.song().get_default_drum_octave(), 2)


class TestLookAndNewKeys(UITest):

    async def test_the_title_is_plain_text_and_the_address_is_on_the_main_screen(self):
        lines = self.text().splitlines()
        self.assertTrue(lines[0].startswith(' llamatron '))
        self.assertNotIn('home.laserllama.net', lines[0])
        self.assertNotIn('█', self.text())
        address = next(number for number, line in enumerate(lines) if 'home.laserllama.net' in line)
        last_page = next(number for number, line in enumerate(lines) if 'Help' in line and 'What the page' in line)
        self.assertEqual(address, last_page + 4)
        self.assertTrue(lines[address].rstrip().endswith('home.laserllama.net'))
        await self.press('p')
        self.assertNotIn('home.laserllama.net', self.text())

    async def test_new_songs_default_to_sixteenth_note_steps(self):
        self.assertEqual(new_song()['step_size'], '1/16')
        document = Document()
        document.add_pattern('p', 2)
        self.assertEqual(document.pattern_length('p'), Fraction(1, 8))

    async def go_to_row(self, name):
        await self.press('p', 'enter')
        if name == 'ratchet':
            await self.press('pagedown')
        names = [row for row, _ in self.app.screen.rows()]
        await self.press(*['down'] * names.index(name))

    def value(self, row):
        return self.document.step_value('tune', row, self.app.screen.step)

    async def test_enter_on_a_chord_cell_opens_a_picker(self):
        await self.go_to_row(Row.CHORD)
        await self.press('enter')
        self.assertIsInstance(self.app.screen, GridChoiceDialog)
        self.assertIn('M7', self.app.screen.options)
        self.app.screen.place = self.app.screen.options.index('m7')
        await self.press('enter')
        self.assertEqual(self.value('chord'), 'm7')
        await self.press('enter')
        self.assertEqual(self.app.screen.options[self.app.screen.place], 'm7')
        self.assertIn('Minor seventh', self.dialog_text())
        self.app.screen.place = self.app.screen.options.index('3')
        await self.press('enter')
        self.assertEqual(self.value('chord'), 3)
        render_song(self.document.song())

    def dialog_text(self):
        return str(self.app.screen.query_one('#dialog-view').render())

    async def test_the_chord_grid_shows_every_chord_at_once(self):
        await self.go_to_row(Row.CHORD)
        await self.press('enter')
        text = self.dialog_text()
        for word in ['(none)', 'TRIADS', 'SEVENTHS', 'NINTHS', '11THS, 13THS', 'SCALE', 'M', 'm6', '7sus4', 'madd9', 'm13', '13']:
            self.assertIn(word, text)
        self.assertLessEqual(len(text.splitlines()), 22)
        self.assertLessEqual(max(len(line) for line in text.splitlines()), 76)

    async def test_arrows_move_around_the_chord_grid(self):
        await self.go_to_row(Row.CHORD)
        await self.press('enter')
        dialog = self.app.screen

        def at():
            return dialog.options[dialog.place]
        self.assertEqual(at(), '(none)')
        await self.press('down')
        self.assertEqual(at(), 'M')
        await self.press('right')
        self.assertEqual(at(), 'dom7')
        await self.press('down')
        self.assertEqual(at(), 'M7')
        await self.press('right', 'right')
        self.assertEqual(at(), 'M11')
        await self.press('down', 'down', 'down', 'down', 'left')
        # Ninths has nothing that low, so left lands on its lowest chord.
        self.assertEqual(at(), 'madd9')
        await self.press('up', 'up', 'up', 'up', 'up')
        self.assertEqual(at(), '(none)')
        await self.press('tab')
        self.assertNotIsInstance(self.app.screen, GridChoiceDialog)

    async def test_the_detail_line_names_the_selected_chord(self):
        await self.go_to_row(Row.CHORD)
        await self.press('enter', 'down', 'right', 'down', 'down', 'down', 'down', 'down')
        self.assertIn('Half-diminished', self.dialog_text())

    async def test_typing_numbers_into_ratchet(self):
        await self.go_to_row(Row.RATCHET)
        await self.press('4')
        self.assertEqual(self.value('ratchet'), 4)
        await self.press('right', 'left', '1', '2')
        self.assertEqual(self.value('ratchet'), 12)

    async def test_too_big_a_number_starts_again(self):
        await self.go_to_row(Row.RATCHET)
        await self.press('1', '6', '3')
        self.assertEqual(self.value('ratchet'), 3)

    async def test_typing_velocity_with_several_digits(self):
        await self.go_to_row(Row.VELOCITY)
        await self.press('1', '0', '0')
        self.assertEqual(self.value('velocity'), 100)
        await self.press('right', 'left', '6', '4')
        self.assertEqual(self.value('velocity'), 64)
        await self.press('+')
        await self.press('9')
        self.assertEqual(self.value('velocity'), 9)

    async def test_zero_is_refused_where_it_is_out_of_range(self):
        await self.go_to_row(Row.VELOCITY)
        await self.press('5', 'right', 'left', '0')
        self.assertEqual(self.value('velocity'), 5)

    async def test_typing_probability(self):
        await self.go_to_row(Row.PROBABILITY)
        await self.press('0')
        self.assertEqual(self.value('probability'), 0)
        await self.press('1', '0', '0')
        self.assertEqual(self.value('probability'), 100)

    async def test_typing_does_not_move_the_cursor(self):
        await self.go_to_row(Row.VELOCITY)
        before = (self.app.screen.step, self.app.screen.row)
        await self.press('1', '0')
        self.assertEqual((self.app.screen.step, self.app.screen.row), before)

    async def test_a_scale_with_more_than_nine_notes_takes_two_digits(self):
        self.document.add_scale(CHROMATIC_SCALE, NoteName.C, scale_type_name(ScaleType.CHROMATIC))
        self.document.set_scale_name(CHROMATIC_SCALE)
        self.document.changed()
        await self.press('p', 'enter', '1', '2')
        self.assertEqual(self.value('degree'), 12)


class TestHelp(UITest):
    """Help has to work on every page, and to fit a console of the usual size."""

    SIZE = (80, 24)

    async def assert_help_fits(self, where):
        page = self.app.screen
        self.assertTrue(page.HELP, where)
        await self.press('h')
        self.assertIsInstance(self.app.screen, MessageDialog, where)
        text = self.text()
        with self.subTest(where=where):
            self.assertIn('Help', text)
            self.assertIn('┏', text)
            self.assertIn('┗', text)
            self.assertIn('« Enter »', text)
        await self.press('enter')
        self.assertIs(self.app.screen, page, where)

    async def test_every_page_has_help_that_fits(self):
        await self.assert_help_fits('main')
        for keys in [
            ['s'], ['d'], ['tab', 'l'], ['tab', 'tab', 'p'], ['enter'], ['tab', 'tab', 't'],
            ['tab', 'c'], ['enter'], ['tab', 'tab', 'g'], ['enter'], ['enter'],
            ['tab', 'tab', 'down', 'enter'], ['enter'],
            ['tab', 'tab', 'tab', 'z'], ['tab', 'a'], ['right', 'enter'],
            ['tab', 'left', 'enter'],
        ]:
            await self.press(*keys)
            await self.assert_help_fits(type(self.app.screen).__name__)

    async def test_h_is_the_same_as_upper_case_and_is_shown(self):
        await self.press('p')
        self.assertIn('« H »', self.text())
        await self.press('H')
        self.assertIsInstance(self.app.screen, MessageDialog)

    async def test_h_is_text_when_typing(self):
        await self.press('t', '+', 'h')
        self.assertEqual(self.app.screen.value, 'h')

    async def test_the_pattern_editor_fits_too(self):
        await self.press('p', 'enter')
        text = self.text()
        self.assertIn('│ Glide', text)
        self.assertIn('Step 1:', text)
        self.assertIn('« Tab »', text)


class TestQuitting(UITest):

    async def test_quitting_with_unsaved_changes_asks_and_then_quits(self):
        self.document.changed()
        with mock.patch.object(self.app, 'exit') as leave:
            await self.press('q')
            self.assertIsInstance(self.app.screen, ConfirmDialog)
            await self.press('n')
            leave.assert_not_called()
            self.assertIsInstance(self.app.screen, MainPage)
            await self.press('q', 'y')
            leave.assert_called_once()


class TestDesign(unittest.TestCase):

    def test_there_are_no_tooltips(self):
        for path in ['app', 'arrange', 'base', 'lists', 'pages', 'pattern_editor']:
            with open(f'src/llamatron/tui/{path}.py', encoding='utf-8') as file:
                self.assertNotIn('tooltip', file.read())

    def test_the_command_palette_is_off(self):
        self.assertFalse(LlamatronApp.ENABLE_COMMAND_PALETTE)
        self.assertTrue(issubclass(LlamatronApp, App))

    def test_the_program_uses_terminal_colors_only(self):
        for path in ['arrange', 'base', 'lists', 'pages', 'pattern_editor']:
            with open(f'src/llamatron/tui/{path}.py', encoding='utf-8') as file:
                text = file.read()
            for color in ['red', 'green', 'blue', 'yellow', 'cyan', 'magenta', 'white', 'black', '#']:
                self.assertNotIn(f"style='{color}", text)

    def test_no_screen_replaces_a_method_that_textual_needs(self):
        # Naming a method remove or render here stops screens from closing or drawing.
        ours = {'compose', 'on_mount', 'on_key', 'on_resize', 'on_screen_resume'}
        pages = [
            Page, ListPage, FieldPage, MainPage, SongPage, FilePage, PatternsPage, TracksPage, ChainsPage,
            ChainEditor, GeneratorsPage, ArpsPage, ArpEditor, AutoRatchetsPage, AutoRatchetEditor,
            ScalesPage, ArrangePage, ScenePage,
            ClipPage, PatternEditor, Dialog, MessageDialog, ConfirmDialog, PromptDialog, ChoiceDialog,
        ]
        for page in pages:
            for name, value in vars(page).items():
                if callable(value) and not name.startswith('_') and name not in ours:
                    with self.subTest(page=page.__name__, name=name):
                        self.assertFalse(hasattr(Screen, name))
