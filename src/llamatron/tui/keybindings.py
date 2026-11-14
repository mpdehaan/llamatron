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
"""Every key binding of the tracker in one place: one class for each page, dialog and component, named after it.

A binding is a tuple of three things: the key or keys (from tui/keys.py, a `Steps` for keys that
step something one way or the other), the name the legend shows for them (a `KeyName` from
strings/legends.py), and what they are said to do (a `What` or a `MSG_..._WHAT` from the same
module). A class here has the same name as the page, dialog or component that binds its keys, and
inherits as that class does, so that a list page's keys are the same on every list page unless
one says otherwise. To change a key, change it here, and nothing else needs to know.

Each class has two lists. `IN_HELP` is every binding of the class, in the order the F1 dialog
lists them, which is also the order of the legend. `IN_LEGEND` is the bindings the legend at the
bottom of the page shows: a binding left out of it still works and is listed by F1. Where one key
means different things as the cursor moves, each meaning is a binding of its own, and the page
binds the one that applies. A page made of parts, like the pattern editor with its two views and
their rows, lists its parts' keys one part after another, each part in its own class's order.

A page binds a key with `self.bind(self.KEYS.RENAME, action=self.rename)`, and the tests press
`keybindings.PatternsPage.RENAME`. `internal_tools/keys.sh` prints every class's bindings, and every use of
one key.
"""

from llamatron.strings.labels import PageName
from llamatron.strings.legends import (
    MSG_PICK_PROGRESSION_WHAT,
    MSG_PICK_RHYTHM_WHAT,
    KeyName, What, MSG_ABOUT_FOOTER_WHAT, MSG_ACCIDENTAL_WHAT, MSG_ADD_CLIP_WHAT, MSG_ADD_SCENE_WHAT, MSG_ADD_TRACK_WHAT, MSG_CELL_LENGTH_WHAT,
    MSG_CHORD_WHAT, MSG_NEXT_LIST_WHAT, MSG_CLOSE_SECTION_WHAT, MSG_COPY_CLIP_WHAT, MSG_COPY_SCENE_WHAT, MSG_COPY_TRACK_WHAT, MSG_DEGREE_WHAT, MSG_DELETE_CLIP_WHAT,
    MSG_DELETE_SCENE_WHAT, MSG_DELETE_TRACK_WHAT, MSG_EDIT_CLIP_WHAT, MSG_IMPORT_WHAT, MSG_PRESS_WHAT, MSG_OPEN_PATTERN_WHAT, MSG_SHRINK_WHAT, MSG_STRETCH_WHAT, MSG_ENTRY_SIZE_WHAT, MSG_GRAB_WHAT, MSG_HELP_FOOTER_WHAT, MSG_INSERT_SCENE_WHAT,
    MSG_INSERT_TRACK_WHAT, MSG_MAKE_CURRENT_WHAT, MSG_ADD_CHAIN_WHAT, MSG_BLANK_PATTERN_WHAT, MSG_REMOVE_CHAIN_WHAT, MSG_MOVE_CLIP_WHAT, MSG_QUIT_WITHOUT_SAVING_WHAT, MSG_SAVE_THEN_QUIT_WHAT, MSG_MOVE_SCENE_WHAT, MSG_MOVE_TRACK_WHAT, MSG_NEW_LINE_WHAT, MSG_NEW_WHAT,
    MSG_NEXT_SECTION_WHAT, MSG_NOTE_WHAT, MSG_ONE_STEP_WHAT, MSG_OPEN_SECTION_WHAT, MSG_PASTE_CLIP_WHAT, MSG_PLACE_NOTE_WHAT, MSG_PLAY_WHAT, MSG_PLAY_CLIP_WHAT, MSG_PLAY_SCENE_WHAT, MSG_PLAY_SONG_WHAT, MSG_STOP_WHAT, MSG_STOP_CLIP_WHAT, MSG_LISTEN_WHAT, MSG_STOP_LISTENING_WHAT,
    MSG_RECONFIGURE_WHAT, MSG_SAVE_AS_WHAT, MSG_SCENE_SETTINGS_WHAT, MSG_A_OR_B_WHAT, MSG_NEXT_ROW_WHAT, MSG_SILENT_WHAT, MSG_SIZE_WHAT, MSG_SPLIT_WHAT, MSG_TO_BUTTONS_WHAT,
    MSG_TO_CLIPS_WHAT, MSG_TO_EDITOR_WHAT, MSG_TO_ROLL_WHAT, MSG_TO_TEXT_WHAT, MSG_TRACK_SETTINGS_WHAT, MSG_TYPE_OCTAVE_WHAT, MSG_VIEW_WHAT, MSG_VISUALIZER_WHAT, MSG_STEP_VISUALIZER_WHAT, MSG_SHOW_DETAILS_WHAT, MSG_HIDE_DETAILS_WHAT, MSG_INTO_DETAILS_WHAT, MSG_OUT_OF_DETAILS_WHAT, MSG_OPEN_DETAIL_WHAT, MSG_CLOSE_DETAILS_WHAT, MSG_LEAVE_CELL_WHAT, MSG_SCENE_VIEW_WHAT, MSG_CLOSE_INSET_WHAT, MSG_TO_PLAYED_WHAT, MSG_TO_WRITTEN_WHAT, MSG_CLOSE_INSET_ESC_WHAT, MSG_ZOOM_WHAT, MSG_SCROLL_SIDEBAR_WHAT, MSG_JUMP_BAR_WHAT,
)
from llamatron.tui.keys import (
    ARROWS, ARROWS_LEFT_RIGHT, ARROWS_UP_DOWN, CANCEL_KEYS, MOVE_DROP_KEYS, DIGITS, LESS_KEYS, MORE_KEYS, NOTE_LETTER_KEYS, NUDGE_LESS_KEYS,
    NUDGE_MORE_KEYS, SEARCH_CHARACTERS, TOGGLE_KEYS, Key, Steps,
)


def all_but(*, bindings, hidden):
    """Return the bindings of a list without the hidden ones, for a legend that leaves some of its class's keys to the F1 dialog."""
    return [binding for binding in bindings if binding not in hidden]


# The pages.

class Page:
    """What every page has: the keys that work everywhere, which the F1 dialog lists first, and Esc, which goes back."""

    SAVE = (Key.CTRL_S, KeyName.CTRL_S, What.SAVE)
    OPEN_SET = (Key.CTRL_O, KeyName.CTRL_O, What.OPEN_SET)
    EXPORT = (Key.CTRL_X, KeyName.CTRL_X, What.EXPORT)
    UNDO = (Key.CTRL_Z, KeyName.CTRL_Z, What.UNDO)
    REDO = (Key.CTRL_Y, KeyName.CTRL_Y, What.REDO)
    # The emergency stop, the user's design of 2026-11-09: note offs, all notes off and all sound off on every channel the instruments use, whatever is known to be playing.
    SILENCE = (Key.CTRL_T, KeyName.CTRL_T, What.SILENCE)
    # Quits at once, from any page, closing FluidSynth and the MIDI sender as quitting does, the user's ask, as Ctrl+C stops a program in a terminal.
    QUIT_NOW = (Key.CTRL_C, KeyName.CTRL_C, What.QUIT_NOW)
    HELP = (Key.F1, KeyName.F1, What.HELP)
    # About is F3, so that F2 renames as on Windows, the user's choice.
    ABOUT = (Key.F3, KeyName.F3, What.ABOUT)
    BACK = (Key.ESCAPE, KeyName.ESCAPE, What.BACK)
    # The keys every page has, in the order the F1 dialog lists them. Ctrl+S is Save because a plain
    # letter would be typed into names, and Cmd+S never reaches a terminal program. Open is Ctrl+O,
    # Export is Ctrl+X, Help is F1 and About is F2 for the same reason, as the user decided on
    # 2026-11-07: everything global has a key that no page could want for itself, so that a page's
    # plain letters are its own and free to change. Undo is Ctrl+Z and redo Ctrl+Y, the pair most
    # people's hands already know, which Textual delivers as keys rather than letting the terminal
    # suspend the program. None of them is in a page's legend, which shows only the page's own
    # keys, because with them there the pattern editor's legend took five lines at 80 columns and
    # pushed the step's description off the screen; the F1 dialog shows them all. On a Mac, F1 and
    # F2 need Fn unless the function keys are set to standard keys.
    # Silence sits before Undo, so that the F1 dialog's two columns of the keys besides F1 keep Undo above Redo.
    EVERYWHERE = [SAVE, OPEN_SET, EXPORT, SILENCE, UNDO, REDO, HELP, ABOUT, QUIT_NOW]
    IN_HELP = [BACK]
    IN_LEGEND = [BACK]


class MainPage(Page):
    """The main screen: a letter opens each page, the arrows and Enter do the same, and Q quits, here alone."""

    FILE = (Key.F, KeyName.F, PageName.FILE)
    SONGS = (Key.S, KeyName.S, PageName.SONGS)
    PATTERNS = (Key.P, KeyName.P, PageName.PATTERNS)
    CHAINS = (Key.C, KeyName.C, PageName.CHAINS)
    GENERATORS = (Key.G, KeyName.G, PageName.GENERATORS)
    SCALES = (Key.Z, KeyName.Z, PageName.SCALES)
    GROOVES = (Key.V, KeyName.V, PageName.GROOVES)
    INSTRUMENTS = (Key.I, KeyName.I, PageName.INSTRUMENTS)
    REGISTERS = (Key.R, KeyName.R, PageName.REGISTERS)
    ARRANGE = (Key.A, KeyName.A, PageName.ARRANGE)
    # The Real Time switch, a cell among the pages that turns real-time playback on and off (the user's design of 2026-11-09).
    REAL_TIME = (Key.T, KeyName.T, PageName.REAL_TIME)
    # The Open and Export cells take a plain letter here, to save a keystroke, since the main screen's letters are its own
    # (the user's choice of 2026-11-09). Ctrl+O and Ctrl+X still work, here as everywhere. Save stays Ctrl+S, since S is Songs.
    OPEN_SET_HERE = (Key.O, KeyName.O, What.OPEN_SET)
    EXPORT_HERE = (Key.X, KeyName.X, What.EXPORT)
    # Import MIDI, in the row of actions after Export (the user's design of 2026-11-10).
    IMPORT_HERE = (Key.M, KeyName.M, What.IMPORT_MIDI)
    QUIT = (Key.Q, KeyName.Q, What.QUIT)
    SELECT = (ARROWS, KeyName.ARROWS, What.SELECT)
    OPEN = (Key.ENTER, KeyName.ENTER, What.OPEN)
    # Help and About work everywhere and have no cell, so the main screen's legend reminds of them, in lower case.
    FOOTER_HELP = (Key.F1, KeyName.F1, MSG_HELP_FOOTER_WHAT)
    FOOTER_ABOUT = (Key.F3, KeyName.F3, MSG_ABOUT_FOOTER_WHAT)
    # The pages in the order of their cells, four to a row.
    PAGES = [FILE, SONGS, PATTERNS, CHAINS, GENERATORS, SCALES, GROOVES, INSTRUMENTS, REGISTERS, ARRANGE, REAL_TIME]
    IN_HELP = [*PAGES, OPEN_SET_HERE, EXPORT_HERE, IMPORT_HERE, QUIT, SELECT, OPEN]
    IN_LEGEND = [SELECT, OPEN, FOOTER_HELP, FOOTER_ABOUT]


class ListPage(Page):
    """A page of rows with a + row at the bottom: the keys every list of named things shares, and the keys of a search."""

    SELECT = (ARROWS_UP_DOWN, KeyName.UP_DOWN, What.SELECT)
    ADD = (Key.A, KeyName.A, What.ADD)
    # Enter on the + row adds, as A does on any row.
    ADD_HERE = (Key.ENTER, KeyName.ENTER, What.ADD)
    EDIT = (Key.ENTER, KeyName.ENTER, What.EDIT)
    # F2 renames too, as on Windows, the user's choice; N stays, since a stock Mac needs fn for F2.
    RENAME = ((Key.N, Key.F2), KeyName.N_F2, What.RENAME)
    COPY = (Key.C, KeyName.C, What.COPY)
    DELETE = (Key.BACKSPACE, KeyName.BACKSPACE, What.DELETE)
    # Move mode, the user's design: M picks up the row, Up and Down carry it, and Enter, Esc or M drops it where it is.
    MOVE = (Key.M, KeyName.M, What.MOVE)
    CARRY = (Steps(back=(Key.UP,), forward=(Key.DOWN,)), KeyName.UP_DOWN, What.CARRY)
    DROP = (MOVE_DROP_KEYS, KeyName.ENTER_ESC_M, What.DROP)
    SORT = (Key.S, KeyName.S, What.SORT)
    SEARCH = (Key.SLASH, KeyName.SLASH, What.SEARCH)
    # While a search is typed, the page's letters are text.
    SEARCH_CANCEL = (Key.ESCAPE, KeyName.ESCAPE, What.CANCEL)
    SEARCH_TYPE = (SEARCH_CHARACTERS, KeyName.SEARCH_CHARACTERS, What.SEARCH)
    SEARCH_ERASE = (Key.BACKSPACE, KeyName.BACKSPACE, What.ERASE)
    SEARCH_COMPLETE = (Key.TAB, KeyName.TAB, What.COMPLETE)
    SEARCH_KEEP = (Key.ENTER, KeyName.ENTER, What.KEEP)
    SEARCHING = [SEARCH_CANCEL, SEARCH_TYPE, SEARCH_ERASE, SEARCH_COMPLETE, SEARCH_KEEP]
    IN_HELP = [Page.BACK, DROP, SEARCH_CANCEL, ADD_HERE, SELECT, CARRY, SEARCH_TYPE, SEARCH_ERASE, SEARCH_COMPLETE, SEARCH_KEEP, ADD, EDIT, RENAME, COPY, DELETE, MOVE, SORT, SEARCH]
    # The search key works everywhere on a list but stays off the legend.
    IN_LEGEND = IN_HELP[:-1]


class NamedListPage(ListPage):
    """A page listing the named things of one section, with the list keys alone."""


class SongsPage(NamedListPage):
    """The Songs page: Space makes the selected song the current one, and Enter opens its settings."""

    CURRENT = (Key.SPACE, KeyName.SPACE, MSG_MAKE_CURRENT_WHAT)
    SETTINGS = (Key.ENTER, KeyName.ENTER, What.SETTINGS)
    IN_HELP = [
        Page.BACK, ListPage.DROP, ListPage.SEARCH_CANCEL, ListPage.ADD_HERE, ListPage.SELECT, ListPage.CARRY, *ListPage.SEARCHING[1:], ListPage.ADD, CURRENT, SETTINGS,
        ListPage.RENAME, ListPage.COPY, ListPage.DELETE, ListPage.MOVE, ListPage.SORT, ListPage.SEARCH,
    ]
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[ListPage.SEARCH])


class PatternsPage(NamedListPage):
    """The Patterns page: the list keys, and L, which plays the selected pattern at once, again and again, until L stops it."""

    LISTEN = (Key.L, KeyName.L, MSG_LISTEN_WHAT)
    STOP_LISTENING = (Key.L, KeyName.L, MSG_STOP_LISTENING_WHAT)
    IN_HELP = [*ListPage.IN_HELP, LISTEN, STOP_LISTENING]
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[ListPage.SEARCH])


class ChainsPage(NamedListPage):
    """The Chains page, with the list keys alone."""


class ScalesPage(NamedListPage):
    """The Scales page, with the list keys alone."""


class GeneratorsPage(ListPage):
    """The Generators page, every generator on one list, the user's design: Enter edits one, A adds one of a kind asked for, and the
    usual keys rename, copy, delete and move one; there's no sort, since the order is the user's own."""

    IN_HELP = [binding for binding in ListPage.IN_HELP if binding is not ListPage.SORT]
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[ListPage.SEARCH])


class OpenPage(ListPage):
    """The page that opens a set file: Enter opens the file or the directory under the cursor."""

    OPEN = (Key.ENTER, KeyName.ENTER, What.OPEN)
    IN_HELP = [Page.BACK, ListPage.SEARCH_CANCEL, ListPage.SELECT, *ListPage.SEARCHING[1:], OPEN, ListPage.SEARCH]
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[ListPage.SEARCH])


class InstrumentsPage(NamedListPage):
    """The Instruments page, with the list keys alone."""


class GroovesPage(NamedListPage):
    """The Grooves page: a factory groove can only be viewed and copied."""

    VIEW = (Key.ENTER, KeyName.ENTER, MSG_VIEW_WHAT)
    IN_HELP = [
        Page.BACK, ListPage.DROP, ListPage.SEARCH_CANCEL, ListPage.ADD_HERE, ListPage.SELECT, ListPage.CARRY, *ListPage.SEARCHING[1:], ListPage.ADD, VIEW, ListPage.EDIT,
        ListPage.RENAME, ListPage.COPY, ListPage.DELETE, ListPage.MOVE, ListPage.SORT, ListPage.SEARCH,
    ]
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[ListPage.SEARCH])


class ChainEditor(ListPage):
    """The chain editor: its rows are the chain's steps, and N renames the chain itself."""

    CHANGE = (Key.ENTER, KeyName.ENTER, What.CHANGE)
    REMOVE = (Key.BACKSPACE, KeyName.BACKSPACE, What.REMOVE)
    IN_HELP = [
        Page.BACK, ListPage.DROP, ListPage.SEARCH_CANCEL, ListPage.ADD_HERE, ListPage.SELECT, ListPage.CARRY, *ListPage.SEARCHING[1:], ListPage.ADD, CHANGE, ListPage.COPY, REMOVE,
        ListPage.MOVE, ListPage.RENAME, ListPage.SEARCH,
    ]
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[ListPage.SEARCH])


class ChainListPage(ListPage):
    """The chains a clip, a scene or a track runs: A adds one, U and D move it, Bksp takes it out of the list."""

    REMOVE = (Key.BACKSPACE, KeyName.BACKSPACE, What.REMOVE)
    IN_HELP = [Page.BACK, ListPage.DROP, ListPage.SEARCH_CANCEL, ListPage.ADD_HERE, ListPage.SELECT, ListPage.CARRY, *ListPage.SEARCHING[1:], ListPage.ADD, REMOVE, ListPage.MOVE, ListPage.SEARCH]
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[ListPage.SEARCH])


class FieldPage(Page):
    """A page of settings: Up and Down pick a field, Left and Right change its value, and what Enter and Bksp do is said by the field."""

    SELECT = (ARROWS_UP_DOWN, KeyName.UP_DOWN, What.SELECT)
    # [ dec and ] inc, the user's one adjust system, named the same way everywhere (2026-11-09); Left and Right do the same, off the legend.
    LESS = ((Key.LEFT, *LESS_KEYS), KeyName.LEFT_BRACKET, What.LESS)
    MORE = ((Key.RIGHT, *MORE_KEYS), KeyName.RIGHT_BRACKET, What.MORE)
    # A field that's true or false answers to Space and Enter alike.
    TOGGLE = (TOGGLE_KEYS, KeyName.SPACE_ENTER, What.TOGGLE)
    # What Enter and Bksp do depends on the field, which says so itself: these words stand for the field's own.
    ENTER = (Key.ENTER, KeyName.ENTER, What.EDIT)
    CLEAR = (Key.BACKSPACE, KeyName.BACKSPACE, What.CLEAR)
    # On a page with sections, PgUp and PgDn jump between their headings, as in the pattern editor's rows.
    SECTION = (Steps(back=(Key.PAGE_UP,), forward=(Key.PAGE_DOWN,)), KeyName.PAGE_UP_DOWN, MSG_NEXT_SECTION_WHAT)
    # F2 renames from any field of a page that has a Name, as on Windows, the user's choice; off the legend, where Enter on Name says rename.
    RENAME = (Key.F2, KeyName.F2, What.RENAME)
    # On the row of buttons under the settings, Left and Right move along it, the user's design.
    ALONG_BUTTONS = (ARROWS_LEFT_RIGHT, KeyName.LEFT_RIGHT, What.SELECT)
    IN_HELP = [Page.BACK, SELECT, ALONG_BUTTONS, LESS, MORE, TOGGLE, ENTER, CLEAR, SECTION, RENAME]
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[RENAME])


class FilePage(FieldPage):
    """The File page: N starts a new set and W saves the set under another name."""

    NEW = (Key.N, KeyName.N, MSG_NEW_WHAT)
    SAVE_AS = (Key.W, KeyName.W, MSG_SAVE_AS_WHAT)
    IN_HELP = [*FieldPage.IN_HELP, NEW, SAVE_AS]
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[FieldPage.RENAME])


class SongPage(FieldPage):
    """The Song page, with the settings keys alone."""


class ScalePage(FieldPage):
    """The Scale page, with the settings keys alone."""


class RegistersPage(FieldPage):
    """The Registers page, a grid of the four registers by their settings, the user's design: the arrows move over it, stopping at
    every edge, [ and ] make the value under the cursor less and more, and Enter, Space and Bksp act on it as on a settings page."""

    MOVE = (ARROWS, KeyName.ARROWS, What.MOVE)
    LESS = (LESS_KEYS, KeyName.LEFT_BRACKET, What.LESS)
    MORE = (MORE_KEYS, KeyName.RIGHT_BRACKET, What.MORE)
    IN_HELP = [Page.BACK, MOVE, LESS, MORE, FieldPage.TOGGLE, FieldPage.ENTER, FieldPage.CLEAR]
    IN_LEGEND = IN_HELP


class ScenePage(FieldPage):
    """The scene page, with the settings keys alone."""


class ClipPage(FieldPage):
    """The clip page: the settings keys, and P, which opens the clip's pattern in the pattern editor from any field, since the page has one pattern."""

    OPEN_PATTERN = (Key.P, KeyName.P, MSG_OPEN_PATTERN_WHAT)
    # Real-time playback: L plays the clip as its scene would, looping until stopped, and L again stops it, with the Play and Stop buttons below the fields doing the same.
    LISTEN = (Key.L, KeyName.L, MSG_LISTEN_WHAT)
    STOP_LISTENING = (Key.L, KeyName.L, MSG_STOP_LISTENING_WHAT)
    IN_HELP = [*FieldPage.IN_HELP, OPEN_PATTERN, LISTEN, STOP_LISTENING]
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[FieldPage.RENAME])


class TrackEditor(FieldPage):
    """The track editor: the settings keys, and H on the Euclid hits field for a named rhythm."""

    PICK_RHYTHM = (Key.H, KeyName.H, MSG_PICK_RHYTHM_WHAT)
    IN_HELP = [*FieldPage.IN_HELP, PICK_RHYTHM]
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[FieldPage.RENAME])


class InstrumentEditor(FieldPage):
    """The instrument editor, with the settings keys alone."""


class ArpEditor(FieldPage):
    """The arpeggiator's editor, with the settings keys alone."""


class AutoRatchetEditor(FieldPage):
    """The AutoRatchet's editor, with the settings keys alone."""


class ProgressionEditor(FieldPage):
    """A progression's editor, with the settings keys alone."""


class VoiceLeadingEditor(FieldPage):
    """A voice leading's editor, with the settings keys alone."""


class HocketEditor(FieldPage):
    """A Hocket's editor, with the settings keys alone."""


class StrumEditor(FieldPage):
    """A Strum's editor, with the settings keys alone."""


class EuclidEditor(FieldPage):
    """A Euclid's editor: the settings keys, and H on Hits for a named rhythm."""

    PICK_RHYTHM = (Key.H, KeyName.H, MSG_PICK_RHYTHM_WHAT)
    IN_HELP = [*FieldPage.IN_HELP, PICK_RHYTHM]
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[FieldPage.RENAME])


class StepRowGeneratorEditor(FieldPage):
    """A Glide's, a Shorten's, a Rush's or a Drag's editor, with the settings keys alone."""


class GlideEditor(StepRowGeneratorEditor):
    """A Glide's editor."""


class ShortenEditor(StepRowGeneratorEditor):
    """A Shorten's editor."""


class RushEditor(StepRowGeneratorEditor):
    """A Rush's editor."""


class DragEditor(StepRowGeneratorEditor):
    """A Drag's editor."""


class ShapeEditor(FieldPage):
    """A shape generator's editor, with the settings keys alone."""


class DensityEditor(ShapeEditor):
    """A Density's editor."""


class SwellEditor(ShapeEditor):
    """A Swell's editor."""


class ArticulateEditor(ShapeEditor):
    """An Articulate's editor."""


class DriftEditor(FieldPage):
    """The drift's editor: the settings keys, except that Left and Right pick version A or B on a row that has both, so only [ and ] change a value."""

    LESS = (LESS_KEYS, KeyName.LEFT_BRACKET, What.LESS)
    MORE = (MORE_KEYS, KeyName.RIGHT_BRACKET, What.MORE)
    VERSION = (ARROWS_LEFT_RIGHT, KeyName.LEFT_RIGHT, MSG_A_OR_B_WHAT)
    IN_HELP = [Page.BACK, FieldPage.SELECT, VERSION, LESS, MORE, FieldPage.TOGGLE, FieldPage.ENTER, FieldPage.CLEAR, FieldPage.SECTION, FieldPage.RENAME, FieldPage.ALONG_BUTTONS]
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[FieldPage.RENAME])


class NotesPage(Page):
    """The Description page: reading, it scrolls and E edits; editing, Tab moves between the text and the Save and Cancel buttons."""

    SCROLL = (Steps(back=(Key.UP,), forward=(Key.DOWN,)), KeyName.UP_DOWN, What.SCROLL)
    EDIT = (Key.E, KeyName.E, What.EDIT)
    CLEAR = (Key.BACKSPACE, KeyName.BACKSPACE, What.CLEAR)
    # While the text is edited.
    CANCEL = (Key.ESCAPE, KeyName.ESCAPE, What.CANCEL)
    MOVE = (ARROWS, KeyName.ARROWS, What.MOVE)
    NEW_LINE = (Key.ENTER, KeyName.ENTER, MSG_NEW_LINE_WHAT)
    ERASE = (Key.BACKSPACE, KeyName.BACKSPACE, What.ERASE)
    TO_BUTTONS = (Key.TAB, KeyName.TAB, MSG_TO_BUTTONS_WHAT)
    # On the Save and Cancel buttons.
    SELECT_BUTTON = (ARROWS_LEFT_RIGHT, KeyName.LEFT_RIGHT, What.SELECT)
    PRESS_BUTTON = (Key.ENTER, KeyName.ENTER, What.CHOOSE)
    TO_TEXT = (Key.TAB, KeyName.TAB, MSG_TO_TEXT_WHAT)
    IN_HELP = [Page.BACK, CANCEL, SCROLL, MOVE, SELECT_BUTTON, NEW_LINE, PRESS_BUTTON, EDIT, CLEAR, ERASE, TO_BUTTONS, TO_TEXT]
    IN_LEGEND = IN_HELP


class StepEditor(Page):
    """A page that edits steps under a cursor, with no keys of its own."""


class OneRowEditor(StepEditor):
    """An editor of one row of numbers: Left and Right move along the row, and Up and Down change the number, since no row lies below the cursor."""

    MOVE = (ARROWS_LEFT_RIGHT, KeyName.LEFT_RIGHT, What.MOVE)
    # [ dec and ] inc as everywhere (2026-11-09); Up and Down do the same, off the legend, since no row lies below the cursor.
    LESS = (NUDGE_LESS_KEYS, KeyName.LEFT_BRACKET, What.LESS)
    MORE = (NUDGE_MORE_KEYS, KeyName.RIGHT_BRACKET, What.MORE)
    TYPE = (DIGITS, KeyName.DIGITS, What.TYPE)
    IN_HELP = [Page.BACK, MOVE, LESS, MORE, TYPE]
    IN_LEGEND = IN_HELP


class OffsetsEditor(OneRowEditor):
    """The offsets editor, one row of an arp's offsets."""

    # Space or Enter silences a step that plays and plays a step that's silent.
    SILENT = (TOGGLE_KEYS, KeyName.SPACE_ENTER, MSG_SILENT_WHAT)
    PLAY = (TOGGLE_KEYS, KeyName.SPACE_ENTER, MSG_PLAY_WHAT)
    INSERT_STEP = (Key.I, KeyName.I, What.INSERT_STEP)
    REMOVE_STEP = (Key.D, KeyName.D, What.REMOVE_STEP)
    # Tab moves between the Offset row and the register add rows under it.
    NEXT_ROW = (Key.TAB, KeyName.TAB, MSG_NEXT_ROW_WHAT)
    IN_HELP = [*OneRowEditor.IN_HELP, NEXT_ROW, SILENT, PLAY, INSERT_STEP, REMOVE_STEP]
    IN_LEGEND = IN_HELP


class ChordsEditor(StepEditor):
    """The chord editor, a progression's chords: the arrows move along the chords and between the Chord, #/b and Inv. rows."""

    MOVE = (ARROWS, KeyName.ARROWS, What.MOVE)
    LESS = (LESS_KEYS, KeyName.LEFT_BRACKET, What.LESS)
    MORE = (MORE_KEYS, KeyName.RIGHT_BRACKET, What.MORE)
    TYPE = (DIGITS, KeyName.DIGITS, What.TYPE)
    # On the #/b and Inv. rows, Space or Enter goes to the next choice, as on the pattern editor's cycle rows.
    NEXT = (TOGGLE_KEYS, KeyName.SPACE_ENTER, What.NEXT)
    INSERT_STEP = (Key.I, KeyName.I, What.INSERT_STEP)
    REMOVE_STEP = (Key.D, KeyName.D, What.REMOVE_STEP)
    PICK = (Key.H, KeyName.H, MSG_PICK_PROGRESSION_WHAT)
    # On the Scale, Quality and Tensions rows, Enter opens the Chord dialog, and Space goes to the next choice.
    CHOOSE = (Key.ENTER, KeyName.ENTER, What.CHOOSE)
    NEXT_CHOICE = (Key.SPACE, KeyName.SPACE, What.NEXT)
    CLEAR = (Key.BACKSPACE, KeyName.BACKSPACE, What.CLEAR)
    IN_HELP = [Page.BACK, MOVE, LESS, MORE, TYPE, NEXT, CHOOSE, NEXT_CHOICE, CLEAR, INSERT_STEP, REMOVE_STEP, PICK]
    IN_LEGEND = IN_HELP


class StepRowEditor(StepEditor):
    """A row of on-or-off steps: Left and Right move, Space or Enter turns a step on or off, I and D insert and remove."""

    MOVE = (ARROWS_LEFT_RIGHT, KeyName.LEFT_RIGHT, What.MOVE)
    # As in the one-row editors, Up and Down change the step under the cursor too, off the legend, since no row lies below it.
    TOGGLE = ((*TOGGLE_KEYS, *ARROWS_UP_DOWN), KeyName.SPACE_ENTER, What.TOGGLE)
    INSERT_STEP = (Key.I, KeyName.I, What.INSERT_STEP)
    REMOVE_STEP = (Key.D, KeyName.D, What.REMOVE_STEP)
    IN_HELP = [Page.BACK, MOVE, TOGGLE, INSERT_STEP, REMOVE_STEP]
    IN_LEGEND = IN_HELP


class GlideStepsEditor(StepRowEditor):
    """A Glide's row of steps."""


class ShortenStepsEditor(StepRowEditor):
    """A Shorten's row of steps."""


class RushStepsEditor(StepRowEditor):
    """A Rush's row of steps."""


class DragStepsEditor(StepRowEditor):
    """A Drag's row of steps."""


class GrooveEditor(OneRowEditor):
    """The groove editor, one row of a groove's cells, with S for the cell length and N to rename."""

    INSERT_CELL = (Key.I, KeyName.I, What.INSERT_CELL)
    REMOVE_CELL = (Key.D, KeyName.D, What.REMOVE_CELL)
    CELL_LENGTH = (Key.S, KeyName.S, MSG_CELL_LENGTH_WHAT)
    # F2 renames too, as on Windows, the user's choice; N stays, since a stock Mac needs fn for F2.
    RENAME = ((Key.N, Key.F2), KeyName.N_F2, What.RENAME)
    IN_HELP = [*OneRowEditor.IN_HELP, INSERT_CELL, REMOVE_CELL, CELL_LENGTH, RENAME]
    IN_LEGEND = IN_HELP


class ArrangePage(Page):
    """Arrange: the keys change with what the cursor is on, a track's name, a scene's name, a clip or a +, so each meaning has a binding of its own."""

    MOVE = (ARROWS, KeyName.ARROWS, What.MOVE)
    # Real-time playback, bound only while the set's Real Time switch is on: Space plays what the cursor is on, or stops it, and the mark before each bar says which.
    PLAY_SONG = (Key.SPACE, KeyName.SPACE, MSG_PLAY_SONG_WHAT)
    PLAY_SCENE = (Key.SPACE, KeyName.SPACE, MSG_PLAY_SCENE_WHAT)
    PLAY_CLIP = (Key.SPACE, KeyName.SPACE, MSG_PLAY_CLIP_WHAT)
    STOP_PLAYING = (Key.SPACE, KeyName.SPACE, MSG_STOP_WHAT)
    STOP_CLIP = (Key.SPACE, KeyName.SPACE, MSG_STOP_CLIP_WHAT)
    # On the row of track names.
    ADD_TRACK = (Key.A, KeyName.A, MSG_ADD_TRACK_WHAT)
    ADD_TRACK_HERE = (Key.ENTER, KeyName.ENTER, MSG_ADD_TRACK_WHAT)
    TRACK_SETTINGS = (Key.ENTER, KeyName.ENTER, MSG_TRACK_SETTINGS_WHAT)
    COPY_TRACK = (Key.C, KeyName.C, MSG_COPY_TRACK_WHAT)
    INSERT_TRACK = (Key.I, KeyName.I, MSG_INSERT_TRACK_WHAT)
    MOVE_TRACK = (Key.M, KeyName.M, MSG_MOVE_TRACK_WHAT)
    DELETE_TRACK = (Key.BACKSPACE, KeyName.BACKSPACE, MSG_DELETE_TRACK_WHAT)
    # On a scene's row.
    ADD_SCENE = (Key.A, KeyName.A, MSG_ADD_SCENE_WHAT)
    ADD_SCENE_HERE = (Key.ENTER, KeyName.ENTER, MSG_ADD_SCENE_WHAT)
    SCENE_SETTINGS = (Key.ENTER, KeyName.ENTER, MSG_SCENE_SETTINGS_WHAT)
    COPY_SCENE = (Key.C, KeyName.C, MSG_COPY_SCENE_WHAT)
    DELETE_SCENE = (Key.BACKSPACE, KeyName.BACKSPACE, MSG_DELETE_SCENE_WHAT)
    INSERT_SCENE = (Key.I, KeyName.I, MSG_INSERT_SCENE_WHAT)
    MOVE_SCENE = (Key.M, KeyName.M, MSG_MOVE_SCENE_WHAT)
    # Move mode on Arrange, the user's design: M on a scene's name, a track's name or a clip picks it up, the arrows carry it (a clip only
    # into an empty cell, the user's rule), and Enter, Esc or M drops it where it is.
    MOVE_CLIP = (Key.M, KeyName.M, MSG_MOVE_CLIP_WHAT)
    CARRY_SCENE = (Steps(back=(Key.UP,), forward=(Key.DOWN,)), KeyName.UP_DOWN, What.CARRY)
    CARRY_TRACK = (Steps(back=(Key.LEFT,), forward=(Key.RIGHT,)), KeyName.LEFT_RIGHT, What.CARRY)
    CARRY_CLIP = (ARROWS, KeyName.ARROWS, What.CARRY)
    DROP = (MOVE_DROP_KEYS, KeyName.ENTER_ESC_M, What.DROP)
    # On a clip, or the empty cell where one would be.
    ADD_CLIP = (Key.ENTER, KeyName.ENTER, MSG_ADD_CLIP_WHAT)
    # B on an empty cell makes a blank pattern named after the track, puts a clip of it there and opens it, the user's design, as Live makes a new clip in an empty slot.
    BLANK_PATTERN = (Key.B, KeyName.B, MSG_BLANK_PATTERN_WHAT)
    EDIT_CLIP = (Key.ENTER, KeyName.ENTER, MSG_EDIT_CLIP_WHAT)
    # P opens the clip's pattern in the pattern editor, the user's choice of 2026-11-09 over Shift+Enter, which a stock terminal sends as Enter.
    OPEN_PATTERN = (Key.P, KeyName.P, MSG_OPEN_PATTERN_WHAT)
    COPY_CLIP = (Key.C, KeyName.C, MSG_COPY_CLIP_WHAT)
    DELETE_CLIP = (Key.BACKSPACE, KeyName.BACKSPACE, MSG_DELETE_CLIP_WHAT)
    PASTE_CLIP = (Key.V, KeyName.V, MSG_PASTE_CLIP_WHAT)
    # A clip's track moves with the same keys as on the track's name, listed last on a clip, after the scene's keys.
    # With Real Time on, the visualizer over the clip area, the user's design of 2026-11-10: the key steps through its modes and back to
    # the clips, from anywhere on the page, and while it shows, Esc brings the clips back rather than leaving the page.
    VISUALIZER = (Key.Z, KeyName.Z, MSG_VISUALIZER_WHAT)
    # While the visualizer shows, [ and ] step to the mode before or after, going round, the user's ask.
    STEP_VISUALIZER = (Steps(back=(Key.LEFT_BRACKET,), forward=(Key.RIGHT_BRACKET,)), KeyName.BRACKETS, MSG_STEP_VISUALIZER_WHAT)
    # The details view, the user's design: D shows, under every bar, the chains and generators and the settings that aren't
    # their defaults, widening the columns to fit, with coloured dividers between the tracks, and D again hides them.
    SHOW_DETAILS = (Key.D, KeyName.D, MSG_SHOW_DETAILS_WHAT)
    HIDE_DETAILS = (Key.D, KeyName.D, MSG_HIDE_DETAILS_WHAT)
    # Tab on a track's name, a scene's name or a clip, the user's design, opens that cell's details if they aren't showing and locks into it:
    # Up and Down pick a chain, a generator, or a line naming a scale, an instrument or a groove, shown in brackets, Enter opens its page,
    # and Tab again or Esc leaves, closing the cell's details in the usual view, Esc closing the topmost thing as everywhere.
    INTO_DETAILS = (Key.TAB, KeyName.TAB, MSG_INTO_DETAILS_WHAT)
    OUT_OF_DETAILS = (Key.TAB, KeyName.TAB, MSG_OUT_OF_DETAILS_WHAT)
    PICK_DETAIL = (ARROWS_UP_DOWN, KeyName.UP_DOWN, What.SELECT)
    OPEN_DETAIL = (Key.ENTER, KeyName.ENTER, MSG_OPEN_DETAIL_WHAT)
    # On the + under a cell's chains Enter adds a chain to the cell, and on a chain's line Bksp takes it out of the cell, the user's design.
    ADD_CHAIN = (Key.ENTER, KeyName.ENTER, MSG_ADD_CHAIN_WHAT)
    REMOVE_CHAIN = (Key.BACKSPACE, KeyName.BACKSPACE, MSG_REMOVE_CHAIN_WHAT)
    # While locked into a cell, D closes every detail and leaves the cell, and Esc leaves the cell, the user's asks.
    CLOSE_DETAILS = (Key.D, KeyName.D, MSG_CLOSE_DETAILS_WHAT)
    # P on a scene's name opens Scene View, the user's design, an Inset Window of every track's notes in the scene; inside it only P closes
    # it, Tab switches between as written and as played, the arrows move its cursor, and Esc closes it as P does.
    SCENE_VIEW = (Key.P, KeyName.P, MSG_SCENE_VIEW_WHAT)
    CLOSE_INSET = (Key.P, KeyName.P, MSG_CLOSE_INSET_WHAT)
    # V switches between as written and as played, PgUp and PgDn jump its cursor a bar, and [ and ] scroll the sidebar, the user's
    # choice, so that Tab keeps its one meaning of the next part of a page.
    TO_PLAYED = (Key.V, KeyName.V, MSG_TO_PLAYED_WHAT)
    TO_WRITTEN = (Key.V, KeyName.V, MSG_TO_WRITTEN_WHAT)
    INSET_BARS = (Steps(back=(Key.PAGE_UP,), forward=(Key.PAGE_DOWN,)), KeyName.PAGE_UP_DOWN, MSG_JUMP_BAR_WHAT)
    INSET_MOVE = (ARROWS, KeyName.ARROWS, What.MOVE)
    ESCAPE_INSET = (CANCEL_KEYS, KeyName.ESCAPE, MSG_CLOSE_INSET_ESC_WHAT)
    # In Scene View, [ and ] switch between as written and as played, - and = draw each sixteenth narrower or wider, and PgUp and PgDn scroll the sidebar of the tracks' details.
    INSET_ZOOM = (Steps(back=(Key.MINUS,), forward=(Key.EQUALS,)), KeyName.MINUS_EQUALS, MSG_ZOOM_WHAT)
    INSET_SCROLL = (Steps(back=(Key.LEFT_BRACKET,), forward=(Key.RIGHT_BRACKET,)), KeyName.BRACKETS, MSG_SCROLL_SIDEBAR_WHAT)
    ESCAPE_CELL = (CANCEL_KEYS, KeyName.ESCAPE, MSG_LEAVE_CELL_WHAT)
    TO_CLIPS = (CANCEL_KEYS, KeyName.ESCAPE, MSG_TO_CLIPS_WHAT)
    IN_HELP = [
        Page.BACK, DROP, TO_CLIPS, ESCAPE_CELL, ESCAPE_INSET, CLOSE_INSET, INSET_MOVE, INSET_BARS, TO_PLAYED, TO_WRITTEN, INSET_ZOOM, INSET_SCROLL, STEP_VISUALIZER, OUT_OF_DETAILS, MOVE, CARRY_SCENE, CARRY_TRACK, CARRY_CLIP, PICK_DETAIL, OPEN_DETAIL, ADD_CHAIN, REMOVE_CHAIN, CLOSE_DETAILS, PLAY_SONG, PLAY_SCENE, PLAY_CLIP, STOP_PLAYING, STOP_CLIP,
        ADD_TRACK, ADD_TRACK_HERE, TRACK_SETTINGS, COPY_TRACK, INSERT_TRACK, MOVE_TRACK, DELETE_TRACK,
        ADD_SCENE, ADD_SCENE_HERE, SCENE_SETTINGS, SCENE_VIEW, COPY_SCENE, DELETE_SCENE, ADD_CLIP, BLANK_PATTERN, EDIT_CLIP, OPEN_PATTERN, MOVE_CLIP, COPY_CLIP, DELETE_CLIP, PASTE_CLIP, INSERT_SCENE,
        MOVE_SCENE,
        SHOW_DETAILS,
        HIDE_DETAILS,
        INTO_DETAILS,
        VISUALIZER,
    ]
    IN_LEGEND = IN_HELP


class PatternEditor(StepEditor):
    """The pattern editor's own keys, whichever view shows: Tab switches the view, S sizes the pattern and R opens Reconfigure."""

    TO_ROLL = (Key.TAB, KeyName.TAB, MSG_TO_ROLL_WHAT)
    TO_EDITOR = (Key.TAB, KeyName.TAB, MSG_TO_EDITOR_WHAT)
    RESIZE = (Key.S, KeyName.S, MSG_SIZE_WHAT)
    RECONFIGURE = (Key.R, KeyName.R, MSG_RECONFIGURE_WHAT)
    # Real-time playback: L plays the pattern at once through the pattern preview, looping until L again stops it.
    LISTEN = (Key.L, KeyName.L, MSG_LISTEN_WHAT)
    STOP_LISTENING = (Key.L, KeyName.L, MSG_STOP_LISTENING_WHAT)
    # F2 renames the pattern, as on Windows, the user's choice, beside rename in R's menu; off the legend.
    RENAME = (Key.F2, KeyName.F2, What.RENAME)
    IN_HELP = [Page.BACK, TO_ROLL, TO_EDITOR, RESIZE, RECONFIGURE, LISTEN, STOP_LISTENING, RENAME]
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[RENAME])


# The pattern editor's two views.

class PatternRows:
    """The rows view of the pattern editor: the cursor's keys, and the keys that insert and remove a step, which its legend shows."""

    MOVE = (ARROWS, KeyName.ARROWS, What.MOVE)
    ENDS = (Steps(back=(Key.HOME,), forward=(Key.END,)), KeyName.HOME_END, What.ENDS)
    SECTION = (Steps(back=(Key.PAGE_UP,), forward=(Key.PAGE_DOWN,)), KeyName.PAGE_UP_DOWN, MSG_NEXT_SECTION_WHAT)
    INSERT_STEP = (Key.I, KeyName.I, What.INSERT_STEP)
    REMOVE_STEP = (Key.D, KeyName.D, What.REMOVE_STEP)
    IN_HELP = [MOVE, ENDS, SECTION, INSERT_STEP, REMOVE_STEP]
    # Home and End are listed by F1 alone.
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[ENDS])


class PianoRoll:
    """The piano roll: one pencil, where every key does one thing, and Space or Enter on a note takes the note out as Bksp does. Its legend keeps to drawing, so K and G are listed by F1 alone. It neither inserts nor removes a step, the user's rule, as Live's piano roll never did.

    Enter draws as Space does, by the user's choice of 2026-11-09, since the two do the same everywhere else, so the chord picker took the free letter H.
    """

    MOVE = (ARROWS, KeyName.ARROWS, What.MOVE)
    ENDS = (Steps(back=(Key.HOME,), forward=(Key.END,)), KeyName.HOME_END, What.ENDS)
    PLACE = (TOGGLE_KEYS, KeyName.SPACE_ENTER, MSG_PLACE_NOTE_WHAT)
    CHORD = (Key.H, KeyName.H, MSG_CHORD_WHAT)
    # [ and ] drag the note's end a step earlier and later, which the user calls shrink and stretch (2026-11-09), since a note is not a number.
    SHORTER = (Key.LEFT_BRACKET, KeyName.LEFT_BRACKET, MSG_SHRINK_WHAT)
    LONGER = (Key.RIGHT_BRACKET, KeyName.RIGHT_BRACKET, MSG_STRETCH_WHAT)
    KNIFE = (Key.K, KeyName.K, MSG_SPLIT_WHAT)
    ACCIDENTAL = (Key.PERIOD, KeyName.PERIOD, MSG_ACCIDENTAL_WHAT)
    ERASE = (Key.BACKSPACE, KeyName.BACKSPACE, What.ERASE)
    GRAB = (Key.G, KeyName.G, MSG_GRAB_WHAT)
    ENTRY_SIZE = (Key.E, KeyName.E, MSG_ENTRY_SIZE_WHAT)
    IN_HELP = [MOVE, ENDS, PLACE, CHORD, SHORTER, LONGER, KNIFE, ACCIDENTAL, ERASE, GRAB, ENTRY_SIZE]
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[ENDS, KNIFE, GRAB])


# The rows of the pattern editor's rows view, whose keys work while the cursor is on the row.

class PatternRow:
    """What the rows share: [ and ] step the value under the cursor, with -, + and = working too, as two legend entries, less and more, by the user's choice of 2026-11-09."""

    LESS = (LESS_KEYS, KeyName.LEFT_BRACKET, What.LESS)
    MORE = (MORE_KEYS, KeyName.RIGHT_BRACKET, What.MORE)
    IN_HELP = [LESS, MORE]
    IN_LEGEND = IN_HELP


class DegreeRow(PatternRow):
    """The Degree row: digits type a degree, or on a drum pattern, where the row is called Note, letters type a note."""

    NOTE = (NOTE_LETTER_KEYS, KeyName.NOTE_LETTERS, MSG_NOTE_WHAT)
    # The digits bound, and their name, are the degrees of the scale: 1-7 in a scale of seven notes.
    DEGREE = (DIGITS, KeyName.DIGITS, MSG_DEGREE_WHAT)
    CLEAR = (Key.BACKSPACE, KeyName.BACKSPACE, What.CLEAR)
    IN_HELP = [NOTE, DEGREE, PatternRow.LESS, PatternRow.MORE, CLEAR]
    IN_LEGEND = IN_HELP


class OctaveRow(PatternRow):
    """The Octave row: digits type an octave, and Bksp goes back to the default."""

    # The name shown is the range of octaves in the set's octave labels.
    TYPE = (DIGITS, KeyName.DIGITS, MSG_TYPE_OCTAVE_WHAT)
    DEFAULT = (Key.BACKSPACE, KeyName.BACKSPACE, What.DEFAULT)
    IN_HELP = [TYPE, PatternRow.LESS, PatternRow.MORE, DEFAULT]
    IN_LEGEND = IN_HELP


class GateRow(PatternRow):
    """The Gate row: Enter types a length, and Bksp goes back to one step."""

    TYPE = (Key.ENTER, KeyName.ENTER, What.TYPE)
    ONE_STEP = (Key.BACKSPACE, KeyName.BACKSPACE, MSG_ONE_STEP_WHAT)
    IN_HELP = [PatternRow.LESS, PatternRow.MORE, TYPE, ONE_STEP]
    IN_LEGEND = IN_HELP


class NumberRow(PatternRow):
    """A row of numbers, like Velocity: digits type into the cell, and Enter asks for the number."""

    TYPE = (DIGITS, KeyName.DIGITS, What.TYPE)
    ASK = (Key.ENTER, KeyName.ENTER, What.TYPE)
    DEFAULT = (Key.BACKSPACE, KeyName.BACKSPACE, What.DEFAULT)
    IN_HELP = [TYPE, PatternRow.LESS, PatternRow.MORE, ASK, DEFAULT]
    IN_LEGEND = IN_HELP


class ControlRow(NumberRow):
    """A row of numbers that a rest can hold too."""


class CcRow(ControlRow):
    """A CC row."""


class AddRow(ControlRow):
    """A register's += row, held within the register's Allowed Inc Max."""


class SetRow(ControlRow):
    """A register's = row, whose number line starts at blank just below the register's minimum."""


class CycleRow(PatternRow):
    """A row with a cycle of choices, like Dot: Space or Enter goes to the next, and [ and ] step back and forward as on every row, the user's one adjust system (2026-11-09)."""

    NEXT = (TOGGLE_KEYS, KeyName.SPACE_ENTER, What.NEXT)
    CLEAR = (Key.BACKSPACE, KeyName.BACKSPACE, What.CLEAR)
    IN_HELP = [NEXT, PatternRow.LESS, PatternRow.MORE, CLEAR]
    IN_LEGEND = IN_HELP


class AccidentalRow(CycleRow):
    """The #/b row."""


class DotRow(CycleRow):
    """The Dot row."""


class InversionRow(CycleRow):
    """The Inversion row."""


class ChordRow(PatternRow):
    """The Chord row: Enter opens the chord picker, so Space alone goes to the next chord, and [ and ] step through them."""

    CHOOSE = (Key.ENTER, KeyName.ENTER, What.CHOOSE)
    NEXT = (Key.SPACE, KeyName.SPACE, What.NEXT)
    CLEAR = (Key.BACKSPACE, KeyName.BACKSPACE, What.CLEAR)
    IN_HELP = [CHOOSE, NEXT, PatternRow.LESS, PatternRow.MORE, CLEAR]
    IN_LEGEND = IN_HELP


class TensionRow(ChordRow):
    """The Tension row: Enter opens the Chord dialog, Space goes to the next single tension, and [ and ] step through them."""


class ChordScaleRow(ChordRow):
    """The Scale row: Enter opens the Chord dialog, Space goes to the next scale type, and [ and ] step through them."""


class ToggleRow(PatternRow):
    """A row that's on or off on each step: Space or Enter toggles."""

    TOGGLE = (TOGGLE_KEYS, KeyName.SPACE_ENTER, What.TOGGLE)
    CLEAR = (Key.BACKSPACE, KeyName.BACKSPACE, What.CLEAR)
    IN_HELP = [TOGGLE, CLEAR]
    IN_LEGEND = IN_HELP


class GlideRow(ToggleRow):
    """The Glide row."""


class GrabRow(ToggleRow):
    """The Grab row."""


class SlideRow(ToggleRow):
    """The Slide row."""


class TieRow(ToggleRow):
    """The Tie row."""


class RegisterRow(CycleRow):
    """A register's +Note or +Vel row: Space or Enter cycles add, subtract and off, and [ and ] step back and forward, the user's design of 2026-11-09."""


class ConditionRow(CycleRow):
    """A condition row: Space or Enter cycles blank, <, > and =, and [ and ] step back and forward."""


class SectionRow(PatternRow):
    """A section's heading: Space or Enter opens a closed section and closes an open one."""

    OPEN = (TOGGLE_KEYS, KeyName.SPACE_ENTER, MSG_OPEN_SECTION_WHAT)
    CLOSE = (TOGGLE_KEYS, KeyName.SPACE_ENTER, MSG_CLOSE_SECTION_WHAT)
    IN_HELP = [OPEN, CLOSE]
    IN_LEGEND = IN_HELP


# The dialogs.

class Dialog:
    """What every dialog has: Esc cancels."""

    CANCEL = (CANCEL_KEYS, KeyName.ESCAPE, What.CANCEL)
    IN_HELP = [CANCEL]
    IN_LEGEND = IN_HELP


class StartScreen:
    """The start screen: Enter starts."""

    START = (Key.ENTER, KeyName.ENTER, What.START)
    IN_HELP = [START]
    IN_LEGEND = IN_HELP


class MessageDialog(Dialog):
    """A message: Enter or Esc closes it."""

    CLOSE = ((Key.ENTER, *CANCEL_KEYS), KeyName.ENTER, What.CLOSE)
    IN_HELP = [CLOSE]
    IN_LEGEND = IN_HELP


class ConfirmDialog(MessageDialog):
    """A Yes or No question: Left and Right move between the buttons, Enter presses one, and Y and N answer at once."""

    SELECT = (ARROWS_LEFT_RIGHT, KeyName.LEFT_RIGHT, What.SELECT)
    ANSWER = (Key.ENTER, KeyName.ENTER, What.ANSWER)
    YES = (Key.Y, KeyName.Y, What.YES)
    NO = (Key.N, KeyName.N, What.NO)
    IN_HELP = [Dialog.CANCEL, SELECT, ANSWER, YES, NO]
    IN_LEGEND = IN_HELP


class QuitDialog(MessageDialog):
    """Quitting with unsaved changes: Left and Right choose a button, Enter presses it, Q quits without saving, S saves and then quits, and Esc cancels."""

    SELECT = (ARROWS_LEFT_RIGHT, KeyName.LEFT_RIGHT, What.SELECT)
    PRESS = (Key.ENTER, KeyName.ENTER, What.ANSWER)
    QUIT = (Key.Q, KeyName.Q, MSG_QUIT_WITHOUT_SAVING_WHAT)
    SAVE = (Key.S, KeyName.S, MSG_SAVE_THEN_QUIT_WHAT)
    IN_HELP = [Dialog.CANCEL, SELECT, PRESS, QUIT, SAVE]
    IN_LEGEND = IN_HELP


class CorrectionsDialog(ConfirmDialog):
    """The question asked before a set opens with its values corrected: the Yes or No dialog's keys."""

    IN_HELP = ConfirmDialog.IN_HELP
    IN_LEGEND = IN_HELP


class ImportedDialog(MessageDialog):
    """What an import made and what it had to change: Enter or Esc closes it, as its one OK button."""

    IN_HELP = MessageDialog.IN_HELP
    IN_LEGEND = IN_HELP


class ImportDialog(Dialog):
    """The MIDI import's dialog of fields: Up and Down pick a field, [ and ] step one, Space or Enter flips a toggle, Enter renames the song, and on the buttons Left and Right choose and Enter presses; I imports from anywhere."""

    SELECT = (ARROWS_UP_DOWN, KeyName.UP_DOWN, What.SELECT)
    CHOOSE_BUTTON = (ARROWS_LEFT_RIGHT, KeyName.LEFT_RIGHT, What.SELECT)
    LESS = ((Key.LEFT, *LESS_KEYS), KeyName.LEFT_BRACKET, What.LESS)
    MORE = ((Key.RIGHT, *MORE_KEYS), KeyName.RIGHT_BRACKET, What.MORE)
    TOGGLE = (TOGGLE_KEYS, KeyName.SPACE_ENTER, What.TOGGLE)
    RENAME = (Key.ENTER, KeyName.ENTER, What.RENAME)
    PRESS = (Key.ENTER, KeyName.ENTER, MSG_PRESS_WHAT)
    IMPORT = (Key.I, KeyName.I, MSG_IMPORT_WHAT)
    IN_HELP = [Dialog.CANCEL, SELECT, CHOOSE_BUTTON, LESS, MORE, TOGGLE, RENAME, PRESS, IMPORT]
    IN_LEGEND = IN_HELP


class PromptDialog(Dialog):
    """A prompt for text: Left and Right move the cursor in it."""

    MOVE = (ARROWS_LEFT_RIGHT, KeyName.LEFT_RIGHT, What.MOVE)
    DONE = (Key.ENTER, KeyName.ENTER, What.DONE)
    ERASE = (Key.BACKSPACE, KeyName.BACKSPACE, What.ERASE)
    IN_HELP = [Dialog.CANCEL, MOVE, DONE, ERASE]
    IN_LEGEND = IN_HELP


class ChoiceDialog(Dialog):
    """A picker, which searches as you type: Tab completes and Bksp erases once something is typed."""

    MOVE = (ARROWS_UP_DOWN, KeyName.UP_DOWN, What.MOVE)
    CHOOSE = (Key.ENTER, KeyName.ENTER, What.CHOOSE)
    SEARCH = (SEARCH_CHARACTERS, KeyName.SEARCH_CHARACTERS, What.SEARCH)
    ERASE = (Key.BACKSPACE, KeyName.BACKSPACE, What.ERASE)
    COMPLETE = (Key.TAB, KeyName.TAB, What.COMPLETE)
    IN_HELP = [Dialog.CANCEL, MOVE, CHOOSE, SEARCH, ERASE, COMPLETE]
    IN_LEGEND = IN_HELP


class PickManyDialog(Dialog):
    """A list where several choices can be picked: Up and Down move, Space turns one on or off, Enter finishes and Esc cancels."""

    MOVE = (ARROWS_UP_DOWN, KeyName.UP_DOWN, What.MOVE)
    FLIP = (Key.SPACE, KeyName.SPACE, What.TOGGLE)
    DONE = (Key.ENTER, KeyName.ENTER, What.DONE)
    IN_HELP = [Dialog.CANCEL, MOVE, FLIP, DONE]
    IN_LEGEND = IN_HELP


class ChordDialog(Dialog):
    """The Chord dialog, three lists side by side: the arrows move, Tab goes to the next list, Space turns a tension on or off, Space or Enter on a category of scales opens its flyout, where Enter picks, and Enter elsewhere takes the chord."""

    MOVE = (ARROWS, KeyName.ARROWS, What.MOVE)
    NEXT_LIST = (Key.TAB, KeyName.TAB, MSG_NEXT_LIST_WHAT)
    FLIP = (Key.SPACE, KeyName.SPACE, What.TOGGLE)
    CHOOSE = (Key.ENTER, KeyName.ENTER, What.CHOOSE)
    # On a category of scale types, which opens its flyout, and on the row that borrows no scale.
    OPEN = (TOGGLE_KEYS, KeyName.SPACE_ENTER, What.OPEN)
    # While a flyout is open, Esc closes the flyout alone, the topmost thing.
    CLOSE_FLYOUT = (CANCEL_KEYS, KeyName.ESCAPE, What.CLOSE)
    IN_HELP = [Dialog.CANCEL, CLOSE_FLYOUT, MOVE, NEXT_LIST, FLIP, OPEN, CHOOSE]
    IN_LEGEND = IN_HELP


class GridChoiceDialog(ChoiceDialog):
    """A picker laid out as a grid, which all four arrows move over and which doesn't search: Tab and Shift+Tab turn its pages."""

    MOVE = (ARROWS, KeyName.ARROWS, What.MOVE)
    OTHER_PAGE = (Steps(back=(Key.SHIFT_TAB,), forward=(Key.TAB,)), KeyName.TAB_SHIFT_TAB, What.OTHER_PAGE)
    IN_HELP = [Dialog.CANCEL, MOVE, ChoiceDialog.CHOOSE, OTHER_PAGE]
    IN_LEGEND = IN_HELP


class HelpDialog(Dialog):
    """The F1 dialog: Tab, Left and Right turn between its two panels, and F1 closes it like Enter and Esc, off the legend."""

    CLOSE = ((Key.ENTER, Key.ESCAPE, Key.F1), KeyName.ENTER_ESCAPE, What.CLOSE)
    OTHER_PANEL = ((Key.TAB, *ARROWS_LEFT_RIGHT), KeyName.TAB_ARROWS, What.OTHER_PANEL)
    IN_HELP = [CLOSE, OTHER_PANEL]
    IN_LEGEND = IN_HELP


class AboutDialog(Dialog):
    """The About dialog: Enter or Esc closes it."""

    CLOSE = ((Key.ENTER, *CANCEL_KEYS), KeyName.ENTER_ESCAPE, What.CLOSE)
    IN_HELP = [CLOSE]
    IN_LEGEND = IN_HELP
