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

"""Every key a page's help names is bound on that page, so that help can't go on naming a key that moved.

On 2026-11-09 the keys that add, move and adjust changed, and the help of several pages still named
the old ones until each was read by hand. This reads every page's help for the keys it names and
tours the tracker, noting which keys each page binds wherever its cursor can go.

A key in a help text is: a key's name (Enter, Esc, Tab, Bksp, Space, Ctrl+S, F1, Home, PgUp and
the capitalised arrows Up, Down, Left and Right); a capital letter standing alone, where A and I
count only before a verb, like "A adds" and "I inserts", since "A name can be anything" is not a
key; and a mark standing alone between spaces, like [ or /. A capital that is a note's name, as in
"middle C", is listed in NOTE_PHRASES, and the marks the Arrange grid draws in LEGEND_MARKS.

Where a page takes typed text, in a list's search and the Description page's text, every
character is bound, so only the named keys bound there count: otherwise any letter would pass.
"""

import inspect
import re
import unittest

from llamatron.tui.screens.arrange_page import FIRST_TRACK_COLUMN, HEADER_ROW, SCENE_COLUMN
from key_map import KeyMap, should_write, write_key_map, written_key_map
from llamatron.tui.keys import Key
from llamatron.tui.screens.notes_page import NotesPage
from llamatron.tui.screens.file_page import FilePage
from llamatron.tui.screens.list_page import ListPage
from llamatron.tui.screens.main_page import MainPage
from llamatron.tui.components.pattern_rows import SECTIONS
from llamatron.tui.screens.pattern_editor import PatternEditor
from llamatron.tui.screens.song_page import SongPage
from llamatron.tui.screens.songs_page import SongsPage
from llamatron.strings.help import HELP_NONE
from llamatron.strings.labels import MSG_CHORDS_LABEL, MSG_STEPS_LABEL, MSG_CHAINS_LABEL, MSG_NOTES_LABEL, MSG_OFFSETS_LABEL
from llamatron.strings.legends import KeyName
from llamatron.tui import keybindings
from llamatron.tui.key_table import first_key
from ui_testing import leaf_pages, UITest
from llamatron.composition.file_format import Section

# The words help uses for the keys whose names on screen are arrows or that the legend has no name of their own for.
# The place on the Generators page of the first kind after the arpeggiators and the AutoRatchets.
FIRST_KIND_AFTER_AUTO_RATCHETS = 2
FIRST_SCENE = 0
EVERYWHERE_ENTRY = '- `{key}` {what}'
KEY_WORDS = {'Shift+Tab': Key.SHIFT_TAB, 'Up': Key.UP, 'Down': Key.DOWN, 'Left': Key.LEFT, 'Right': Key.RIGHT, 'Home': Key.HOME, 'End': Key.END, 'PgUp': Key.PAGE_UP, 'PgDn': Key.PAGE_DOWN}


def named_keys():
    """Return each key that has a name of more than one plain letter on screen, like Tab, Bksp and Ctrl+S, by that name: the keys that Key and KeyName call the same."""
    names = {name: shown for name, shown in vars(KeyName).items() if name.isupper() and hasattr(Key, name)}
    return {shown: getattr(Key, name) for name, shown in names.items() if len(shown) > 1 and shown.isascii()}


# Every name help can call a key by, and the key: the names the legend shows, then the words above.
KEYS_BY_NAME = {**named_keys(), **KEY_WORDS}
# A key's name standing as a word of its own, the longest names tried first so that Shift+Tab is not read as Tab.
NAMED_KEY = re.compile(r'(?<![\w+])(' + '|'.join(re.escape(name) for name in sorted(KEYS_BY_NAME, key=len, reverse=True)) + r')(?![\w+])')
# A capital letter standing alone, with the word after it, and a mark standing alone between spaces.
LETTER_KEY = re.compile(r"(?<![\w'+/])([A-Z])(?![\w'+/])(?:\s+(\w+))?")
MARK_KEY = re.compile(r'(?<!\S)([^\w\s])(?!\S)')
# The capitals that are also words, which are keys only before a verb, and how a verb ends there: "A adds", "I inserts".
WORD_LETTERS = ('A', 'I')
VERB_ENDING = 's'
# Where a capital letter is a note's name and not a key.
NOTE_PHRASES = ('middle C', 'C major', 'C Major')
# Marks the Arrange grid draws on a clip, which its help explains: a looping clip and a morph.
LEGEND_MARKS = ('∞', '~')
BLANK = ' '
# Keys a page's help names that work on another page, which the help says: Song's help says N renames on the Songs page,
# File's that Tab reaches the buttons of the Notes page it opens, and the main screen's that Esc goes back, which it does on every other page.
ELSEWHERE = {
    (SongPage, first_key(keybindings.SongsPage.RENAME)): SongsPage,
    (FilePage, Key.TAB): NotesPage,
    (MainPage, Key.ESCAPE): SongsPage,
}
# The most presses a walk makes in one direction before giving up on reaching an edge.
MAX_WALK = 90
MSG_NOT_BOUND = "{page}'s help names {key!r}, which {where} never binds"
MSG_NOT_TOURED = 'the tour in test_tui_help_keys.py never opens {page}'
MSG_STRAY_BINDING = '{page} binds {binding}, which is not a binding of keybindings.{owner}'
MSG_KEY_CLASH = '{page}: {key!r} is bound to {first!r} and to {second!r} at once'
# Help texts of the test's own, and the keys each names.
HELP_WITH_AN_ARTICLE = 'A name can be anything. A adds one, I inserts a step and C copies it.'
HELP_WITH_NAMED_KEYS = 'Shift+Tab goes back, Ctrl+S saves, and Up and down select. Space or Enter toggles; PgUp/PgDn jump.'
HELP_WITH_A_NOTE = 'Middle is where middle C is, and A adds a C major scale.'
HELP_WITH_MARKS = '[ and ] drag its end, late (+) or early (-), and ~ means a morph.'


def named_keys(text):
    """Return the keys a help text names by name, and the text with those names blanked so that the S of Ctrl+S is not read as a letter."""
    names = {KEYS_BY_NAME[name] for name in NAMED_KEY.findall(text)}
    return names, NAMED_KEY.sub(BLANK, text)


def is_letter_key(*, letter, next_word):
    """Return whether a capital standing alone is a key: always, except A and I, which are keys only before a verb."""
    if letter not in WORD_LETTERS:
        return True
    return bool(next_word) and next_word.endswith(VERB_ENDING)


def letter_keys(text):
    for phrase in NOTE_PHRASES:
        text = text.replace(phrase, BLANK)
    return {letter.lower() for letter, next_word in LETTER_KEY.findall(text) if is_letter_key(letter=letter, next_word=next_word)}


def mark_keys(text):
    """Return the marks standing alone between spaces, which are keys unless the grid draws them, like the ~ of a morph."""
    return {mark for mark in MARK_KEY.findall(text) if mark not in LEGEND_MARKS}


def keys_named(text):
    """Return every key a help text names."""
    names, rest = named_keys(text)
    return names | letter_keys(rest) | mark_keys(text)


def vars_of(kind):
    """Return everything a class of tui/keybindings.py holds, its own and what it inherits."""
    return [value for _, value in inspect.getmembers(kind)]


class TestKeysNamedInHelp(unittest.TestCase):
    """How a help text is read for its keys."""

    def test_a_and_i_are_keys_only_before_a_verb(self):
        self.assertEqual(keys_named(HELP_WITH_AN_ARTICLE), {Key.A, Key.I, Key.C})

    def test_key_names_are_read_whole(self):
        expected = {Key.SHIFT_TAB, Key.CTRL_S, Key.UP, Key.SPACE, Key.ENTER, Key.PAGE_UP, Key.PAGE_DOWN}
        self.assertEqual(keys_named(HELP_WITH_NAMED_KEYS), expected)

    def test_a_note_name_is_not_a_key(self):
        self.assertEqual(keys_named(HELP_WITH_A_NOTE), {Key.A})

    def test_a_mark_is_a_key_when_it_stands_alone_and_the_grid_does_not_draw_it(self):
        self.assertEqual(keys_named(HELP_WITH_MARKS), {Key.LEFT_BRACKET, Key.RIGHT_BRACKET})


class KeyTour(UITest):
    """Tours every page, noting the keys bound wherever the cursor can go. Each check of the tour is a class of its own, so that the two tours run side by side."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.bound = {}
        self.strays = set()
        self.clashes = set()
        self.key_map = KeyMap()

    def note_rules(self, page):
        """Remember every binding here that isn't one of the class it was bound for, and every key that two bindings have at once."""
        seen = {}
        for item in page.key_table():
            if not any(value is item.binding for value in vars_of(item.owner)):
                self.strays.add(MSG_STRAY_BINDING.format(page=type(page).__name__, owner=item.owner.__name__, binding=item.binding))
            for name in item.keys:
                if name in seen:
                    self.clashes.add(MSG_KEY_CLASH.format(page=type(page).__name__, key=name, first=seen[name], second=item.what))
                seen[name] = item.what

    def note(self):
        """Remember the keys the page on screen binds where its cursor is now."""
        page = self.app.screen
        self.note_rules(page)
        self.key_map.note(page)
        names = {name for item in page.key_table() for name in item.keys}
        # Where text is typed every character is bound, so only the named keys there count.
        if page.takes_text():
            names = {name for name in names if len(name) > 1}
        self.bound.setdefault(type(page), set()).update(names)

    def moves_a_cursor(self, name):
        """Return whether an arrow moves a cursor here: an arrow that steps a value or scrolls is left alone, so that the walk changes nothing."""
        return any(name in item.keys and item.wants_key for item in self.app.screen.key_table())

    async def go(self, name):
        """Press an arrow that moves a cursor here, and return whether anything moved."""
        if not self.moves_a_cursor(name):
            return False
        before = self.drawn()
        self.press_at_once(name)
        return self.drawn() != before

    async def go_to_the_edge(self, name):
        for _ in range(MAX_WALK):
            if not await self.go(name):
                return

    async def walk(self):
        """Note the keys at every place the page's cursor reaches: each row from the top, and along each row."""
        page = self.app.screen
        await self.go_to_the_edge(Key.UP)
        await self.go_to_the_edge(Key.LEFT)
        for _ in range(MAX_WALK):
            self.note()
            for _ in range(MAX_WALK):
                if not await self.go(Key.RIGHT):
                    break
                self.note()
            await self.go_to_the_edge(Key.LEFT)
            if not await self.go(Key.DOWN):
                break
        if isinstance(page, ListPage) and any(item.binding is keybindings.ListPage.SEARCH for item in page.key_table()):
            await self.press(keybindings.ListPage.SEARCH)
            self.note()
            await self.press(Key.ESCAPE)
        # The walk pressed without waiting, so let the screen catch up before the tour goes on.
        await self.pilot.pause()
        self.assertIs(self.app.screen, page)

    async def open_every_section(self):
        """Open each section of the pattern editor's rows, so that the walk reaches every row."""
        for _ in SECTIONS:
            await self.press(Key.PAGE_DOWN)
            opened = len(self.app.open_sections)
            await self.press(Key.SPACE)
            if len(self.app.open_sections) < opened:
                await self.press(Key.SPACE)

    async def tour(self):
        """Open every page, each walked on the way back out, so that a walk never leaves the cursor where the next key needs it."""
        await self.press(keybindings.MainPage.FILE)
        await self.select_field(MSG_NOTES_LABEL)
        await self.press(Key.ENTER)
        await self.walk()
        await self.press(Key.TAB)
        self.note()
        await self.press(Key.ESCAPE)
        await self.walk()
        await self.press(Key.ESCAPE)
        await self.walk()
        await self.press(keybindings.FilePage.OPEN_SET)
        await self.walk()
        await self.press(Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.SONGS, Key.ENTER)
        await self.walk()
        await self.press(Key.ESCAPE)
        await self.walk()
        await self.press(Key.ESCAPE, keybindings.MainPage.PATTERNS, Key.ENTER)
        self.assertIsInstance(self.app.screen, PatternEditor)
        await self.walk()
        await self.press(keybindings.PatternEditor.TO_EDITOR)
        await self.open_every_section()
        await self.walk()
        await self.press(Key.ESCAPE)
        await self.walk()
        await self.press(Key.ESCAPE, keybindings.MainPage.CHAINS, Key.ENTER)
        await self.walk()
        await self.press(Key.ESCAPE)
        await self.walk()
        # The Generators page lists every generator, each opening its editor; an arp's Offsets field opens the offsets editor.
        await self.press(Key.ESCAPE, keybindings.MainPage.GENERATORS)
        await self.walk()
        for place in range(len(self.app.screen.generators())):
            await self.press(Key.ESCAPE, keybindings.MainPage.GENERATORS, *[Key.DOWN] * place, Key.ENTER)
            await self.walk()
            await self.press(Key.ESCAPE)
        await self.press(Key.ESCAPE)
        await self.open_generator(section=Section.ARPS)
        await self.select_field(MSG_OFFSETS_LABEL)
        await self.press(Key.ENTER)
        await self.walk()
        await self.press(Key.ESCAPE, Key.ESCAPE, Key.ESCAPE)
        # A Glide's, a Shorten's, a Rush's and a Drag's Steps field opens its steps page.
        for section in (Section.GLIDES, Section.SHORTENS, Section.RUSHES, Section.DRAGS):
            await self.open_generator(section=section)
            await self.select_field(MSG_STEPS_LABEL)
            await self.press(Key.ENTER)
            await self.walk()
            await self.press(Key.ESCAPE, Key.ESCAPE, Key.ESCAPE)
        # A progression's Chords field opens the chord editor.
        await self.open_generator(section=Section.PROGRESSIONS)
        await self.select_field(MSG_CHORDS_LABEL)
        await self.press(Key.ENTER)
        await self.walk()
        await self.press(Key.ESCAPE, Key.ESCAPE, Key.ESCAPE)
        await self.press(Key.ESCAPE, keybindings.MainPage.SCALES, Key.ENTER)
        await self.walk()
        await self.press(Key.ESCAPE)
        await self.walk()
        # A groove of the set's own can be edited, which a factory groove can't.
        await self.press(Key.ESCAPE, keybindings.MainPage.GROOVES, keybindings.GroovesPage.ADD)
        await self.walk()
        await self.press(Key.ESCAPE)
        await self.walk()
        await self.press(Key.ESCAPE, keybindings.MainPage.INSTRUMENTS, keybindings.InstrumentsPage.ADD)
        await self.walk()
        await self.press(Key.ESCAPE)
        await self.walk()
        await self.press(Key.ESCAPE, keybindings.MainPage.REGISTERS)
        await self.walk()
        # Arrange opens on the first scene's name, with the corner above it, since the instrument added above turned Real Time on, and the first track's name to the corner's right.
        await self.press(Key.ESCAPE, keybindings.MainPage.ARRANGE, Key.UP, Key.RIGHT, Key.ENTER)
        await self.walk()
        # The track editor's Chains field opens the list of its chains, given one so that its keys show.
        await self.select_field(MSG_CHAINS_LABEL)
        await self.press(Key.ENTER, keybindings.ChainListPage.ADD, Key.ENTER)
        await self.walk()
        await self.press(Key.ESCAPE)
        await self.press(Key.ESCAPE, Key.DOWN, Key.ENTER)
        await self.walk()
        await self.press(Key.ESCAPE, Key.LEFT, Key.ENTER)
        await self.walk()
        # A copied clip is what gives a clip its paste key.
        await self.press(Key.ESCAPE, Key.RIGHT, keybindings.ArrangePage.COPY_CLIP)
        await self.walk()
        # Arrange's details view, and Tab inside the first track's name, which shows the chain the track editor gave it above.
        await self.press(keybindings.ArrangePage.SHOW_DETAILS)
        await self.walk()
        self.app.screen.row = HEADER_ROW
        self.app.screen.column = FIRST_TRACK_COLUMN
        await self.press(keybindings.ArrangePage.INTO_DETAILS)
        self.note()
        await self.press(keybindings.ArrangePage.OUT_OF_DETAILS, keybindings.ArrangePage.HIDE_DETAILS)
        # Move mode on a track, a scene and a clip, and Scene View on the scene.
        await self.press(keybindings.ArrangePage.MOVE_TRACK)
        self.note()
        await self.press(Key.ENTER)
        self.app.screen.row = FIRST_SCENE
        self.app.screen.column = SCENE_COLUMN
        await self.press(keybindings.ArrangePage.MOVE_SCENE)
        self.note()
        await self.press(Key.ENTER, keybindings.ArrangePage.SCENE_VIEW)
        self.note()
        await self.press(keybindings.ArrangePage.CLOSE_INSET)
        self.app.screen.column = FIRST_TRACK_COLUMN
        await self.press(keybindings.ArrangePage.MOVE_CLIP)
        self.note()
        await self.press(Key.ENTER)
        await self.press(Key.ESCAPE)
        await self.walk()


class TestBoundKeysAreTheirClassesAndDistinct(KeyTour):

    async def test_every_bound_key_is_one_of_its_class_and_no_key_does_two_things_in_one_place(self):
        """A page binds only the bindings of its own class in tui/keybindings.py, and where the cursor is, a key reaches one binding, so that the first to be listed never hides another."""
        await self.tour()
        self.assertEqual(sorted(self.strays), [])
        self.assertEqual(sorted(self.clashes), [])


class TestHelpNamesOnlyBoundKeys(KeyTour):
    """Checks each page's help against the keys the tour found bound on it."""

    async def test_every_key_a_pages_help_names_is_bound_on_that_page(self):
        await self.tour()
        for page in leaf_pages():
            if page.HELP == HELP_NONE:
                continue
            with self.subTest(page=page.__name__):
                self.assertIn(page, self.bound, MSG_NOT_TOURED.format(page=page.__name__))
            for name in sorted(keys_named(page.HELP)):
                where = ELSEWHERE.get((page, name), page)
                with self.subTest(page=page.__name__, key=name):
                    self.assertIn(name, self.bound.get(where, ()), MSG_NOT_BOUND.format(page=page.__name__, key=name, where=where.__name__))


class TestKeyMapIsCurrent(KeyTour):
    """.claude/KEYMAP.md says what the tour finds, the user's ask, so that a question about a key is one lookup; internal_tools/key_map.sh rewrites it."""

    async def test_the_key_map_says_what_the_tour_finds(self):
        await self.tour()
        everywhere = '\n'.join(EVERYWHERE_ENTRY.format(key=binding[1], what=binding[2]) for binding in keybindings.Page.EVERYWHERE)
        text = self.key_map.text(everywhere=everywhere)
        if should_write():
            write_key_map(text)
        self.assertEqual(written_key_map(), text, 'run internal_tools/key_map.sh')
