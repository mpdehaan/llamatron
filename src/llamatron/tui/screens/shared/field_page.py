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

"""The Field page: settings in a column, where the keys depend on the setting under the cursor."""

from rich.text import Text

from llamatron.composition import setlist
from llamatron.strings import errors, labels as labels_text, legends, marks
from llamatron.tui import drawing, key_table, keybindings
from llamatron.tui.components.button_row import button_row
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.tui.drawing import cursor_mark, padded, Style
from llamatron.tui.key_table import cursor_moved
from llamatron.tui.keys import Key
from llamatron.tui.screens.shared import field as field_values
from llamatron.tui.screens.shared.field import Button, Cells, Field, Heading, NameField
from llamatron.tui.screens.shared.page import Page


class FieldPage(Page):
    """Settings in a column, where the keys depend on the setting under the cursor."""

    KEYS = keybindings.FieldPage

    def __init__(self, holder):
        super().__init__(holder)
        self.place = 0
        # The cell the cursor is on in a row of cells, counted from the left.
        self.cell = 0

    def fields(self):
        return []

    def shared_sections(self):
        """Return the sections every page of its kind shows after its own fields, such as a generator's statements about the registers; none unless a page says."""
        return []

    def every_field(self):
        """Return the page's fields with the sections every page of its kind shares put after them, before the page's buttons, which always come last."""
        fields = self.fields()
        shared = self.shared_sections()
        if not shared:
            return fields
        first_button = next((place for place, field in enumerate(fields) if isinstance(field, Button)), len(fields))
        return [*fields[:first_button], *shared, *fields[first_button:]]

    def text_field(self, *, label, current, set_text):
        """A field for text like the title: current() reads it, and set_text(text) stores it, blank text clearing it."""
        return Field(label=label, value=current, adjust=None, enter=lambda: self.ask(dialog=PromptDialog(title=label, value=current()), then=set_text), enter_what=legends.What.EDIT,
                     clear=lambda: set_text(setlist.NO_TEXT), clear_what=legends.What.CLEAR)

    def page_keys(self):
        return []

    def notes(self, width):
        """Return lines to show under the settings."""
        return []

    def shown_fields(self):
        """Return the fields that show: every one, except those after a closed section's heading, up to the next heading; a page's buttons always show."""
        shown = []
        open_now = True
        for field in self.every_field():
            if isinstance(field, Heading):
                shown.append(field)
                open_now = self.is_open(field)
            elif open_now or isinstance(field, Button):
                shown.append(field)
        return shown

    def is_open(self, heading):
        # A heading that starts open is closed by the same toggle that opens another.
        return (heading.label in self.app.open_field_sections) != heading.starts_open

    def heading(self, *, label, is_set, said=None, starts_open=False):
        """Return a section's heading, closed until opened, or open until closed, and remembered for the session; said() is what it shows after its name, where that is not the mark of a value inside."""
        return Heading(label=label, is_set=is_set, toggle=lambda: self.toggle_section(label), said=said, starts_open=starts_open)

    def heading_over_cursor(self):
        """Return the label of the heading the cursor is on or under, or None where the cursor is above every heading."""
        over = [field for field in self.shown_fields()[:self.place + 1] if isinstance(field, Heading)]
        return over[-1].label if over else None

    def toggle_section(self, label):
        self.app.open_field_sections ^= {label}

    def jump_section(self, direction):
        """Move the cursor to the next section's heading, or the one before, staying put past the last or the first."""
        places = [place for place, field in enumerate(self.shown_fields()) if isinstance(field, Heading)]
        ahead = [place for place in places if place > self.place] if direction == key_table.STEP_FORWARD else [place for place in places if place < self.place]
        if ahead:
            self.place = ahead[0] if direction == key_table.STEP_FORWARD else ahead[-1]

    def ends_a_list(self, field):
        """Return whether a field is the last row of a list among the settings, which leaves a blank line after it. No field is, unless the page says so."""
        return False

    def field(self):
        fields = self.shown_fields()
        self.place = max(min(self.place, len(fields) - 1), 0)
        return fields[self.place] if fields else None

    def move_cursor(self, name):
        """Move between the fields with Up and Down, Down from the last field reaching the row of buttons and Up from any button
        going back to the last field; Down on the buttons stays."""
        fields = self.shown_fields()
        if not fields:
            return
        # A row is come to at its first cell.
        self.cell = 0
        first_button = self.first_button_place()
        if self.buttons_stacked():
            # Buttons too wide for one row stand one under another, and Up and Down go through them as through the fields.
            self.place = cursor_moved(place=self.place, name=name, count=len(fields))
            return
        if self.place >= first_button:
            if name == Key.UP and first_button:
                self.place = first_button - 1
            return
        self.place = cursor_moved(place=self.place, name=name, count=min(first_button + 1, len(fields)))

    def buttons_stacked(self):
        """Return whether the page's buttons were last drawn one under another, a row of them being wider than the page."""
        return getattr(self, 'stacked_buttons', False)

    def row_of_buttons(self, *, buttons, selected, width):
        """Return the lines of the page's buttons: boxed in one row where the row fits the width, and otherwise one a line, each
        in brackets, the selected one marked and bold."""
        row = [Text(drawing.INDENT) + line for line in button_row(buttons=[(button.key_name, button.label) for button in buttons], selected=selected)]
        self.stacked_buttons = width is not None and max(line.cell_len for line in row) > width
        if not self.stacked_buttons:
            return row
        lines = []
        for place, button in enumerate(buttons):
            line = Text(no_wrap=True)
            line.append(cursor_mark(place == selected))
            line.append(marks.MSG_STACKED_BUTTON.format(name=button.label), style=Style.BOLD if place == selected else Style.PLAIN)
            lines.append(line)
        return lines

    def cell_field(self):
        """Return what the keys act on: the field under the cursor, or, in a row of cells, the cell the cursor is on."""
        field = self.field()
        if not isinstance(field, Cells):
            return field
        self.cell = max(min(self.cell, len(field.cells) - 1), 0)
        return field.cells[self.cell]

    def move_along_cells(self, name):
        """Move between the cells of a row with Left and Right, stopping at both ends."""
        self.cell = cursor_moved(place=self.cell, name=name, count=len(self.field().cells))

    def first_button_place(self):
        """Return the place of the first button among the fields shown, or how many fields show when there's none."""
        fields = self.shown_fields()
        return next((place for place, field in enumerate(fields) if isinstance(field, Button)), len(fields))

    def move_along_buttons(self, name):
        """Move along the row of buttons with Left and Right, stopping at both ends."""
        first_button = self.first_button_place()
        count = len(self.shown_fields()) - first_button
        self.place = first_button + cursor_moved(place=self.place - first_button, name=name, count=count)

    def remember_place(self):
        field = self.field()
        return None if field is None else field.label

    def restore_place(self, place):
        """Put the cursor back on the field with the same label, since an undo can add or remove fields above it."""
        labels = [field.label for field in self.shown_fields()]
        if place in labels:
            self.place = labels.index(place)

    def keys(self):
        result = [self.bind(self.KEYS.SELECT, action=self.move_cursor, wants_key=True)]
        row = self.field()
        field = self.cell_field()
        if isinstance(row, Cells):
            result.append(self.bind(self.KEYS.ALONG_CELLS, action=self.move_along_cells, wants_key=True))
        if field is not None:
            if field.adjust and not isinstance(row, Cells):
                result.append(self.bind(self.KEYS.MORE, action=lambda: field.adjust(1)))
                result.append(self.bind(self.KEYS.LESS, action=lambda: field.adjust(-1)))
            if field.enter and field.is_toggle():
                # A toggle answers to Space and Enter alike, like the pattern editor's toggle rows.
                result.append(self.bind(self.KEYS.TOGGLE, action=field.enter))
            elif field.enter:
                result.append(self.bind(self.KEYS.ENTER, action=field.enter, what=field.enter_what))
            if field.clear:
                result.append(self.bind(self.KEYS.CLEAR, action=field.clear, what=field.clear_what))
        name = next((item for item in self.every_field() if isinstance(item, NameField)), None)
        if name is not None:
            result.append(self.bind(self.KEYS.RENAME, action=name.rename))
        if isinstance(field, Button) and not self.buttons_stacked():
            result.append(self.bind(self.KEYS.ALONG_BUTTONS, action=self.move_along_buttons, wants_key=True))
        if any(isinstance(item, Heading) for item in self.every_field()):
            result.append(self.bind(self.KEYS.SECTION, action=self.jump_section))
        result += self.page_keys()
        return [self.bind(self.KEYS.BACK, action=self.go_back), *result]

    def body(self, *, width, height):
        """Return the settings after a blank line, the first section after another, then the page's buttons after one blank line, then its notes after another.

        The labels take the width of the longest of every field, shown or not, so that opening a
        section never moves the values beside them.
        """
        fields = self.shown_fields()
        self.field()
        label_width = max((len(self.label_text(field)) for field in self.every_field() if not isinstance(field, Button)), default=0) + 2
        lines = [Text(drawing.NOTHING)]
        selected = 0
        seen_heading = False
        buttons = [field for field in fields if isinstance(field, Button)]
        for place, field in enumerate(fields):
            if isinstance(field, Button):
                continue
            if isinstance(field, Heading) and not seen_heading:
                seen_heading = True
                if place:
                    lines.append(Text(drawing.NOTHING))
            if place == self.place:
                selected = len(lines)
            line = Text(no_wrap=True)
            line.append(cursor_mark(place == self.place))
            if isinstance(field, Heading):
                line.append(self.label_text(field).ljust(label_width), style=Style.BOLD)
                line.append(padded(field.value()), style=Style.DIM)
                lines.append(line)
                continue
            line.append(field.label.ljust(label_width), style=Style.BOLD if place == self.place else Style.PLAIN)
            if isinstance(field, Cells):
                self.append_cells(line=line, row=field, selected=place == self.place)
                lines.append(line)
                continue
            line.append(padded(field.value()))
            # A field whose Enter opens a list of choices shows a dim mark after its value, so that it isn't taken for one that's typed.
            if field.enter_what == legends.What.CHOOSE:
                line.append(marks.MSG_PICKER_MARK, style=Style.DIM)
            lines.append(line)
            # A page that starts with its thing's Name leaves a blank line before its other settings.
            if place == 0 and field.label == labels_text.MSG_NAME_LABEL and len(fields) > 1 and not isinstance(fields[1], Button):
                lines.append(Text(drawing.NOTHING))
            elif self.ends_a_list(field):
                lines.append(Text(drawing.NOTHING))
        if buttons:
            # The buttons sit in one row under the settings after a blank line, boxed as the dialogs' are.
            first_button = self.first_button_place()
            lines.append(Text(drawing.NOTHING))
            row = self.row_of_buttons(buttons=buttons, selected=self.place - first_button, width=width)
            if self.place >= first_button:
                selected = len(lines) + (self.place - first_button if self.buttons_stacked() else 1)
            lines += row
        notes = self.notes(width)
        if notes:
            lines += [Text(drawing.NOTHING), *notes]
        return self.window_of_lines(lines=lines, selected=selected, height=height)

    def append_cells(self, *, line, row, selected):
        """Draw a row's cells side by side, the cell under the cursor in reverse video as a grid's is, and a cell that opens a list with the picker's mark."""
        for place, cell in enumerate(row.cells):
            on_cell = selected and place == min(self.cell, len(row.cells) - 1)
            line.append(padded(cell.value()), style=Style.REVERSE if on_cell else Style.PLAIN)
            if cell.enter_what == legends.What.CHOOSE:
                line.append(marks.MSG_PICKER_MARK, style=Style.DIM)
            line.append(field_values.CELL_GAP)

    def label_text(self, field):
        """Return a field's label as drawn: a section's heading with its open or closed mark, any other field's label as it is."""
        if isinstance(field, Heading):
            mark = marks.MSG_SECTION_OPEN_MARK if self.is_open(field) else marks.MSG_SECTION_CLOSED_MARK
            return labels_text.MSG_SECTION_LABEL.format(mark=mark, name=field.label)
        return field.label

    def window_of_lines(self, *, lines, selected, height):
        """Return the lines that fit the height, scrolled so that the selected line shows, a settings page being taller than a console at times."""
        if height is None or len(lines) <= height:
            self.first_line = 0
            return lines
        first = min(max(getattr(self, 'first_line', 0), selected - height + 1), selected)
        self.first_line = max(min(first, len(lines) - height), 0)
        return lines[self.first_line:self.first_line + height]

    def button(self, *, binding, label, action):
        """Return a button that runs one of the keys that work everywhere on Enter, labelled as the main screen labels it and showing the key's name."""
        return Button(label=label, key_name=binding.name, enter=action, enter_what=binding.what)

    # Common kinds of setting.

    def ask_number(self, *, title, value, then, low=None, high=None):
        def answered(text):
            try:
                number = int(text.strip())
            except ValueError:
                self.refuse(errors.ERR_TYPED_NOT_AN_INTEGER.format(text=text))
                return
            if (low is not None and number < low) or (high is not None and number > high):
                self.refuse(errors.ERR_OUT_OF_RANGE.format(number=number, low=low, high=high))
                return
            then(number)
        self.ask(dialog=PromptDialog(title=title, value=value), then=answered)
