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
"""Every physical key the text UI handles, each named once, and the groups of keys that are bound together.

`Key.L` is the letter l and nothing else: what a key does on a page is said in tui/keybindings.py,
which names these keys, and nowhere else is a key written out. The names are the ones
`pressed_key` in tui/key_table.py gives a key press: Textual's name for a key that types nothing,
like enter or ctrl+s, and the character itself, in lower case, for a key that types one.
"""

import string
from typing import NamedTuple


class Key:
    """Each key, by the one name the tracker knows it by."""

    ENTER = 'enter'
    TAB = 'tab'
    SHIFT_TAB = 'shift+tab'
    BACKSPACE = 'backspace'
    DELETE = 'delete'
    ESCAPE = 'escape'
    SPACE = 'space'
    UP = 'up'
    DOWN = 'down'
    LEFT = 'left'
    RIGHT = 'right'
    SHIFT_UP = 'shift+up'
    SHIFT_DOWN = 'shift+down'
    SHIFT_LEFT = 'shift+left'
    SHIFT_RIGHT = 'shift+right'
    HOME = 'home'
    END = 'end'
    PAGE_UP = 'pageup'
    PAGE_DOWN = 'pagedown'
    F1 = 'f1'
    F2 = 'f2'
    F3 = 'f3'
    F5 = 'f5'
    CTRL_O = 'ctrl+o'
    CTRL_S = 'ctrl+s'
    CTRL_X = 'ctrl+x'
    CTRL_T = 'ctrl+t'
    CTRL_C = 'ctrl+c'
    CTRL_Y = 'ctrl+y'
    CTRL_Z = 'ctrl+z'
    # The letters, which are the same key in upper and lower case.
    A = 'a'
    B = 'b'
    C = 'c'
    D = 'd'
    E = 'e'
    F = 'f'
    G = 'g'
    H = 'h'
    I = 'i'
    J = 'j'
    K = 'k'
    L = 'l'
    M = 'm'
    N = 'n'
    O = 'o'
    P = 'p'
    Q = 'q'
    R = 'r'
    S = 's'
    T = 't'
    U = 'u'
    V = 'v'
    W = 'w'
    X = 'x'
    Y = 'y'
    Z = 'z'
    # The digits.
    DIGIT_0 = '0'
    DIGIT_1 = '1'
    DIGIT_2 = '2'
    DIGIT_3 = '3'
    DIGIT_4 = '4'
    DIGIT_5 = '5'
    DIGIT_6 = '6'
    DIGIT_7 = '7'
    DIGIT_8 = '8'
    DIGIT_9 = '9'
    # The marks that are keys of their own, none of which needs Shift on a US keyboard but the plus.
    PLUS = '+'
    EQUALS = '='
    MINUS = '-'
    SLASH = '/'
    PERIOD = '.'
    LEFT_BRACKET = '['
    RIGHT_BRACKET = ']'


class Steps(NamedTuple):
    """Keys that step something one way or the other, like [ and ] or Home and End: the keys that go back, towards the first, the lower or the shorter, and the keys that go forward."""

    back: tuple
    forward: tuple


# The character a press of the space bar types into text, where Key.SPACE is the key's name.
SPACE_CHARACTER = ' '

# Groups of keys that are bound together.
ARROWS = (Key.LEFT, Key.RIGHT, Key.UP, Key.DOWN)
ARROWS_UP_DOWN = (Key.UP, Key.DOWN)
ARROWS_LEFT_RIGHT = (Key.LEFT, Key.RIGHT)
# Shift with an arrow, which no page binds: not every terminal sends one, and macOS keeps Ctrl with an arrow for itself. The tests check that none is bound.
SHIFT_UP_DOWN = (Key.SHIFT_UP, Key.SHIFT_DOWN)
SHIFT_LEFT_RIGHT = (Key.SHIFT_LEFT, Key.SHIFT_RIGHT)
# Esc cancels a dialog, as it goes back on a page; Tab never cancels or goes back.
CANCEL_KEYS = (Key.ESCAPE,)
# The ends of a pattern in its editor.
HOME_END = (Key.HOME, Key.END)
# Anything that's true or false answers to Space and Enter alike, so that either habit works.
TOGGLE_KEYS = (Key.SPACE, Key.ENTER)
# The keys that end Move mode, leaving what was carried where it is, the user's design.
MOVE_DROP_KEYS = (Key.ENTER, Key.ESCAPE, Key.M)
LETTERS = (
    Key.A, Key.B, Key.C, Key.D, Key.E, Key.F, Key.G, Key.H, Key.I, Key.J, Key.K, Key.L, Key.M,
    Key.N, Key.O, Key.P, Key.Q, Key.R, Key.S, Key.T, Key.U, Key.V, Key.W, Key.X, Key.Y, Key.Z,
)
# The letters that are the names of notes, which type a note on a drum pattern's Note row.
NOTE_LETTER_KEYS = (Key.A, Key.B, Key.C, Key.D, Key.E, Key.F, Key.G)
DIGITS = (Key.DIGIT_0, Key.DIGIT_1, Key.DIGIT_2, Key.DIGIT_3, Key.DIGIT_4, Key.DIGIT_5, Key.DIGIT_6, Key.DIGIT_7, Key.DIGIT_8, Key.DIGIT_9)
# What can be typed into a search: letters, digits, every mark a keyboard types, and a space.
SEARCH_CHARACTERS = (*LETTERS, *DIGITS, *string.punctuation, Key.SPACE)
# ] means more and [ means less wherever a value steps, since neither needs Shift on a US keyboard, which + does. +, = and - still work, off the legend, for the habit of them.
MORE_KEYS = (Key.RIGHT_BRACKET, Key.PLUS, Key.EQUALS)
LESS_KEYS = (Key.LEFT_BRACKET, Key.MINUS)
# In a one-row editor, the offsets and groove editors, Up and Down step the value too, since no row lies below the cursor.
NUDGE_MORE_KEYS = (Key.UP, *MORE_KEYS)
NUDGE_LESS_KEYS = (Key.DOWN, *LESS_KEYS)


class RowSection:
    """The pattern editor's sections of rows under Degree and Octave, each headed by a row that Space or Enter opens or closes, which PgUp and PgDn jump between."""

    BASICS = 'basics'
    # Not 'chord', which is the Chord row's own name.
    CHORD = 'chord_section'
    TIMING = 'timing'
    ADVANCED = 'advanced'
    CC = 'cc'
    REGISTER_MOD = 'register_mod'
    REGISTER_APPLY = 'register_apply'
    REGISTER_COND = 'register_cond'


# The sections open when the program starts, which hold what the first set of rows held before the sections: the rest open as they're wanted and stay open for the session.
OPEN_AT_START = (RowSection.BASICS, RowSection.TIMING)
