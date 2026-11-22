# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Every key binding of the tracker in one place: one class for each page, dialog and component, named after it.

A binding is a `Binding` of three things: its `keys`, the key or keys (from interface/tracker/keys.py, a `Steps` for keys that
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

from llamatron.interface.tracker import keys
from llamatron.interface.tracker.keys import Binding, Key, Steps
from llamatron.user_strings import labels, legends


def all_but(*, bindings, hidden):
    """Return the bindings of a list without the hidden ones, for a legend that leaves some of its class's keys to the F1 dialog."""
    return [binding for binding in bindings if binding not in hidden]


# The pages.

class Page:
    """What every page has: the keys that work everywhere, which the F1 dialog lists first, and Esc, which goes back."""

    SAVE = Binding(Key.CTRL_S, legends.KeyName.CTRL_S, legends.What.SAVE)
    OPEN_SET = Binding(Key.CTRL_O, legends.KeyName.CTRL_O, legends.What.OPEN_SET)
    EXPORT = Binding(Key.CTRL_X, legends.KeyName.CTRL_X, legends.What.EXPORT)
    UNDO = Binding(Key.CTRL_Z, legends.KeyName.CTRL_Z, legends.What.UNDO)
    REDO = Binding(Key.CTRL_Y, legends.KeyName.CTRL_Y, legends.What.REDO)
    # The emergency stop: note offs, all notes off and all sound off on every channel the instruments use, whatever is known to be playing.
    SILENCE = Binding(Key.CTRL_T, legends.KeyName.CTRL_T, legends.What.SILENCE)
    # Quits at once, from any page, closing FluidSynth and the MIDI sender as quitting does, as Ctrl+C stops a program in a terminal.
    QUIT_NOW = Binding(Key.CTRL_C, legends.KeyName.CTRL_C, legends.What.QUIT_NOW)
    HELP = Binding(Key.F1, legends.KeyName.F1, legends.What.HELP)
    # About is F3, so that F2 renames as on Windows.
    ABOUT = Binding(Key.F3, legends.KeyName.F3, legends.What.ABOUT)
    # The song wizard is F5, set apart from F1 and F3, which only inform: F9 and the keys above it are the Mac's own.
    WIZARD = Binding(Key.F5, legends.KeyName.F5, legends.What.WIZARD)
    BACK = Binding(Key.ESCAPE, legends.KeyName.ESCAPE, legends.What.BACK)
    # The keys every page has, in the order the F1 dialog lists them. Ctrl+S is Save because a plain
    # letter would be typed into names, and Cmd+S never reaches a terminal program. Open is Ctrl+O,
    # Export is Ctrl+X, Help is F1 and About is F2 for the same reason:
    # everything global has a key that no page could want for itself, so that a page's
    # plain letters are its own and free to change. Undo is Ctrl+Z and redo Ctrl+Y, the pair most
    # people's hands already know, which Textual delivers as keys rather than letting the terminal
    # suspend the program. None of them is in a page's legend, which shows only the page's own
    # keys, because with them there the pattern editor's legend took five lines at 80 columns and
    # pushed the step's description off the screen; the F1 dialog shows them all. On a Mac, F1 and
    # F2 need Fn unless the function keys are set to standard keys.
    # Silence sits before Undo, so that the F1 dialog's two columns of the keys besides F1 keep Undo above Redo.
    # The wizard sits after Silence, so that Undo still starts the second column, above Redo.
    EVERYWHERE = [SAVE, OPEN_SET, EXPORT, SILENCE, WIZARD, UNDO, REDO, HELP, ABOUT, QUIT_NOW]
    IN_HELP = [BACK]
    IN_LEGEND = [BACK]


class MainPage(Page):
    """The main screen: a letter opens each page, the arrows and Enter do the same, and Q quits, here alone."""

    FILE = Binding(Key.F, legends.KeyName.F, labels.PageName.FILE)
    SONGS = Binding(Key.S, legends.KeyName.S, labels.PageName.SONGS)
    PATTERNS = Binding(Key.P, legends.KeyName.P, labels.PageName.PATTERNS)
    GENERATORS = Binding(Key.G, legends.KeyName.G, labels.PageName.GENERATORS)
    SCALES = Binding(Key.Z, legends.KeyName.Z, labels.PageName.SCALES)
    GROOVES = Binding(Key.V, legends.KeyName.V, labels.PageName.GROOVES)
    INSTRUMENTS = Binding(Key.I, legends.KeyName.I, labels.PageName.INSTRUMENTS)
    REGISTERS = Binding(Key.R, legends.KeyName.R, labels.PageName.REGISTERS)
    DRAWS = Binding(Key.D, legends.KeyName.D, labels.PageName.DRAWS)
    ARRANGE = Binding(Key.A, legends.KeyName.A, labels.PageName.ARRANGE)
    # The Real Time switch, a cell among the pages that turns real-time playback on and off.
    REAL_TIME = Binding(Key.T, legends.KeyName.T, labels.PageName.REAL_TIME)
    # The Open and Export cells take a plain letter here, to save a keystroke, since the main screen's letters are its own
    #. Ctrl+O and Ctrl+X still work, here as everywhere. Save stays Ctrl+S, since S is Songs.
    OPEN_SET_HERE = Binding(Key.O, legends.KeyName.O, legends.What.OPEN_SET)
    EXPORT_HERE = Binding(Key.X, legends.KeyName.X, legends.What.EXPORT)
    # Import MIDI, in the row of actions after Export.
    IMPORT_HERE = Binding(Key.L, legends.KeyName.L, legends.What.IMPORT_MIDI)
    QUIT = Binding(Key.Q, legends.KeyName.Q, legends.What.QUIT)
    SELECT = Binding(keys.ARROWS, legends.KeyName.ARROWS, legends.What.SELECT)
    OPEN = Binding(Key.ENTER, legends.KeyName.ENTER, legends.What.OPEN)
    # Help and About work everywhere and have no cell, so the main screen's legend reminds of them, in lower case.
    FOOTER_HELP = Binding(Key.F1, legends.KeyName.F1, legends.MSG_HELP_FOOTER_WHAT)
    FOOTER_ABOUT = Binding(Key.F3, legends.KeyName.F3, legends.MSG_ABOUT_FOOTER_WHAT)
    # The pages in the order of their cells, four to a row.
    PAGES = [FILE, SONGS, PATTERNS, GENERATORS, SCALES, GROOVES, INSTRUMENTS, REGISTERS, DRAWS, ARRANGE, REAL_TIME]
    IN_HELP = [*PAGES, OPEN_SET_HERE, EXPORT_HERE, IMPORT_HERE, QUIT, SELECT, OPEN]
    IN_LEGEND = [SELECT, OPEN, FOOTER_HELP, FOOTER_ABOUT]


class ListPage(Page):
    """A page of rows with a + row at the bottom: the keys every list of named things shares, and the keys of a search."""

    SELECT = Binding(keys.ARROWS_UP_DOWN, legends.KeyName.UP_DOWN, legends.What.SELECT)
    ADD = Binding(Key.A, legends.KeyName.A, legends.What.ADD)
    # Enter on the + row adds, as A does on any row.
    ADD_HERE = Binding(Key.ENTER, legends.KeyName.ENTER, legends.What.ADD)
    EDIT = Binding(Key.ENTER, legends.KeyName.ENTER, legends.What.EDIT)
    # F2 renames too, as on Windows; N stays, since a stock Mac needs fn for F2.
    RENAME = Binding((Key.N, Key.F2), legends.KeyName.N_F2, legends.What.RENAME)
    COPY = Binding(Key.C, legends.KeyName.C, legends.What.COPY)
    DELETE = Binding(Key.BACKSPACE, legends.KeyName.BACKSPACE, legends.What.DELETE)
    # Move mode: M picks up the row, Up and Down carry it, and Enter, Esc or M drops it where it is.
    MOVE = Binding(Key.M, legends.KeyName.M, legends.What.MOVE)
    CARRY = Binding(Steps(back=(Key.UP,), forward=(Key.DOWN,)), legends.KeyName.UP_DOWN, legends.What.CARRY)
    DROP = Binding(keys.MOVE_DROP_KEYS, legends.KeyName.ENTER_ESC_M, legends.What.DROP)
    SORT = Binding(Key.S, legends.KeyName.S, legends.What.SORT)
    SEARCH = Binding(Key.SLASH, legends.KeyName.SLASH, legends.What.SEARCH)
    # While a search is typed, the page's letters are text.
    SEARCH_CANCEL = Binding(Key.ESCAPE, legends.KeyName.ESCAPE, legends.What.CANCEL)
    SEARCH_TYPE = Binding(keys.SEARCH_CHARACTERS, legends.KeyName.SEARCH_CHARACTERS, legends.What.SEARCH)
    SEARCH_ERASE = Binding(Key.BACKSPACE, legends.KeyName.BACKSPACE, legends.What.ERASE)
    SEARCH_COMPLETE = Binding(Key.TAB, legends.KeyName.TAB, legends.What.COMPLETE)
    SEARCH_KEEP = Binding(Key.ENTER, legends.KeyName.ENTER, legends.What.KEEP)
    SEARCHING = [SEARCH_CANCEL, SEARCH_TYPE, SEARCH_ERASE, SEARCH_COMPLETE, SEARCH_KEEP]
    IN_HELP = [Page.BACK, DROP, SEARCH_CANCEL, ADD_HERE, SELECT, CARRY, SEARCH_TYPE, SEARCH_ERASE, SEARCH_COMPLETE, SEARCH_KEEP, ADD, EDIT, RENAME, COPY, DELETE, MOVE, SORT, SEARCH]
    # The search key works everywhere on a list but stays off the legend.
    IN_LEGEND = IN_HELP[:-1]


class NamedListPage(ListPage):
    """A page listing the named things of one section, with the list keys alone."""


class SongsPage(NamedListPage):
    """The Songs page: Space makes the selected song the current one, and Enter opens its settings."""

    CURRENT = Binding(Key.SPACE, legends.KeyName.SPACE, legends.MSG_MAKE_CURRENT_WHAT)
    SETTINGS = Binding(Key.ENTER, legends.KeyName.ENTER, legends.What.SETTINGS)
    IN_HELP = [
        Page.BACK, ListPage.DROP, ListPage.SEARCH_CANCEL, ListPage.ADD_HERE, ListPage.SELECT, ListPage.CARRY, *ListPage.SEARCHING[1:], ListPage.ADD, CURRENT, SETTINGS,
        ListPage.RENAME, ListPage.COPY, ListPage.DELETE, ListPage.MOVE, ListPage.SORT, ListPage.SEARCH,
    ]
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[ListPage.SEARCH])


class PatternsPage(NamedListPage):
    """The Patterns page, which lists the patterns by group, always sorted, so it neither moves nor sorts: the
    list keys, G, which moves the selected pattern to another group, the keys of a group's heading and of the two buttons that
    add, and L, which plays the selected pattern at once, again and again, until L stops it."""

    LISTEN = Binding(Key.L, legends.KeyName.L, legends.MSG_LISTEN_WHAT)
    STOP_LISTENING = Binding(Key.L, legends.KeyName.L, legends.MSG_STOP_LISTENING_WHAT)
    GROUP = Binding(Key.G, legends.KeyName.G, legends.MSG_GROUP_WHAT)
    # A group's heading opens and closes as a settings page's section does, and PgUp and PgDn jump between the headings.
    TOGGLE_GROUP = Binding(keys.TOGGLE_KEYS, legends.KeyName.SPACE_ENTER, legends.What.TOGGLE)
    NEXT_GROUP = Binding(Steps(back=(Key.PAGE_UP,), forward=(Key.PAGE_DOWN,)), legends.KeyName.PAGE_UP_DOWN, legends.MSG_NEXT_GROUP_WHAT)
    NEW_PATTERN = Binding(Key.ENTER, legends.KeyName.ENTER, legends.MSG_NEW_PATTERN_WHAT)
    NEW_GROUP = Binding(Key.ENTER, legends.KeyName.ENTER, legends.MSG_NEW_GROUP_WHAT)
    # On a group's heading Bksp takes its patterns out of the group and deletes none.
    UNGROUP = Binding(Key.BACKSPACE, legends.KeyName.BACKSPACE, legends.MSG_UNGROUP_WHAT)
    IN_HELP = [
        Page.BACK, ListPage.SEARCH_CANCEL, ListPage.SELECT, *ListPage.SEARCHING[1:], TOGGLE_GROUP, NEW_PATTERN, NEW_GROUP, ListPage.EDIT, GROUP, ListPage.ADD,
        ListPage.RENAME, ListPage.COPY, ListPage.DELETE, UNGROUP, LISTEN, STOP_LISTENING, NEXT_GROUP, ListPage.SEARCH,
    ]
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[ListPage.SEARCH, NEXT_GROUP])


class ScalesPage(NamedListPage):
    """The Scales page, with the list keys alone."""


class GeneratorsPage(ListPage):
    """The Generators page, which lists the generators by type, always sorted, so it neither moves nor sorts: Enter edits one,
    A adds one of a type asked for, the usual keys rename, copy and delete one, and a type's heading opens and closes."""

    # A type's heading opens and closes as a settings page's section does, and PgUp and PgDn jump between the headings.
    TOGGLE_TYPE = Binding(keys.TOGGLE_KEYS, legends.KeyName.SPACE_ENTER, legends.What.TOGGLE)
    NEXT_TYPE = Binding(Steps(back=(Key.PAGE_UP,), forward=(Key.PAGE_DOWN,)), legends.KeyName.PAGE_UP_DOWN, legends.MSG_NEXT_TYPE_WHAT)
    IN_HELP = [
        Page.BACK, ListPage.SEARCH_CANCEL, ListPage.ADD_HERE, ListPage.SELECT, *ListPage.SEARCHING[1:], TOGGLE_TYPE, ListPage.ADD, ListPage.EDIT, ListPage.RENAME, ListPage.COPY,
        ListPage.DELETE, NEXT_TYPE, ListPage.SEARCH,
    ]
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[ListPage.SEARCH, NEXT_TYPE])


class OpenPage(ListPage):
    """The page that opens a set file: Enter opens the file or the directory under the cursor."""

    OPEN = Binding(Key.ENTER, legends.KeyName.ENTER, legends.What.OPEN)
    IN_HELP = [Page.BACK, ListPage.SEARCH_CANCEL, ListPage.SELECT, *ListPage.SEARCHING[1:], OPEN, ListPage.SEARCH]
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[ListPage.SEARCH])


class InstrumentsPage(NamedListPage):
    """The Instruments page, with the list keys alone."""


class GroovesPage(NamedListPage):
    """The Grooves page: a factory groove can only be viewed and copied."""

    VIEW = Binding(Key.ENTER, legends.KeyName.ENTER, legends.MSG_VIEW_WHAT)
    IN_HELP = [
        Page.BACK, ListPage.DROP, ListPage.SEARCH_CANCEL, ListPage.ADD_HERE, ListPage.SELECT, ListPage.CARRY, *ListPage.SEARCHING[1:], ListPage.ADD, VIEW, ListPage.EDIT,
        ListPage.RENAME, ListPage.COPY, ListPage.DELETE, ListPage.MOVE, ListPage.SORT, ListPage.SEARCH,
    ]
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[ListPage.SEARCH])


class ChainEditor(ListPage):
    """The chain editor: its rows are the chain's steps, and N renames the chain itself."""

    CHANGE = Binding(Key.ENTER, legends.KeyName.ENTER, legends.What.CHANGE)
    REMOVE = Binding(Key.BACKSPACE, legends.KeyName.BACKSPACE, legends.What.REMOVE)
    WHEN = Binding(Key.W, Key.W.upper(), legends.What.WHEN)
    IN_HELP = [
        Page.BACK, ListPage.DROP, ListPage.SEARCH_CANCEL, ListPage.ADD_HERE, ListPage.SELECT, ListPage.CARRY, *ListPage.SEARCHING[1:], ListPage.ADD, CHANGE, ListPage.COPY, REMOVE,
        ListPage.MOVE, ListPage.RENAME, WHEN, ListPage.SEARCH,
    ]
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[ListPage.SEARCH])


class GeneratorListPage(ListPage):
    """The chains a clip, a scene or a track runs: A adds one, U and D move it, Bksp takes it out of the list."""

    REMOVE = Binding(Key.BACKSPACE, legends.KeyName.BACKSPACE, legends.What.REMOVE)
    IN_HELP = [Page.BACK, ListPage.DROP, ListPage.SEARCH_CANCEL, ListPage.ADD_HERE, ListPage.SELECT, ListPage.CARRY, *ListPage.SEARCHING[1:], ListPage.ADD, REMOVE, ListPage.MOVE, ListPage.SEARCH]
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[ListPage.SEARCH])


class FieldPage(Page):
    """A page of settings: Up and Down pick a field, Left and Right change its value, and what Enter and Bksp do is said by the field."""

    SELECT = Binding(keys.ARROWS_UP_DOWN, legends.KeyName.UP_DOWN, legends.What.SELECT)
    # [ dec and ] inc, the one adjust system, named the same way everywhere; Left and Right do the same, off the legend.
    LESS = Binding((Key.LEFT, *keys.LESS_KEYS), legends.KeyName.LEFT_BRACKET, legends.What.LESS)
    MORE = Binding((Key.RIGHT, *keys.MORE_KEYS), legends.KeyName.RIGHT_BRACKET, legends.What.MORE)
    # A field that's true or false answers to Space and Enter alike.
    TOGGLE = Binding(keys.TOGGLE_KEYS, legends.KeyName.SPACE_ENTER, legends.What.TOGGLE)
    # What Enter and Bksp do depends on the field, which says so itself: these words stand for the field's own.
    ENTER = Binding(Key.ENTER, legends.KeyName.ENTER, legends.What.EDIT)
    CLEAR = Binding(Key.BACKSPACE, legends.KeyName.BACKSPACE, legends.What.CLEAR)
    # On a page with sections, PgUp and PgDn jump between their headings, as in the pattern editor's rows.
    SECTION = Binding(Steps(back=(Key.PAGE_UP,), forward=(Key.PAGE_DOWN,)), legends.KeyName.PAGE_UP_DOWN, legends.MSG_NEXT_SECTION_WHAT)
    # F2 renames from any field of a page that has a Name, as on Windows; off the legend, where Enter on Name says rename.
    RENAME = Binding(Key.F2, legends.KeyName.F2, legends.What.RENAME)
    # On the row of buttons under the settings, Left and Right move along it.
    ALONG_BUTTONS = Binding(keys.ARROWS_LEFT_RIGHT, legends.KeyName.LEFT_RIGHT, legends.What.SELECT)
    # In a row of cells side by side, Left and Right move between the cells, and step nothing.
    ALONG_CELLS = Binding(keys.ARROWS_LEFT_RIGHT, legends.KeyName.LEFT_RIGHT, legends.What.MOVE)
    IN_HELP = [Page.BACK, SELECT, ALONG_BUTTONS, ALONG_CELLS, LESS, MORE, TOGGLE, ENTER, CLEAR, SECTION, RENAME]
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[RENAME])


class WizardPage(FieldPage):
    """The song wizard: a tree of its parts at the left and the settings of the part under the cursor at the right.
    In the tree, Up and Down move, Left and Right close and open a part, and ENTER or Tab moves into the settings; there the
    settings' own keys work, and ESC or Tab moves back to the tree. ESC in the tree closes the wizard."""

    TREE = Binding(keys.ARROWS_UP_DOWN, legends.KeyName.UP_DOWN, legends.What.MOVE)
    FOLD = Binding(keys.ARROWS_LEFT_RIGHT, legends.KeyName.LEFT_RIGHT, legends.MSG_WIZARD_FOLD_WHAT)
    INTO_FIELDS = Binding((Key.ENTER, Key.TAB), legends.KeyName.ENTER, legends.What.EDIT)
    TO_TREE = Binding((Key.ESCAPE, Key.TAB), legends.KeyName.ESCAPE, legends.MSG_WIZARD_TO_TREE_WHAT)
    CLOSE = Binding(Key.ESCAPE, legends.KeyName.ESCAPE, legends.What.CLOSE)
    # A part that is one of a list, as a section of the form, takes the keys every list has; A also adds from the part that holds the list.
    ADD = Binding(Key.A, legends.KeyName.A, legends.What.ADD)
    INSERT = Binding(Key.I, legends.KeyName.I, legends.What.INSERT)
    COPY = Binding(Key.C, legends.KeyName.C, legends.What.COPY)
    DELETE = Binding(Key.BACKSPACE, legends.KeyName.BACKSPACE, legends.What.DELETE)
    MOVE = Binding(Key.M, legends.KeyName.M, legends.What.MOVE)
    CARRY = Binding(Steps(back=(Key.UP,), forward=(Key.DOWN,)), legends.KeyName.UP_DOWN, legends.What.CARRY)
    DROP = Binding(keys.MOVE_DROP_KEYS, legends.KeyName.ENTER_ESC_M, legends.What.DROP)
    # On a part with something to hear, as the hook, a tune or a section: the part of the song as it would be made, through FluidSynth.
    LISTEN = Binding(Key.L, legends.KeyName.L, legends.MSG_LISTEN_WHAT)
    STOP_LISTENING = Binding(Key.L, legends.KeyName.L, legends.MSG_STOP_LISTENING_WHAT)
    # On a riff or a section's melody: other notes written for it, after a question. On a riff: its name.
    REGENERATE = Binding(Key.R, legends.KeyName.R, legends.MSG_REGENERATE_WHAT)
    RENAME_RIFF = Binding(Key.N, legends.KeyName.N, legends.What.RENAME)
    IN_HELP = [CLOSE, TO_TREE, DROP, TREE, CARRY, FOLD, INTO_FIELDS, INSERT, ADD, COPY, DELETE, MOVE, LISTEN, STOP_LISTENING, REGENERATE, RENAME_RIFF, *FieldPage.IN_HELP[1:]]
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[FieldPage.RENAME])


class FilePage(FieldPage):
    """The File page: N starts a new set and W saves the set under another name."""

    NEW = Binding(Key.N, legends.KeyName.N, legends.MSG_NEW_WHAT)
    SAVE_AS = Binding(Key.W, legends.KeyName.W, legends.MSG_SAVE_AS_WHAT)
    IN_HELP = [*FieldPage.IN_HELP, NEW, SAVE_AS]
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[FieldPage.RENAME])


class SongPage(FieldPage):
    """The Song page, with the settings keys alone."""


class ScalePage(FieldPage):
    """The Scale page, with the settings keys alone."""


class DrawsPage(FieldPage):
    """The Draws page: each draw a section of settings over its strip, where Left and Right move between slots and [ and ] change one."""

    # On a draw's strip, [ and ] change the slot under the cursor, Left and Right moving between slots.
    SLOT_LESS = Binding(keys.LESS_KEYS, legends.KeyName.LEFT_BRACKET, legends.What.LESS)
    SLOT_MORE = Binding(keys.MORE_KEYS, legends.KeyName.RIGHT_BRACKET, legends.What.MORE)
    # On a draw's strip, a digit puts that number in the slot under the cursor at once; ENTER still asks for any number.
    TYPE_SLOT = Binding(keys.DIGITS, legends.KeyName.DIGITS, legends.What.TYPE)
    IN_HELP = [Page.BACK, FieldPage.SELECT, FieldPage.ALONG_CELLS, FieldPage.LESS, FieldPage.MORE, SLOT_LESS, SLOT_MORE, TYPE_SLOT, FieldPage.TOGGLE, FieldPage.ENTER, FieldPage.CLEAR, FieldPage.SECTION]
    IN_LEGEND = IN_HELP


class RegistersPage(FieldPage):
    """The Registers page, a grid of the four registers by their settings: the arrows move over it, stopping at
    every edge, [ and ] make the value under the cursor less and more, and Enter, Space and Bksp act on it as on a settings page."""

    MOVE = Binding(keys.ARROWS, legends.KeyName.ARROWS, legends.What.MOVE)
    LESS = Binding(keys.LESS_KEYS, legends.KeyName.LEFT_BRACKET, legends.What.LESS)
    MORE = Binding(keys.MORE_KEYS, legends.KeyName.RIGHT_BRACKET, legends.What.MORE)
    IN_HELP = [Page.BACK, MOVE, LESS, MORE, FieldPage.TOGGLE, FieldPage.ENTER, FieldPage.CLEAR]
    IN_LEGEND = IN_HELP


class ScenePage(FieldPage):
    """The scene page, with the settings keys alone."""


class ClipPage(FieldPage):
    """The clip page: the settings keys, and J, which jumps to the clip's pattern in the pattern editor from any field, since the page has one pattern."""

    OPEN_PATTERN = Binding(Key.J, legends.KeyName.J, legends.MSG_OPEN_PATTERN_WHAT)
    # The clip's list of patterns: A adds one, and M picks up the pattern under the cursor, which Up and Down carry and ENTER, ESC or M drops.
    ADD_PATTERN = Binding(Key.A, legends.KeyName.A, legends.MSG_ADD_PATTERN_WHAT)
    MOVE_PATTERN = Binding(Key.M, legends.KeyName.M, legends.MSG_MOVE_PATTERN_WHAT)
    CARRY = Binding(Steps(back=(Key.UP,), forward=(Key.DOWN,)), legends.KeyName.UP_DOWN, legends.What.CARRY)
    DROP = Binding(keys.MOVE_DROP_KEYS, legends.KeyName.ENTER_ESC_M, legends.What.DROP)
    # Real-time playback: L plays the clip as its scene would, looping until stopped, and L again stops it, with the Play and Stop buttons below the fields doing the same.
    LISTEN = Binding(Key.L, legends.KeyName.L, legends.MSG_LISTEN_WHAT)
    STOP_LISTENING = Binding(Key.L, legends.KeyName.L, legends.MSG_STOP_LISTENING_WHAT)
    IN_HELP = [FieldPage.IN_HELP[0], DROP, *FieldPage.IN_HELP[1:], CARRY, ADD_PATTERN, MOVE_PATTERN, OPEN_PATTERN, LISTEN, STOP_LISTENING]
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[FieldPage.RENAME])


class TrackEditor(FieldPage):
    """The track editor: the settings keys."""

    IN_HELP = FieldPage.IN_HELP
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[FieldPage.RENAME])


class InstrumentEditor(FieldPage):
    """The instrument editor: the settings keys, and K, which opens the Keyswitch Map from any field, as its button does."""

    KEYSWITCH_MAP = Binding(Key.K, legends.KeyName.K, legends.MSG_KEYSWITCH_MAP_WHAT)
    IN_HELP = [*FieldPage.IN_HELP, KEYSWITCH_MAP]
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[FieldPage.RENAME])


class ArpEditor(FieldPage):
    """The arpeggiator's editor, with the settings keys alone."""


class ChainStatementsPage(FieldPage):
    """A chain's statements about the registers, with the settings keys alone."""


class HocketEditor(FieldPage):
    """A Hocket's editor, with the settings keys alone."""


class PluginEditor(FieldPage):
    """A generator's page drawn from its plugin's view, with the settings keys alone."""


class MusicianEditor(FieldPage):
    """A musician's editor, with the settings keys alone."""


class DriftEditor(FieldPage):
    """The drift's editor: the settings keys, except that Left and Right pick version A or B on a row that has both, so only [ and ] change a value."""

    LESS = Binding(keys.LESS_KEYS, legends.KeyName.LEFT_BRACKET, legends.What.LESS)
    MORE = Binding(keys.MORE_KEYS, legends.KeyName.RIGHT_BRACKET, legends.What.MORE)
    VERSION = Binding(keys.ARROWS_LEFT_RIGHT, legends.KeyName.LEFT_RIGHT, legends.MSG_A_OR_B_WHAT)
    IN_HELP = [Page.BACK, FieldPage.SELECT, VERSION, LESS, MORE, FieldPage.TOGGLE, FieldPage.ENTER, FieldPage.CLEAR, FieldPage.SECTION, FieldPage.RENAME, FieldPage.ALONG_BUTTONS]
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[FieldPage.RENAME])


class NotesPage(Page):
    """The Description page: reading, it scrolls and E edits; editing, Tab moves between the text and the Save and Cancel buttons."""

    SCROLL = Binding(Steps(back=(Key.UP,), forward=(Key.DOWN,)), legends.KeyName.UP_DOWN, legends.What.SCROLL)
    EDIT = Binding(Key.E, legends.KeyName.E, legends.What.EDIT)
    CLEAR = Binding(Key.BACKSPACE, legends.KeyName.BACKSPACE, legends.What.CLEAR)
    # While the text is edited.
    CANCEL = Binding(Key.ESCAPE, legends.KeyName.ESCAPE, legends.What.CANCEL)
    MOVE = Binding(keys.ARROWS, legends.KeyName.ARROWS, legends.What.MOVE)
    NEW_LINE = Binding(Key.ENTER, legends.KeyName.ENTER, legends.MSG_NEW_LINE_WHAT)
    ERASE = Binding(Key.BACKSPACE, legends.KeyName.BACKSPACE, legends.What.ERASE)
    TO_BUTTONS = Binding(Key.TAB, legends.KeyName.TAB, legends.MSG_TO_BUTTONS_WHAT)
    # On the Save and Cancel buttons.
    SELECT_BUTTON = Binding(keys.ARROWS_LEFT_RIGHT, legends.KeyName.LEFT_RIGHT, legends.What.SELECT)
    PRESS_BUTTON = Binding(Key.ENTER, legends.KeyName.ENTER, legends.What.CHOOSE)
    TO_TEXT = Binding(Key.TAB, legends.KeyName.TAB, legends.MSG_TO_TEXT_WHAT)
    IN_HELP = [Page.BACK, CANCEL, SCROLL, MOVE, SELECT_BUTTON, NEW_LINE, PRESS_BUTTON, EDIT, CLEAR, ERASE, TO_BUTTONS, TO_TEXT]
    IN_LEGEND = IN_HELP


class StepEditor(Page):
    """A page that edits steps under a cursor, with no keys of its own."""


class OneRowEditor(StepEditor):
    """An editor of one row of numbers: Left and Right move along the row, and Up and Down change the number, since no row lies below the cursor."""

    MOVE = Binding(keys.ARROWS_LEFT_RIGHT, legends.KeyName.LEFT_RIGHT, legends.What.MOVE)
    # [ dec and ] inc as everywhere; Up and Down do the same, off the legend, since no row lies below the cursor.
    LESS = Binding(keys.NUDGE_LESS_KEYS, legends.KeyName.LEFT_BRACKET, legends.What.LESS)
    MORE = Binding(keys.NUDGE_MORE_KEYS, legends.KeyName.RIGHT_BRACKET, legends.What.MORE)
    TYPE = Binding(keys.DIGITS, legends.KeyName.DIGITS, legends.What.TYPE)
    IN_HELP = [Page.BACK, MOVE, LESS, MORE, TYPE]
    IN_LEGEND = IN_HELP


class OffsetsEditor(OneRowEditor):
    """The offsets editor, one row of an arp's offsets."""

    # Space or Enter silences a step that plays and plays a step that's silent.
    SILENT = Binding(keys.TOGGLE_KEYS, legends.KeyName.SPACE_ENTER, legends.MSG_SILENT_WHAT)
    PLAY = Binding(keys.TOGGLE_KEYS, legends.KeyName.SPACE_ENTER, legends.MSG_PLAY_WHAT)
    INSERT_STEP = Binding(Key.I, legends.KeyName.I, legends.What.INSERT_STEP)
    REMOVE_STEP = Binding(Key.D, legends.KeyName.D, legends.What.REMOVE_STEP)
    # Tab moves between the Offset row and the register add rows under it.
    NEXT_ROW = Binding(Key.TAB, legends.KeyName.TAB, legends.MSG_NEXT_ROW_WHAT)
    IN_HELP = [*OneRowEditor.IN_HELP, NEXT_ROW, SILENT, PLAY, INSERT_STEP, REMOVE_STEP]
    IN_LEGEND = IN_HELP


class ChordsEditor(StepEditor):
    """The chord editor, a progression's chords: the arrows move along the chords and between the Chord, #/b and Inv. rows."""

    MOVE = Binding(keys.ARROWS, legends.KeyName.ARROWS, legends.What.MOVE)
    LESS = Binding(keys.LESS_KEYS, legends.KeyName.LEFT_BRACKET, legends.What.LESS)
    MORE = Binding(keys.MORE_KEYS, legends.KeyName.RIGHT_BRACKET, legends.What.MORE)
    TYPE = Binding(keys.DIGITS, legends.KeyName.DIGITS, legends.What.TYPE)
    # On the #/b and Inv. rows, Space or Enter goes to the next choice, as on the pattern editor's cycle rows.
    NEXT = Binding(keys.TOGGLE_KEYS, legends.KeyName.SPACE_ENTER, legends.What.NEXT)
    INSERT_STEP = Binding(Key.I, legends.KeyName.I, legends.What.INSERT_STEP)
    REMOVE_STEP = Binding(Key.D, legends.KeyName.D, legends.What.REMOVE_STEP)
    PICK = Binding(Key.H, legends.KeyName.H, legends.MSG_PICK_PROGRESSION_WHAT)
    # On the Scale, Quality and Tensions rows, Enter opens the Chord dialog, and Space goes to the next choice.
    CHOOSE = Binding(Key.ENTER, legends.KeyName.ENTER, legends.What.CHOOSE)
    NEXT_CHOICE = Binding(Key.SPACE, legends.KeyName.SPACE, legends.What.NEXT)
    CLEAR = Binding(Key.BACKSPACE, legends.KeyName.BACKSPACE, legends.What.CLEAR)
    IN_HELP = [Page.BACK, MOVE, LESS, MORE, TYPE, NEXT, CHOOSE, NEXT_CHOICE, CLEAR, INSERT_STEP, REMOVE_STEP, PICK]
    IN_LEGEND = IN_HELP


class StepRowEditor(StepEditor):
    """A row of on-or-off steps: Left and Right move, Space or Enter turns a step on or off, I and D insert and remove."""

    MOVE = Binding(keys.ARROWS_LEFT_RIGHT, legends.KeyName.LEFT_RIGHT, legends.What.MOVE)
    # As in the one-row editors, Up and Down change the step under the cursor too, off the legend, since no row lies below it.
    TOGGLE = Binding((*keys.TOGGLE_KEYS, *keys.ARROWS_UP_DOWN), legends.KeyName.SPACE_ENTER, legends.What.TOGGLE)
    INSERT_STEP = Binding(Key.I, legends.KeyName.I, legends.What.INSERT_STEP)
    REMOVE_STEP = Binding(Key.D, legends.KeyName.D, legends.What.REMOVE_STEP)
    IN_HELP = [Page.BACK, MOVE, TOGGLE, INSERT_STEP, REMOVE_STEP]
    IN_LEGEND = IN_HELP


class GuitarBarEditor(StepEditor):
    """A Guitarify's bar of strokes: Left and Right move, [ and ] change the stroke, Space or ENTER accents, I and D insert and remove, S the cell length, R a ready-made bar."""

    MOVE = Binding(keys.ARROWS_LEFT_RIGHT, legends.KeyName.LEFT_RIGHT, legends.What.MOVE)
    # Up and Down change the stroke too, off the legend, since no row lies below the cursor.
    LESS = Binding(keys.NUDGE_LESS_KEYS, legends.KeyName.LEFT_BRACKET, legends.What.LESS)
    MORE = Binding(keys.NUDGE_MORE_KEYS, legends.KeyName.RIGHT_BRACKET, legends.What.MORE)
    ACCENT = Binding(keys.TOGGLE_KEYS, legends.KeyName.SPACE_ENTER, legends.MSG_ACCENT_WHAT)
    INSERT_CELL = Binding(Key.I, legends.KeyName.I, legends.What.INSERT_CELL)
    REMOVE_CELL = Binding(Key.D, legends.KeyName.D, legends.What.REMOVE_CELL)
    CELL_LENGTH = Binding(Key.S, legends.KeyName.S, legends.MSG_CELL_LENGTH_WHAT)
    READY_BARS = Binding(Key.R, legends.KeyName.R, legends.MSG_READY_BARS_WHAT)
    IN_HELP = [Page.BACK, MOVE, LESS, MORE, ACCENT, INSERT_CELL, REMOVE_CELL, CELL_LENGTH, READY_BARS]
    IN_LEGEND = IN_HELP


class GrooveEditor(OneRowEditor):
    """The groove editor, one row of a groove's cells, with S for the cell length and N to rename."""

    INSERT_CELL = Binding(Key.I, legends.KeyName.I, legends.What.INSERT_CELL)
    REMOVE_CELL = Binding(Key.D, legends.KeyName.D, legends.What.REMOVE_CELL)
    CELL_LENGTH = Binding(Key.S, legends.KeyName.S, legends.MSG_CELL_LENGTH_WHAT)
    # F2 renames too, as on Windows; N stays, since a stock Mac needs fn for F2.
    RENAME = Binding((Key.N, Key.F2), legends.KeyName.N_F2, legends.What.RENAME)
    IN_HELP = [*OneRowEditor.IN_HELP, INSERT_CELL, REMOVE_CELL, CELL_LENGTH, RENAME]
    IN_LEGEND = IN_HELP


class ArrangePage(Page):
    """Arrange: the keys change with what the cursor is on, a track's name, a scene's name, a clip or a +, so each meaning has a binding of its own."""

    MOVE = Binding(keys.ARROWS, legends.KeyName.ARROWS, legends.What.MOVE)
    # Real-time playback, bound only while the set's Real Time switch is on: Space plays what the cursor is on, or stops it, and the mark before each bar says which.
    PLAY_SONG = Binding(Key.SPACE, legends.KeyName.SPACE, legends.MSG_PLAY_SONG_WHAT)
    PLAY_SCENE = Binding(Key.SPACE, legends.KeyName.SPACE, legends.MSG_PLAY_SCENE_WHAT)
    PLAY_CLIP = Binding(Key.SPACE, legends.KeyName.SPACE, legends.MSG_PLAY_CLIP_WHAT)
    STOP_PLAYING = Binding(Key.SPACE, legends.KeyName.SPACE, legends.MSG_STOP_WHAT)
    STOP_CLIP = Binding(Key.SPACE, legends.KeyName.SPACE, legends.MSG_STOP_CLIP_WHAT)
    # On the row of track names.
    ADD_TRACK = Binding(Key.A, legends.KeyName.A, legends.MSG_ADD_TRACK_WHAT)
    ADD_TRACK_HERE = Binding(Key.ENTER, legends.KeyName.ENTER, legends.MSG_ADD_TRACK_WHAT)
    TRACK_SETTINGS = Binding(Key.ENTER, legends.KeyName.ENTER, legends.MSG_TRACK_SETTINGS_WHAT)
    COPY_TRACK = Binding(Key.C, legends.KeyName.C, legends.MSG_COPY_TRACK_WHAT)
    INSERT_TRACK = Binding(Key.I, legends.KeyName.I, legends.MSG_INSERT_TRACK_WHAT)
    MOVE_TRACK = Binding(Key.M, legends.KeyName.M, legends.MSG_MOVE_TRACK_WHAT)
    DELETE_TRACK = Binding(Key.BACKSPACE, legends.KeyName.BACKSPACE, legends.MSG_DELETE_TRACK_WHAT)
    # On a scene's row.
    ADD_SCENE = Binding(Key.A, legends.KeyName.A, legends.MSG_ADD_SCENE_WHAT)
    ADD_SCENE_HERE = Binding(Key.ENTER, legends.KeyName.ENTER, legends.MSG_ADD_SCENE_WHAT)
    SCENE_SETTINGS = Binding(Key.ENTER, legends.KeyName.ENTER, legends.MSG_SCENE_SETTINGS_WHAT)
    COPY_SCENE = Binding(Key.C, legends.KeyName.C, legends.MSG_COPY_SCENE_WHAT)
    DELETE_SCENE = Binding(Key.BACKSPACE, legends.KeyName.BACKSPACE, legends.MSG_DELETE_SCENE_WHAT)
    INSERT_SCENE = Binding(Key.I, legends.KeyName.I, legends.MSG_INSERT_SCENE_WHAT)
    MOVE_SCENE = Binding(Key.M, legends.KeyName.M, legends.MSG_MOVE_SCENE_WHAT)
    # Move mode on Arrange: M on a scene's name, a track's name or a clip picks it up, the arrows carry it (a clip only
    # into an empty cell), and Enter, Esc or M drops it where it is.
    MOVE_CLIP = Binding(Key.M, legends.KeyName.M, legends.MSG_MOVE_CLIP_WHAT)
    CARRY_SCENE = Binding(Steps(back=(Key.UP,), forward=(Key.DOWN,)), legends.KeyName.UP_DOWN, legends.What.CARRY)
    CARRY_TRACK = Binding(Steps(back=(Key.LEFT,), forward=(Key.RIGHT,)), legends.KeyName.LEFT_RIGHT, legends.What.CARRY)
    CARRY_CLIP = Binding(keys.ARROWS, legends.KeyName.ARROWS, legends.What.CARRY)
    DROP = Binding(keys.MOVE_DROP_KEYS, legends.KeyName.ENTER_ESC_M, legends.What.DROP)
    # On a clip, or the empty cell where one would be.
    ADD_CLIP = Binding(Key.ENTER, legends.KeyName.ENTER, legends.MSG_ADD_CLIP_WHAT)
    # B on an empty cell makes a blank pattern named after the track, puts a clip of it there and opens it, as Live makes a new clip in an empty slot.
    BLANK_PATTERN = Binding(Key.B, legends.KeyName.B, legends.MSG_BLANK_PATTERN_WHAT)
    EDIT_CLIP = Binding(Key.ENTER, legends.KeyName.ENTER, legends.MSG_EDIT_CLIP_WHAT)
    # P opens the clip's pattern in the pattern editor, chosen over Shift+Enter, which a stock terminal sends as Enter.
    OPEN_PATTERN = Binding(Key.J, legends.KeyName.J, legends.MSG_OPEN_PATTERN_WHAT)
    COPY_CLIP = Binding(Key.C, legends.KeyName.C, legends.MSG_COPY_CLIP_WHAT)
    DELETE_CLIP = Binding(Key.BACKSPACE, legends.KeyName.BACKSPACE, legends.MSG_DELETE_CLIP_WHAT)
    PASTE_CLIP = Binding(Key.V, legends.KeyName.V, legends.MSG_PASTE_CLIP_WHAT)
    # A clip's track moves with the same keys as on the track's name, listed last on a clip, after the scene's keys.
    # With Real Time on, the visualizer over the clip area: the key steps through its modes and back to
    # the clips, from anywhere on the page, and while it shows, Esc brings the clips back rather than leaving the page.
    VISUALIZER = Binding(Key.Z, legends.KeyName.Z, legends.MSG_VISUALIZER_WHAT)
    # Fracture: after a question, every clip of the song gets a pattern of its own, so that sections that shared one can be edited apart.
    FRACTURE = Binding(Key.F, legends.KeyName.F, legends.MSG_FRACTURE_WHAT)
    # While the visualizer shows, [ and ] step to the mode before or after, going round.
    STEP_VISUALIZER = Binding(Steps(back=(Key.LEFT_BRACKET,), forward=(Key.RIGHT_BRACKET,)), legends.KeyName.BRACKETS, legends.MSG_STEP_VISUALIZER_WHAT)
    # The details view: D shows, under every bar, the chains and generators and the settings that aren't
    # their defaults, widening the columns to fit, with coloured dividers between the tracks, and D again hides them.
    SHOW_DETAILS = Binding(Key.D, legends.KeyName.D, legends.MSG_SHOW_DETAILS_WHAT)
    HIDE_DETAILS = Binding(Key.D, legends.KeyName.D, legends.MSG_HIDE_DETAILS_WHAT)
    # Tab on a track's name, a scene's name or a clip, opens that cell's details if they aren't showing and locks into it:
    # Up and Down pick a chain, a generator, or a line naming a scale, an instrument or a groove, shown in brackets, Enter opens its page,
    # and Tab again or Esc leaves, closing the cell's details in the usual view, Esc closing the topmost thing as everywhere.
    INTO_DETAILS = Binding(Key.TAB, legends.KeyName.TAB, legends.MSG_INTO_DETAILS_WHAT)
    OUT_OF_DETAILS = Binding(Key.TAB, legends.KeyName.TAB, legends.MSG_OUT_OF_DETAILS_WHAT)
    PICK_DETAIL = Binding(keys.ARROWS_UP_DOWN, legends.KeyName.UP_DOWN, legends.What.SELECT)
    OPEN_DETAIL = Binding(Key.ENTER, legends.KeyName.ENTER, legends.MSG_OPEN_DETAIL_WHAT)
    # On the + under a cell's chains Enter adds a chain to the cell, and on a chain's line Bksp takes it out of the cell.
    ADD_CHAIN = Binding(Key.ENTER, legends.KeyName.ENTER, legends.MSG_ADD_CHAIN_WHAT)
    REMOVE_CHAIN = Binding(Key.BACKSPACE, legends.KeyName.BACKSPACE, legends.MSG_REMOVE_CHAIN_WHAT)
    # While locked into a cell, D closes every detail and leaves the cell, and Esc leaves the cell.
    CLOSE_DETAILS = Binding(Key.D, legends.KeyName.D, legends.MSG_CLOSE_DETAILS_WHAT)
    # P on a scene's name opens Scene View, an Inset Window of every track's notes in the scene; inside it only P closes
    # it, Tab switches between as written and as played, the arrows move its cursor, and Esc closes it as P does.
    SCENE_VIEW = Binding(Key.P, legends.KeyName.P, legends.MSG_SCENE_VIEW_WHAT)
    CLOSE_INSET = Binding(Key.P, legends.KeyName.P, legends.MSG_CLOSE_INSET_WHAT)
    # V switches between as written and as played, PgUp and PgDn jump its cursor a bar, and [ and ] scroll the sidebar,
    # so that Tab keeps its one meaning of the next part of a page.
    TO_PLAYED = Binding(Key.V, legends.KeyName.V, legends.MSG_TO_PLAYED_WHAT)
    TO_WRITTEN = Binding(Key.V, legends.KeyName.V, legends.MSG_TO_WRITTEN_WHAT)
    INSET_BARS = Binding(Steps(back=(Key.PAGE_UP,), forward=(Key.PAGE_DOWN,)), legends.KeyName.PAGE_UP_DOWN, legends.MSG_JUMP_BAR_WHAT)
    INSET_MOVE = Binding(keys.ARROWS, legends.KeyName.ARROWS, legends.What.MOVE)
    ESCAPE_INSET = Binding(keys.CANCEL_KEYS, legends.KeyName.ESCAPE, legends.MSG_CLOSE_INSET_ESC_WHAT)
    # In Scene View, [ and ] switch between as written and as played, - and = draw each sixteenth narrower or wider, and PgUp and PgDn scroll the sidebar of the tracks' details.
    INSET_ZOOM = Binding(Steps(back=(Key.MINUS,), forward=(Key.EQUALS,)), legends.KeyName.MINUS_EQUALS, legends.MSG_ZOOM_WHAT)
    INSET_SCROLL = Binding(Steps(back=(Key.LEFT_BRACKET,), forward=(Key.RIGHT_BRACKET,)), legends.KeyName.BRACKETS, legends.MSG_SCROLL_SIDEBAR_WHAT)
    ESCAPE_CELL = Binding(keys.CANCEL_KEYS, legends.KeyName.ESCAPE, legends.MSG_LEAVE_CELL_WHAT)
    TO_CLIPS = Binding(keys.CANCEL_KEYS, legends.KeyName.ESCAPE, legends.MSG_TO_CLIPS_WHAT)
    IN_HELP = [
        Page.BACK, DROP, TO_CLIPS, ESCAPE_CELL, ESCAPE_INSET, CLOSE_INSET, INSET_MOVE, INSET_BARS, TO_PLAYED, TO_WRITTEN, INSET_ZOOM, INSET_SCROLL, STEP_VISUALIZER, OUT_OF_DETAILS, MOVE, CARRY_SCENE, CARRY_TRACK, CARRY_CLIP, PICK_DETAIL, OPEN_DETAIL, ADD_CHAIN, REMOVE_CHAIN, CLOSE_DETAILS, PLAY_SONG, PLAY_SCENE, PLAY_CLIP, STOP_PLAYING, STOP_CLIP,
        ADD_TRACK, ADD_TRACK_HERE, TRACK_SETTINGS, COPY_TRACK, INSERT_TRACK, MOVE_TRACK, DELETE_TRACK,
        ADD_SCENE, ADD_SCENE_HERE, SCENE_SETTINGS, SCENE_VIEW, COPY_SCENE, DELETE_SCENE, ADD_CLIP, BLANK_PATTERN, EDIT_CLIP, OPEN_PATTERN, MOVE_CLIP, COPY_CLIP, DELETE_CLIP, PASTE_CLIP, INSERT_SCENE,
        MOVE_SCENE,
        SHOW_DETAILS,
        HIDE_DETAILS,
        INTO_DETAILS,
        VISUALIZER,
        FRACTURE,
    ]
    IN_LEGEND = IN_HELP


class PatternEditor(StepEditor):
    """The pattern editor's own keys, whichever view shows: Tab switches the view, S sizes the pattern and R opens Reconfigure."""

    TO_ROLL = Binding(Key.TAB, legends.KeyName.TAB, legends.MSG_TO_ROLL_WHAT)
    TO_EDITOR = Binding(Key.TAB, legends.KeyName.TAB, legends.MSG_TO_EDITOR_WHAT)
    RESIZE = Binding(Key.S, legends.KeyName.S, legends.MSG_SIZE_WHAT)
    RECONFIGURE = Binding(Key.R, legends.KeyName.R, legends.MSG_RECONFIGURE_WHAT)
    # M opens Munge, the list of ways to rearrange, copy and clear the pattern's steps, many of them around the cursor.
    MUNGE = Binding(Key.M, legends.KeyName.M, legends.What.MUNGE)
    # Real-time playback: L plays the pattern at once through the pattern preview, looping until L again stops it.
    LISTEN = Binding(Key.L, legends.KeyName.L, legends.MSG_LISTEN_WHAT)
    STOP_LISTENING = Binding(Key.L, legends.KeyName.L, legends.MSG_STOP_LISTENING_WHAT)
    # F2 renames the pattern, as on Windows, beside rename in R's menu; off the legend.
    RENAME = Binding(Key.F2, legends.KeyName.F2, legends.What.RENAME)
    IN_HELP = [Page.BACK, TO_ROLL, TO_EDITOR, RESIZE, MUNGE, RECONFIGURE, LISTEN, STOP_LISTENING, RENAME]
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[RENAME])


# The pattern editor's two views.

class PatternRows:
    """The rows view of the pattern editor: the cursor's keys, and the keys that insert and remove a step, which its legend shows."""

    MOVE = Binding(keys.ARROWS, legends.KeyName.ARROWS, legends.What.MOVE)
    ENDS = Binding(Steps(back=(Key.HOME,), forward=(Key.END,)), legends.KeyName.HOME_END, legends.What.ENDS)
    SECTION = Binding(Steps(back=(Key.PAGE_UP,), forward=(Key.PAGE_DOWN,)), legends.KeyName.PAGE_UP_DOWN, legends.MSG_NEXT_SECTION_WHAT)
    INSERT_STEP = Binding(Key.I, legends.KeyName.I, legends.What.INSERT_STEP)
    REMOVE_STEP = Binding(Key.D, legends.KeyName.D, legends.What.REMOVE_STEP)
    IN_HELP = [MOVE, ENDS, SECTION, INSERT_STEP, REMOVE_STEP]
    # Home and End are listed by F1 alone.
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[ENDS])


class PianoRoll:
    """The piano roll: one pencil, where every key does one thing, and Space or Enter on a note takes the note out as Bksp does. Its legend keeps to drawing, so X and G are listed by F1 alone. It neither inserts nor removes a step, as Live's piano roll never did.

    Enter draws as Space does, since the two do the same everywhere else, so the chord picker took the free letter H.
    """

    MOVE = Binding(keys.ARROWS, legends.KeyName.ARROWS, legends.What.MOVE)
    ENDS = Binding(Steps(back=(Key.HOME,), forward=(Key.END,)), legends.KeyName.HOME_END, legends.What.ENDS)
    PLACE = Binding(keys.TOGGLE_KEYS, legends.KeyName.SPACE_ENTER, legends.MSG_PLACE_NOTE_WHAT)
    CHORD = Binding(Key.H, legends.KeyName.H, legends.MSG_CHORD_WHAT)
    # [ and ] drag the note's end a step earlier and later, called shrink and stretch, since a note is not a number.
    SHORTER = Binding(Key.LEFT_BRACKET, legends.KeyName.LEFT_BRACKET, legends.MSG_SHRINK_WHAT)
    LONGER = Binding(Key.RIGHT_BRACKET, legends.KeyName.RIGHT_BRACKET, legends.MSG_STRETCH_WHAT)
    # Keyswitch took the knife's letter, and the knife the letter people know for cutting.
    KEYSWITCH = Binding(Key.K, legends.KeyName.K, legends.MSG_KEYSWITCH_WHAT)
    KNIFE = Binding(Key.X, legends.KeyName.X, legends.MSG_SPLIT_WHAT)
    ACCIDENTAL = Binding(Key.PERIOD, legends.KeyName.PERIOD, legends.MSG_ACCIDENTAL_WHAT)
    ERASE = Binding(Key.BACKSPACE, legends.KeyName.BACKSPACE, legends.What.ERASE)
    GRAB = Binding(Key.G, legends.KeyName.G, legends.MSG_GRAB_WHAT)
    ENTRY_SIZE = Binding(Key.E, legends.KeyName.E, legends.MSG_ENTRY_SIZE_WHAT)
    IN_HELP = [MOVE, ENDS, PLACE, CHORD, KEYSWITCH, SHORTER, LONGER, KNIFE, ACCIDENTAL, ERASE, GRAB, ENTRY_SIZE]
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[ENDS, KNIFE, GRAB])


# The rows of the pattern editor's rows view, whose keys work while the cursor is on the row.

class PatternRow:
    """What the rows share: [ and ] step the value under the cursor, with -, + and = working too, as two legend entries, less and more."""

    LESS = Binding(keys.LESS_KEYS, legends.KeyName.LEFT_BRACKET, legends.What.LESS)
    MORE = Binding(keys.MORE_KEYS, legends.KeyName.RIGHT_BRACKET, legends.What.MORE)
    IN_HELP = [LESS, MORE]
    IN_LEGEND = IN_HELP


class DegreeRow(PatternRow):
    """The Degree row: digits type a degree, or on a drum pattern, where the row is called Note, letters type a note."""

    NOTE = Binding(keys.NOTE_LETTER_KEYS, legends.KeyName.NOTE_LETTERS, legends.MSG_NOTE_WHAT)
    # The digits bound, and their name, are the degrees of the scale: 1-7 in a scale of seven notes.
    DEGREE = Binding(keys.DIGITS, legends.KeyName.DIGITS, legends.MSG_DEGREE_WHAT)
    CLEAR = Binding(Key.BACKSPACE, legends.KeyName.BACKSPACE, legends.What.CLEAR)
    # Space puts a note on an empty step, the first degree, and takes the note off a step that has one.
    TOGGLE_NOTE = Binding(Key.SPACE, legends.KeyName.SPACE, legends.What.TOGGLE)
    IN_HELP = [NOTE, DEGREE, PatternRow.LESS, PatternRow.MORE, TOGGLE_NOTE, CLEAR]
    IN_LEGEND = IN_HELP


class OctaveRow(PatternRow):
    """The Octave row: digits type an octave, and Bksp goes back to the default."""

    # The name shown is the range of octaves in the set's octave labels.
    TYPE = Binding(keys.DIGITS, legends.KeyName.DIGITS, legends.MSG_TYPE_OCTAVE_WHAT)
    DEFAULT = Binding(Key.BACKSPACE, legends.KeyName.BACKSPACE, legends.What.DEFAULT)
    IN_HELP = [TYPE, PatternRow.LESS, PatternRow.MORE, DEFAULT]
    IN_LEGEND = IN_HELP


class GateRow(PatternRow):
    """The Gate row: Enter types a length, and Bksp goes back to one step."""

    TYPE = Binding(Key.ENTER, legends.KeyName.ENTER, legends.What.TYPE)
    ONE_STEP = Binding(Key.BACKSPACE, legends.KeyName.BACKSPACE, legends.MSG_ONE_STEP_WHAT)
    IN_HELP = [PatternRow.LESS, PatternRow.MORE, TYPE, ONE_STEP]
    IN_LEGEND = IN_HELP


class NumberRow(PatternRow):
    """A row of numbers, like Velocity: digits type into the cell, and Enter asks for the number."""

    TYPE = Binding(keys.DIGITS, legends.KeyName.DIGITS, legends.What.TYPE)
    ASK = Binding(Key.ENTER, legends.KeyName.ENTER, legends.What.TYPE)
    DEFAULT = Binding(Key.BACKSPACE, legends.KeyName.BACKSPACE, legends.What.DEFAULT)
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
    """A row with a cycle of choices, like Dot: Space or Enter goes to the next, and [ and ] step back and forward as on every row, the one adjust system."""

    NEXT = Binding(keys.TOGGLE_KEYS, legends.KeyName.SPACE_ENTER, legends.What.NEXT)
    CLEAR = Binding(Key.BACKSPACE, legends.KeyName.BACKSPACE, legends.What.CLEAR)
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

    CHOOSE = Binding(Key.ENTER, legends.KeyName.ENTER, legends.What.CHOOSE)
    NEXT = Binding(Key.SPACE, legends.KeyName.SPACE, legends.What.NEXT)
    CLEAR = Binding(Key.BACKSPACE, legends.KeyName.BACKSPACE, legends.What.CLEAR)
    IN_HELP = [CHOOSE, NEXT, PatternRow.LESS, PatternRow.MORE, CLEAR]
    IN_LEGEND = IN_HELP


class TensionRow(ChordRow):
    """The Tension row: Enter opens the Chord dialog, Space goes to the next single tension, and [ and ] step through them."""


class ChordScaleRow(ChordRow):
    """The Scale row: Enter opens the Chord dialog, Space goes to the next scale type, and [ and ] step through them."""


class ToggleRow(PatternRow):
    """A row that's on or off on each step: Space or Enter toggles."""

    TOGGLE = Binding(keys.TOGGLE_KEYS, legends.KeyName.SPACE_ENTER, legends.What.TOGGLE)
    CLEAR = Binding(Key.BACKSPACE, legends.KeyName.BACKSPACE, legends.What.CLEAR)
    IN_HELP = [TOGGLE, CLEAR]
    IN_LEGEND = IN_HELP


class AccentRow(ToggleRow):
    """The Accent row."""


class KeyswitchSlotRow(ToggleRow):
    """A row of the Keyswitch section, one slot of the instrument's Keyswitch Map."""


class GlideRow(ToggleRow):
    """The Glide row."""


class GrabRow(ToggleRow):
    """The Grab row."""


class SlideRow(ToggleRow):
    """The Slide row."""


class TieRow(ToggleRow):
    """The Tie row."""


class DrawResetRow(ToggleRow):
    """A draw's Reset row, in the Use Draws section."""


class RegisterRow(CycleRow):
    """A register's +Note or +Vel row: Space or Enter cycles add, subtract and off, and [ and ] step back and forward."""


class StatementRow(PatternRow):
    """A row of a step's statement about the registers: Enter opens the picker of the part, Space goes to the next choice or number, and [ and ] step."""

    CHOOSE = Binding(Key.ENTER, legends.KeyName.ENTER, legends.What.CHOOSE)
    NEXT = Binding(Key.SPACE, legends.KeyName.SPACE, legends.What.NEXT)
    CLEAR = Binding(Key.BACKSPACE, legends.KeyName.BACKSPACE, legends.What.CLEAR)
    IN_HELP = [CHOOSE, NEXT, PatternRow.LESS, PatternRow.MORE, CLEAR]
    IN_LEGEND = IN_HELP


class SectionRow(PatternRow):
    """A section's heading: Space or Enter opens a closed section and closes an open one."""

    OPEN = Binding(keys.TOGGLE_KEYS, legends.KeyName.SPACE_ENTER, legends.MSG_OPEN_SECTION_WHAT)
    CLOSE = Binding(keys.TOGGLE_KEYS, legends.KeyName.SPACE_ENTER, legends.MSG_CLOSE_SECTION_WHAT)
    IN_HELP = [OPEN, CLOSE]
    IN_LEGEND = IN_HELP


# The dialogs.

class Dialog:
    """What every dialog has: Esc cancels."""

    CANCEL = Binding(keys.CANCEL_KEYS, legends.KeyName.ESCAPE, legends.What.CANCEL)
    IN_HELP = [CANCEL]
    IN_LEGEND = IN_HELP


class StartScreen:
    """The start screen: Enter starts."""

    START = Binding(Key.ENTER, legends.KeyName.ENTER, legends.What.START)
    IN_HELP = [START]
    IN_LEGEND = IN_HELP


class MessageDialog(Dialog):
    """A message: Enter or Esc closes it."""

    CLOSE = Binding((Key.ENTER, *keys.CANCEL_KEYS), legends.KeyName.ENTER, legends.What.CLOSE)
    IN_HELP = [CLOSE]
    IN_LEGEND = IN_HELP


class ConfirmDialog(MessageDialog):
    """A Yes or No question: Left and Right move between the buttons, Enter presses one, and Y and N answer at once."""

    SELECT = Binding(keys.ARROWS_LEFT_RIGHT, legends.KeyName.LEFT_RIGHT, legends.What.SELECT)
    ANSWER = Binding(Key.ENTER, legends.KeyName.ENTER, legends.What.ANSWER)
    YES = Binding(Key.Y, legends.KeyName.Y, legends.What.YES)
    NO = Binding(Key.N, legends.KeyName.N, legends.What.NO)
    IN_HELP = [Dialog.CANCEL, SELECT, ANSWER, YES, NO]
    IN_LEGEND = IN_HELP


class QuitDialog(MessageDialog):
    """Quitting with unsaved changes: Left and Right choose a button, Enter presses it, Q quits without saving, S saves and then quits, and Esc cancels."""

    SELECT = Binding(keys.ARROWS_LEFT_RIGHT, legends.KeyName.LEFT_RIGHT, legends.What.SELECT)
    PRESS = Binding(Key.ENTER, legends.KeyName.ENTER, legends.What.ANSWER)
    QUIT = Binding(Key.Q, legends.KeyName.Q, legends.MSG_QUIT_WITHOUT_SAVING_WHAT)
    SAVE = Binding(Key.S, legends.KeyName.S, legends.MSG_SAVE_THEN_QUIT_WHAT)
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

    SELECT = Binding(keys.ARROWS_UP_DOWN, legends.KeyName.UP_DOWN, legends.What.SELECT)
    CHOOSE_BUTTON = Binding(keys.ARROWS_LEFT_RIGHT, legends.KeyName.LEFT_RIGHT, legends.What.SELECT)
    LESS = Binding((Key.LEFT, *keys.LESS_KEYS), legends.KeyName.LEFT_BRACKET, legends.What.LESS)
    MORE = Binding((Key.RIGHT, *keys.MORE_KEYS), legends.KeyName.RIGHT_BRACKET, legends.What.MORE)
    TOGGLE = Binding(keys.TOGGLE_KEYS, legends.KeyName.SPACE_ENTER, legends.What.TOGGLE)
    RENAME = Binding(Key.ENTER, legends.KeyName.ENTER, legends.What.RENAME)
    PRESS = Binding(Key.ENTER, legends.KeyName.ENTER, legends.MSG_PRESS_WHAT)
    IMPORT = Binding(Key.I, legends.KeyName.I, legends.MSG_IMPORT_WHAT)
    IN_HELP = [Dialog.CANCEL, SELECT, CHOOSE_BUTTON, LESS, MORE, TOGGLE, RENAME, PRESS, IMPORT]
    IN_LEGEND = IN_HELP


class NewPatternDialog(Dialog):
    """The New Pattern dialog: Up and Down pick a row, [ and ] step the scale length, where Enter is OK, Space or Enter flips the drum toggle, and on the buttons Left and Right choose and Enter presses."""

    SELECT = Binding(keys.ARROWS_UP_DOWN, legends.KeyName.UP_DOWN, legends.What.SELECT)
    CHOOSE_BUTTON = Binding(keys.ARROWS_LEFT_RIGHT, legends.KeyName.LEFT_RIGHT, legends.What.SELECT)
    LESS = Binding((Key.LEFT, *keys.LESS_KEYS), legends.KeyName.LEFT_BRACKET, legends.What.LESS)
    MORE = Binding((Key.RIGHT, *keys.MORE_KEYS), legends.KeyName.RIGHT_BRACKET, legends.What.MORE)
    TOGGLE = Binding(keys.TOGGLE_KEYS, legends.KeyName.SPACE_ENTER, legends.What.TOGGLE)
    OK = Binding(Key.ENTER, legends.KeyName.ENTER, legends.MSG_OK_WHAT)
    PRESS = Binding(Key.ENTER, legends.KeyName.ENTER, legends.MSG_PRESS_WHAT)
    IN_HELP = [Dialog.CANCEL, SELECT, CHOOSE_BUTTON, LESS, MORE, TOGGLE, OK, PRESS]
    IN_LEGEND = IN_HELP


class NewRiffDialog(Dialog):
    """The New Riff dialog: Up and Down pick a row, [ and ] step a choice, where Enter writes the riff, Space or Enter flips the toggle, and on the buttons Left and Right choose and Enter presses."""

    SELECT = Binding(keys.ARROWS_UP_DOWN, legends.KeyName.UP_DOWN, legends.What.SELECT)
    CHOOSE_BUTTON = Binding(keys.ARROWS_LEFT_RIGHT, legends.KeyName.LEFT_RIGHT, legends.What.SELECT)
    LESS = Binding((Key.LEFT, *keys.LESS_KEYS), legends.KeyName.LEFT_BRACKET, legends.What.LESS)
    MORE = Binding((Key.RIGHT, *keys.MORE_KEYS), legends.KeyName.RIGHT_BRACKET, legends.What.MORE)
    TOGGLE = Binding(keys.TOGGLE_KEYS, legends.KeyName.SPACE_ENTER, legends.What.TOGGLE)
    WRITE = Binding(Key.ENTER, legends.KeyName.ENTER, legends.MSG_WRITE_RIFF_WHAT)
    PRESS = Binding(Key.ENTER, legends.KeyName.ENTER, legends.MSG_PRESS_WHAT)
    IN_HELP = [Dialog.CANCEL, SELECT, CHOOSE_BUTTON, LESS, MORE, TOGGLE, WRITE, PRESS]
    IN_LEGEND = IN_HELP


class PromptDialog(Dialog):
    """A prompt for text: Left and Right move the cursor in it."""

    MOVE = Binding(keys.ARROWS_LEFT_RIGHT, legends.KeyName.LEFT_RIGHT, legends.What.MOVE)
    DONE = Binding(Key.ENTER, legends.KeyName.ENTER, legends.What.DONE)
    ERASE = Binding(Key.BACKSPACE, legends.KeyName.BACKSPACE, legends.What.ERASE)
    IN_HELP = [Dialog.CANCEL, MOVE, DONE, ERASE]
    IN_LEGEND = IN_HELP


class ChoiceDialog(Dialog):
    """A picker, which searches as you type: Tab completes and Bksp erases once something is typed."""

    MOVE = Binding(keys.ARROWS_UP_DOWN, legends.KeyName.UP_DOWN, legends.What.MOVE)
    CHOOSE = Binding(Key.ENTER, legends.KeyName.ENTER, legends.What.CHOOSE)
    SEARCH = Binding(keys.SEARCH_CHARACTERS, legends.KeyName.SEARCH_CHARACTERS, legends.What.SEARCH)
    ERASE = Binding(Key.BACKSPACE, legends.KeyName.BACKSPACE, legends.What.ERASE)
    COMPLETE = Binding(Key.TAB, legends.KeyName.TAB, legends.What.COMPLETE)
    IN_HELP = [Dialog.CANCEL, MOVE, CHOOSE, SEARCH, ERASE, COMPLETE]
    IN_LEGEND = IN_HELP


class GroupedChoiceDialog(ChoiceDialog):
    """A picker under headings: Space or Enter opens and closes a heading, PgUp and PgDn jump between headings, and typing searches every choice."""

    OPEN = Binding(keys.TOGGLE_KEYS, legends.KeyName.SPACE_ENTER, legends.What.OPEN)
    CLOSE = Binding(keys.TOGGLE_KEYS, legends.KeyName.SPACE_ENTER, legends.What.CLOSE)
    HEADING = Binding(Steps(back=(Key.PAGE_UP,), forward=(Key.PAGE_DOWN,)), legends.KeyName.PAGE_UP_DOWN, legends.MSG_NEXT_SECTION_WHAT)
    START_SEARCH = Binding(keys.SEARCH_STARTERS, legends.KeyName.SEARCH_CHARACTERS, legends.What.SEARCH)
    IN_HELP = [Dialog.CANCEL, ChoiceDialog.MOVE, OPEN, CLOSE, ChoiceDialog.CHOOSE, HEADING, START_SEARCH, ChoiceDialog.SEARCH, ChoiceDialog.ERASE, ChoiceDialog.COMPLETE]
    IN_LEGEND = IN_HELP


class SoundDialog(Dialog):
    """The Sound dialog: Up and Down move, Space or Enter opens a group's flyout, where Enter takes a sound and Esc or Left closes it; / searches every
    sound, where Enter goes to the sound found; L tries the sound under the cursor."""

    MOVE = Binding(keys.ARROWS_UP_DOWN, legends.KeyName.UP_DOWN, legends.What.MOVE)
    MOVE_IN_FLYOUT = Binding(keys.ARROWS, legends.KeyName.ARROWS, legends.What.MOVE)
    OPEN = Binding(keys.TOGGLE_KEYS, legends.KeyName.SPACE_ENTER, legends.What.OPEN)
    CHOOSE = Binding(Key.ENTER, legends.KeyName.ENTER, legends.What.CHOOSE)
    # While a flyout or the search is open, Esc closes it alone, the topmost thing.
    CLOSE = Binding(keys.CANCEL_KEYS, legends.KeyName.ESCAPE, legends.What.CLOSE)
    SEARCH = Binding(Key.SLASH, legends.KeyName.SLASH, legends.What.SEARCH)
    TYPE = Binding(keys.SEARCH_CHARACTERS, legends.KeyName.SEARCH_CHARACTERS, legends.What.SEARCH)
    FIND = Binding(Key.ENTER, legends.KeyName.ENTER, legends.What.OPEN)
    ERASE = Binding(Key.BACKSPACE, legends.KeyName.BACKSPACE, legends.What.ERASE)
    COMPLETE = Binding(Key.TAB, legends.KeyName.TAB, legends.What.COMPLETE)
    LISTEN = Binding(Key.L, legends.KeyName.L, legends.MSG_LISTEN_WHAT)
    STOP_LISTENING = Binding(Key.L, legends.KeyName.L, legends.MSG_STOP_LISTENING_WHAT)
    # On the Note row, where the asker's sound plays on one note: [ and ] step the note, a note's name is typed, and Enter sets what was typed or takes the note.
    NOTE_LESS = Binding(keys.LESS_KEYS, legends.KeyName.LEFT_BRACKET, legends.What.LESS)
    NOTE_MORE = Binding(keys.MORE_KEYS, legends.KeyName.RIGHT_BRACKET, legends.What.MORE)
    TYPE_NOTE = Binding(keys.NOTE_CHARACTERS, legends.KeyName.NOTE_LETTERS, legends.MSG_TYPE_NOTE_WHAT)
    TAKE_NOTE = Binding(Key.ENTER, legends.KeyName.ENTER, legends.What.CHOOSE)
    IN_HELP = [Dialog.CANCEL, CLOSE, MOVE, MOVE_IN_FLYOUT, OPEN, CHOOSE, SEARCH, TYPE, FIND, ERASE, COMPLETE, LISTEN, STOP_LISTENING, NOTE_LESS, NOTE_MORE, TYPE_NOTE, TAKE_NOTE]
    IN_LEGEND = IN_HELP


class PickManyDialog(Dialog):
    """A list where several choices can be picked: Up and Down move, Space turns one on or off, Enter finishes and Esc cancels."""

    MOVE = Binding(keys.ARROWS_UP_DOWN, legends.KeyName.UP_DOWN, legends.What.MOVE)
    FLIP = Binding(Key.SPACE, legends.KeyName.SPACE, legends.What.TOGGLE)
    DONE = Binding(Key.ENTER, legends.KeyName.ENTER, legends.What.DONE)
    IN_HELP = [Dialog.CANCEL, MOVE, FLIP, DONE]
    IN_LEGEND = IN_HELP


class KeyswitchMapDialog(Dialog):
    """An instrument's Keyswitch Map: Up and Down move through the ten slots and down to the buttons, Left and Right move between the slot's name, where Enter renames, and its note, N names the slot from either, Enter opens its note picker, Bksp empties it, O is OK and Esc is CANCEL.

    On the buttons, Left and Right choose one and Enter presses it. In the note picker, drawn over the map, Left and Right move along the octave's keys, Up and Down change the octave, Enter takes the note and Esc closes the picker with nothing changed.
    """

    MOVE = Binding(keys.ARROWS_UP_DOWN, legends.KeyName.UP_DOWN, legends.What.MOVE)
    RENAME = Binding((Key.N, Key.F2), legends.KeyName.N_F2, legends.What.RENAME)
    NOTE = Binding(Key.ENTER, legends.KeyName.ENTER, legends.MSG_KEYSWITCH_NOTE_WHAT)
    # The cursor is on a slot's name or its note: Enter renames on the name and opens the note picker on the note, and the legend says which arrow reaches the other.
    TO_NOTE = Binding(Key.RIGHT, legends.KeyName.TO_THE_RIGHT, legends.MSG_KEYSWITCH_NOTE_WHAT)
    TO_NAME = Binding(Key.LEFT, legends.KeyName.TO_THE_LEFT, legends.MSG_KEYSWITCH_NAME_WHAT)
    RENAME_HERE = Binding(Key.ENTER, legends.KeyName.ENTER, legends.What.RENAME)
    CLEAR = Binding(Key.BACKSPACE, legends.KeyName.BACKSPACE, legends.What.CLEAR)
    OK = Binding(Key.O, legends.KeyName.O, legends.MSG_OK_WHAT)
    ALONG_BUTTONS = Binding(keys.ARROWS_LEFT_RIGHT, legends.KeyName.LEFT_RIGHT, legends.What.SELECT)
    PRESS = Binding(Key.ENTER, legends.KeyName.ENTER, legends.What.ANSWER)
    PICK_NOTE = Binding(keys.ARROWS_LEFT_RIGHT, legends.KeyName.LEFT_RIGHT, legends.MSG_KEYSWITCH_NOTE_WHAT)
    PICK_OCTAVE = Binding(keys.ARROWS_UP_DOWN, legends.KeyName.UP_DOWN, legends.MSG_KEYSWITCH_OCTAVE_WHAT)
    TAKE_NOTE = Binding(Key.ENTER, legends.KeyName.ENTER, legends.What.CHOOSE)
    CLOSE_PICKER = Binding(keys.CANCEL_KEYS, legends.KeyName.ESCAPE, legends.What.CLOSE)
    IN_HELP = [Dialog.CANCEL, MOVE, TO_NOTE, TO_NAME, RENAME, RENAME_HERE, NOTE, CLEAR, OK, ALONG_BUTTONS, PRESS, PICK_NOTE, PICK_OCTAVE, TAKE_NOTE, CLOSE_PICKER]
    IN_LEGEND = all_but(bindings=IN_HELP, hidden=[Dialog.CANCEL, OK])


class RowDialog(Dialog):
    """The Row dialog, one row of numbers: Left and Right move, [ and ] change the number, I inserts a cell and D removes one, Bksp puts back the usual row, Enter is OK and Esc is CANCEL."""

    MOVE = Binding(keys.ARROWS_LEFT_RIGHT, legends.KeyName.LEFT_RIGHT, legends.What.MOVE)
    LESS = Binding(keys.NUDGE_LESS_KEYS, legends.KeyName.LEFT_BRACKET, legends.What.LESS)
    MORE = Binding(keys.NUDGE_MORE_KEYS, legends.KeyName.RIGHT_BRACKET, legends.What.MORE)
    INSERT_CELL = Binding(Key.I, legends.KeyName.I, legends.What.INSERT_CELL)
    REMOVE_CELL = Binding(Key.D, legends.KeyName.D, legends.What.REMOVE_CELL)
    USUAL = Binding(Key.BACKSPACE, legends.KeyName.BACKSPACE, legends.MSG_USUAL_ROW_WHAT)
    DONE = Binding(Key.ENTER, legends.KeyName.ENTER, legends.What.DONE)
    IN_HELP = [Dialog.CANCEL, MOVE, LESS, MORE, INSERT_CELL, REMOVE_CELL, USUAL, DONE]
    IN_LEGEND = [MOVE, LESS, MORE, INSERT_CELL, REMOVE_CELL, USUAL]


class KeyswitchDialog(PickManyDialog):
    """The dialog that picks a step's keyswitches: Up and Down move, Space turns the slot under the cursor on or off, a digit turns its slot on or off, Enter is OK and Esc is CANCEL, the two shown as buttons."""

    TOGGLE_SLOT = Binding(keys.DIGITS, legends.KeyName.DIGITS, legends.What.TOGGLE)
    IN_HELP = [Dialog.CANCEL, PickManyDialog.MOVE, PickManyDialog.FLIP, TOGGLE_SLOT, PickManyDialog.DONE]
    IN_LEGEND = [PickManyDialog.MOVE, PickManyDialog.FLIP, TOGGLE_SLOT]


class ChordDialog(Dialog):
    """The Chord dialog, three lists side by side: the arrows move, Tab goes to the next list, Space turns a tension on or off, Space or Enter on a category of scales opens its flyout, where Enter picks, and Enter elsewhere takes the chord."""

    MOVE = Binding(keys.ARROWS, legends.KeyName.ARROWS, legends.What.MOVE)
    NEXT_LIST = Binding(Key.TAB, legends.KeyName.TAB, legends.MSG_NEXT_LIST_WHAT)
    FLIP = Binding(Key.SPACE, legends.KeyName.SPACE, legends.What.TOGGLE)
    CHOOSE = Binding(Key.ENTER, legends.KeyName.ENTER, legends.What.CHOOSE)
    # On a category of scale types, which opens its flyout, and on the row that borrows no scale.
    OPEN = Binding(keys.TOGGLE_KEYS, legends.KeyName.SPACE_ENTER, legends.What.OPEN)
    # While a flyout is open, Esc closes the flyout alone, the topmost thing.
    CLOSE_FLYOUT = Binding(keys.CANCEL_KEYS, legends.KeyName.ESCAPE, legends.What.CLOSE)
    IN_HELP = [Dialog.CANCEL, CLOSE_FLYOUT, MOVE, NEXT_LIST, FLIP, OPEN, CHOOSE]
    IN_LEGEND = IN_HELP


class GridChoiceDialog(ChoiceDialog):
    """A picker laid out as a grid, which all four arrows move over and which doesn't search: Tab and Shift+Tab turn its pages."""

    MOVE = Binding(keys.ARROWS, legends.KeyName.ARROWS, legends.What.MOVE)
    OTHER_PAGE = Binding(Steps(back=(Key.SHIFT_TAB,), forward=(Key.TAB,)), legends.KeyName.TAB_SHIFT_TAB, legends.What.OTHER_PAGE)
    IN_HELP = [Dialog.CANCEL, MOVE, ChoiceDialog.CHOOSE, OTHER_PAGE]
    IN_LEGEND = IN_HELP


class HelpDialog(Dialog):
    """The F1 dialog: Tab, Left and Right turn between its two panels, and F1 closes it like Enter and Esc, off the legend."""

    CLOSE = Binding((Key.ENTER, Key.ESCAPE, Key.F1), legends.KeyName.ENTER_ESCAPE, legends.What.CLOSE)
    OTHER_PANEL = Binding((Key.TAB, *keys.ARROWS_LEFT_RIGHT), legends.KeyName.TAB_ARROWS, legends.What.OTHER_PANEL)
    IN_HELP = [CLOSE, OTHER_PANEL]
    IN_LEGEND = IN_HELP


class AboutDialog(Dialog):
    """The About dialog: Enter or Esc closes it."""

    CLOSE = Binding((Key.ENTER, *keys.CANCEL_KEYS), legends.KeyName.ENTER_ESCAPE, legends.What.CLOSE)
    IN_HELP = [CLOSE]
    IN_LEGEND = IN_HELP
