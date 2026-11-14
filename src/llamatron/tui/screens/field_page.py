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

from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.strings.legends import What
from llamatron.strings.marks import MSG_PICKER_MARK
from llamatron.tui.components.button_row import button_row
from llamatron.tui.keys import Key
from llamatron.tui.drawing import cursor_mark, INDENT, NOTHING, padded, Style
from llamatron.tui.key_table import cursor_moved
from llamatron.strings.labels import MSG_NAME_LABEL
from llamatron.tui.screens.field import NameField, Button, Field, Heading
from llamatron.composition.setlist import NO_TEXT
from llamatron.strings.labels import MSG_SECTION_LABEL
from llamatron.strings.marks import MSG_SECTION_CLOSED_MARK, MSG_SECTION_OPEN_MARK
from llamatron.tui.key_table import STEP_FORWARD
from llamatron.tui.screens.page import Page
from llamatron.strings.errors import ERR_OUT_OF_RANGE, ERR_TYPED_NOT_AN_INTEGER
from llamatron.tui import keybindings


class FieldPage(Page):
    """Settings in a column, where the keys depend on the setting under the cursor."""

    KEYS = keybindings.FieldPage

    def __init__(self, holder):
        super().__init__(holder)
        self.place = 0

    def fields(self):
        return []

    def text_field(self, *, label, current, set_text):
        """A field for text like the title: current() reads it, and set_text(text) stores it, blank text clearing it."""
        return Field(label=label, value=current, adjust=None, enter=lambda: self.ask(dialog=PromptDialog(title=label, value=current()), then=set_text), enter_what=What.EDIT,
                     clear=lambda: set_text(NO_TEXT), clear_what=What.CLEAR)

    def page_keys(self):
        return []

    def notes(self, width):
        """Return lines to show under the settings."""
        return []

    def shown_fields(self):
        """Return the fields that show: every one, except those after a closed section's heading, up to the next heading; a page's buttons always show."""
        shown = []
        open_now = True
        for field in self.fields():
            if isinstance(field, Heading):
                shown.append(field)
                open_now = self.is_open(field)
            elif open_now or isinstance(field, Button):
                shown.append(field)
        return shown

    def is_open(self, heading):
        return heading.label in self.app.open_field_sections

    def heading(self, *, label, is_set):
        """Return a section's heading, closed until opened and remembered open or closed for the session."""
        return Heading(label=label, is_set=is_set, toggle=lambda: self.toggle_section(label))

    def toggle_section(self, label):
        self.app.open_field_sections ^= {label}

    def jump_section(self, direction):
        """Move the cursor to the next section's heading, or the one before, staying put past the last or the first."""
        places = [place for place, field in enumerate(self.shown_fields()) if isinstance(field, Heading)]
        ahead = [place for place in places if place > self.place] if direction == STEP_FORWARD else [place for place in places if place < self.place]
        if ahead:
            self.place = ahead[0] if direction == STEP_FORWARD else ahead[-1]

    def field(self):
        fields = self.shown_fields()
        self.place = max(min(self.place, len(fields) - 1), 0)
        return fields[self.place] if fields else None

    def move_cursor(self, name):
        """Move between the fields with Up and Down, Down from the last field reaching the row of buttons and Up from any button
        going back to the last field, the user's design; Down on the buttons stays."""
        fields = self.shown_fields()
        if not fields:
            return
        first_button = self.first_button_place()
        if self.place >= first_button:
            if name == Key.UP and first_button:
                self.place = first_button - 1
            return
        self.place = cursor_moved(place=self.place, name=name, count=min(first_button + 1, len(fields)))

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
        field = self.field()
        if field is not None:
            if field.adjust:
                result.append(self.bind(self.KEYS.MORE, action=lambda: field.adjust(1)))
                result.append(self.bind(self.KEYS.LESS, action=lambda: field.adjust(-1)))
            if field.enter and field.is_toggle():
                # A toggle answers to Space and Enter alike, like the pattern editor's toggle rows.
                result.append(self.bind(self.KEYS.TOGGLE, action=field.enter))
            elif field.enter:
                result.append(self.bind(self.KEYS.ENTER, action=field.enter, what=field.enter_what))
            if field.clear:
                result.append(self.bind(self.KEYS.CLEAR, action=field.clear, what=field.clear_what))
        name = next((item for item in self.fields() if isinstance(item, NameField)), None)
        if name is not None:
            result.append(self.bind(self.KEYS.RENAME, action=name.rename))
        if isinstance(field, Button):
            result.append(self.bind(self.KEYS.ALONG_BUTTONS, action=self.move_along_buttons, wants_key=True))
        if any(isinstance(item, Heading) for item in self.fields()):
            result.append(self.bind(self.KEYS.SECTION, action=self.jump_section))
        result += self.page_keys()
        return [self.bind(self.KEYS.BACK, action=self.go_back), *result]

    def body(self, *, width, height):
        """Return the settings after a blank line, the first section after another, then the page's buttons after one blank line, then its notes after another.

        The labels take the width of the longest of every field, shown or not, so that opening a
        section never moves the values beside them (the user's rule).
        """
        fields = self.shown_fields()
        self.field()
        label_width = max((len(self.label_text(field)) for field in self.fields() if not isinstance(field, Button)), default=0) + 2
        lines = [Text(NOTHING)]
        selected = 0
        seen_heading = False
        buttons = [field for field in fields if isinstance(field, Button)]
        for place, field in enumerate(fields):
            if isinstance(field, Button):
                continue
            if isinstance(field, Heading) and not seen_heading:
                seen_heading = True
                if place:
                    lines.append(Text(NOTHING))
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
            line.append(padded(field.value()))
            # A field whose Enter opens a list of choices shows a dim mark after its value, the user's choice, so that it isn't taken for one that's typed.
            if field.enter_what == What.CHOOSE:
                line.append(MSG_PICKER_MARK, style=Style.DIM)
            lines.append(line)
            # A page that starts with its thing's Name leaves a blank line before its other settings, the user's rule.
            if place == 0 and field.label == MSG_NAME_LABEL and len(fields) > 1 and not isinstance(fields[1], Button):
                lines.append(Text(NOTHING))
        if buttons:
            # The buttons sit in one row under the settings after a blank line, boxed as the dialogs' are, the user's design.
            first_button = self.first_button_place()
            lines.append(Text(NOTHING))
            if self.place >= first_button:
                selected = len(lines) + 1
            row = button_row(buttons=[(button.key_name, button.label) for button in buttons], selected=self.place - first_button)
            lines += [Text(INDENT) + line for line in row]
        notes = self.notes(width)
        if notes:
            lines += [Text(NOTHING), *notes]
        return self.window_of_lines(lines=lines, selected=selected, height=height)

    def label_text(self, field):
        """Return a field's label as drawn: a section's heading with its open or closed mark, any other field's label as it is."""
        if isinstance(field, Heading):
            mark = MSG_SECTION_OPEN_MARK if self.is_open(field) else MSG_SECTION_CLOSED_MARK
            return MSG_SECTION_LABEL.format(mark=mark, name=field.label)
        return field.label

    def window_of_lines(self, *, lines, selected, height):
        """Return the lines that fit the height, scrolled so that the selected line shows, the user's settings pages being taller than a console at times."""
        if height is None or len(lines) <= height:
            self.first_line = 0
            return lines
        first = min(max(getattr(self, 'first_line', 0), selected - height + 1), selected)
        self.first_line = max(min(first, len(lines) - height), 0)
        return lines[self.first_line:self.first_line + height]

    def button(self, *, binding, label, action):
        """Return a button that runs one of the keys that work everywhere on Enter, labelled as the main screen labels it and showing the key's name."""
        _, key_name, what = binding
        return Button(label=label, key_name=key_name, enter=action, enter_what=what)

    # Common kinds of setting.

    def ask_number(self, *, title, value, then, low=None, high=None):
        def answered(text):
            try:
                number = int(text.strip())
            except ValueError:
                self.refuse(ERR_TYPED_NOT_AN_INTEGER.format(text=text))
                return
            if (low is not None and number < low) or (high is not None and number > high):
                self.refuse(ERR_OUT_OF_RANGE.format(number=number, low=low, high=high))
                return
            then(number)
        self.ask(dialog=PromptDialog(title=title, value=value), then=answered)
