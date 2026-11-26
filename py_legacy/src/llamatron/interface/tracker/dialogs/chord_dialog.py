# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Chord dialog: one chord's quality, inversion, tensions and borrowed scale as lists side by side, with the notes doubled an
octave away between the inversion and the tensions where a pattern's step is chosen,
with what the chord comes to said under them as the choice moves, its name in the scale it is
drawn from and its exact notes.

The pattern editor's Chord, Tension and Scale rows, the piano roll and a progression's chord editor all open it, so a chord is
chosen one way everywhere. Up and Down move in a list, Left, Right and Tab go from list to list, Space turns the tension
under the cursor on or off, Enter answers with the three choices and Esc cancels, changing nothing.

The scale list holds categories of scale types, not the fifty types: Space or Enter on a category opens
its flyout, drawn as a box of the dialog's size over it, a little down and to the right, so that the two read as a stack, with the category's scale types, where Up and Down move, Enter picks one and
closes the flyout, and Esc or Left closes it with nothing changed. A flyout is not a dialog: nothing opens over the Chord
dialog. After a pick the cursor goes on to the qualities, so that the next Enter takes the chord.
"""

from llamatron.interface.forms import moves
from llamatron.interface.forms.dialogs import blank, ChoiceRow, heading_said, said_on_one_line
from llamatron.interface.tracker import drawing, keybindings, keys as keys_values
from llamatron.interface.tracker.dialogs import dialog
from llamatron.interface.tracker.dialogs.dialog import Dialog
from llamatron.interface.tracker.drawing import cursor_mark, fit, legend
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.renderers import dialogs as dialog_renderer
from llamatron.model.objects.naming import words
from llamatron.model.schema import file_format
from llamatron.user_strings import labels, marks, messages

# The lists, left to right: quality, inversion, the notes doubled where a pattern's step is chosen, tensions, scale.
QUALITY_LIST = 0
INVERSION_LIST = 1
DOUBLE_LIST = 2
TENSION_LIST = 3
SCALE_LIST = 4
# How wide each list is drawn, and the gap between two: together they take the room an 80 column console leaves inside the dialog.
LIST_WIDTHS = {QUALITY_LIST: 23, INVERSION_LIST: 8, DOUBLE_LIST: 8, TENSION_LIST: 8, SCALE_LIST: 21}
LIST_HEADINGS = {
    QUALITY_LIST: labels.Column.SELECT_QUALITY, INVERSION_LIST: labels.Column.INVERSION, DOUBLE_LIST: labels.Column.DOUBLE,
    TENSION_LIST: labels.Column.TENSIONS, SCALE_LIST: labels.Column.BORROW_SCALE,
}
LIST_GAP = 1
# The room for the sentences under the lists, so that the dialog keeps its height as the choice moves.
SENTENCE_LINES = 3
# The keyboard under the sentences: its lines, the blank line over it, and the lines of the box's top and bottom edges.
KEYBOARD_LINES = 3
KEYBOARD_GAP = 1
DIALOG_BORDERS = 2
# A width no legend reaches, for measuring one laid out on a single line.
WIDEST = 1000
# The fewest cells worth showing of a category's name beside the scale type borrowed.
SHORTEST_CATEGORY_NAME = 4
# The row of the scale list that borrows no scale, above the categories.
NOT_BORROWED_ROW = 0


class ChordChoice:
    """What the Chord dialog answers with: a chord symbol or None, an inversion or None for root position, the tensions as a tuple, lowest first, or None, and a
    scale type or None."""

    __slots__ = ('quality', 'inversion', 'tensions', 'kind', 'doubling')

    def __init__(self, *, quality, tensions, kind, inversion=None, doubling=None):
        self.quality = quality
        self.inversion = inversion
        self.tensions = tensions
        self.kind = kind
        # What the step's Double row plays again an octave away, or None.
        self.doubling = doubling


class ChordDialog(Dialog):
    """Answers with a ChordChoice, or None when cancelled."""

    KEYS = keybindings.ChordDialog
    # How many rows of a list show at once, each list scrolling to keep its cursor's in view: enough for every category and for the longest flyout.
    SHOWN = 10

    def __init__(self, *, title, qualities, quality_names, inversions, categories, current, said, opens_on=QUALITY_LIST, moved=None, keyboard=None, doublings=None):
        """qualities are the chord symbols offered, None first, named by quality_names; inversions the inversions offered, None, root position, first;
        doublings, where a pattern's step is chosen, the values of its Double row, None first, and otherwise None for no such list; categories the scale types offered,
        each a name and its scale types; current the ChordChoice the dialog opens on; and said a function from a ChordChoice
        to the lines said under the lists. moved, when given, is called with the ChordChoice whenever the choice moves, and
        with the choice the dialog opened on when it is cancelled, so that the page underneath can show the chord before it is taken.
        keyboard, when given, is a function from a ChordChoice to the lines of a keyboard showing the chord in its scale, or to None
        where the scale isn't known for certain; the dialog draws it under the sentences where the console has the room."""
        super().__init__()
        self.keyboard = keyboard
        self.title = title
        self.qualities = list(qualities)
        self.quality_names = list(quality_names)
        self.inversions = list(inversions)
        self.doublings = list(doublings or [None])
        # The lists shown, left to right: the doublings only where they are offered.
        self.parts = [QUALITY_LIST, INVERSION_LIST, *([DOUBLE_LIST] if doublings else []), TENSION_LIST, SCALE_LIST]
        self.categories = list(categories)
        self.said = said
        self.moved = moved
        self.opened_on = current
        self.shown = None
        self.picked = set(current.tensions or ())
        self.kind = current.kind
        self.part = opens_on
        self.places = {
            QUALITY_LIST: self.qualities.index(current.quality), INVERSION_LIST: self.inversions.index(current.inversion),
            DOUBLE_LIST: self.doublings.index(current.doubling), TENSION_LIST: 0, SCALE_LIST: self.row_of_kind(current.kind),
        }
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
        """Return the keys that work with the cursor in one of the lists."""
        result = [
            self.bind(self.KEYS.CANCEL, action=self.cancel),
            self.bind(self.KEYS.MOVE, action=self.move_cursor, wants_key=True),
            self.bind(self.KEYS.NEXT_LIST, action=self.next_list),
        ]
        if part == SCALE_LIST:
            return [*result, self.bind(self.KEYS.OPEN, action=self.open_row)]
        if part == TENSION_LIST:
            result.append(self.bind(self.KEYS.FLIP, action=self.toggle))
        return [*result, self.bind(self.KEYS.CHOOSE, action=lambda: self.dismiss(self.choice()))]

    def cancel(self):
        """Close with nothing changed, the page underneath shown the chord it had."""
        # Only a choice that moved away was written underneath; one that never moved, or came back, left the set as it was.
        if self.moved is not None and self.shown is not None and self.shown != chosen_parts(self.opened_on):
            self.moved(self.opened_on)
        self.dismiss(None)

    def draw(self):
        """Draw the dialog, and tell the page underneath when the choice has moved."""
        super().draw()
        if self.moved is None:
            return
        choice = self.choice()
        now = chosen_parts(choice)
        if self.shown is None:
            self.shown = now
        elif now != self.shown:
            self.shown = now
            self.moved(choice)

    def counts(self):
        """Return how many rows each list has, by the list."""
        return {
            QUALITY_LIST: len(self.qualities), INVERSION_LIST: len(self.inversions), DOUBLE_LIST: len(self.doublings),
            TENSION_LIST: len(file_format.TENSIONS), SCALE_LIST: len(self.categories) + 1,
        }

    def move_cursor(self, name):
        """Move within the cursor's list with Up and Down and from list to list with Left and Right, stopping at every edge."""
        if name in keys_values.ARROWS_LEFT_RIGHT:
            place = moves.moved(place=self.parts.index(self.part), name=Key.UP if name == Key.LEFT else Key.DOWN, count=len(self.parts))
            self.part = self.parts[place]
        else:
            self.places[self.part] = moves.moved(place=self.places[self.part], name=name, count=self.counts()[self.part])

    def next_list(self):
        self.part = self.parts[(self.parts.index(self.part) + 1) % len(self.parts)]

    def toggle(self):
        self.picked ^= {list(file_format.TENSIONS)[self.places[TENSION_LIST]]}

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
        elif name not in keys_values.ARROWS_LEFT_RIGHT:
            self.flyout_place = moves.moved(place=self.flyout_place, name=name, count=len(self.kinds_of_row(self.flyout)))

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
        tensions = tuple(tension for tension in file_format.TENSIONS if tension in self.picked) or None
        return ChordChoice(
            quality=self.qualities[self.places[QUALITY_LIST]], inversion=self.inversions[self.places[INVERSION_LIST]], tensions=tensions, kind=self.shown_kind(),
            doubling=self.doublings[self.places[DOUBLE_LIST]],
        )

    def scale_row_text(self, row):
        """Return a row of the scale list: the row that borrows none, or a category, drawn as a button since it opens a flyout, with the scale type
        borrowed after the name of the one that holds it, the only row with the mark."""
        if row == NOT_BORROWED_ROW:
            return messages.MSG_SCALE_NOT_BORROWED
        name, kinds = self.categories[row - 1]
        if self.kind in kinds and row == self.row_of_kind(self.kind):
            # The scale type borrowed is shown whole, and the category's name gives way to it where both don't fit.
            chosen = words(self.kind).title()
            room = LIST_WIDTHS[SCALE_LIST] - len(cursor_mark(False)) - len(marks.MSG_FLYOUT_CHOSEN.format(name=drawing.NOTHING, chosen=chosen))
            if room < SHORTEST_CATEGORY_NAME:
                return marks.MSG_FLYOUT_CHOSEN_ALONE.format(chosen=chosen)
            return marks.MSG_FLYOUT_CHOSEN.format(name=fit(text=name, width=room).rstrip(), chosen=chosen)
        return marks.MSG_FLYOUT_CLOSED.format(name=name)

    def row_text(self, *, part, place):
        """Return one row of a list: a quality's name, an inversion, a tension with its mark, or a scale type."""
        if part == QUALITY_LIST:
            return self.quality_names[place]
        if part == INVERSION_LIST:
            return marks.MSG_NONE_SHOWN if self.inversions[place] is None else str(self.inversions[place])
        if part == DOUBLE_LIST:
            return marks.MSG_NONE_SHOWN if self.doublings[place] is None else labels.MSG_DOUBLINGS[self.doublings[place]]
        if part == TENSION_LIST:
            tension = list(file_format.TENSIONS)[place]
            return (marks.MSG_TOGGLE_ON if tension in self.picked else marks.MSG_FIELD_TOGGLE_OFF) + drawing.SPACE + tension
        return self.scale_row_text(place)

    def list_lines(self, part):
        """Return a list's rows as drawn: SHOWN of them around its cursor, the cursor's marked, in bold in the list the cursor is in."""
        count = self.counts()[part]
        cursor = self.places[part]
        start = max(min(cursor - self.SHOWN // 2, count - self.SHOWN), 0)
        rows = [ChoiceRow(text=self.row_text(part=part, place=place), under_cursor=place == cursor, bold=place == cursor and part == self.part)
                for place in range(start, min(start + self.SHOWN, count))]
        return dialog_renderer.column_lines(rows=rows, width=LIST_WIDTHS[part], height=self.SHOWN)

    def flyout_lines(self, width):
        """Return the open flyout's lines, or None: its category as the heading, a scale type a row with the cursor's marked, what the chord comes to, and its own keys."""
        if self.flyout is None:
            return None
        name, kinds = self.categories[self.flyout - 1]
        rows = [ChoiceRow(text=words(kind).title(), under_cursor=place == self.flyout_place, bold=place == self.flyout_place) for place, kind in enumerate(kinds)]
        lines = [*dialog_renderer.said_lines(paragraphs=[heading_said(marks.MSG_FLYOUT_TITLE.format(name=name)), blank()], width=width), *dialog_renderer.row_lines_of(rows=rows, width=None)]
        # The scale types take the room the lists take underneath, so that the sentences and the keys sit where the dialog's do.
        lines = dialog_renderer.filled(lines=lines, height=self.SHOWN + 4)
        return [*lines, *self.sentences(width), *dialog_renderer.said_lines(paragraphs=[blank()], width=width), *legend(keys=self.keys(), width=width)]

    def legend_lines(self, width):
        """Return the keys of the cursor's list, in as many lines as the list with the most keys takes, so that the dialog keeps its height from list to list."""
        most = max(len(legend(keys=self.list_keys(part), width=width)) for part in self.parts)
        lines = legend(keys=self.list_keys(self.part), width=width)
        return dialog_renderer.filled(lines=lines, height=most)

    def wanted_width(self):
        """Return the width at which every list's keys fit on one line, so that the dialog is one size on every list."""
        return max(legend(keys=self.list_keys(part), width=WIDEST)[0].cell_len for part in self.parts) + dialog.DIALOG_MARGIN

    def sentences(self, width):
        """Return what is said of the choice, as SENTENCE_LINES lines."""
        said = [said_on_one_line(text) for text in self.said(self.choice())][:SENTENCE_LINES]
        return dialog_renderer.filled(lines=dialog_renderer.said_lines(paragraphs=said, width=width), height=SENTENCE_LINES)

    def lines(self, width):
        headings = [LIST_HEADINGS[part] for part in self.parts]
        widths = [LIST_WIDTHS[part] for part in self.parts]
        heading = dialog_renderer.column_headings(names=headings, widths=widths, chosen=self.parts.index(self.part), gap=LIST_GAP)
        columns = [self.list_lines(part) for part in self.parts]
        lists = dialog_renderer.side_by_side(columns=columns, gap=LIST_GAP)
        return [heading, *lists, *dialog_renderer.said_lines(paragraphs=[blank()], width=width), *self.sentences_and_keyboard(width)]

    def has_room_for_keyboard(self, width):
        """Return whether the console is tall enough for the dialog with the keyboard under its sentences."""
        without = 2 + 1 + self.SHOWN + 1 + SENTENCE_LINES + 1 + len(self.legend_lines(width)) + DIALOG_BORDERS
        return self.app.size.height >= without + KEYBOARD_GAP + KEYBOARD_LINES

    def sentences_and_keyboard(self, width):
        """Return what is said of the choice and then, where the scale is known for certain and the console has the room, the
        keyboard, one blank line under the last sentence, the lines left over under it so that the dialog
        keeps its height as the choice moves. The keyboard can't be selected."""
        keyboard = self.keyboard(self.choice()) if self.keyboard is not None and self.has_room_for_keyboard(width) else None
        if keyboard is None:
            return self.sentences(width)
        said = dialog_renderer.said_lines(paragraphs=[said_on_one_line(text) for text in self.said(self.choice())][:SENTENCE_LINES], width=width)
        return [*said, *dialog_renderer.said_lines(paragraphs=[blank()] * KEYBOARD_GAP, width=width), *keyboard, *dialog_renderer.said_lines(paragraphs=[blank()] * (SENTENCE_LINES - len(said)), width=width)]


def chosen_parts(choice):
    """Return what a ChordChoice writes on a step, as one value to compare: its quality, inversion, tensions, scale and doubling."""
    return (choice.quality, choice.inversion, choice.tensions, choice.kind, choice.doubling)
