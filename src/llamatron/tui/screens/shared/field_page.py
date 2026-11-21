# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Field page: settings in a column, where the keys depend on the setting under the cursor."""

from rich.text import Text

from llamatron.model.objects import setlist
from llamatron.tui import drawing, key_table, keybindings
from llamatron.tui.components.button_row import button_row
from llamatron.tui.cursor import Cursor, key_between, NoSuchPlace
from llamatron.tui.drawing import cursor_mark, Style
from llamatron.tui.key_table import cursor_moved
from llamatron.tui.keys import Key
from llamatron.tui.screens.shared.field import Button, Cells, Field, Heading, NameField, NumberField
from llamatron.tui.screens.shared.page import Page
from llamatron.user_strings import errors, labels as labels_text, legends, marks


class FieldPage(Page):
    """Settings in a column, where the keys depend on the setting under the cursor."""

    KEYS = keybindings.FieldPage

    def __init__(self, holder):
        super().__init__(holder)
        self.cursor = Cursor(place=0)
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
        return Field(label=label, value=current, adjust=None, enter=lambda: self.ask_text(title=label, value=current(), then=set_text), enter_what=legends.What.EDIT,
                     clear=lambda: set_text(setlist.NO_TEXT), clear_what=legends.What.CLEAR)

    def setting_number_field(self, *, label, holder, name, shown=None, in_effect=None, start=None, typed=None, clear_what=None):
        """A field for a whole number that is a setting of something in the set, by the setting's file name.

        The range is the setting's own, said once where the setting is described, and the number is stored through
        the document, which the holder checks; Bksp leaves the setting out. in_effect is the number shown and stepped
        from where that is not the number written, as a track's accent is its default until one is set.
        """
        described = holder.SETTINGS[name]

        def store(number):
            self.document().set_setting(holder=holder, name=name, value=number)
        return NumberField(
            page=self, label=label, number=holder.get_written(name) if in_effect is None else in_effect, start=start, shown=shown, typed=typed,
            lowest=described.get_lowest(), highest=described.get_highest(), set=store, clear=lambda: store(None), clear_what=clear_what,
        )

    def page_keys(self):
        return []

    def remarks(self, width):
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
        over = [field for field in self.shown_fields()[:self.cursor.get_place() + 1] if isinstance(field, Heading)]
        return over[-1].label if over else None

    def toggle_section(self, label):
        self.app.open_field_sections ^= {label}

    def jump_section(self, direction):
        """Move the cursor to the next section's heading, or the one before, staying put past the last or the first."""
        places = [place for place, field in enumerate(self.shown_fields()) if isinstance(field, Heading)]
        ahead = [place for place in places if place > self.cursor.get_place()] if direction == key_table.STEP_FORWARD else [place for place in places if place < self.cursor.get_place()]
        if ahead:
            self.cursor.set_place(ahead[0] if direction == key_table.STEP_FORWARD else ahead[-1])

    def ends_a_list(self, field):
        """Return whether a field is the last row of a list among the settings, which leaves a blank line after it. No field is, unless the page says so."""
        return False

    def field(self):
        fields = self.shown_fields()
        self.cursor.set_place(max(min(self.cursor.get_place(), len(fields) - 1), 0))
        return fields[self.cursor.get_place()] if fields else None

    def under_cursor(self):
        """Return the label of the field or the button the cursor is on."""
        field = self.field()
        return field.label if field else None

    def closed_heading_over(self, label):
        """Return the heading of the closed section a field is in, by the field's label, or raise NoSuchPlace where the page has no such field.

        A page that builds a section's fields only once the section is open cannot say which closed section holds
        a field, so there the last closed section is the one opened, and the next asking finds the field or opens the one before.
        """
        heading = None
        closed = []
        for field in self.every_field():
            if isinstance(field, Heading):
                heading = field
                if not self.is_open(field):
                    closed.append(field)
            if field.label == label and heading is not None:
                return heading
        if not closed:
            raise NoSuchPlace(screen=self, target=label)
        return closed[-1]

    def key_toward(self, target):
        """Return the key that brings the cursor nearer the field or the button with a label, or None when the cursor is on it.

        A field in a closed section is reached as a person reaches it: the way to its section's heading, then the key that opens the section.
        Down from the last field reaches the buttons, which Left and Right go along, or Up and Down where they are stacked.
        """
        labels = [field.label for field in self.shown_fields()]
        if target not in labels:
            return self.key_toward(self.closed_heading_over(target).label) or Key.ENTER
        there = labels.index(target)
        here = self.cursor.get_place()
        first_button = self.first_button_place()
        if here < first_button or there < first_button or self.buttons_stacked():
            return key_between(here=here, there=there)
        return key_between(here=here, there=there, back=Key.LEFT, forward=Key.RIGHT)

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
            self.cursor.move(name=name, count=len(fields))
            return
        if self.cursor.get_place() >= first_button:
            if name == Key.UP and first_button:
                self.cursor.set_place(first_button - 1)
            return
        self.cursor.move(name=name, count=min(first_button + 1, len(fields)))

    def buttons_stacked(self):
        """Return whether the page's buttons were last drawn one under another, a row of them being wider than the page."""
        return getattr(self, 'stacked_buttons', False)

    def row_of_buttons(self, *, buttons, selected, width):
        """Return the lines of the page's buttons: boxed in one row where the row fits the width, and otherwise one a line, each
        in brackets, the selected one marked and bold."""
        keys_and_names = [(button.key_name, button.label) for button in buttons]
        row = [Text(drawing.INDENT) + line for line in button_row(buttons=keys_and_names, selected=selected)]
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
        self.cursor.set_place(first_button + cursor_moved(place=self.cursor.get_place() - first_button, name=name, count=count))

    def remember_place(self):
        field = self.field()
        return None if field is None else field.label

    def restore_place(self, place):
        """Put the cursor back on the field with the same label, since an undo can add or remove fields above it."""
        labels = [field.label for field in self.shown_fields()]
        if place in labels:
            self.cursor.set_place(labels.index(place))

    def keys(self):
        result = [self.bind(self.KEYS.SELECT, action=self.move_cursor, wants_key=True)]
        row = self.field()
        if row is not None:
            result += row.row_keys(self)
        field = self.cell_field()
        if field is not None:
            result += field.keys(self)
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
        label_width = max((len(field.get_drawn_label(self)) for field in self.every_field() if not isinstance(field, Button)), default=0) + 2
        cursor = self.cursor.get_place()
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
            here = place == cursor
            if here:
                selected = len(lines) + field.SELECTED_LINE
            lines += field.lines(page=self, here=here, label_width=label_width, width=width)
            if field.MAY_LEAVE_A_GAP and self.has_gap_after(place=place, field=field, fields=fields):
                lines.append(Text(drawing.NOTHING))
        if buttons:
            # The buttons sit in one row under the settings after a blank line, boxed as the dialogs' are.
            first_button = self.first_button_place()
            lines.append(Text(drawing.NOTHING))
            row = self.row_of_buttons(buttons=buttons, selected=cursor - first_button, width=width)
            if cursor >= first_button:
                selected = len(lines) + (cursor - first_button if self.buttons_stacked() else 1)
            lines += row
        remarks = self.remarks(width)
        if remarks:
            lines += [Text(drawing.NOTHING), *remarks]
        return self.window_of_lines(lines=lines, selected=selected, height=height)

    def has_gap_after(self, *, place, field, fields):
        """Return whether a blank line follows a setting: a Name that starts the page before its other settings, and the last of a list."""
        if place == 0 and field.label == labels_text.MSG_NAME_LABEL and len(fields) > 1 and not isinstance(fields[1], Button):
            return True
        return self.ends_a_list(field)

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
        self.ask_text(title=title, value=value, then=answered)
