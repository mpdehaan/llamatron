# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""How the cursor goes through a settings page's form: down its fields in order, into and along a tab box's columns, out at a
column's foot, and along its buttons, and which move brings it nearer a field named by its label.

The navigator asks its page what the form shows (shown_fields), where its cursor is, its tab box and chosen tab, the heading
of a closed section, where the box's fields were drawn (box_spots) and whether its buttons stand one under another; it knows
nothing of how any of it looks.
"""

from llamatron.interface.forms import moves, tab_box as tab_box_nodes
from llamatron.interface.forms.nodes import Button


class FormNavigator:
    """Moves one page's cursor through its form."""

    __slots__ = ('_page',)

    def __init__(self, page):
        self._page = page

    def key_toward(self, target):
        """Return the key that brings the cursor nearer the field or the button with a label, or None when the cursor is on it.

        A field in a closed section is reached as a person reaches it: the way to its section's heading, then the key that opens the section.
        Down from the last field reaches the buttons, which Left and Right go along, or Up and Down where they are stacked.
        """
        labels = [field.label for field in self._page.shown_fields()]
        box = self._page.tab_box()
        if target not in labels and box is not None and box.place_holding(target) is not None:
            return self.key_toward(box.label) or key_toward_tab(here=self._page.chosen_tab(box), there=box.place_holding(target))
        if target not in labels:
            return self.key_toward(self._page.closed_heading_over(target).label) or moves.CHOOSE
        there = labels.index(target)
        here = self._page.cursor.get_place()
        row = self.box_place()
        if self.in_box() and row < there <= row + self.box_field_count():
            return self.key_inside_box(here=here - row - 1, there=there - row - 1)
        first_button = self.first_button_place()
        if here < first_button or there < first_button or self._page.buttons_stacked():
            return moves.toward(here=here, there=there)
        return moves.toward(here=here, there=there, back=moves.LEFT, forward=moves.RIGHT)

    def key_inside_box(self, *, here, there):
        """Return the key that brings the cursor nearer a field of the chosen tab from another: along a column, across a band, or
        toward the band that holds it."""
        spots = self._page.box_spots()
        start = spots[here]
        end = spots[there]
        if start.band == end.band and start.column == end.column:
            return moves.toward(here=start.line, there=end.line)
        if start.band == end.band:
            return key_across(here=start.column, there=end.column)
        return moves.toward(here=start.band, there=end.band)

    def move_cursor(self, name):
        """Move between the fields with Up and Down, Down from the last field reaching the row of buttons and Up from any button
        going back to the last field; Down on the buttons stays. Inside the tab box, Up and Down keep to a column."""
        fields = self._page.shown_fields()
        if not fields:
            return
        # A row is come to at its first cell.
        self._page.cell = 0
        if self.box_place() is not None:
            self.move_with_box(name)
            return
        self.move_in_order(name)

    def move_with_box(self, name):
        """Move with Up or Down on a page with a tab box: inside it, along a column and out at its head or foot; from under it, Up
        comes in at the foot of its first column; elsewhere, as on any page."""
        row = self.box_place()
        count = self.box_field_count()
        place = self._page.cursor.get_place()
        if row < place <= row + count:
            self.move_inside_box(name=name, row=row, here=place - row - 1)
            return
        self.move_in_order(name)
        if name == moves.UP and place > row + count and self._page.cursor.get_place() == row + count:
            self._page.cursor.set_place(row + 1 + tab_box_nodes.spot_from_below(self._page.box_spots()))

    def move_inside_box(self, *, name, row, here):
        """Move with Up or Down from the field at a place among the chosen tab's: to the field it leads to, the row of tabs, or
        what is under the box, staying put where nothing is."""
        spots = self._page.box_spots()
        if name == moves.DOWN:
            there = tab_box_nodes.spot_below(spots=spots, here=here)
        else:
            there = tab_box_nodes.spot_above(spots=spots, here=here)
        if there == tab_box_nodes.ON_TAB_ROW:
            self._page.cursor.set_place(row)
        elif there == tab_box_nodes.BELOW_BOX:
            below = row + len(spots) + 1
            if below < len(self._page.shown_fields()):
                self._page.cursor.set_place(below)
        else:
            self._page.cursor.set_place(row + 1 + there)

    def move_across(self, direction):
        """Move with Left or Right inside the tab box, to the field beside in the column to that side, stopping at the sides."""
        row = self.box_place()
        here = self._page.cursor.get_place() - row - 1
        self._page.cursor.set_place(row + 1 + tab_box_nodes.spot_beside(spots=self._page.box_spots(), here=here, direction=direction))

    def box_place(self):
        """Return the place of the row of tabs among the fields shown, or None on a page with no tab box."""
        for place, field in enumerate(self._page.shown_fields()):
            if field.IS_TAB_ROW:
                return place
        return None

    def box_field_count(self):
        """Return how many fields the chosen tab shows."""
        box = self._page.tab_box()
        return len(box.tabs[self._page.chosen_tab(box)].every_field())

    def in_box(self):
        """Return whether the cursor is on a field inside the tab box, not its row of tabs."""
        row = self.box_place()
        return row is not None and row < self._page.cursor.get_place() <= row + self.box_field_count()

    def move_in_order(self, name):
        """Move with Up or Down through the fields in order, then the buttons."""
        fields = self._page.shown_fields()
        first_button = self.first_button_place()
        if self._page.buttons_stacked():
            # Buttons too wide for one row stand one under another, and Up and Down go through them as through the fields.
            self._page.cursor.move(name=name, count=len(fields))
            return
        if self._page.cursor.get_place() >= first_button:
            if name == moves.UP and first_button:
                self._page.cursor.set_place(first_button - 1)
            return
        self._page.cursor.move(name=name, count=min(first_button + 1, len(fields)))

    def first_button_place(self):
        """Return the place of the page's first button among the fields shown, or how many fields show when there's none: after
        the chosen tab's fields, whose last may be a button of the tab's own."""
        start = page_buttons_start(self._page.shown_fields())
        box = self.box_place()
        if box is None:
            return start
        return max(start, box + 1 + self.box_field_count())

    def move_along_buttons(self, name):
        """Move along the row of buttons with Left and Right, stopping at both ends."""
        first_button = self.first_button_place()
        count = len(self._page.shown_fields()) - first_button
        self._page.cursor.set_place(first_button + moves.moved(place=self._page.cursor.get_place() - first_button, name=name, count=count))


def key_toward_tab(*, here, there):
    """Return the move on the row of tabs that brings the chosen tab nearer another, by their places."""
    if there < here:
        return moves.LEFT
    return moves.RIGHT


def key_across(*, here, there):
    """Return left or right, toward a column of the tab box from another."""
    if there < here:
        return moves.LEFT
    return moves.RIGHT


def page_buttons_start(fields):
    """Return the place where a page's own buttons start among its fields: the run of buttons at the end, which the page draws
    in a row below its settings, or how many fields there are when none end it. A button among a tab's columns stands before
    that run and is drawn in its tab."""
    start = len(fields)
    while start and isinstance(fields[start - 1], Button):
        start -= 1
    return start
