# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Registers page: the settings of the song's four registers, AX to DX."""

from rich.text import Text

from llamatron.model.vocabulary import file_format, limits
from llamatron.model.vocabulary.file_format import RegisterSetting
from llamatron.tui import drawing, keybindings, themes
from llamatron.tui.cursor import key_between, NoSuchPlace
from llamatron.tui.drawing import cursor_mark, padded, Style
from llamatron.tui.key_table import cursor_moved
from llamatron.tui.keys import Key
from llamatron.tui.screens.shared.field import ChoiceField, NumberField, Toggle
from llamatron.tui.screens.shared.field_page import FieldPage
from llamatron.user_strings import help as help_text, labels, legends, marks, messages


# The grid's settings across, a register's name's room at the left, and the room either side of a value.
GRID_COLUMNS = 6
NAME_WIDTH = 6
CELL_PADDING = 2


class RegistersPage(FieldPage):
    """Each register's default, minimum and maximum, what it does at those limits, whether each scene resets it, and the most a step may add to it."""

    THEME = themes.REGISTERS

    KEYS = keybindings.RegistersPage

    crumbs = (labels.Crumb.REGISTERS,)
    HELP = help_text.HELP_REGISTERS_PAGE

    def fields(self):
        """Return every register's settings, register by register, each in the grid's order of columns."""
        result = []
        for name in file_format.REGISTER_NAMES:
            result += self.register_fields(name)
        return result

    def register_fields(self, name):
        """Return one register's settings as fields, in the grid's order of columns: Allowed inc max, Reset behavior, Minimum, Default,
        Maximum and Reset each scene."""
        register = self.document().register(name)
        values = {
            RegisterSetting.DEFAULT: register.get_default(), RegisterSetting.MINIMUM: register.get_minimum(),
            RegisterSetting.MAXIMUM: register.get_maximum(),
        }
        numbers = {setting: self.number_field(name=name, setting=setting, what=what, value=values[setting]) for setting, what in labels.MSG_REGISTER_NUMBER_FIELDS}
        result = []
        result.append(ChoiceField(
            page=self, label=labels.MSG_REGISTER_FIELD_LABEL.format(name=name, what=labels.MSG_REGISTER_RESET_BEHAVIOR_FIELD), choices=file_format.RESET_BEHAVIORS, current=register.get_reset_behavior(),
            names=[labels.MSG_RESET_BEHAVIOR_NAMES[choice] for choice in file_format.RESET_BEHAVIORS], shown=labels.MSG_RESET_BEHAVIOR_NAMES[register.get_reset_behavior()],
            set=lambda choice: self.change(name=name, setting=RegisterSetting.RESET_BEHAVIOR, value=None if choice == file_format.RESET_BEHAVIORS[0] else choice),
        ))
        reset = Toggle(
            label=labels.MSG_REGISTER_FIELD_LABEL.format(name=name, what=labels.MSG_REGISTER_RESET_EACH_SCENE_FIELD), on=register.resets_each_scene(),
            set=lambda on: self.change(name=name, setting=RegisterSetting.RESET_EACH_SCENE, value=True if on else None),
        )
        label = labels.MSG_REGISTER_FIELD_LABEL.format(name=name, what=labels.MSG_REGISTER_ALLOWED_INC_MAX_FIELD)
        result.insert(0, NumberField(
            page=self, label=label, number=register.get_allowed_inc_max(), lowest=limits.MIN_ALLOWED_INC_MAX, highest=limits.MAX_REGISTER_VALUE,
            title=messages.MSG_REGISTER_PROMPT.format(label=label, lowest=limits.MIN_ALLOWED_INC_MAX, highest=limits.MAX_REGISTER_VALUE),
            set=lambda number: self.change(name=name, setting=RegisterSetting.ALLOWED_INC_MAX, value=number), enter_what=legends.MSG_REGISTER_ENTER_WHAT,
            clear=lambda: self.change(name=name, setting=RegisterSetting.ALLOWED_INC_MAX, value=None), clear_what=legends.MSG_REGISTER_CLEAR_WHAT,
        ))
        result += [numbers[RegisterSetting.MINIMUM], numbers[RegisterSetting.DEFAULT], numbers[RegisterSetting.MAXIMUM], reset]
        return result

    # The grid: a row for each register and a column for each setting.

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

    def key_toward(self, target):
        """Return the key that brings the cursor nearer the cell with a label: Up or Down to its register, then Left or Right to its setting."""
        labels = [field.label for field in self.fields()]
        if target not in labels:
            raise NoSuchPlace(screen=self, target=target)
        row, column = divmod(labels.index(target), GRID_COLUMNS)
        here_row, here_column = divmod(self.cursor.get_place(), GRID_COLUMNS)
        return key_between(here=here_row, there=row) or key_between(here=here_column, there=column, back=Key.LEFT, forward=Key.RIGHT)

    def move_in_grid(self, name):
        """Move the cursor a register up or down or a setting left or right, stopping at every edge."""
        row, column = divmod(self.cursor.get_place(), GRID_COLUMNS)
        if name in (Key.UP, Key.DOWN):
            row = cursor_moved(place=row, name=name, count=len(file_format.REGISTER_NAMES))
        else:
            column = cursor_moved(place=column, name=name, count=GRID_COLUMNS)
        self.cursor.set_place(row * GRID_COLUMNS + column)

    def widest_values(self):
        """Return the text each column is as wide as: its heading or the widest value it can ever hold, so that changing a value
        never moves the columns beside it."""
        numbers = [str(limits.MIN_REGISTER_VALUE), str(limits.MAX_REGISTER_VALUE)]
        held = [numbers, labels.MSG_RESET_BEHAVIOR_NAMES.values(), numbers, numbers, numbers, [marks.MSG_TOGGLE_ON, marks.MSG_FIELD_TOGGLE_OFF]]
        return [max([heading, *values], key=len) for heading, values in zip(labels.MSG_REGISTER_COLUMNS, held)]

    def body(self, *, width, height):
        """Return the grid: the settings' names over their columns, then a row for each register, the cursor's cell in reverse
        video as in the other grids, and under it the cursor's setting in full."""
        fields = self.fields()
        self.field()
        cells = [row_values(fields=fields, row=row) for row in range(len(file_format.REGISTER_NAMES))]
        widths = [len(widest) + CELL_PADDING for widest in self.widest_values()]
        heading = Text(drawing.SPACE * NAME_WIDTH, style=Style.BOLD, no_wrap=True)
        for column, name in enumerate(labels.MSG_REGISTER_COLUMNS):
            heading.append(padded(name.ljust(widths[column] - CELL_PADDING)), style=Style.BOLD)
        lines = [Text(drawing.NOTHING), heading]
        for row, register in enumerate(file_format.REGISTER_NAMES):
            line = Text(no_wrap=True)
            line.append(cursor_mark(self.cursor.get_place() // GRID_COLUMNS == row) + register.ljust(NAME_WIDTH - len(cursor_mark(False))), style=Style.BOLD)
            for column in range(GRID_COLUMNS):
                selected = self.cursor.get_place() == row * GRID_COLUMNS + column
                line.append(padded(str(cells[row][column]).ljust(widths[column] - CELL_PADDING)), style=Style.REVERSE if selected else Style.PLAIN)
            lines.append(line)
        lines += [Text(drawing.NOTHING), Text(drawing.SPACE + fields[self.cursor.get_place()].label, style=Style.DIM)]
        return lines

    def number_field(self, *, name, setting, what, value):
        label = labels.MSG_REGISTER_FIELD_LABEL.format(name=name, what=what)
        prompt = messages.MSG_REGISTER_PROMPT.format(label=label, lowest=limits.MIN_REGISTER_VALUE, highest=limits.MAX_REGISTER_VALUE)
        return NumberField(
            page=self, label=label, number=value, lowest=limits.MIN_REGISTER_VALUE, highest=limits.MAX_REGISTER_VALUE, title=prompt,
            set=lambda number: self.change(name=name, setting=setting, value=number), enter_what=legends.MSG_REGISTER_ENTER_WHAT,
            clear=lambda: self.change(name=name, setting=setting, value=None), clear_what=legends.MSG_REGISTER_CLEAR_WHAT,
        )

    def change(self, *, name, setting, value):
        """Change a setting, showing why if the register refuses it, like a minimum above the default."""
        problem = self.document().set_register_setting(name=name, setting=setting, value=value)
        if problem:
            self.refuse(problem)


def row_values(*, fields, row):
    """Return the values of one register's row of the grid."""
    return [fields[row * GRID_COLUMNS + column].value() for column in range(GRID_COLUMNS)]
