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

import os
import string
import tempfile
import unittest
from fractions import Fraction

from textual import events
from textual.app import App
from textual.screen import Screen

from rendering import render_data
from llamatron.composition.named_scale import scale_type_name
from llamatron.composition.song import Song
from llamatron.note import NoteName
from llamatron.scale import ScaleType
from llamatron.tui.app import LlamatronApp
from llamatron.tui.arrange import RESET_LABEL, ArrangePage, ClipPage, ScenePage
from llamatron.tui.base import ChoiceDialog, ConfirmDialog, Dialog, GridChoiceDialog, MessageDialog, Page, PromptDialog
from llamatron.composition.file_format import (
    REGISTER_ADD_ROWS, REGISTER_NAMES, REGISTER_NOTE_ROWS, REGISTER_VELOCITY_ROWS, STEP_SIZE_CHOICES, RegisterName, Row,
    SceneSetting, Section,
)
from llamatron.composition.file_format import NAMED_GENERATORS
from llamatron.composition.defaults import DEFAULT_REGISTER_MAXIMUM, DEFAULT_REGISTER_MINIMUM
from llamatron.composition.register import MSG_OUT_OF_ORDER
from llamatron.tui.registers_page import FIELD_LABEL, NUMBER_FIELDS, WRAP_FIELD, RegistersPage
from llamatron.composition.limits import MAX_REGISTER_VALUE
from llamatron.tui.document import Document, new_song
from llamatron.version import VERSION
from llamatron.tui.lists import FieldPage, ListPage
from llamatron.tui.pages import (
    ArpEditor, ArpsPage, AutoRatchetEditor, AutoRatchetsPage, ChainEditor, ChainsPage, DescriptionPage, FilePage,
    GeneratorsPage, MainPage, OffsetsEditor, PatternsPage, ScalesPage, SongPage, TrackEditor, TracksPage,
)
from llamatron.tui.pattern_editor import (
    ADVANCED, CC, DESCRIBE_TIED, NORMAL, NORMAL_ROWS, REGISTER_CHANGES, REGISTERS, ROW_LABELS, ROW_SET_HEADERS,
    ROW_SET_NAMES, ROW_SETS, TOGGLE_ON, PatternEditor,
)

# How the pattern editor shows a row's label at the left of the grid, a key in the key list,
# and a step whose quiet row isn't set.
ROW_SHOWN = '│ {label}'
KEY_SHOWN = '« {label} »'
QUIET_VALUE = '.'
# Names the tests give to the scales and chains they add.
SMALL_SCALE = 'small'
CHROMATIC_SCALE = 'all'
EMPTY_CHAIN = 'x'


def fixed_text(template):
    """Return the longest piece of a message template that isn't filled in, to look for on screen."""
    pieces = [literal for literal, _, _, _ in string.Formatter().parse(template)]
    return max(pieces, key=len)


# What shows when a register's settings would be out of order.
OUT_OF_ORDER_START = fixed_text(MSG_OUT_OF_ORDER)


def a_song(path=None):
    data = new_song()
    data['auto_ratchets'] = {'rolls': {'counts': [1, 4]}}
    data['patterns'] = {
        'tune': {
            'steps': 4, 'step_size': '1/8', 'degree': [1, 3, None, None], 'gate': ['1/4', '1/4', '1/8', None],
            'octave': [3, 3, None, None],
        },
        'beat': {'steps': 2, 'step_size': '1/8', 'drum': True, 'degree': ['C', None], 'gate': ['1/16', None], 'octave': [1, None]},
        'other': {'steps': 1, 'step_size': '1/2', 'degree': [5]},
    }
    data['tracks'] = {'lead': {}, 'drums': {}}
    data['arps'] = {'up': {'step': '1/8', 'order': 'up'}}
    data['chains'] = {'named': [{'arp': 'up'}, {'auto_ratchet': 'rolls'}], 'empty': []}
    data['scenes'] = [
        {'name': 'one', 'tracks': {'lead': {'pattern': 'tune'}, 'drums': {'pattern': 'beat', 'loop': True}}},
        {'name': 'two', 'tracks': {}},
    ]
    return Document(data, path)


def _key_event(name):
    """Return the event a terminal sends for a key."""
    named = {
        'space': ' ', '+': '+', '-': '-', '*': '*', '/': '/',
        'enter': '\r', 'backspace': '\x7f', 'escape': '\x1b', 'up': None, 'down': None,
        'left': None, 'right': None, 'tab': '\t', 'f5': None,
    }
    words = {'+': 'plus', '-': 'minus', '*': 'asterisk', '/': 'slash'}
    if name in named:
        return events.Key(words.get(name, name), named[name])
    return events.Key(name, name)


def screen_text(app):
    """Return what's on screen, with «» around anything in reverse video."""
    lines = []
    for strip in app.screen._compositor.render_strips():
        line, reverse = '', False
        for segment in strip:
            now = bool(segment.style and segment.style.reverse)
            if now != reverse:
                line += '«' if now else '»'
                reverse = now
            line += segment.text
        lines.append(line + ('»' if reverse else ''))
    return '\n'.join(lines)


class UITest(unittest.IsolatedAsyncioTestCase):
    """Runs the real program with no terminal, pressing keys."""

    SIZE = (100, 40)

    async def asyncSetUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(temporary.name)
        self.folder = temporary.name
        self.document = a_song()
        self.app = LlamatronApp(self.document)
        self.running = self.app.run_test(size=self.SIZE)
        self.pilot = await self.running.__aenter__()
        self.addAsyncCleanup(self.running.__aexit__, None, None, None)
        await self.pilot.pause()

    async def press(self, *keys):
        # Pressing keys through the terminal driver takes a tenth of a second each, so these go
        # straight to the screen. TestRealKeys checks the same keys through the driver.
        for name in keys:
            self.app.screen.on_key(_key_event(name))
            await self.pilot.pause()

    async def type(self, text):
        await self.press(*[{' ': 'space'}.get(letter, letter) for letter in text])

    def empty_the_arrangement(self):
        """Delete every scene and then every track, through the document, as a page would."""
        for index in reversed(range(len(self.document.song().get_scenes()))):
            self.document.delete_scene(index)
        for name in self.document.song().get_track_names():
            self.document.delete_track(name)

    def delete_every_generator(self):
        """Delete every arp and AutoRatchet, which the chains must have stopped using first."""
        song = self.document.song()
        for kind, section in NAMED_GENERATORS.items():
            for name in song.get_generator_names(kind):
                self.document.delete_generator(section, name)

    def text(self):
        return screen_text(self.app)

    async def select_field(self, label):
        """Move a settings page's cursor to the field with this label, wherever the page puts it."""
        labels = [field.label for field in self.app.screen.fields()]
        offset = labels.index(label) - self.app.screen.place
        await self.press(*(['down'] * offset if offset > 0 else ['up'] * -offset))


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
        self.assertEqual(self.document.step_value('tune', 'degree', 1), 5)
        await self.pilot.press('down', 'plus')
        self.assertEqual(self.document.step_value('tune', 'gate', 1), '1/2')
        await self.pilot.press('asterisk')
        self.assertEqual(self.document.step_value('tune', 'gate', 1), 1)
        await self.pilot.press('slash')
        self.assertEqual(self.document.step_value('tune', 'gate', 1), '1/2')
        await self.pilot.press('minus')
        self.assertEqual(self.document.step_value('tune', 'gate', 1), '1/4')
        await self.pilot.press('down', 'space')
        self.assertEqual(self.document.step_value('tune', 'dot', 1), 'd')
        await self.pilot.press('down', 'space')
        self.assertEqual(self.document.step_value('tune', 'accidental', 1), '#')
        await self.pilot.press('backspace')
        self.assertIsNone(self.document.step_value('tune', 'accidental', 1))
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
        self.document.data['scenes'][0]['tracks']['lead'].update(loop=True, grab_track='drums', direction='eitherway')
        self.document.data['scenes'][0]['tracks']['drums'].pop('loop')
        self.document.data['scenes'][0]['tracks']['drums']['pattern'] = 'other'
        self.document.changed()
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
        self.assertNotIn('title', self.document.data)
        await self.press('up', 'up', 'enter')
        await self.type('Rain on the Bridge')
        await self.press('enter', 'down', 'enter')
        await self.type('Someone')
        await self.press('enter')
        self.assertEqual((self.document.data['title'], self.document.data['author']), ('Rain on the Bridge', 'Someone'))
        self.document.save('song.yml')
        with open('song.yml') as file:
            self.assertTrue(file.read().startswith(f'version: {VERSION}\ntitle: Rain on the Bridge\nauthor: Someone\ntempo: 120\n'))
        self.assertEqual(Document.load('song.yml').data['title'], 'Rain on the Bridge')
        await self.press('backspace')
        self.assertNotIn('author', self.document.data)

    async def test_plus_and_minus_change_the_tempo(self):
        await self.press('+', '+', '-')
        self.assertEqual(self.document.data['tempo'], 121)
        self.assertTrue(self.document.dirty)

    async def test_typing_a_tempo(self):
        await self.press('enter', 'backspace', 'backspace', 'backspace')
        await self.type('90')
        await self.press('enter')
        self.assertEqual(self.document.data['tempo'], 90)

    async def test_nonsense_is_refused(self):
        await self.press('enter', 'backspace', 'backspace', 'backspace')
        await self.type('xx')
        await self.press('enter')
        self.assertEqual(self.document.data['tempo'], 120)
        self.assertIn('not a whole number', self.text())

    async def test_step_size_offers_only_the_allowed_values(self):
        await self.select_field('Step size')
        await self.press('+')
        self.assertEqual(self.document.data['step_size'], '1/8')
        await self.press('enter')
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options, STEP_SIZE_CHOICES)

    async def test_seed_can_be_set(self):
        await self.press('down', 'down', '+')
        self.assertEqual(self.document.data['seed'], 2)

    async def test_scale_can_be_none(self):
        await self.press('down', 'backspace')
        self.assertIsNone(self.document.data['scale'])

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
        self.assertEqual(self.app.document.data['patterns'], {})
        self.assertEqual(self.app.document.data['scale'], 'C Major')

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
        self.document.data['scenes'][0]['tracks']['lead']['loop'] = True
        self.document.changed()
        await self.press('r')
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn('every clip is set to loop', self.text().replace('\n', ' ').replace('┃', ' ').replace('  ', ' '))
        self.assertFalse(os.path.exists('output/untitled/untitled.als'))


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
        self.assertEqual(self.document.data['description'], 'Hi there\nok\n')
        await self.press('backspace', 'backspace', 'backspace')
        self.assertEqual(self.document.data['description'], 'Hi there\n')
        # Six steps left from the end of 'Hi there' is just after 'Hi'.
        await self.press(*['left'] * 6)
        await self.type('X')
        self.assertEqual(self.document.data['description'], 'HiX there\n')
        await self.press('tab')
        self.assertFalse(self.app.screen.editing)
        self.assertIn('HiX there', self.text())
        await self.press('tab')
        self.assertIn('1 line(s), D to read', self.text())

    async def test_h_is_text_while_editing_and_help_while_reading(self):
        await self.press('e', 'h')
        self.assertEqual(self.document.data['description'], 'h\n')
        await self.press('tab', 'h')
        self.assertIsInstance(self.app.screen, MessageDialog)

    async def test_erasing_at_the_start_of_a_line_joins_it_to_the_one_before(self):
        self.document.set_description('one\ntwo\n')
        await self.press('e', 'up', 'down')
        self.app.screen.column = 0
        await self.press('backspace')
        self.assertEqual(self.document.data['description'], 'onetwo\n')

    async def test_clearing_asks_first(self):
        self.document.set_description('one\n')
        await self.press('backspace')
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press('y')
        self.assertNotIn('description', self.document.data)

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


class TestPatternList(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press('p')

    def names(self):
        return list(self.document.data['patterns'])

    async def test_plus_adds_one_and_opens_it(self):
        await self.press('+')
        self.app.screen.value = 'new'
        await self.press('enter')
        self.assertIn('new', self.names())
        self.assertIsInstance(self.app.screen, PatternEditor)
        self.assertEqual(self.document.data['patterns']['new']['steps'], 16)

    async def test_u_and_d_move_the_selected_pattern(self):
        await self.press('d')
        self.assertEqual(self.names(), ['beat', 'tune', 'other'])
        self.assertEqual(self.app.screen.current(), 'tune')
        await self.press('u')
        self.assertEqual(self.names(), ['tune', 'beat', 'other'])

    async def test_s_sorts(self):
        await self.press('s')
        self.assertEqual(self.names(), ['beat', 'other', 'tune'])

    async def test_c_copies(self):
        await self.press('c')
        self.assertIn('tune copy', self.names())

    async def test_deleting_something_used_is_refused_and_says_what_uses_it(self):
        await self.press('backspace')
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn('scene 1 (one), track lead', self.text())
        await self.press('enter')
        self.assertIn('tune', self.names())

    async def test_a_refusal_lists_five_and_then_dots(self):
        for number in range(7):
            self.document.data['scenes'].append({'name': f'x{number}', 'tracks': {'lead': {'pattern': 'other'}}})
        self.document.changed()
        await self.press('down', 'down', 'backspace')
        text = self.text()
        self.assertEqual(text.count('(x'), 5)
        self.assertIn('... and 2 more', text)

    async def test_deleting_something_unused_confirms_first(self):
        await self.press('down', 'down', 'backspace')
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press('n')
        self.assertIn('other', self.names())
        await self.press('backspace', 'y')
        self.assertNotIn('other', self.names())

    async def test_a_duplicate_name_is_refused(self):
        await self.press('n')
        self.app.screen.value = 'beat'
        await self.press('enter')
        self.assertIn('tune', self.names())
        self.assertIn('already in use', self.text())

    async def test_renaming_updates_clips(self):
        await self.press('n')
        self.app.screen.value = 'melody'
        await self.press('enter')
        self.assertEqual(self.document.cell(0, 'lead')['pattern'], 'melody')


class TestPatternEditor(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press('p', 'enter')
        self.editor = self.app.screen

    def value(self, row, step=None):
        return self.document.step_value('tune', row, self.editor.step if step is None else step)

    async def go_to_row(self, name):
        names = [row for row, _ in self.editor.rows()]
        for _ in range(names.index(name) - self.editor.row):
            await self.press('down')

    async def test_grid_size_comes_from_the_step_count_and_typing_never_grows_it(self):
        self.assertEqual(self.text().count('│ Degree'), 1)
        await self.press('right', 'right', 'right')
        await self.press('5', '5', '5')
        self.assertEqual(self.document.data['patterns']['tune']['steps'], 4)
        self.assertEqual(len(self.document.data['patterns']['tune']['degree']), 4)

    async def test_typing_does_not_move_the_cursor(self):
        await self.press('right', '5')
        self.assertEqual((self.editor.step, self.editor.row), (1, 0))

    async def test_arrows_move_between_steps_and_rows(self):
        await self.press('right')
        self.assertEqual(self.editor.step, 1)
        await self.press('down')
        self.assertEqual(self.editor.row_name(), 'gate')
        await self.press('down')
        self.assertEqual(self.editor.row_name(), 'dot')
        await self.press('up', 'left')
        self.assertEqual((self.editor.row_name(), self.editor.step), ('gate', 0))

    async def test_the_rows_are_all_there_in_order(self):
        self.assertEqual([name for name, _ in self.editor.rows()], NORMAL_ROWS)

    async def test_a_new_note_gets_the_default_octave_and_a_gate_of_one_step(self):
        self.document.set_default_octave(4)
        await self.press('right', 'right', 'right', '5')
        self.assertEqual(self.value('degree'), 5)
        self.assertIsNone(self.value('gate'))
        self.assertEqual(self.value('octave'), 4)
        self.assertIn('gate 1/8', self.text())

    async def test_a_new_note_keeps_a_gate_it_already_has(self):
        await self.press('right', 'right', '5')
        self.assertEqual(self.value('gate'), '1/8')

    async def test_a_degree_must_fit_the_scale(self):
        self.document.add_scale(SMALL_SCALE, NoteName.C, scale_type_name(ScaleType.MAJOR_PENTATONIC))
        self.document.set_scale_name(SMALL_SCALE)
        self.document.data['scenes'][0].pop('scale', None)
        self.document.changed()
        await self.press('6')
        self.assertEqual(self.value('degree'), 1)
        await self.press('5')
        self.assertEqual(self.value('degree'), 5)
        await self.press('+')
        self.assertEqual(self.value('degree'), 5)

    async def test_backspace_empties_a_step_which_is_a_rest(self):
        await self.press('backspace')
        self.assertIsNone(self.value('degree'))
        self.assertIsNone(self.value('gate'))
        self.assertIsNone(self.value('octave'))
        self.assertIn('Step 1: empty', self.text())

    async def test_backspace_on_an_empty_step_does_nothing(self):
        await self.press('backspace', 'backspace', 'backspace')
        self.assertIn('Step 1: empty', self.text())

    async def test_an_empty_step_has_no_gate_to_change(self):
        await self.press('right', 'right', 'right')
        self.assertIn('Step 4: empty', self.text())
        await self.press('down', '+')
        self.assertIsNone(self.value('gate'))

    async def test_plus_and_minus_step_through_plain_lengths(self):
        await self.go_to_row('gate')
        await self.press('+')
        self.assertEqual(self.value('gate'), '1/2')
        await self.press('-', '-')
        self.assertEqual(self.value('gate'), '1/8')

    async def test_a_gate_cannot_go_below_the_shortest_length(self):
        await self.go_to_row('gate')
        for _ in range(8):
            await self.press('-')
        self.assertEqual(self.value('gate'), '1/64')

    async def test_star_and_slash_double_and_halve(self):
        await self.go_to_row('gate')
        await self.press('*')
        self.assertEqual(self.value('gate'), '1/2')
        await self.press('/', '/')
        self.assertEqual(self.value('gate'), '1/8')

    async def test_backspace_on_a_gate_makes_it_one_step(self):
        await self.go_to_row('gate')
        await self.press('backspace')
        self.assertIsNone(self.value('gate'))

    async def test_enter_types_a_gate_as_a_whole_number_or_a_fraction(self):
        await self.go_to_row('gate')
        await self.press('enter')
        self.app.screen.value = '5/16'
        await self.press('enter')
        self.assertEqual(self.value('gate'), '5/16')
        for typed in ['0.25', '0', '9']:
            await self.press('enter')
            self.app.screen.value = typed
            await self.press('enter')
            with self.subTest(typed=typed):
                self.assertEqual(self.value('gate'), '5/16')

    async def test_the_dot_row_makes_a_gate_dotted_or_a_triplet(self):
        await self.go_to_row('dot')
        await self.press('+')
        self.assertEqual(self.value('dot'), 'd')
        self.assertIn('gate 1/4 dotted', self.text())
        await self.press('+')
        self.assertEqual(self.value('dot'), 't')
        await self.press('backspace')
        self.assertIsNone(self.value('dot'))

    async def test_e_sets_the_pattern_step_size_and_blank_uses_the_song(self):
        await self.press('e')
        self.app.screen.value = '1/8'
        await self.press('enter')
        self.assertEqual(self.document.data['patterns']['tune']['step_size'], '1/8')
        self.assertIn('Step size 1/8', self.text())
        await self.press('e')
        self.app.screen.value = ''
        await self.press('enter')
        self.assertNotIn('step_size', self.document.data['patterns']['tune'])
        self.assertIn("Step size 1/16 (the song's)", self.text())

    async def test_space_and_plus_and_minus_cycle_sharp_and_flat(self):
        await self.go_to_row('accidental')
        await self.press('space')
        self.assertEqual(self.value('accidental'), '#')
        await self.press('+')
        self.assertEqual(self.value('accidental'), 'b')
        await self.press('space')
        self.assertIsNone(self.value('accidental'))
        await self.press('-')
        self.assertEqual(self.value('accidental'), 'b')

    async def test_octave_uses_whatever_is_typed(self):
        await self.go_to_row('octave')
        await self.press('7')
        self.assertEqual(self.value('octave'), 7)
        await self.press('+', '+', '+')
        self.assertEqual(self.value('octave'), 8)
        for _ in range(12):
            await self.press('-')
        self.assertEqual(self.value('octave'), -2)

    async def test_chord_cycles_through_the_symbols(self):
        await self.go_to_row('chord')
        seen = []
        for _ in range(4):
            await self.press('+')
            seen.append(self.value('chord'))
        self.assertEqual(seen, ['M', 'm', 'dim', 'aug'])
        await self.press('-', '-', '-', '-', '-')
        self.assertEqual(self.value('chord'), 13)
        await self.press('-')
        self.assertEqual(self.value('chord'), 11)

    async def test_velocity_probability_and_ratchet(self):
        await self.go_to_row('velocity')
        await self.press('-')
        self.assertEqual(self.value('velocity'), 126)
        await self.press('enter')
        self.app.screen.value = '60'
        await self.press('enter')
        self.assertEqual(self.value('velocity'), 60)
        await self.press('down', '-')
        self.assertEqual(self.value('probability'), 99)
        await self.press('pagedown')
        await self.go_to_row('ratchet')
        await self.press('+')
        self.assertEqual(self.value('ratchet'), 2)

    async def test_a_typed_value_out_of_range_is_refused(self):
        await self.go_to_row('velocity')
        await self.press('enter')
        self.app.screen.value = '500'
        await self.press('enter')
        self.assertIsNone(self.value('velocity'))
        self.assertIn('from 1 to 127', self.text())

    async def test_glide_toggles_with_space_and_shows_a_star(self):
        await self.go_to_row('glide')
        self.assertEqual(self.editor.cell_text('glide', 0), ' ')
        await self.press('space')
        self.assertIs(self.value('glide'), True)
        self.assertEqual(self.editor.cell_text('glide', 0), '*')
        await self.press('space')
        self.assertIs(self.value('glide'), False)
        self.assertEqual(self.editor.cell_text('glide', 0), ' ')

    async def test_an_empty_step_has_nothing_to_change_but_cc_values(self):
        await self.press('right', 'right')
        await self.go_to_row('velocity')
        labels = [item.shown_label() for item in self.editor.keys()]
        self.assertNotIn('Enter', labels)
        self.assertNotIn('+', labels)

    async def test_the_result_builds_and_saves(self):
        await self.press('5')
        await self.go_to_row('glide')
        await self.press('space')
        render_data(self.document.data)
        self.document.save('x.yml')
        Document.load('x.yml')

    async def test_shortening_asks_only_if_it_loses_something(self):
        await self.press('r')
        self.app.screen.value = '1'
        await self.press('enter')
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press('n')
        self.assertEqual(self.document.data['patterns']['tune']['steps'], 4)
        await self.press('r')
        self.app.screen.value = '9'
        await self.press('enter')
        self.assertEqual(self.document.data['patterns']['tune']['steps'], 9)
        await self.press('r')
        self.app.screen.value = '5'
        await self.press('enter')
        self.assertEqual(self.document.data['patterns']['tune']['steps'], 5)

    async def test_a_pattern_keeps_at_least_one_step(self):
        await self.press('r')
        self.app.screen.value = '0'
        await self.press('enter')
        self.assertEqual(self.document.data['patterns']['tune']['steps'], 4)
        self.assertIn('from 1 to 4096', self.text())
        await self.press('r')
        self.app.screen.value = '1'
        await self.press('enter', 'y', 'x')
        self.assertEqual(self.document.data['patterns']['tune']['steps'], 1)

    async def test_insert_and_remove_step(self):
        await self.press('right', 'i')
        self.assertEqual(self.document.data['patterns']['tune']['degree'], [1, None, 3, None, None])
        await self.press('x')
        self.assertEqual(self.document.data['patterns']['tune']['degree'], [1, 3, None, None])

    async def test_long_patterns_wrap_and_stay_on_screen(self):
        await self.press('r')
        self.app.screen.value = '200'
        await self.press('enter')
        await self.press(*['right'] * 100)
        self.assertEqual(self.editor.step, 100)
        self.assertIn('101', self.text())

    async def test_the_header_shows_the_time(self):
        self.assertIn('0:01', self.text())


class TestDrumPatterns(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press('p', 'down', 'enter')
        self.editor = self.app.screen

    def value(self, row):
        return self.document.step_value('beat', row, self.editor.step)

    async def test_takes_letters_in_upper_or_lower_case(self):
        await self.press('right', 'f')
        self.assertEqual(self.value('degree'), 'F')
        await self.press('G')
        self.assertEqual(self.value('degree'), 'G')

    async def test_a_new_hit_gets_the_drum_octave(self):
        self.document.set_default_drum_octave(2)
        await self.press('i', 'c')
        self.assertEqual(self.value('octave'), 2)

    async def test_has_no_chord_row(self):
        self.assertNotIn('chord', [name for name, _ in self.editor.rows()])
        self.assertIn('│ Note', self.text())

    async def test_numbers_do_nothing(self):
        await self.press('5')
        self.assertEqual(self.value('degree'), 'C')

    async def test_the_toggle_asks_before_clearing_notes(self):
        await self.press('t')
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press('n')
        self.assertTrue(self.document.data['patterns']['beat']['drum'])
        await self.press('t', 'y')
        self.assertNotIn('drum', self.document.data['patterns']['beat'])
        self.assertFalse(self.document.has_notes('beat'))

    async def test_it_builds(self):
        await self.press('right', 'f')
        render_data(self.document.data)


class TestArrange(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press('a')
        self.page = self.app.screen

    def scenes(self):
        return [scene['name'] for scene in self.document.data['scenes']]

    async def test_empty_clips_and_the_last_row_show_a_plus(self):
        self.assertEqual(self.text().count('+'), 2 + 1 + self.text().count('« + »'))

    async def test_scenes_show_their_time(self):
        self.assertIn('0:01', self.text().split('\n')[4])

    async def test_plus_adds_a_scene_below_the_cursor(self):
        await self.press('+')
        self.assertEqual(len(self.scenes()), 3)
        self.assertEqual(self.page.row, 1)

    async def test_u_and_d_move_scenes_in_render_order(self):
        await self.press('d')
        self.assertEqual(self.scenes(), ['two', 'one'])
        song = render_data(self.document.data)
        self.assertEqual([scene.name for scene in song.scenes], ['two', 'one'])

    async def test_copy_and_delete_on_the_scene_name_act_on_the_scene(self):
        await self.press('c')
        self.assertEqual(self.scenes(), ['one', 'one copy', 'two'])
        await self.press('backspace')
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        self.assertIn('clip(s)', self.text())
        await self.press('y')
        self.assertEqual(self.scenes(), ['one', 'two'])

    async def test_enter_on_a_blank_clip_picks_a_pattern_and_opens_it(self):
        await self.press('right', 'down', 'enter')
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        await self.press('down', 'enter')
        self.assertIsInstance(self.app.screen, ClipPage)
        self.assertEqual(self.document.cell(1, 'lead'), {'pattern': 'beat'})

    async def test_no_patterns_is_explained(self):
        for name in self.document.song().get_pattern_names():
            self.document.delete_pattern(name)
        await self.press('right', 'down', 'enter')
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn('Patterns page', self.text())

    async def test_enter_on_a_scene_opens_its_settings(self):
        await self.press('enter')
        self.assertIsInstance(self.app.screen, ScenePage)

    async def test_copy_and_paste_a_clip(self):
        await self.press('right', 'c', 'down', 'v')
        self.assertEqual(self.document.cell(1, 'lead'), {'pattern': 'tune'})
        self.document.cell(1, 'lead')['repeat'] = 2
        self.assertNotIn('repeat', self.document.cell(0, 'lead'))

    async def test_delete_a_clip_confirms(self):
        await self.press('right', 'backspace')
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press('y')
        self.assertIsNone(self.document.cell(0, 'lead'))

    async def test_every_clip_looping_is_shown(self):
        self.document.cell(0, 'lead')['loop'] = True
        self.document.changed()
        self.app.screen.draw()
        await self.pilot.pause()
        self.assertIn('every clip loops', self.text())

    async def test_scrolls_to_keep_the_cursor_on_screen(self):
        for number in range(20):
            self.document.data['tracks'][f't{number}'] = {}
        self.document.changed()
        await self.press(*['right'] * 22)
        self.assertIn('t19', self.text())


class TestArrangeSmallTerminal(UITest):
    SIZE = (60, 18)

    async def test_nothing_breaks(self):
        for name in ['a', 'right', 'tab', 'p', 'enter', 'tab', 'tab']:
            await self.press(name)
        self.assertIsInstance(self.app.screen, MainPage)


class TestClipPage(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press('a', 'right', 'enter')
        self.page = self.app.screen

    def cell(self):
        return self.document.cell(0, 'lead')

    def labels(self):
        return [field.label for field in self.page.fields()]

    async def go_to(self, label):
        self.page.place = self.labels().index(label)
        self.page.draw()
        await self.pilot.pause()

    async def test_repeat_is_always_available(self):
        self.assertIn('Repeat', self.labels())
        await self.go_to('Repeat')
        await self.press('+')
        self.assertEqual(self.cell()['repeat'], 2)
        self.assertEqual(self.document.clip_seconds(0, 'lead'), 2)

    async def test_morph_only_appears_with_a_repeat_above_one(self):
        self.assertNotIn('Morph to', self.labels())
        await self.go_to('Repeat')
        await self.press('+')
        self.assertIn('Morph to', self.labels())
        self.assertNotIn('Morph direction', self.labels())

    async def test_choosing_a_second_pattern_offers_a_direction(self):
        await self.go_to('Repeat')
        await self.press('+')
        await self.go_to('Morph to')
        await self.press('enter', 'down', 'enter')
        self.assertEqual(self.cell()['morph_to'], 'beat')
        self.assertEqual(self.cell()['morph_style'], 'left')
        await self.go_to('Morph direction')
        await self.press('+')
        self.assertEqual(self.cell()['morph_style'], 'right')
        await self.press('+')
        self.assertEqual(self.cell()['morph_style'], 'middle')
        render_data(self.document.data)

    async def test_going_back_to_one_repeat_removes_the_morph(self):
        self.cell().update(repeat=2, morph_to='other', morph_style='left')
        await self.go_to('Repeat')
        await self.press('-')
        self.assertEqual(self.cell(), {'pattern': 'tune'})

    async def test_loop_is_a_toggle(self):
        await self.go_to('Loop')
        await self.press('enter')
        self.assertTrue(self.cell()['loop'])
        await self.press('enter')
        self.assertNotIn('loop', self.cell())

    async def test_chain_can_be_chosen_and_removed(self):
        await self.go_to('Chain')
        await self.press('enter', 'down', 'enter')
        self.assertEqual(self.cell()['chain'], 'named')
        await self.press('backspace')
        self.assertNotIn('chain', self.cell())

    async def test_shows_its_length(self):
        self.assertIn('0:01', self.text())


class TestRhythmAndNotesFromOnAClip(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press('a', 'right', 'enter')
        self.page = self.app.screen

    def cell(self):
        return self.document.cell(0, 'lead')

    async def go_to(self, label):
        self.page.place = [field.label for field in self.page.fields()].index(label)
        self.page.draw()
        await self.pilot.pause()

    async def test_they_are_at_the_bottom_of_the_page(self):
        self.cell().update(repeat=2, morph_to='other', morph_style='left')
        labels = [field.label for field in self.page.fields()]
        self.assertEqual(labels[-1], 'Grab track')

    async def test_choosing_none_clears(self):
        self.cell()['grab_track'] = 'drums'
        await self.go_to('Grab track')
        await self.press('enter')
        self.app.screen.place = 0
        await self.press('enter')
        self.assertNotIn('grab_track', self.cell())

    async def test_choosing_a_grab_track(self):
        await self.go_to('Grab track')
        await self.press('enter')
        self.assertEqual(self.app.screen.options, ['(none)', 'drums'])
        self.app.screen.place = 1
        await self.press('enter')
        self.assertEqual(self.cell()['grab_track'], 'drums')

    async def test_a_circular_grab_is_refused_with_a_message(self):
        self.document.cell(0, 'drums')['grab_track'] = 'lead'
        await self.go_to('Grab track')
        await self.press('enter')
        self.app.screen.place = 1
        await self.press('enter')
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn('Circular grab', self.text())
        self.assertIn('a circle: lead → drums →', self.text())
        self.assertIn('Remove the grab from another clip in this scene first.', self.text())
        self.assertNotIn('grab_track', self.cell())

    async def test_says_when_the_grab_track_has_no_grab_steps_to_change(self):
        self.cell().update(grab_track='drums')
        self.page.draw()
        await self.pilot.pause()
        self.assertIn('this pattern has none yet', self.text())
        self.document.set_step_value('tune', 'grab', 0, True)
        self.page.draw()
        await self.pilot.pause()
        self.assertNotIn('this pattern has none yet', self.text())
        render_data(self.document.data)

    async def test_the_grid_marks_them(self):
        self.cell().update(grab_track='drums')
        await self.press('tab')
        self.assertIn('tune g', self.text())

    async def test_a_pattern_in_use_this_way_cannot_be_deleted(self):
        self.cell().update(repeat=2, morph_to='other')
        await self.press('tab', 'tab', 'p', 'down', 'down', 'backspace')
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn('scene 1 (one), track lead', self.text())

    async def test_the_result_saves_and_loads(self):
        self.cell().update(grab_track='drums')
        self.document.save('x.yml')
        self.assertEqual(Document.load('x.yml').cell(0, 'lead'), self.cell())


class TestRegistersPage(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press('r')
        self.page = self.app.screen

    def label(self, name, what):
        return FIELD_LABEL.format(name=name, what=what)

    def register(self, name):
        return self.document.register(name)

    async def test_it_opens_from_the_main_screen_with_every_register(self):
        self.assertIsInstance(self.page, RegistersPage)
        labels = [field.label for field in self.page.fields()]
        for name in REGISTER_NAMES:
            for _, what in NUMBER_FIELDS:
                self.assertIn(self.label(name, what), labels)
            self.assertIn(self.label(name, WRAP_FIELD), labels)

    async def test_numbers_change_and_go_back_to_their_defaults(self):
        await self.select_field(self.label(RegisterName.BX, 'maximum'))
        await self.press('+')
        self.assertEqual(self.register(RegisterName.BX).get_maximum(), DEFAULT_REGISTER_MAXIMUM + 1)
        await self.press('backspace')
        self.assertEqual(self.register(RegisterName.BX).get_maximum(), DEFAULT_REGISTER_MAXIMUM)
        self.assertNotIn(Section.REGISTERS, self.document.data)

    async def test_a_typed_number_can_be_negative(self):
        lowest = -50
        await self.select_field(self.label(RegisterName.DX, 'minimum'))
        await self.press('enter')
        self.app.screen.value = str(lowest)
        await self.press('enter')
        self.assertEqual(self.register(RegisterName.DX).get_minimum(), lowest)
        render_data(self.document.data)

    async def test_settings_out_of_order_are_refused_with_the_reason(self):
        await self.select_field(self.label(RegisterName.AX, 'minimum'))
        await self.press('+')
        self.assertEqual(self.register(RegisterName.AX).get_minimum(), DEFAULT_REGISTER_MINIMUM)
        self.assertIn(OUT_OF_ORDER_START, self.text())

    async def test_wrapping_toggles(self):
        await self.select_field(self.label(RegisterName.CX, WRAP_FIELD))
        await self.press('enter')
        self.assertTrue(self.register(RegisterName.CX).wraps())
        await self.press('enter')
        self.assertFalse(self.register(RegisterName.CX).wraps())

    async def test_settings_save_and_load(self):
        await self.select_field(self.label(RegisterName.AX, 'maximum'))
        await self.press('-')
        self.document.save('x.yml')
        self.assertEqual(Document.load('x.yml').register(RegisterName.AX).get_maximum(), DEFAULT_REGISTER_MAXIMUM - 1)


class TestScenePage(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press('a', 'enter')
        self.page = self.app.screen

    def scene(self):
        return self.document.data['scenes'][0]

    async def go_to(self, label):
        self.page.place = [field.label for field in self.page.fields()].index(label)
        self.page.draw()
        await self.pilot.pause()

    async def test_shows_the_length_of_its_longest_clip(self):
        self.assertIn('Length', self.text())
        self.assertIn('0:01', self.text())

    async def test_scale_can_be_set_and_cleared(self):
        await self.go_to('Scale')
        await self.press('enter', 'down', 'enter')
        self.assertEqual(self.scene()['scale'], 'C Major')
        await self.press('backspace')
        self.assertNotIn('scale', self.scene())

    async def test_tempo_and_ramp(self):
        await self.go_to('Tempo')
        await self.press('+')
        self.assertEqual(self.scene()['tempo'], 121)
        await self.go_to('Tempo ramps to')
        await self.press('+')
        self.assertEqual((self.scene()['tempo_start'], self.scene()['tempo_end']), (121, 122))
        self.assertNotIn('tempo', self.scene())
        render_data(self.document.data)
        await self.press('backspace')
        self.assertEqual(self.scene()['tempo'], 121)
        self.assertNotIn('tempo_end', self.scene())

    async def test_repeat(self):
        await self.go_to('Repeat')
        await self.press('+')
        self.assertEqual(self.scene()['repeat'], 2)
        self.assertEqual(self.document.scene_seconds(0), 2)

    async def test_rename(self):
        await self.press('enter')
        self.app.screen.value = 'intro'
        await self.press('enter')
        self.assertEqual(self.scene()['name'], 'intro')


    async def test_it_can_reset_each_register(self):
        label = RESET_LABEL.format(name=RegisterName.BX)
        await self.go_to(label)
        await self.press('enter')
        self.assertEqual(self.scene()[SceneSetting.RESET], [RegisterName.BX])
        await self.press('enter')
        self.assertNotIn(SceneSetting.RESET, self.scene())

class TestTracksScalesChainsAndArps(UITest):

    async def test_tracks(self):
        await self.press('t', '+')
        await self.type('bass')
        await self.press('enter')
        self.assertEqual(list(self.document.data['tracks']), ['lead', 'drums', 'bass'])
        await self.press('n')
        self.app.screen.value = 'low'
        await self.press('enter', 'u')
        self.assertEqual(list(self.document.data['tracks']), ['lead', 'low', 'drums'])
        await self.press('c')
        self.assertIn('low copy', self.document.data['tracks'])

    async def test_a_tracks_settings(self):
        await self.press('t', 'enter')
        self.assertIsInstance(self.app.screen, TrackEditor)
        await self.select_field('Mute')
        await self.press('enter')
        self.assertIs(self.document.track('lead')['mute'], True)
        await self.press('enter')
        self.assertNotIn('mute', self.document.track('lead'))
        await self.select_field('Transpose')
        await self.press('+', '+')
        self.assertEqual(self.document.track('lead')['transpose'], 2)
        await self.select_field('CC 1')
        await self.press('enter')
        self.app.screen.value = '74'
        await self.press('enter')
        self.assertEqual(self.document.track('lead')['cc'], [74, None, None, None])
        await self.press('backspace')
        self.assertNotIn('cc', self.document.track('lead'))
        await self.select_field('Drum')
        await self.press('enter')
        self.assertIs(self.document.track('lead')['drum'], True)
        self.assertIn('(drum track)', self.text())
        await self.press('tab')
        self.assertIn('drum', self.text())
        render_data(self.document.data)

    async def test_editing_an_arps_offsets_and_octaves(self):
        await self.press('g', 'enter', 'enter')
        self.assertIsInstance(self.app.screen, ArpEditor)
        await self.press('down', 'down', '+')
        self.assertEqual(self.document.data['arps']['up']['octave_range'], 2)
        await self.press('down', '+')
        self.assertEqual(self.document.data['arps']['up']['octave_jump'], 'after_each_note')
        self.assertIn('after each note', self.text())
        await self.press('down', 'enter')
        self.assertIsInstance(self.app.screen, OffsetsEditor)
        self.assertEqual(self.document.data['arps']['up']['offsets'], [0] * 8)
        await self.press('right', '7', 'right', 'space', 'right', '-', '-', 'x', 'i')
        self.assertEqual(self.document.data['arps']['up']['offsets'], [0, 7, None, 0, 0, 0, 0, 0])
        await self.press('tab')
        self.assertIn('0 7 - 0 0 0 0 0', self.text())
        await self.press('backspace')
        self.assertNotIn('offsets', self.document.data['arps']['up'])
        render_data(self.document.data)

    async def test_offsets_have_one_to_sixteen_steps(self):
        self.document.data['arps']['up']['offsets'] = [0] * 16
        await self.press('g', 'enter', 'enter', *['down'] * 4, 'enter')
        self.assertNotIn('« I »', self.text())
        self.document.data['arps']['up']['offsets'] = [3]
        await self.press('right')
        self.assertNotIn('« X »', self.text())

    async def test_deleting_a_track_says_it_deletes_its_clips(self):
        await self.press('t', 'backspace')
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        self.assertIn('1 clip(s)', self.text())
        await self.press('y')
        self.assertEqual(list(self.document.data['tracks']), ['drums'])
        self.assertIsNone(self.document.cell(0, 'lead'))

    async def test_the_default_scale_must_be_unset_before_deleting_it(self):
        await self.press('z', 'backspace')
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn('the song', self.text())
        await self.press('enter', 'tab', 's', 'down', 'down', 'down', 'backspace', 'tab', 'z', 'backspace', 'y')
        self.assertEqual(self.document.data['scales'], {})

    async def test_adding_a_scale_picks_a_root_a_kind_and_a_name(self):
        await self.press('z', '+')
        self.assertIn('root note', self.text())
        self.app.screen.place = self.app.screen.options.index('F#')
        await self.press('enter')
        self.app.screen.place = self.app.screen.options.index('dorian')
        await self.press('enter')
        self.assertEqual(self.app.screen.value, 'F# Dorian')
        self.app.screen.value = 'main'
        await self.press('enter')
        self.assertEqual(self.document.data['scales']['main'], {'root': 'F#', 'type': 'dorian'})

    def dialog_text(self):
        return str(self.app.screen.query_one('#dialog-view').render())

    async def test_roots_are_laid_out_like_a_keyboard(self):
        await self.press('z', '+')
        dialog = self.app.screen
        self.assertIsInstance(dialog, GridChoiceDialog)
        lines = self.dialog_text().splitlines()
        self.assertIn('C   C#   D   D#   E   F   F#   G   G#   A   A#   B', '\n'.join(lines))
        dialog.place = dialog.options.index('C')
        await self.press('right')
        self.assertEqual(dialog.options[dialog.place], 'C#')
        await self.press('down')
        self.assertEqual(dialog.options[dialog.place], 'Db')
        await self.press('right')
        self.assertEqual(dialog.options[dialog.place], 'D')

    async def test_scales_are_grouped_and_show_their_notes(self):
        await self.press('z', '+')
        self.app.screen.place = self.app.screen.options.index('D')
        await self.press('enter')
        dialog = self.app.screen
        text = self.dialog_text()
        for word in ['MODES', 'MINOR & MAJOR', 'SYMMETRIC', 'PENTATONIC & BLUES', 'whole half dim', 'ionian', 'egyptian']:
            self.assertIn(word, text)
        self.assertNotIn('diminished', text)
        self.assertNotIn('hirajoshi', text)
        self.assertLessEqual(len(text.splitlines()), 22)
        dialog.place = dialog.options.index('dorian')
        await self.press('down')
        self.assertEqual(dialog.options[dialog.place], 'phrygian')
        await self.press('up')
        self.assertIn('D dorian: D E F G A B C', self.dialog_text())
        await self.press('enter')
        self.assertEqual(self.app.screen.value, 'D Dorian')

    async def open_scale_kinds(self):
        await self.press('z', '+')
        self.app.screen.place = self.app.screen.options.index('D')
        await self.press('enter')
        return self.app.screen

    async def test_the_scale_picker_shows_its_other_page(self):
        dialog = await self.open_scale_kinds()
        dialog.place = dialog.options.index('dorian')
        first = self.dialog_text().splitlines()
        for word in [' COMMON ', ' JAZZ & WORLD ', 'PgDn ▸', 'PgUp/PgDn', 'other page']:
            self.assertIn(word, '\n'.join(first))
        self.assertNotIn('◂ PgUp', '\n'.join(first))
        await self.press('pagedown')
        text = self.dialog_text()
        for word in ['MELODIC MINOR', 'MIDDLE EAST & EUROPE', 'EAST ASIA', 'INDIA', 'JAZZ', 'phrygian dom', 'mixolydian flat6', '◂ PgUp']:
            self.assertIn(word, text)
        self.assertNotIn('PgDn ▸', text)
        self.assertNotIn('natural minor', text)
        lines = text.splitlines()
        self.assertLessEqual(len(lines), 22)
        self.assertLessEqual(max(len(line) for line in lines), 76)
        # The cursor stays in its column, on the nearest row.
        self.assertEqual(dialog.options[dialog.place], 'lydian augmented')
        await self.press('pagedown')
        self.assertEqual(dialog.page, 1)
        await self.press('pageup', 'pageup')
        self.assertEqual(dialog.page, 0)

    async def test_both_scale_pages_are_the_same_size(self):
        dialog = await self.open_scale_kinds()
        sizes = []
        for page in range(len(dialog.pages)):
            dialog.page = page
            dialog.place = next(cell for row in dialog.grid for cell in row if isinstance(cell, int))
            dialog.draw()
            lines = self.dialog_text().splitlines()
            sizes.append((len(lines), {len(line) for line in lines}))
        self.assertEqual(len(set(map(str, sizes))), 1, sizes)
        self.assertEqual(len(sizes[0][1]), 1)

    async def test_a_long_title_does_not_widen_the_scale_picker(self):
        dialog = await self.open_scale_kinds()
        width = len(self.dialog_text().splitlines()[0])
        dialog.title = 'Change ' + 'a very long scale name ' * 4
        dialog.draw()
        self.assertEqual({len(line) for line in self.dialog_text().splitlines()}, {width})
        self.assertIn('JAZZ & WORLD', self.dialog_text())

    async def test_arrows_cross_to_the_other_page(self):
        dialog = await self.open_scale_kinds()
        dialog.place = dialog.options.index('blues')
        await self.press('right')
        self.assertEqual(dialog.page, 1)
        self.assertEqual(dialog.options[dialog.place], 'lydian augmented')
        await self.press('left')
        self.assertEqual(dialog.page, 0)
        self.assertEqual(dialog.options[dialog.place], 'blues')
        await self.press('left', 'left', 'left')
        # The first page doesn't go round to the last.
        self.assertEqual(dialog.page, 0)
        self.assertEqual(dialog.options[dialog.place], 'dorian')
        await self.press('pagedown', 'right', 'right', 'right')
        self.assertEqual(dialog.page, 1)
        self.assertEqual(dialog.options[dialog.place], 'iwato')

    async def test_picking_a_world_scale(self):
        dialog = await self.open_scale_kinds()
        dialog.place = dialog.options.index('major')
        await self.press('pagedown', 'right', 'right')
        self.assertEqual(dialog.options[dialog.place], 'hirajoshi')
        self.assertIn('D hirajoshi: D E F A A#', self.dialog_text())
        await self.press('enter')
        self.app.screen.value = 'main'
        await self.press('enter')
        self.assertEqual(self.document.data['scales']['main'], {'root': 'D', 'type': 'hirajoshi'})
        render_data(self.document.data)

    async def test_two_scales_can_be_the_same_notes(self):
        await self.press('z', 'c')
        self.assertEqual(self.document.data['scales']['C Major copy'], {'root': 'C', 'type': 'major'})

    async def test_changing_a_scale_keeps_its_name_and_changes_what_uses_it(self):
        await self.press('z', 'enter')
        self.app.screen.place = self.app.screen.options.index('D')
        await self.press('enter', 'enter')
        self.assertEqual(self.document.data['scale'], 'C Major')
        self.assertEqual(self.document.data['scales']['C Major']['root'], 'D')

    async def test_renaming_a_scale_updates_what_uses_it(self):
        self.document.data['scenes'][0]['scale'] = 'C Major'
        await self.press('z', 'n')
        self.app.screen.value = 'main'
        await self.press('enter')
        self.assertEqual(self.document.data['scale'], 'main')
        self.assertEqual(self.document.data['scenes'][0]['scale'], 'main')
        render_data(self.document.data)

    async def test_arps_are_under_generators(self):
        await self.press('g')
        self.assertIn('Arpeggiators', self.text())
        self.assertIn('AutoRatchets', self.text())
        self.assertEqual(len(self.app.screen.rows()), 2)
        await self.press('enter')
        self.assertIsInstance(self.app.screen, ArpsPage)

    async def test_editing_an_arp(self):
        await self.press('g', 'enter', 'enter')
        self.assertIsInstance(self.app.screen, ArpEditor)
        await self.press('+')
        self.assertEqual(self.document.data['arps']['up']['step'], '1/4')
        await self.press('down', '+')
        self.assertEqual(self.document.data['arps']['up']['order'], 'down')

    async def test_adding_an_arp(self):
        await self.press('g', 'enter', '+')
        await self.type('rise')
        await self.press('enter')
        self.assertEqual(self.document.data['arps']['rise']['order'], 'up')
        Song.from_data(self.document.data)

    async def test_an_auto_ratchet_can_be_made_edited_and_added_to_a_chain(self):
        await self.press('g', 'down', 'enter')
        self.assertIsInstance(self.app.screen, AutoRatchetsPage)
        await self.press('+')
        await self.type('fast')
        await self.press('enter')
        self.assertEqual(self.document.data['auto_ratchets']['fast'], {'counts': [2]})
        await self.press('enter')
        self.assertIsInstance(self.app.screen, AutoRatchetEditor)
        await self.press('enter')
        self.app.screen.value = '1 1 4'
        await self.press('enter')
        self.assertEqual(self.document.data['auto_ratchets']['fast']['counts'], [1, 1, 4])
        await self.press('tab', 'tab', 'tab', 'c', 'down', 'enter', '+')
        self.assertEqual(self.app.screen.options, ['arp: up', 'auto_ratchet: rolls', 'auto_ratchet: fast'])
        await self.press('down', 'down', 'enter')
        self.assertEqual(self.document.data['chains']['empty'], [{'auto_ratchet': 'fast'}])
        render_data(self.document.data)

    async def test_bad_counts_are_refused(self):
        await self.press('g', 'down', 'enter', 'enter', 'enter')
        self.app.screen.value = '1 x'
        await self.press('enter')
        self.assertEqual(self.document.data['auto_ratchets']['rolls']['counts'], [1, 4])
        self.assertIn('whole numbers', self.text())

    async def test_deleting_an_auto_ratchet_in_a_chain_is_refused(self):
        self.document.data['chains']['empty'] = [{'auto_ratchet': 'rolls'}]
        await self.press('g', 'down', 'enter', 'backspace')
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn('chain empty', self.text())

    async def test_deleting_an_arp_in_a_chain_is_refused(self):
        await self.press('g', 'enter', 'backspace')
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn('chain named', self.text())

    async def test_a_chain_can_add_a_named_arp(self):
        await self.press('c', 'down', 'enter')
        self.assertIsInstance(self.app.screen, ChainEditor)
        await self.press('+', 'enter')
        self.assertEqual(self.document.data['chains']['empty'], [{'arp': 'up'}])
        Song.from_data(self.document.data)

    async def test_adding_a_chain_step_needs_an_arp_first(self):
        for name in self.document.song().get_chain_names():
            self.document.delete_chain(name)
        self.delete_every_generator()
        self.document.add_chain(EMPTY_CHAIN)
        await self.press('c', 'enter', '+')
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn('Generators', self.text())


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
        self.assertEqual(list(self.document.data['tracks']), ['lead', 'drums', 'bass'])

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
        self.assertEqual(list(self.document.data['tracks']), ['lead', 'drums'])
        self.assertIsInstance(self.app.screen, TracksPage)

    async def test_lists_that_cannot_add_have_none(self):
        await self.press('g')
        self.assertEqual(len(self.app.screen.rows_with_plus()), 2)

    async def test_arrange_has_one_for_scenes(self):
        await self.press('a', 'down', 'down')
        self.assertTrue(self.app.screen.on_plus_row())
        self.assertNotIn('« Bksp »', self.text())
        await self.press('enter')
        self.assertEqual(len(self.document.data['scenes']), 3)
        self.assertEqual(self.app.screen.row, 2)
        self.assertEqual(self.document.data['scenes'][2]['tracks'], {})

    async def test_arrange_with_no_scenes_starts_on_it(self):
        self.empty_the_arrangement()
        await self.press('a', 'enter')
        self.assertEqual(len(self.document.data['scenes']), 1)


class TestSettingArrows(UITest):

    async def test_left_and_right_do_the_same_as_minus_and_plus(self):
        await self.press('s', 'down', 'down', 'right', 'right', 'left')
        self.assertEqual(self.document.data['tempo'], 121)

    async def test_on_every_setting_with_a_value_to_step(self):
        await self.press('s', 'down', 'down', 'down', 'left')
        self.assertIsNone(self.document.data['scale'])
        await self.press('right')
        self.assertEqual(self.document.data['scale'], 'C Major')
        await self.press('down', 'right')
        self.assertEqual(self.document.data['seed'], 2)
        await self.press('down', 'right')
        self.assertEqual(self.document.data['step_size'], '1/8')
        await self.press('down', 'left')
        self.assertEqual(self.document.data['default_octave'], 2)
        await self.press('down', 'right')
        self.assertEqual(self.document.data['default_drum_octave'], 2)


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
        await self.go_to_row('chord')
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
        render_data(self.document.data)

    def dialog_text(self):
        return str(self.app.screen.query_one('#dialog-view').render())

    async def test_the_chord_grid_shows_every_chord_at_once(self):
        await self.go_to_row('chord')
        await self.press('enter')
        text = self.dialog_text()
        for word in ['(none)', 'TRIADS', 'SEVENTHS', 'NINTHS', '11THS, 13THS', 'SCALE', 'M', 'm6', '7sus4', 'madd9', 'm13', '13']:
            self.assertIn(word, text)
        self.assertLessEqual(len(text.splitlines()), 22)
        self.assertLessEqual(max(len(line) for line in text.splitlines()), 76)

    async def test_arrows_move_around_the_chord_grid(self):
        await self.go_to_row('chord')
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
        await self.go_to_row('chord')
        await self.press('enter', 'down', 'right', 'down', 'down', 'down', 'down', 'down')
        self.assertIn('Half-diminished', self.dialog_text())

    async def test_typing_numbers_into_ratchet(self):
        await self.go_to_row('ratchet')
        await self.press('4')
        self.assertEqual(self.value('ratchet'), 4)
        await self.press('right', 'left', '1', '2')
        self.assertEqual(self.value('ratchet'), 12)

    async def test_too_big_a_number_starts_again(self):
        await self.go_to_row('ratchet')
        await self.press('1', '6', '3')
        self.assertEqual(self.value('ratchet'), 3)

    async def test_typing_velocity_with_several_digits(self):
        await self.go_to_row('velocity')
        await self.press('1', '0', '0')
        self.assertEqual(self.value('velocity'), 100)
        await self.press('right', 'left', '6', '4')
        self.assertEqual(self.value('velocity'), 64)
        await self.press('+')
        await self.press('9')
        self.assertEqual(self.value('velocity'), 9)

    async def test_zero_is_refused_where_it_is_out_of_range(self):
        await self.go_to_row('velocity')
        await self.press('5', 'right', 'left', '0')
        self.assertEqual(self.value('velocity'), 5)

    async def test_typing_probability(self):
        await self.go_to_row('probability')
        await self.press('0')
        self.assertEqual(self.value('probability'), 0)
        await self.press('1', '0', '0')
        self.assertEqual(self.value('probability'), 100)

    async def test_typing_does_not_move_the_cursor(self):
        await self.go_to_row('velocity')
        before = (self.app.screen.step, self.app.screen.row)
        await self.press('1', '0')
        self.assertEqual((self.app.screen.step, self.app.screen.row), before)

    async def test_a_scale_with_more_than_nine_notes_takes_two_digits(self):
        self.document.add_scale(CHROMATIC_SCALE, NoteName.C, scale_type_name(ScaleType.CHROMATIC))
        self.document.set_scale_name(CHROMATIC_SCALE)
        self.document.changed()
        await self.press('p', 'enter', '1', '2')
        self.assertEqual(self.value('degree'), 12)


class TestDirectionsAndGrab(UITest):

    async def test_a_pattern_chooses_a_direction(self):
        await self.press('p', 'enter', 'p')
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options[0], 'forward    first step to last')
        self.assertEqual(self.app.screen.options[1], 'reverse a  step 1, then backward from the last')
        self.app.screen.place = 4
        await self.press('enter')
        self.assertEqual(self.document.data['patterns']['tune']['direction'], 'pendulum')
        self.assertIn('Direction pendulum', self.text())
        render_data(self.document.data)

    async def clip_page(self):
        await self.press('a', 'right', 'enter')
        return self.app.screen

    async def go_to(self, page, label):
        page.place = [field.label for field in page.fields()].index(label)
        page.draw()
        await self.pilot.pause()

    async def test_a_clip_shows_the_patterns_direction_until_it_overrides_it(self):
        self.document.data['patterns']['tune']['direction'] = 'alternate'
        page = await self.clip_page()
        self.assertIn('(pattern: alternate)', self.text())
        await self.go_to(page, 'Direction')
        await self.press('right')
        self.assertEqual(self.document.cell(0, 'lead')['direction'], 'forward')
        await self.press('right')
        self.assertEqual(self.document.cell(0, 'lead')['direction'], 'reverse_a')
        await self.press('backspace')
        self.assertNotIn('direction', self.document.cell(0, 'lead'))

    async def test_a_clip_direction_can_be_chosen_from_a_list(self):
        page = await self.clip_page()
        await self.go_to(page, 'Direction')
        await self.press('enter')
        self.assertEqual(self.app.screen.options[0], "(pattern)  use each pattern's direction")
        self.assertEqual(self.app.screen.options[1], 'forward    first step to last')
        self.app.screen.place = self.app.screen.options.index('brownian   on 50%, back 25%, stay 25%')
        await self.press('enter')
        self.assertEqual(self.document.cell(0, 'lead')['direction'], 'brownian')

    async def test_the_grid_marks_a_clip_with_its_own_direction(self):
        self.document.cell(0, 'lead')['direction'] = 'random'
        await self.press('a')
        self.assertIn('tune d', self.text())

    async def test_the_grab_row_is_always_in_the_advanced_rows(self):
        await self.press('p', 'enter')
        self.assertNotIn(ROW_SHOWN.format(label=ROW_LABELS[Row.GRAB]), self.text())
        await self.press('pagedown')
        self.assertIn(ROW_SHOWN.format(label=ROW_LABELS[Row.GRAB]), self.text())
        self.assertIn(ROW_SET_HEADERS[ADVANCED], self.text())

    async def test_marking_a_step_with_space(self):
        await self.press('p', 'enter', 'pagedown')
        while self.app.screen.row_name() != Row.GRAB:
            await self.press('down')
        await self.press('space')
        self.assertTrue(self.document.step_value('tune', 'grab', 0))
        self.assertEqual(self.app.screen.cell_text('grab', 0), '*')
        render_data(self.document.data)


class TestDirectionsAndGrabOnAUsualConsole(UITest):
    SIZE = (80, 24)

    async def test_everything_still_fits_with_the_grab_row(self):
        self.document.data['patterns']['tune']['source_pattern'] = 'other'
        await self.press('p', 'enter', 'pagedown')
        text = self.text()
        self.assertIn(ROW_SHOWN.format(label=ROW_LABELS[Row.GRAB]), text)
        self.assertIn('Step 1:', text)
        for item in self.app.screen.key_table():
            self.assertIn(f'« {item.shown_label()} »', text)


class TestRowSets(UITest):
    """PgDn and PgUp step the rows under Degree through the editor's sets of rows."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press('p', 'enter')
        self.editor = self.app.screen

    async def go_to_set(self, row_set):
        """Press PgDn until a set of rows shows."""
        while self.app.row_set != row_set:
            await self.press('pagedown')

    def shown(self, row):
        return ROW_SHOWN.format(label=ROW_LABELS[row])

    async def test_pgdn_goes_through_every_set_in_order_and_round(self):
        for row_set, rows in ROW_SETS.items():
            self.assertEqual(self.app.row_set, row_set)
            text = self.text()
            for row in rows:
                self.assertIn(self.shown(row), text)
            await self.press('pagedown')
        self.assertEqual(self.app.row_set, NORMAL)

    async def test_pgup_goes_back(self):
        await self.press('pageup')
        self.assertEqual(self.app.row_set, list(ROW_SETS)[-1])
        await self.press('pagedown')
        self.assertEqual(self.app.row_set, NORMAL)

    async def test_the_key_names_the_next_set(self):
        self.assertIn(ROW_SET_NAMES[ADVANCED], self.text())

    async def test_cc_rows_take_values_even_on_a_rest(self):
        await self.go_to_set(CC)
        rest = 2
        value = 100
        await self.press('right', 'right', 'down')
        self.assertEqual(self.editor.row_name(), Row.CC1)
        self.assertEqual(self.editor.cell_text(Row.CC1, rest), QUIET_VALUE)
        await self.press(*str(value))
        self.assertEqual(self.document.step_value('tune', Row.CC1, rest), value)
        await self.press('+')
        self.assertEqual(self.document.step_value('tune', Row.CC1, rest), value + 1)
        await self.press('backspace')
        self.assertIsNone(self.document.step_value('tune', Row.CC1, rest))
        while self.editor.row_name() != Row.SLIDE:
            await self.press('down')
        await self.press('space')
        self.assertIs(self.document.step_value('tune', Row.SLIDE, rest), True)
        self.assertEqual(self.editor.cell_text(Row.SLIDE, rest), TOGGLE_ON)
        render_data(self.document.data)

    async def test_the_set_stays_for_other_patterns(self):
        await self.press('pagedown', 'tab', 'enter')
        self.assertIn(self.shown(Row.RATCHET_OFFSET), self.text())

    async def test_switching_keeps_degree_and_otherwise_goes_to_it(self):
        for _ in ROW_SETS:
            await self.press('down', 'pagedown')
            self.assertEqual(self.editor.row_name(), Row.DEGREE)

    async def test_typing_a_ratchet_offset_and_going_negative(self):
        await self.go_to_set(ADVANCED)
        while self.editor.row_name() != Row.RATCHET_OFFSET:
            await self.press('down')
        typed = 2
        await self.press(str(typed))
        self.assertEqual(self.document.step_value('tune', Row.RATCHET_OFFSET, 0), typed)
        presses = typed + 1
        await self.press(*['-'] * presses)
        self.assertEqual(self.document.step_value('tune', Row.RATCHET_OFFSET, 0), typed - presses)
        self.assertEqual(self.editor.cell_text(Row.RATCHET_OFFSET, 0), str(typed - presses))

    async def test_unset_register_changes_show_a_dot(self):
        await self.go_to_set(REGISTER_CHANGES)
        for row in REGISTER_ADD_ROWS.values():
            self.assertEqual(self.editor.cell_text(row, 0), QUIET_VALUE)

    async def test_register_changes_take_typed_values_including_negative_ones_even_on_a_rest(self):
        await self.go_to_set(REGISTER_CHANGES)
        rest = 2
        typed = -3
        row = REGISTER_ADD_ROWS[RegisterName.BX]
        await self.press('right', 'right')
        while self.editor.row_name() != row:
            await self.press('down')
        await self.press('enter')
        self.app.screen.value = str(typed)
        await self.press('enter')
        self.assertEqual(self.document.step_value('tune', row, rest), typed)
        await self.press('enter')
        self.app.screen.value = str(MAX_REGISTER_VALUE + 1)
        await self.press('enter')
        self.assertEqual(self.document.step_value('tune', row, rest), typed)
        render_data(self.document.data)

    async def test_register_uses_are_toggles_on_notes(self):
        await self.go_to_set(REGISTERS)
        row = REGISTER_VELOCITY_ROWS[RegisterName.CX]
        while self.editor.row_name() != row:
            await self.press('down')
        await self.press('space')
        self.assertIs(self.document.step_value('tune', row, 0), True)
        self.assertEqual(self.editor.cell_text(row, 0), TOGGLE_ON)
        await self.press('backspace')
        self.assertIs(self.document.step_value('tune', row, 0), False)

    async def test_a_drum_pattern_has_no_rows_that_move_notes(self):
        await self.go_to_set(REGISTERS)
        await self.press('tab', 'down', 'enter')
        rows = [name for name, _ in self.app.screen.rows()]
        for name in REGISTER_NOTE_ROWS.values():
            self.assertNotIn(name, rows)
        for name in REGISTER_VELOCITY_ROWS.values():
            self.assertIn(name, rows)

    async def test_on_a_drum_note_row_a_and_f_are_notes(self):
        await self.press('tab', 'down', 'enter')
        editor = self.app.screen
        await self.press('right', 'a')
        self.assertEqual(self.document.step_value('beat', Row.DEGREE, 1), 'A')
        self.assertEqual(self.app.row_set, NORMAL)
        await self.press('f')
        self.assertEqual(self.document.step_value('beat', Row.DEGREE, 1), 'F')
        labels = [item.shown_label() for item in editor.key_table()]
        self.assertNotIn('F', labels)

    async def test_on_other_drum_rows_f_is_a_command(self):
        await self.press('tab', 'down', 'enter', 'down')
        labels = [item.shown_label() for item in self.app.screen.key_table()]
        self.assertIn('F', labels)


class TestTieRow(UITest):
    """Tie is on the normal rows, works only on empty steps, and holds the note before it."""

    EMPTY_STEP = 2

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press('p', 'enter')
        self.editor = self.app.screen
        while self.editor.row_name() != Row.TIE:
            await self.press('down')

    def tie(self, step):
        return self.document.step_value('tune', Row.TIE, step)

    async def test_it_is_a_normal_row_and_toggles_on_an_empty_step(self):
        self.assertIn(ROW_SHOWN.format(label=ROW_LABELS[Row.TIE]), self.text())
        await self.press(*['right'] * self.EMPTY_STEP)
        await self.press('space')
        self.assertIs(self.tie(self.EMPTY_STEP), True)
        self.assertEqual(self.editor.cell_text(Row.TIE, self.EMPTY_STEP), TOGGLE_ON)
        self.assertIn(DESCRIBE_TIED.format(step=self.EMPTY_STEP + 1), self.text())
        render_data(self.document.data)
        await self.press('backspace')
        self.assertIs(self.tie(self.EMPTY_STEP), False)

    async def test_a_step_with_a_note_has_no_tie_keys(self):
        labels = [item.shown_label() for item in self.editor.key_table()]
        self.assertNotIn('Space', labels)
        await self.press('space')
        self.assertFalse(self.tie(0))

    async def test_typing_a_degree_on_a_tied_step_removes_the_tie(self):
        await self.press(*['right'] * self.EMPTY_STEP, 'space')
        while self.editor.row_name() != Row.DEGREE:
            await self.press('up')
        await self.press('5')
        self.assertIs(self.tie(self.EMPTY_STEP), False)
        self.assertEqual(self.document.step_value('tune', Row.DEGREE, self.EMPTY_STEP), 5)
        render_data(self.document.data)

    async def test_shortening_past_a_tie_asks_first(self):
        last = self.editor.steps() - 1
        await self.press(*['right'] * last, 'space')
        await self.press('r')
        self.app.screen.value = str(last)
        await self.press('enter')
        self.assertIsInstance(self.app.screen, ConfirmDialog)


class TestRearrangingAPattern(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.document.data['patterns']['long'] = {
            'steps': 5, 'degree': [1, 2, 3, 4, 5], 'gate': ['1/4', '1/8', '1/16', '1/2', '1'], 'velocity': [10, 20, 30, 40, 50],
        }
        await self.press('p', 'down', 'down', 'down', 'enter')
        self.editor = self.app.screen

    def rows(self, row='degree'):
        return self.document.data['patterns']['long'][row]

    async def test_flip_reverses_everything_after_the_cursor(self):
        await self.press('right', 'f')
        self.assertEqual(self.rows(), [1, 2, 5, 4, 3])

    async def test_every_row_moves_with_its_step(self):
        await self.press('right', 'f')
        self.assertEqual(self.rows('gate'), ['1/4', '1/8', '1', '1/2', '1/16'])
        self.assertEqual(self.rows('velocity'), [10, 20, 50, 40, 30])

    async def test_flip_twice_puts_it_back_and_the_cursor_stays(self):
        await self.press('right', 'f', 'f')
        self.assertEqual(self.rows(), [1, 2, 3, 4, 5])
        self.assertEqual(self.editor.step, 1)

    async def test_flip_on_the_last_step_says_why_nothing_happens(self):
        await self.press('left', 'f')
        self.assertEqual(self.rows(), [1, 2, 3, 4, 5])
        self.assertIn('no steps after', self.text())

    async def test_swap_exchanges_both_sides_of_the_cursor(self):
        await self.press('right', 's')
        self.assertEqual(self.rows(), [3, 4, 5, 2, 1])
        self.assertEqual(self.rows('gate'), ['1/16', '1/2', '1', '1/8', '1/4'])

    async def test_the_cursor_stays_on_its_step_so_swapping_twice_puts_it_back(self):
        await self.press('right', 's')
        self.assertEqual(self.editor.step, 3)
        self.assertEqual(self.document.step_value('long', 'degree', self.editor.step), 2)
        await self.press('s')
        self.assertEqual(self.rows(), [1, 2, 3, 4, 5])
        self.assertEqual(self.editor.step, 1)

    async def test_swap_at_either_end(self):
        await self.press('s')
        self.assertEqual(self.rows(), [2, 3, 4, 5, 1])
        self.assertEqual(self.editor.step, 4)

    async def test_the_time_stays_the_same(self):
        before = self.document.pattern_length('long')
        await self.press('right', 'f', 's')
        self.assertEqual(self.document.pattern_length('long'), before)

    async def test_load_replaces_everything_after_asking(self):
        await self.press('l')
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertNotIn('long', self.app.screen.options)
        self.app.screen.place = self.app.screen.options.index('beat')
        await self.press('enter')
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press('n')
        self.assertEqual(self.rows(), [1, 2, 3, 4, 5])
        await self.press('l')
        self.app.screen.place = self.app.screen.options.index('beat')
        await self.press('enter', 'y')
        self.assertEqual(self.document.data['patterns']['long'], self.document.data['patterns']['beat'])
        self.assertEqual(self.editor.steps(), 2)
        self.assertIn('│ Note', self.text())

    async def test_a_loaded_copy_is_separate(self):
        await self.press('l')
        self.app.screen.place = self.app.screen.options.index('beat')
        await self.press('enter', 'y', 'right', 'f')
        self.assertEqual(self.document.step_value('long', 'degree', 1), 'F')
        self.assertIsNone(self.document.step_value('beat', 'degree', 1))

    async def test_load_keeps_the_name_and_what_uses_it(self):
        self.document.cell(0, 'lead')['pattern'] = 'long'
        await self.press('l')
        self.app.screen.place = self.app.screen.options.index('other')
        await self.press('enter', 'y')
        self.assertEqual(self.document.cell(0, 'lead')['pattern'], 'long')
        render_data(self.document.data)

    async def test_the_old_keys_moved(self):
        await self.press('r')
        self.assertIsInstance(self.app.screen, PromptDialog)
        self.assertEqual(self.app.screen.value, '5')


class TestAdvancedRowsOnAUsualConsole(UITest):
    SIZE = (80, 24)

    async def test_every_set_of_rows_fits(self):
        await self.press('p', 'enter')
        for _ in ROW_SETS:
            text = self.text()
            self.assertIn('Step 1:', text)
            for item in self.app.screen.key_table():
                self.assertIn(KEY_SHOWN.format(label=item.shown_label()), text)
            await self.press('pagedown')


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


if __name__ == '__main__':
    unittest.main()
