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

"""The base class and helpers for the text UI tests, which run the real program with no terminal and press keys."""

import importlib
import inspect
import os
import pkgutil
import string
import tempfile
from textual.widgets import Static
import unittest
from unittest import mock

from llamatron.composition import file_format
from llamatron.composition.file_format import ClipSlotSetting, EuclidPart, GeneratorKind, PatternSetting, Row, SceneSetting, Section, ShapePart
from llamatron.composition.generator_settings import ArpSetting, AutoRatchetSetting, FollowChordsSetting, HocketSetting, ProgressionSetting, StepRowSetting, written_name
from llamatron.composition.setlist import new_setlist, Setlist
from llamatron.generators.arp import ChordOrder
from llamatron.music.note import NoteName
from llamatron.realtime.fluidsynth import FluidSynth
from llamatron.strings import names as names_text
from llamatron.support.memory import Memory
from llamatron.tui import drawing, keybindings
from llamatron.tui.app import LlamatronApp
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.grouped_choice_dialog import GroupedChoiceDialog
from llamatron.tui.document import Document
from llamatron.tui.key_table import every_key, first_key, key_event
from llamatron.tui.keys import Key, Steps
import llamatron.tui.screens
from llamatron.tui.screens.arrange.arrange_page import ArrangePlace
from llamatron.tui.screens.generators import generator_pages
from llamatron.tui.screens.shared import page as page_values
from llamatron.tui.screens.shared.field import Button
from llamatron.tui.screens.shared.field_page import FieldPage
from llamatron.tui.screens.shared.list_page import ListPage
from llamatron.tui.screens.shared.page import Page

# Every document a test makes checks what it remembers: an answer kept after what it came from changed fails the test (support/memory.py).
Memory.check_every_answer()
# A space, which the header's lines start with.
SPACE = ' '


# How the pattern editor shows a row's label at the left of the grid, a key in the key list,
# and a step whose quiet row isn't set.
# pilot.pause's delay that only lets the screen handle its messages, with no wait for the process to go idle.
SETTLED = 0
MSG_REAL_FLUIDSYNTH = 'a test started a real FluidSynth: give its transport a stand-in, as test_tui_playback.py does'
# Where the warning of silent instruments asks whether FluidSynth is installed.
FLUIDSYNTH_INSTALLED = 'llamatron.tui.silent_instruments.fluidsynth_installed'
# Where the transport asks the same.
TRANSPORT_FINDS_FLUIDSYNTH = 'llamatron.tui.transport.is_installed'
ROW_SHOWN = '│ {label}'


KEY_SHOWN = '« {label} »'
# How screen_text shows a piece of text in reverse video.
REVERSED = '«{text}»'


QUIET_VALUE = '.'
# The name the tests give a chromatic scale they add, to play every degree.
CHROMATIC_SCALE = 'all'

# Names the tests give to their own things, and other values they use.
ROLLS = 'rolls'
# A drift of the test song's, which only changes loudness, slightly, so that it changes no test's notes.
SWAY = 'sway'
THIN = 'thin'
POP = 'pop'
SMOOTH = 'smooth'
FOLK = 'folk'
CLAVE = 'clave'
SLIDES = 'slides'
CLIPS = 'clips'
PUSH = 'push'
LAZY = 'lazy'
TRADE = 'trade'
PICKED = 'picked'
FOLLOWS = 'follows'
BREATHES = 'breathes'
STRUMMER = 'strummer'
FADE = 'fade'
CLIPPED = 'clipped'
DRIFT_SOFTER = 'b_velocity'
TUNE = 'tune'
BEAT = 'beat'
OTHER = 'other'
LEAD = 'lead'
DRUMS = 'drums'
# The pattern groups of the test set: the tune's, which sorts first, and the beat's; the third pattern is in none, as an older file's are.
MELODIES = 'melodies'
RHYTHMS = 'rhythms'
UP_ARP = 'up'
NAMED = 'named'
EMPTY = 'empty'
EIGHTH = '1/8'
HALF = '1/2'
ONE = 'one'
TWO = 'two'
QUARTER = '1/4'
SIXTEENTH = '1/16'


def fixed_text(template):
    """Return the longest piece of a message template that isn't filled in, to look for on screen."""
    pieces = [literal for literal, _, _, _ in string.Formatter().parse(template)]
    return max(pieces, key=len)


def a_song(*, path=None):
    """Return a Document holding a set of one song with a few patterns, two tracks, a chain and two scenes."""
    data = new_setlist()
    song = data[Section.SONGS][names_text.MSG_DEFAULT_SONG_NAME]
    data[Section.AUTO_RATCHETS] = {ROLLS: {AutoRatchetSetting.COUNTS: [1, 4]}}
    data[Section.DRIFTS] = {SWAY: {DRIFT_SOFTER: -1}}
    # A shape generator of each kind, which no chain names, so that their pages have something to show.
    data[Section.PROGRESSIONS] = {POP: {ProgressionSetting.CHORDS: [1, 5, 6, 4]}}
    data[Section.VOICE_LEADINGS] = {SMOOTH: {}}
    data[Section.STRUMS] = {FOLK: {}}
    data[Section.EUCLIDS] = {CLAVE: {EuclidPart.HITS: 3, EuclidPart.STEPS: 8}}
    data[Section.GLIDES] = {SLIDES: {StepRowSetting.STEPS: [True, False, False]}}
    data[Section.SHORTENS] = {CLIPS: {StepRowSetting.STEPS: [False, True]}}
    data[Section.RUSHES] = {PUSH: {StepRowSetting.STEPS: [True, False, False, False]}}
    data[Section.DRAGS] = {LAZY: {StepRowSetting.STEPS: [False, True]}}
    data[Section.HOCKETS] = {TRADE: {HocketSetting.SOURCE: LEAD}}
    data[Section.GUITARIFIES] = {PICKED: {}}
    data[Section.FOLLOW_CHORDS] = {FOLLOWS: {FollowChordsSetting.CHORDS_FROM: LEAD}}
    data[Section.PHRASINGS] = {BREATHES: {}}
    data[Section.MUSICIANS] = {STRUMMER: {}}
    data[Section.DENSITIES] = {THIN: {ShapePart.START: 50}}
    data[Section.SWELLS] = {FADE: {ShapePart.START: 80}}
    data[Section.ARTICULATES] = {CLIPPED: {ShapePart.START: 50}}
    data[Section.PATTERNS] = {
        TUNE: {
            PatternSetting.GROUP: MELODIES, PatternSetting.STEPS: 4, PatternSetting.STEP_SIZE: EIGHTH, Row.DEGREE: [1, 3, None, None], Row.GATE: [QUARTER, QUARTER, EIGHTH, None],
            Row.OCTAVE: [5, 5, None, None],
        },
        BEAT: {PatternSetting.GROUP: RHYTHMS, PatternSetting.STEPS: 2, PatternSetting.STEP_SIZE: EIGHTH, PatternSetting.DRUM: True, Row.DEGREE: [NoteName.C, None], Row.GATE: [SIXTEENTH, None], Row.OCTAVE: [3, None]},
        OTHER: {PatternSetting.STEPS: 1, PatternSetting.STEP_SIZE: HALF, Row.DEGREE: [5]},
    }
    song[Section.TRACKS] = {LEAD: {}, DRUMS: {}}
    data[Section.ARPS] = {UP_ARP: {ArpSetting.STEP: EIGHTH, ArpSetting.ORDER: written_name(ChordOrder.UP)}}
    data[Section.CHAINS] = {NAMED: [{GeneratorKind.ARP: UP_ARP}, {GeneratorKind.AUTO_RATCHET: ROLLS}], EMPTY: []}
    song[Section.SCENES] = [
        {SceneSetting.NAME: ONE, SceneSetting.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: TUNE}, DRUMS: {ClipSlotSetting.PATTERN: BEAT, ClipSlotSetting.LOOP: True}}},
        {SceneSetting.NAME: TWO, SceneSetting.TRACKS: {}},
    ]
    return Document(setlist=Setlist.from_data(data=data), path=path)


# The page classes that exist to be subclassed, which no one opens.
BASE_PAGES = (Page, ListPage, FieldPage)
PACKAGE_DOT = '.'


def leaf_pages():
    """Return every page class in tui/screens that isn't there to be subclassed, which the rules about every page go through."""
    found = []
    for module_info in pkgutil.walk_packages(llamatron.tui.screens.__path__, prefix=llamatron.tui.screens.__name__ + PACKAGE_DOT):
        if module_info.ispkg:
            continue
        module = importlib.import_module(module_info.name)
        for _, member in inspect.getmembers(module, inspect.isclass):
            if issubclass(member, Page) and member.__module__ == module.__name__ and member not in found:
                found.append(member)
    return [page for page in found if page not in BASE_PAGES and not any(other is not page and issubclass(other, page) for other in found)]


# What Textual calls the keys whose own name is the mark they type.
# What a test is told when it presses a binding whose keys step one way or the other without saying which way, or names a key the binding doesn't have.
STEPS_NEED_A_WAY = 'the binding {binding} steps one way or the other: press back_key(binding) or forward_key(binding)'
NOT_A_KEY_OF = '{key} is not one of the keys of the binding {binding}'


def keys_stepping(*, binding, back):
    """Return the keys of a stepping binding that step one way: back, or forward."""
    keys = binding.keys
    assert isinstance(keys, Steps), binding
    return keys.back if back else keys.forward


def back_key(binding):
    """Return the key a test presses to step a binding of tui/keybindings.py back: the first of the keys that do, which is the one the legend names."""
    return keys_stepping(binding=binding, back=True)[0]


def forward_key(binding):
    """Return the key a test presses to step a binding of tui/keybindings.py forward: the first of the keys that do, which is the one the legend names."""
    return keys_stepping(binding=binding, back=False)[0]


def key_name(binding):
    """Return what the tracker calls a binding's keys on screen, in the legend and the F1 dialog."""
    return binding.name


def key_of(*, binding, key):
    """Return one named key of a binding, for a test of a key that isn't the binding's first: the older keys that still work, off the legend."""
    assert key in every_key(binding), NOT_A_KEY_OF.format(key=key, binding=binding)
    return key


def pressed(key):
    """Return the name of the key to press: a key's name as it is, or the first key of a binding of tui/keybindings.py, which says what the key does."""
    if isinstance(key, str):
        return key
    assert not isinstance(key.keys, Steps), STEPS_NEED_A_WAY.format(binding=key)
    return first_key(key)


# The header's two lines, as the screen's text numbers them.
TITLE_LINE = 0
CRUMBS_LINE = 0
SONG_LINE = 1


def screen_text(app):
    """Return what's on screen, with «» around anything in reverse video."""
    lines = []
    for strip in app.screen._compositor.render_strips():
        line = ''
        reverse = False
        for segment in strip:
            now = bool(segment.style and segment.style.reverse)
            if now != reverse:
                line += REVERSED[0] if now else REVERSED[-1]
                reverse = now
            line += segment.text
        lines.append(line + (REVERSED[-1] if reverse else ''))
    return '\n'.join(lines)


# What the typing helper says when a test types with nothing open to type into.
NOTHING_TAKES_TEXT = 'typing {text!r} would press the keys of {screen}, which takes no text'
# The most keys a walk to a named place may take, so that a walk that can never arrive fails rather than hangs.
MOST_MOVES = 400
MSG_NEVER_REACHED = 'the cursor never reached {target}'

class UITest(unittest.IsolatedAsyncioTestCase):
    """Runs the real program with no terminal, pressing keys."""

    SIZE = (100, 40)

    async def asyncSetUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(temporary.name)
        self.folder = temporary.name
        # FluidSynth counts as installed, whatever this computer has, so that opening an example, whose instruments play through it,
        # warns of nothing; tests/tui/test_tui_silent_instruments.py says otherwise where it tests the warning.
        installed = mock.patch(FLUIDSYNTH_INSTALLED, return_value=True)
        installed.start()
        self.addCleanup(installed.stop)
        # The transport and the pattern preview find FluidSynth installed too, so that Listen is offered the same on every computer.
        found = mock.patch(TRANSPORT_FINDS_FLUIDSYNTH, return_value=True)
        found.start()
        self.addCleanup(found.stop)
        # No test starts a real FluidSynth, which would load a SoundFont and open the Mac's audio: the tests of FluidSynth give the transport a stand-in.
        refused = mock.patch.object(FluidSynth, '_popen', side_effect=AssertionError(MSG_REAL_FLUIDSYNTH))
        refused.start()
        self.addCleanup(refused.stop)
        self.document = a_song()
        self.app = self.make_app()
        self.running = self.app.run_test(size=self.SIZE)
        self.pilot = await self.running.__aenter__()
        self.addAsyncCleanup(self.running.__aexit__, None, None, None)
        await self.pilot.pause()

    def make_app(self):
        """Return the tracker the test runs, on a_song() unless a test class starts the tracker another way. The temporary folder is already the working directory."""
        return LlamatronApp(document=self.document)

    async def press(self, *keys):
        # Pressing keys through the terminal driver takes a tenth of a second each, so these go
        # straight to the screen. TestRealKeys checks the same keys through the driver.
        for key in keys:
            self.app.screen.on_key(key_event(pressed(key)))
            await self.settle()

    async def open_patterns_on(self, name):
        """Open the Patterns page from the main screen and put its cursor on a pattern, wherever the pattern's group puts its row."""
        await self.press(keybindings.MainPage.PATTERNS)
        page = self.app.screen
        names = page.row_names()
        self.assertIn(name, names)
        while page.current() != name:
            await self.press(Key.UP if names.index(name) < page.cursor.get_place() else Key.DOWN)

    async def settle(self):
        """Let the tracker handle what a key sent, a dialog or a page opening, without waiting for the computer to go idle as pilot.pause() does,
        which took a fiftieth of a second a key, or far more with the suite's classes running side by side."""
        await self.pilot.pause(SETTLED)

    def press_at_once(self, key):
        """Press a key that only moves a page's cursor, without waiting for the event loop, which takes a thirtieth of a second a key.

        The page handles the key and draws before this returns, so drawn() is current, though
        text() is not until the next press(). A key that opens a page or a dialog needs press().
        """
        self.app.screen.on_key(key_event(pressed(key)))

    def drawn(self):
        """Return what the page on screen last drew, to compare before and after a key: two drawings are equal when their text and styles are."""
        return self.app.screen.query_one(page_values.VIEW_SELECTOR, Static).content

    async def type(self, text):
        """Type text into the prompt, the picker's search, the list's search or the description that is open, and fail when none is.

        Typing a name while a page is showing would press the page's keys, one per letter, and
        two tests once passed that way: the key that should have opened the prompt had stopped
        working, and the letter a of the name fast pressed the new add key.
        """
        self.assertTrue(self.app.screen.takes_text(), NOTHING_TAKES_TEXT.format(text=text, screen=type(self.app.screen).__name__))
        await self.press(*[{' ': Key.SPACE}.get(letter, letter) for letter in text])

    def empty_the_arrangement(self):
        """Delete every scene and then every track, through the document, as a page would."""
        for index in reversed(range(len(self.document.song().get_scenes()))):
            self.document.change(self.document.song().remove_scene, index)
        for name in self.document.song().get_track_names():
            self.document.delete_named(section=Section.TRACKS, name=name)

    def track(self, name):
        return self.document.song().get_track(name)

    def arp(self, name):
        return self.document.song().get_generator_settings(kind=GeneratorKind.ARP, name=name)

    def auto_ratchet(self, name):
        return self.document.song().get_generator_settings(kind=GeneratorKind.AUTO_RATCHET, name=name)

    def chain_steps(self, name):
        return self.document.song().get_chain(name).get_steps()

    def root_and_kind(self, name):
        """Return a named scale's root and type as the file writes them."""
        scale = self.document.song().get_named_scale(name)
        return scale.get_root(), scale.get_kind()

    def add_pattern_with_rows(self, *, name, steps, rows):
        """Add a pattern through the document and fill its rows, given as {row: [value per step]}."""
        self.document.add_pattern(name=name, steps=steps)
        for row, values in rows.items():
            for step, value in enumerate(values):
                self.document.change(self.document.setlist().get_pattern(name).set_value, row=row, step=step, value=value)

    def delete_every_generator(self):
        """Delete every arp and AutoRatchet, which the chains must have stopped using first."""
        song = self.document.song()
        for kind, section in file_format.NAMED_GENERATORS.items():
            for name in song.get_generator_names(kind):
                self.document.delete_named(section=section, name=name)

    def text(self):
        return screen_text(self.app)

    def title_line(self):
        """Return the header's first line: the crumbs, llamatron centred, the open set and the save mark."""
        return self.text().splitlines()[TITLE_LINE]

    def song_line(self):
        """Return the header's second line: the current song and the song's length, at the right."""
        return self.text().splitlines()[SONG_LINE]

    def assert_header(self, *, set_crumb, song_crumb):
        """Check the header's right side: the set on the first line and the song on the second, one block starting in one column, left of the save mark and the length."""
        first = self.title_line()
        second = self.song_line()
        self.assertIn(set_crumb, first)
        self.assertIn(song_crumb, second)
        self.assertEqual(first.index(set_crumb), second.index(song_crumb))

    def assert_title(self, *, set_crumb):
        """Check the set is named on the header's first line, with llamatron centred when there's room for it."""
        line = self.title_line()
        self.assertIn(set_crumb, line)
        if page_values.PROGRAM_NAME in line:
            self.assertEqual(line.index(page_values.PROGRAM_NAME), (len(line) - len(page_values.PROGRAM_NAME)) // 2)

    def crumbs_line(self):
        """Return the header's line with the crumbs, which say where the page was reached from, in its left corner: the first."""
        return self.text().splitlines()[CRUMBS_LINE]

    def assert_buttons_come_last_after_a_blank_line(self):
        """Check a settings page's buttons are its last fields, drawn below the settings shown with one blank line between."""
        fields = self.app.screen.shown_fields()
        buttons = [field for field in fields if isinstance(field, Button)]
        self.assertTrue(buttons)
        self.assertEqual(fields[-len(buttons):], buttons)
        # They sit in one row of boxes, the row's middle line naming each, a box's top line between it and the blank line.
        lines = self.text().splitlines()
        row = next(index for index, line in enumerate(lines) if buttons[0].label in line)
        for button in buttons:
            self.assertIn(button.label, lines[row])
        self.assertEqual(lines[row - 2].strip(), drawing.NOTHING)
        self.assertIn(fields[-len(buttons) - 1].label, lines[row - 3])

    async def reconfigure(self, choice):
        """Open the pattern editor's Reconfigure dialog and pick one of its actions, by its place in the editor's Reconfigure class."""
        await self.press(keybindings.PatternEditor.RECONFIGURE)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        await self.press(*[Key.DOWN] * choice, Key.ENTER)

    async def pick_entry_size(self, size):
        """On the piano roll, open the entry size picker with its key and choose a size by what the picker calls it."""
        await self.press(keybindings.PianoRoll.ENTRY_SIZE)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        await self.pick(size)

    async def open_generator(self, *, section, name=None):
        """Open a generator's editor from the Generators page, where each is under its type's heading: the one named, or the first of its section's kind."""
        await self.press(keybindings.MainPage.GENERATORS)
        kind = generator_pages.GENERATOR_PAGES[section].kind
        found_kind, found_name = next(pair for pair in self.app.screen.generators() if pair[0] == kind and (name is None or pair[1] == name))
        self.app.screen.put_cursor_on(kind=found_kind, name=found_name)
        await self.press(Key.ENTER)

    async def add_generator(self, section):
        """Add a generator of a section's kind from the Generators page, which names it and opens its editor, and return its name."""
        await self.press(keybindings.MainPage.GENERATORS, keybindings.GeneratorsPage.ADD)
        await self.pick(generator_pages.GENERATOR_PAGES[section].label)
        return self.app.screen.item

    async def pick(self, option):
        """Choose an option from the open picker by what it says, however the picker orders its list."""
        dialog = self.app.screen
        self.assertIn(option, dialog.options)
        if isinstance(dialog, GroupedChoiceDialog):
            # Its choices lie under headings closed until opened, so the option is searched for by its name, which finds it whatever is open.
            await self.type(option)
            self.assertEqual(dialog.options[dialog.cursor.get_place()], option)
            await self.press(Key.ENTER)
            return
        await UITest.go_to(self, option)
        await self.press(Key.ENTER)

    async def go_to(self, target):
        """Move the screen's cursor to what is named: a field or a button by its label, a list's row by what it lists, a picker's option by what it says.

        The screen says which key leads there (key_toward), so a test names where it wants to be and
        never counts presses, and a page that gains a field or a row breaks no test that does not care.
        """
        for _ in range(MOST_MOVES):
            key = self.app.screen.key_toward(target)
            if key is None:
                return
            await self.press(key)
        self.fail(MSG_NEVER_REACHED.format(target=target))

    async def go_to_clip(self, *, scene, track):
        """Move Arrange's cursor to the clip a track plays in a scene, the scene named or counted from 0."""
        await UITest.go_to(self, ArrangePlace(scene=self.scene_place(scene), track=track))

    async def go_to_scene(self, scene):
        """Move Arrange's cursor to a scene's name, the scene named or counted from 0."""
        await UITest.go_to(self, ArrangePlace(scene=self.scene_place(scene)))

    async def go_to_track(self, track):
        """Move Arrange's cursor to a track's name in the header."""
        await UITest.go_to(self, ArrangePlace(track=track))

    def scene_place(self, scene):
        """Return a scene's place in the current song, given its name or its place."""
        if isinstance(scene, int):
            return scene
        return [each.get_name() for each in self.app.screen.document().song().get_scenes()].index(scene)

    async def go_to_panel(self, name):
        """Move the song wizard's tree cursor to the wizard panel of a name."""
        wizard = self.app.screen
        for _ in range(MOST_MOVES):
            key = wizard.key_toward_panel(name)
            if key is None:
                return
            await self.press(key)
        self.fail(MSG_NEVER_REACHED.format(target=name))

    def assert_cursor_on(self, target):
        """Check that the screen's cursor is on what is named, as go_to() names it."""
        self.assertEqual(self.app.screen.under_cursor(), target)

    async def select_field(self, label):
        """Move a settings page's cursor to the field with this label, wherever the page puts it, opening its section first where that is closed."""
        await UITest.go_to(self, label)

