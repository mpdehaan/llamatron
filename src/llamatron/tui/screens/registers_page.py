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

"""The Registers page: the settings of the song's four registers, AX to DX."""

from llamatron.composition.file_format import AT_LIMITS, REGISTER_NAMES, RegisterSetting
from llamatron.composition.limits import MAX_REGISTER_VALUE, MIN_ALLOWED_INC_MAX, MIN_REGISTER_VALUE
from llamatron.tui.screens.field import ChoiceField, NumberField, Toggle
from llamatron.tui.screens.field_page import FieldPage
from llamatron.strings.help import HELP_REGISTERS_PAGE
from llamatron.strings.labels import (
    Crumb, MSG_AT_LIMIT_NAMES, MSG_REGISTER_ALLOWED_INC_MAX_FIELD, MSG_REGISTER_AT_LIMIT_FIELD, MSG_REGISTER_FIELD_LABEL, MSG_REGISTER_NUMBER_FIELDS,
    MSG_REGISTER_RESET_EACH_SCENE_FIELD,
)
from llamatron.strings.legends import MSG_REGISTER_CLEAR_WHAT, MSG_REGISTER_ENTER_WHAT
from llamatron.strings.messages import MSG_REGISTER_PROMPT
from rich.text import Text

from llamatron.strings.labels import MSG_REGISTER_COLUMNS
from llamatron.tui.drawing import NOTHING, SPACE, Style, cursor_mark, padded
from llamatron.tui.key_table import cursor_moved
from llamatron.tui.keys import Key
from llamatron.tui import themes
from llamatron.tui import keybindings


# The grid's settings across, a register's name's room at the left, and the room either side of a value.
GRID_COLUMNS = 6
NAME_WIDTH = 6
CELL_PADDING = 2


class RegistersPage(FieldPage):
    """Each register's default, minimum and maximum, what it does at those limits, whether each scene resets it, and the most a step may add to it."""

    THEME = themes.REGISTERS

    KEYS = keybindings.RegistersPage

    crumbs = (Crumb.REGISTERS,)
    HELP = HELP_REGISTERS_PAGE

    def fields(self):
        """Return every register's settings, register by register, each in the grid's order of columns."""
        result = []
        for name in REGISTER_NAMES:
            result += self.register_fields(name)
        return result

    def register_fields(self, name):
        """Return one register's settings as fields, in the grid's order of columns: Allowed inc max, At limit, Minimum, Default,
        Maximum and Reset each scene, the user's order."""
        register = self.document().register(name)
        values = {
            RegisterSetting.DEFAULT: register.get_default(), RegisterSetting.MINIMUM: register.get_minimum(),
            RegisterSetting.MAXIMUM: register.get_maximum(),
        }
        numbers = {setting: self.number_field(name=name, setting=setting, what=what, value=values[setting]) for setting, what in MSG_REGISTER_NUMBER_FIELDS}
        result = []
        result.append(ChoiceField(
            page=self, label=MSG_REGISTER_FIELD_LABEL.format(name=name, what=MSG_REGISTER_AT_LIMIT_FIELD), choices=AT_LIMITS, current=register.get_at_limit(),
            names=[MSG_AT_LIMIT_NAMES[choice] for choice in AT_LIMITS], shown=MSG_AT_LIMIT_NAMES[register.get_at_limit()],
            set=lambda choice: self.change(name=name, setting=RegisterSetting.AT_LIMIT, value=None if choice == AT_LIMITS[0] else choice),
        ))
        reset = Toggle(
            label=MSG_REGISTER_FIELD_LABEL.format(name=name, what=MSG_REGISTER_RESET_EACH_SCENE_FIELD), on=register.resets_each_scene(),
            set=lambda on: self.change(name=name, setting=RegisterSetting.RESET_EACH_SCENE, value=True if on else None),
        )
        label = MSG_REGISTER_FIELD_LABEL.format(name=name, what=MSG_REGISTER_ALLOWED_INC_MAX_FIELD)
        result.insert(0, NumberField(
            page=self, label=label, number=register.get_allowed_inc_max(), lowest=MIN_ALLOWED_INC_MAX, highest=MAX_REGISTER_VALUE,
            title=MSG_REGISTER_PROMPT.format(label=label, lowest=MIN_ALLOWED_INC_MAX, highest=MAX_REGISTER_VALUE),
            set=lambda number: self.change(name=name, setting=RegisterSetting.ALLOWED_INC_MAX, value=number), enter_what=MSG_REGISTER_ENTER_WHAT,
            clear=lambda: self.change(name=name, setting=RegisterSetting.ALLOWED_INC_MAX, value=None), clear_what=MSG_REGISTER_CLEAR_WHAT,
        ))
        result += [numbers[RegisterSetting.MINIMUM], numbers[RegisterSetting.DEFAULT], numbers[RegisterSetting.MAXIMUM], reset]
        return result

    # The grid, the user's design: a row for each register and a column for each setting.

    def keys(self):
        field = self.field()
        result = [self.bind(self.KEYS.BACK, action=self.go_back), self.bind(self.KEYS.MOVE, action=self.move_in_grid, wants_key=True)]
        if field.adjust:
            result += [self.bind(self.KEYS.LESS, action=lambda: field.adjust(-1)), self.bind(self.KEYS.MORE, action=lambda: field.adjust(1))]
        if field.is_toggle():
            result.append(self.bind(self.KEYS.TOGGLE, action=field.enter))
        elif field.enter:
            result.append(self.bind(self.KEYS.ENTER, action=field.enter, what=field.enter_what))
        if field.clear:
            result.append(self.bind(self.KEYS.CLEAR, action=field.clear, what=field.clear_what))
        return result

    def move_in_grid(self, name):
        """Move the cursor a register up or down or a setting left or right, stopping at every edge."""
        row, column = divmod(self.place, GRID_COLUMNS)
        if name in (Key.UP, Key.DOWN):
            row = cursor_moved(place=row, name=name, count=len(REGISTER_NAMES))
        else:
            column = cursor_moved(place=column, name=name, count=GRID_COLUMNS)
        self.place = row * GRID_COLUMNS + column

    def body(self, *, width, height):
        """Return the grid: the settings' names over their columns, then a row for each register, the cursor's cell in reverse
        video as in the other grids, and under it the cursor's setting in full."""
        fields = self.fields()
        self.field()
        cells = [[fields[row * GRID_COLUMNS + column].value() for column in range(GRID_COLUMNS)] for row in range(len(REGISTER_NAMES))]
        widths = [max(len(MSG_REGISTER_COLUMNS[column]), *(len(str(cells[row][column])) for row in range(len(REGISTER_NAMES)))) + CELL_PADDING for column in range(GRID_COLUMNS)]
        heading = Text(SPACE * NAME_WIDTH, style=Style.BOLD, no_wrap=True)
        for column, name in enumerate(MSG_REGISTER_COLUMNS):
            heading.append(padded(name.ljust(widths[column] - CELL_PADDING)), style=Style.BOLD)
        lines = [Text(NOTHING), heading]
        for row, register in enumerate(REGISTER_NAMES):
            line = Text(no_wrap=True)
            line.append(cursor_mark(self.place // GRID_COLUMNS == row) + register.ljust(NAME_WIDTH - len(cursor_mark(False))), style=Style.BOLD)
            for column in range(GRID_COLUMNS):
                selected = self.place == row * GRID_COLUMNS + column
                line.append(padded(str(cells[row][column]).ljust(widths[column] - CELL_PADDING)), style=Style.REVERSE if selected else Style.PLAIN)
            lines.append(line)
        lines += [Text(NOTHING), Text(SPACE + fields[self.place].label, style=Style.DIM)]
        return lines

    def number_field(self, *, name, setting, what, value):
        label = MSG_REGISTER_FIELD_LABEL.format(name=name, what=what)
        prompt = MSG_REGISTER_PROMPT.format(label=label, lowest=MIN_REGISTER_VALUE, highest=MAX_REGISTER_VALUE)
        return NumberField(
            page=self, label=label, number=value, lowest=MIN_REGISTER_VALUE, highest=MAX_REGISTER_VALUE, title=prompt,
            set=lambda number: self.change(name=name, setting=setting, value=number), enter_what=MSG_REGISTER_ENTER_WHAT,
            clear=lambda: self.change(name=name, setting=setting, value=None), clear_what=MSG_REGISTER_CLEAR_WHAT,
        )

    def change(self, *, name, setting, value):
        """Change a setting, showing why if the register refuses it, like a minimum above the default."""
        problem = self.document().set_register_setting(name=name, setting=setting, value=value)
        if problem:
            self.refuse(problem)
