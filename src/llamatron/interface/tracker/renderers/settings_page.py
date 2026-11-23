# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""How a settings page is drawn: its settings after a blank line, the first section after another, a tab box with its row of
tabs, then its buttons after one blank line, then its remarks after another, scrolled so that the cursor's line shows.

The drawing leaves on the page what moving its cursor needs to know of how it was drawn: whether its buttons stand one under
another (stacked_buttons), how wide its tab box is (box_width) and the first of its lines shown (first_line).
"""

from rich.text import Text

from llamatron.interface.forms import tab_box as tab_box_nodes
from llamatron.interface.forms.nodes import Button, Heading
from llamatron.interface.tracker import drawing
from llamatron.interface.tracker.components.button_row import button_row
from llamatron.interface.tracker.drawing import cursor_mark, Style
from llamatron.interface.tracker.renderers.drawn_lines import DrawnLines
from llamatron.interface.tracker.renderers.fields import field_lines
from llamatron.interface.tracker.renderers.tab_box import box_lines
from llamatron.user_strings import labels as labels_text, marks

# How wide a page's tab box is drawn before the page knows its width.
BOX_WIDTH = 80


class SettingsPageDrawing:
    """Draws one settings page, a FieldPage, as Rich lines."""

    __slots__ = ('_page',)

    def __init__(self, page):
        self._page = page

    def body(self, *, width, height):
        """Return the settings after a blank line, the first section after another, then the page's buttons after one blank line, then its notes after another.

        The labels take the width of the longest of every field, shown or not, so that opening a
        section never moves the values beside them.
        """
        fields = self._page.shown_fields()
        self._page.field()
        drawn = DrawnLines()
        drawn.blank()
        self.draw_settings(drawn=drawn, fields=fields, width=width)
        self.draw_buttons(drawn=drawn, buttons=fields[self._page.first_button_place():], width=width)
        remarks = self._page.remarks(width)
        if remarks:
            drawn.blank()
            drawn.add(remarks)
        return self.window_of_lines(lines=drawn.get_lines(), selected=drawn.get_selected(), height=height)

    def draw_settings(self, *, drawn, fields, width):
        """Add the settings to the drawing, each field's lines, a tab box with its row of tabs, and a blank line before a section's
        heading and after a field that leaves one."""
        label_width = self.label_width()
        cursor = self._page.cursor.get_place()
        seen_heading = False
        inside_box = 0
        for place, field in enumerate(fields[:self._page.first_button_place()]):
            if inside_box:
                # The chosen tab's fields are drawn with the box, by its row of tabs.
                inside_box -= 1
                continue
            if field.IS_TAB_ROW:
                inside_box, box, box_selected = self.box_at(place=place, cursor=cursor, width=width)
                drawn.add(box, selected_at=box_selected)
                drawn.blank()
                continue
            if isinstance(field, Heading) and (not seen_heading or self._page.HEADINGS_APART):
                seen_heading = True
                if place:
                    drawn.blank()
            selected_at = field.SELECTED_LINE if place == cursor else None
            drawn.add(field_lines(field, page=self._page, here=place == cursor, label_width=label_width, width=width), selected_at=selected_at)
            if field.MAY_LEAVE_A_GAP and self.has_gap_after(place=place, field=field, fields=fields):
                drawn.blank()

    def label_width(self):
        """Return how wide the settings' labels are drawn: as wide as the longest of every field, shown or not, and a space
        either side, so that opening a section never moves the values beside them."""
        return max((len(field.get_drawn_label(self._page)) for field in self._page.every_field() if not isinstance(field, Button) and not field.IS_TAB_BOX), default=0) + 2

    def draw_buttons(self, *, drawn, buttons, width):
        """Add the page's buttons to the drawing, in one row under the settings after a blank line, boxed as the dialogs' are."""
        if not buttons:
            return
        first_button = self._page.first_button_place()
        place = self._page.cursor.get_place() - first_button
        drawn.blank()
        row = self.row_of_buttons(buttons=buttons, selected=place, width=width)
        # Whether the buttons stand one under another is known once the row is made, so the line the cursor is on is too.
        selected_at = None
        if place >= 0:
            selected_at = place if self._page.buttons_stacked() else 1
        drawn.add(row, selected_at=selected_at)

    def row_of_buttons(self, *, buttons, selected, width):
        """Return the lines of the page's buttons: boxed in one row where the row fits the width, and otherwise one a line, each
        in brackets, the selected one marked and bold."""
        keys_and_names = [(button.key_name, button.label) for button in buttons]
        row = [Text(drawing.INDENT) + line for line in button_row(buttons=keys_and_names, selected=selected)]
        self._page.stacked_buttons = width is not None and max(line.cell_len for line in row) > width
        if not self._page.stacked_buttons:
            return row
        lines = []
        for place, button in enumerate(buttons):
            line = Text(no_wrap=True)
            line.append(cursor_mark(place == selected))
            line.append(marks.MSG_STACKED_BUTTON.format(name=button.label), style=Style.BOLD if place == selected else Style.PLAIN)
            lines.append(line)
        return lines

    def box_at(self, *, place, cursor, width):
        """Return how many of the chosen tab's fields follow the row of tabs at a place, the box's lines, and the place of the
        cursor's line among them, or None where the cursor is outside the box."""
        box = self._page.tab_box()
        chosen = self._page.chosen_tab(box)
        count = len(box.tabs[chosen].every_field())
        inside = None
        if cursor == place:
            inside = tab_box_nodes.ON_TAB_ROW
        elif place < cursor <= place + count:
            inside = cursor - place - 1
        self._page.box_width = width or BOX_WIDTH
        lines, selected = box_lines(page=self._page, box=box, chosen=chosen, cursor=inside, width=self._page.box_width)
        return count, lines, selected

    def has_gap_after(self, *, place, field, fields):
        """Return whether a blank line follows a setting: a Name that starts the page before its other settings, and the last of a list."""
        if place == 0 and field.label == labels_text.MSG_NAME_LABEL and len(fields) > 1 and not isinstance(fields[1], Button):
            return True
        return self._page.ends_a_list(field)

    def window_of_lines(self, *, lines, selected, height):
        """Return the lines that fit the height, scrolled so that the selected line shows, a settings page being taller than a console at times."""
        if height is None or len(lines) <= height:
            self._page.first_line = 0
            return lines
        first = min(max(getattr(self._page, 'first_line', 0), selected - height + 1), selected)
        self._page.first_line = max(min(first, len(lines) - height), 0)
        return lines[self._page.first_line:self._page.first_line + height]
