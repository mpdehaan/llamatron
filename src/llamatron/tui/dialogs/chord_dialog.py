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

"""The Chord dialog (the user's design): one chord's quality, tensions and borrowed scale as three lists side by side, in the
user's order, with what the chord comes to said under them as the choice moves, its name in the scale it is
drawn from and its exact notes.

The pattern editor's Chord, Tension and Scale rows, the piano roll and a progression's chord editor all open it, so a chord is
chosen one way everywhere. Up and Down move in a list, Left, Right and Tab go from list to list, Space turns the tension
under the cursor on or off, Enter answers with the three choices and Esc cancels, changing nothing.

The scale list holds categories of scale types, not the fifty types (the user's design): Space or Enter on a category opens
its flyout, drawn as a box of the dialog's size over it, a little down and to the right, so that the two read as a stack, with the category's scale types, where Up and Down move, Enter picks one and
closes the flyout, and Esc or Left closes it with nothing changed. A flyout is not a dialog: nothing opens over the Chord
dialog. After a pick the cursor goes on to the qualities, so that the next Enter takes the chord.
"""

from rich.text import Text

from llamatron.composition.file_format import TENSIONS
from llamatron.composition.naming import words
from llamatron.strings.labels import Column
from llamatron.strings.marks import MSG_FIELD_TOGGLE_OFF, MSG_FLYOUT_CHOSEN, MSG_FLYOUT_CLOSED, MSG_FLYOUT_TITLE, MSG_TOGGLE_ON
from llamatron.strings.messages import MSG_SCALE_NOT_BORROWED
from llamatron.tui.dialogs.dialog import DIALOG_MARGIN, Dialog
from llamatron.tui.drawing import NOTHING, SPACE, Style, cursor_mark, fit, legend
from llamatron.tui.key_table import cursor_moved
from llamatron.tui.keys import ARROWS_LEFT_RIGHT, Key
from llamatron.tui import keybindings

# The three lists, left to right, in the user's order, the same wherever a chord is chosen: quality, tensions, scale.
QUALITY_LIST = 0
TENSION_LIST = 1
SCALE_LIST = 2
LISTS = 3
# How wide each list is drawn, and the gap between two.
LIST_WIDTHS = (24, 12, 26)
LIST_GAP = 2
# The room for the sentences under the lists, so that the dialog keeps its height as the choice moves.
SENTENCE_LINES = 3
# A width no legend reaches, for measuring one laid out on a single line.
WIDEST = 1000
# The fewest cells worth showing of a category's name beside the scale type borrowed.
SHORTEST_CATEGORY_NAME = 4
# The row of the scale list that borrows no scale, above the categories.
NOT_BORROWED_ROW = 0


class ChordChoice:
    """What the Chord dialog answers with: a chord symbol or None, the tensions as a tuple, lowest first, or None, and a scale type or None."""

    __slots__ = ('quality', 'tensions', 'kind')

    def __init__(self, *, quality, tensions, kind):
        self.quality = quality
        self.tensions = tensions
        self.kind = kind


class ChordDialog(Dialog):
    """Answers with a ChordChoice, or None when cancelled."""

    KEYS = keybindings.ChordDialog
    # How many rows of a list show at once, each list scrolling to keep its cursor's in view: enough for every category and for the longest flyout.
    SHOWN = 10

    def __init__(self, *, title, qualities, quality_names, categories, current, said, opens_on=QUALITY_LIST, moved=None):
        """qualities are the chord symbols offered, None first, named by quality_names; categories the scale types offered,
        each a name and its scale types; current the ChordChoice the dialog opens on; and said a function from a ChordChoice
        to the lines said under the lists. moved, when given, is called with the ChordChoice whenever the choice moves, and
        with the choice the dialog opened on when it is cancelled, so that the page underneath can show the chord before it is taken."""
        super().__init__()
        self.title = title
        self.qualities = list(qualities)
        self.quality_names = list(quality_names)
        self.categories = list(categories)
        self.said = said
        self.moved = moved
        self.opened_on = current
        self.shown = None
        self.picked = set(current.tensions or ())
        self.kind = current.kind
        self.part = opens_on
        self.places = [self.qualities.index(current.quality), 0, self.row_of_kind(current.kind)]
        # The category whose flyout is open, or None, and the cursor's place in it.
        self.flyout = None
        self.flyout_place = 0

    def keys(self):
        if self.flyout is not None:
            return [
                self.bind(self.KEYS.CLOSE_FLYOUT, action=self.close_flyout),
                self.bind(self.KEYS.MOVE, action=self.move_in_flyout, wants_key=True),
                self.bind(self.KEYS.CHOOSE, action=self.pick_in_flyout),
            ]
        return self.list_keys(self.part)

    def list_keys(self, part):
        """Return the keys that work with the cursor in one of the three lists."""
        result = [
            self.bind(self.KEYS.CANCEL, action=self.cancel),
            self.bind(self.KEYS.MOVE, action=self.move, wants_key=True),
            self.bind(self.KEYS.NEXT_LIST, action=self.next_list),
        ]
        if part == SCALE_LIST:
            return [*result, self.bind(self.KEYS.OPEN, action=self.open_row)]
        if part == TENSION_LIST:
            result.append(self.bind(self.KEYS.FLIP, action=self.flip))
        return [*result, self.bind(self.KEYS.CHOOSE, action=lambda: self.dismiss(self.choice()))]

    def cancel(self):
        """Close with nothing changed, the page underneath shown the chord it had."""
        if self.moved is not None and self.shown is not None:
            self.moved(self.opened_on)
        self.dismiss(None)

    def draw(self):
        """Draw the dialog, and tell the page underneath when the choice has moved."""
        super().draw()
        if self.moved is None:
            return
        choice = self.choice()
        now = (choice.quality, choice.tensions, choice.kind)
        if self.shown is None:
            self.shown = now
        elif now != self.shown:
            self.shown = now
            self.moved(choice)

    def counts(self):
        return (len(self.qualities), len(TENSIONS), len(self.categories) + 1)

    def move(self, name):
        """Move within the cursor's list with Up and Down and from list to list with Left and Right, stopping at every edge."""
        if name in ARROWS_LEFT_RIGHT:
            self.part = cursor_moved(place=self.part, name=Key.UP if name == Key.LEFT else Key.DOWN, count=LISTS)
        else:
            self.places[self.part] = cursor_moved(place=self.places[self.part], name=name, count=self.counts()[self.part])

    def next_list(self):
        self.part = (self.part + 1) % LISTS

    def flip(self):
        self.picked ^= {list(TENSIONS)[self.places[TENSION_LIST]]}

    # The scale: a row that borrows none, then the categories, each with a flyout of its scale types.

    def row_of_kind(self, kind):
        """Return the scale list's row a scale type is found under: the first category holding it, or the row that borrows none."""
        for row, (_, kinds) in enumerate(self.categories):
            if kind in kinds:
                return row + 1
        return NOT_BORROWED_ROW

    def kinds_of_row(self, row):
        return self.categories[row - 1][1]

    def set_kind(self, kind):
        """Borrow a scale type, or none with None, and put the scale list's cursor on the row that holds it."""
        self.kind = kind
        self.places[SCALE_LIST] = self.row_of_kind(kind)

    def open_row(self):
        """Open the flyout of the category under the cursor, on the scale type borrowed when the category holds it; on the row that borrows none, borrow none."""
        row = self.places[SCALE_LIST]
        if row == NOT_BORROWED_ROW:
            self.kind = None
            self.part = QUALITY_LIST
            return
        kinds = self.kinds_of_row(row)
        self.flyout = row
        self.flyout_place = kinds.index(self.kind) if self.kind in kinds else 0

    def close_flyout(self):
        self.flyout = None

    def move_in_flyout(self, name):
        """Move in the flyout with Up and Down, stopping at its edges; Left closes it, and Right does nothing."""
        if name == Key.LEFT:
            self.close_flyout()
        elif name not in ARROWS_LEFT_RIGHT:
            self.flyout_place = cursor_moved(place=self.flyout_place, name=name, count=len(self.kinds_of_row(self.flyout)))

    def pick_in_flyout(self):
        """Borrow the scale type under the flyout's cursor, close the flyout, and go on to the qualities, where Enter takes the chord."""
        self.kind = self.kinds_of_row(self.flyout)[self.flyout_place]
        self.flyout = None
        self.part = QUALITY_LIST

    def shown_kind(self):
        """Return the scale type the sentences speak of: the one under the flyout's cursor while a flyout is open, and otherwise the one borrowed."""
        if self.flyout is None:
            return self.kind
        return self.kinds_of_row(self.flyout)[self.flyout_place]

    def choice(self):
        tensions = tuple(tension for tension in TENSIONS if tension in self.picked) or None
        return ChordChoice(quality=self.qualities[self.places[QUALITY_LIST]], tensions=tensions, kind=self.shown_kind())

    def scale_row_text(self, row):
        """Return a row of the scale list: the row that borrows none, or a category, with the scale type borrowed after the one that holds it."""
        if row == NOT_BORROWED_ROW:
            return MSG_SCALE_NOT_BORROWED
        name, kinds = self.categories[row - 1]
        if self.kind in kinds and row == self.row_of_kind(self.kind):
            # The scale type borrowed is shown whole, and the category's name gives way to it where both don't fit.
            chosen = words(self.kind).title()
            room = LIST_WIDTHS[SCALE_LIST] - len(cursor_mark(False)) - len(MSG_FLYOUT_CHOSEN.format(name=NOTHING, chosen=chosen))
            return MSG_FLYOUT_CHOSEN.format(name=fit(text=name, width=room).rstrip() if room >= SHORTEST_CATEGORY_NAME else NOTHING, chosen=chosen).lstrip()
        return MSG_FLYOUT_CLOSED.format(name=name)

    def row_text(self, *, part, place):
        """Return one row of a list: a quality's name, a tension with its mark, or a scale type."""
        if part == QUALITY_LIST:
            return self.quality_names[place]
        if part == TENSION_LIST:
            tension = list(TENSIONS)[place]
            return (MSG_TOGGLE_ON if tension in self.picked else MSG_FIELD_TOGGLE_OFF) + SPACE + tension
        return self.scale_row_text(place)

    def list_lines(self, part):
        """Return a list's rows as drawn: SHOWN of them around its cursor, the cursor's marked, in bold in the list the cursor is in."""
        count = self.counts()[part]
        cursor = self.places[part]
        start = max(min(cursor - self.SHOWN // 2, count - self.SHOWN), 0)
        width = LIST_WIDTHS[part]
        lines = []
        for place in range(start, start + self.SHOWN):
            if place >= count:
                lines.append(Text(SPACE * width))
                continue
            text = fit(text=cursor_mark(place == cursor) + self.row_text(part=part, place=place), width=width)
            lines.append(Text(text, style=Style.BOLD if place == cursor and part == self.part else NOTHING))
        return lines

    def flyout_lines(self, width):
        """Return the open flyout's lines, or None: its category as the heading, a scale type a row with the cursor's marked, what the chord comes to, and its own keys."""
        if self.flyout is None:
            return None
        name, kinds = self.categories[self.flyout - 1]
        lines = [Text(MSG_FLYOUT_TITLE.format(name=name), style=Style.BOLD), Text(NOTHING)]
        for place, kind in enumerate(kinds):
            lines.append(Text(cursor_mark(place == self.flyout_place) + words(kind).title(), style=Style.BOLD if place == self.flyout_place else NOTHING))
        # The scale types take the room the lists take underneath, so that the sentences and the keys sit where the dialog's do.
        lines += [Text(NOTHING)] * (self.SHOWN + 2 - len(kinds))
        return [*lines, *self.sentences(width), Text(NOTHING), *legend(keys=self.keys(), width=width)]

    def legend_lines(self, width):
        """Return the keys of the cursor's list, in as many lines as the list with the most keys takes, so that the dialog keeps its height from list to list."""
        most = max(len(legend(keys=self.list_keys(part), width=width)) for part in range(LISTS))
        lines = legend(keys=self.list_keys(self.part), width=width)
        return [*lines, *[Text(NOTHING)] * (most - len(lines))]

    def wanted_width(self):
        """Return the width at which every list's keys fit on one line, so that the dialog is one size on every list (the user's design)."""
        return max(legend(keys=self.list_keys(part), width=WIDEST)[0].cell_len for part in range(LISTS)) + DIALOG_MARGIN

    def sentences(self, width):
        """Return what is said of the choice, as SENTENCE_LINES lines."""
        said = [fit(text=text, width=width).rstrip() for text in self.said(self.choice())][:SENTENCE_LINES]
        return [*[Text(text) for text in said], *[Text(NOTHING) for _ in range(SENTENCE_LINES - len(said))]]

    def lines(self, width):
        headings = (Column.SELECT_QUALITY, Column.TENSIONS, Column.BORROW_SCALE)
        heading = Text(NOTHING)
        for part, name in enumerate(headings):
            heading.append(fit(text=SPACE * len(cursor_mark(False)) + name, width=LIST_WIDTHS[part]), style=Style.BOLD if part == self.part else Style.DIM)
            heading.append(SPACE * LIST_GAP if part < LISTS - 1 else NOTHING)
        result = [heading]
        columns = [self.list_lines(part) for part in range(LISTS)]
        for row in range(self.SHOWN):
            line = Text(NOTHING)
            for part in range(LISTS):
                line.append_text(columns[part][row])
                line.append(SPACE * LIST_GAP if part < LISTS - 1 else NOTHING)
            result.append(line)
        result.append(Text(NOTHING))
        return [*result, *self.sentences(width)]
