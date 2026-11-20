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

"""The Modulators page: the settings of the song's four modulators, XMod to ZMod, a grid moved over as the Registers page is."""

from fractions import Fraction
from rich.text import Text

from llamatron.composition import file_format
from llamatron.composition.file_format import ModulatorSetting, WaveShape
from llamatron.strings import errors, help as help_text, labels, legends, marks, messages
from llamatron.tui import drawing, keybindings, themes
from llamatron.tui.cursor import key_between, NoSuchPlace
from llamatron.tui.drawing import cursor_mark, padded, Style
from llamatron.tui.key_table import cursor_moved
from llamatron.tui.keys import Key
from llamatron.tui.screens.shared.field import ChoiceField, Field, NumberField, Toggle
from llamatron.tui.screens.shared.field_page import FieldPage

# A modulator's name's room at the left, and the room either side of a value.
NAME_WIDTH = 7
CELL_PADDING = 2
GRID_COLUMNS = len(labels.MSG_MODULATOR_COLUMNS)
# Where each setting stands among a modulator's columns, as MSG_MODULATOR_COLUMNS names them.
RATE_COLUMN = 1
RATE_IN_COLUMN = 2
MINIMUM_COLUMN = 3
START_COLUMN = 4
MAXIMUM_COLUMN = 5
INVERT_COLUMN = 6


class ModulatorsPage(FieldPage):
    """Each modulator's shape, whether it is inverted, its rate in bars or in hertz, and its minimum, start and maximum."""

    THEME = themes.MODULATORS

    KEYS = keybindings.ModulatorsPage

    crumbs = (labels.Crumb.MODULATORS,)
    HELP = help_text.HELP_MODULATORS_PAGE

    def fields(self):
        """Return every modulator's settings, modulator by modulator, each in the grid's order of columns."""
        result = []
        for name in file_format.MODULATOR_NAMES:
            result += self.modulator_fields(name)
        return result

    def label(self, *, name, column):
        return labels.MSG_MODULATOR_FIELD_LABEL.format(name=name, what=labels.MSG_MODULATOR_FIELD_WHATS[column])

    def modulator_fields(self, name):
        """Return one modulator's settings as fields, in the grid's order: Shape, Invert, Rate in, Rate, Minimum, Start and Maximum."""
        modulator = self.document().modulator(name)
        shape = ChoiceField(
            page=self, label=self.label(name=name, column=0), choices=file_format.WAVE_SHAPES, current=modulator.get_shape(),
            names=[labels.MSG_WAVE_SHAPE_NAMES[choice] for choice in file_format.WAVE_SHAPES], shown=labels.MSG_WAVE_SHAPE_NAMES[modulator.get_shape()],
            set=lambda choice: self.change(name=name, setting=ModulatorSetting.SHAPE, value=choice),
        )
        # A sample and hold draws its values, and has nothing to turn upside down.
        blocked = modulator.get_shape() == WaveShape.SAMPLE_AND_HOLD
        invert = Toggle(
            label=self.label(name=name, column=INVERT_COLUMN), on=modulator.is_inverted(),
            set=lambda on: self.change(name=name, setting=ModulatorSetting.INVERT, value=True if on else None),
            **({'shown_on': marks.MSG_BLOCKED_CELL, 'shown_off': marks.MSG_BLOCKED_CELL} if blocked else {}),
        )
        rate_in = ChoiceField(
            page=self, label=self.label(name=name, column=RATE_IN_COLUMN), choices=file_format.RATES_IN, current=modulator.get_rate_in(),
            names=[labels.MSG_RATE_IN_NAMES[choice] for choice in file_format.RATES_IN], shown=labels.MSG_RATE_IN_NAMES[modulator.get_rate_in()],
            set=lambda choice: self.change(name=name, setting=ModulatorSetting.RATE_IN, value=choice),
        )
        numbers = [self.number_field(name=name, column=column, setting=setting, value=modulator.get_setting(setting))
                   for column, setting in ((MINIMUM_COLUMN, ModulatorSetting.MINIMUM), (START_COLUMN, ModulatorSetting.START), (MAXIMUM_COLUMN, ModulatorSetting.MAXIMUM))]
        return [shape, self.rate_field(name=name, modulator=modulator), rate_in, *numbers, invert]

    def rate_field(self, *, name, modulator):
        """Return the Rate: a length in bars chosen from a list, or a number of hertz in hundredths, stepped or typed."""
        label = self.label(name=name, column=RATE_COLUMN)
        if modulator.counts_bars():
            current = modulator.get_setting(ModulatorSetting.BARS)
            return ChoiceField(page=self, label=label, choices=file_format.BAR_RATES, current=current, shown=current, set=lambda choice: self.change(name=name, setting=ModulatorSetting.BARS, value=choice))
        slowest, fastest, steps = self.document().hertz_range()
        hundredths = round(modulator.get_setting(ModulatorSetting.HERTZ) * steps)
        lowest = round(slowest * steps)
        highest = fastest * steps

        def stepped(offset):
            self.set_hertz(name=name, hundredths=min(max(hundredths + offset, lowest), highest))

        def typed():
            title = messages.MSG_MODULATOR_PROMPT.format(label=label, lowest=slowest, highest=fastest)
            self.ask_text(title=title, value=marks.MSG_HERTZ.format(hundredths / steps), then=lambda text: self.type_hertz(name=name, text=text))
        return Field(label=label, value=lambda: marks.MSG_HERTZ.format(hundredths / steps), adjust=stepped, enter=typed,
                     enter_what=legends.MSG_REGISTER_ENTER_WHAT, clear=lambda: self.change(name=name, setting=ModulatorSetting.HERTZ, value=None), clear_what=legends.MSG_REGISTER_CLEAR_WHAT)

    def set_hertz(self, *, name, hundredths):
        """Store a rate of a whole number of hundredths of a hertz, as the file writes it: a whole number where it is one."""
        hertz = Fraction(hundredths, self.document().hertz_range()[2])
        self.change(name=name, setting=ModulatorSetting.HERTZ, value=int(hertz) if hertz.denominator == 1 else float(hertz))

    def type_hertz(self, *, name, text):
        """Store a rate typed in hertz, such as 0.5, to the nearest hundredth, or say why it cannot be."""
        try:
            hertz = float(text)
        except ValueError:
            self.refuse(errors.ERR_NOT_A_HERTZ.format(value=text))
            return
        self.set_hertz(name=name, hundredths=round(hertz * self.document().hertz_range()[2]))

    def number_field(self, *, name, column, setting, value):
        label = self.label(name=name, column=column)
        lowest, highest = self.document().modulator_range()
        return NumberField(
            page=self, label=label, number=value, lowest=lowest, highest=highest,
            title=messages.MSG_MODULATOR_PROMPT.format(label=label, lowest=lowest, highest=highest),
            set=lambda number: self.change(name=name, setting=setting, value=number), enter_what=legends.MSG_REGISTER_ENTER_WHAT,
            clear=lambda: self.change(name=name, setting=setting, value=None), clear_what=legends.MSG_REGISTER_CLEAR_WHAT,
        )

    def change(self, *, name, setting, value):
        """Change a setting, showing why if the modulator refuses it, like a start above the maximum."""
        problem = self.document().set_modulator_setting(name=name, setting=setting, value=value)
        if problem:
            self.refuse(problem)

    # The grid: a row for each modulator and a column for each setting.

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
        """Return the key that brings the cursor nearer the cell with a label: Up or Down to its modulator, then Left or Right to its setting."""
        shown = [field.label for field in self.fields()]
        if target not in shown:
            raise NoSuchPlace(screen=self, target=target)
        row, column = divmod(shown.index(target), GRID_COLUMNS)
        here_row, here_column = divmod(self.cursor.get_place(), GRID_COLUMNS)
        return key_between(here=here_row, there=row) or key_between(here=here_column, there=column, back=Key.LEFT, forward=Key.RIGHT)

    def move_in_grid(self, name):
        """Move the cursor a modulator up or down or a setting left or right, stopping at every edge."""
        row, column = divmod(self.cursor.get_place(), GRID_COLUMNS)
        if name in (Key.UP, Key.DOWN):
            row = cursor_moved(place=row, name=name, count=len(file_format.MODULATOR_NAMES))
        else:
            column = cursor_moved(place=column, name=name, count=GRID_COLUMNS)
        self.cursor.set_place(row * GRID_COLUMNS + column)

    def widest_values(self):
        """Return the text each column is as wide as: its heading or the widest value it can ever hold, so that changing a value
        never moves the columns beside it."""
        lowest, highest = self.document().modulator_range()
        numbers = [str(lowest), str(highest)]
        hertz = [marks.MSG_HERTZ.format(rate) for rate in self.document().hertz_range()[:2]]
        held = [
            labels.MSG_WAVE_SHAPE_NAMES.values(), [*file_format.BAR_RATES, *hertz], labels.MSG_RATE_IN_NAMES.values(), numbers, numbers, numbers,
            [marks.MSG_TOGGLE_ON, marks.MSG_FIELD_TOGGLE_OFF, marks.MSG_BLOCKED_CELL],
        ]
        return [max([heading, *values], key=len) for heading, values in zip(labels.MSG_MODULATOR_COLUMNS, held)]

    def body(self, *, width, height):
        """Return the grid: the settings' names over their columns, then a row for each modulator, the cursor's cell in reverse video,
        and under it the cursor's setting in full."""
        fields = self.fields()
        self.field()
        rows = len(file_format.MODULATOR_NAMES)
        cells = [[str(fields[row * GRID_COLUMNS + column].value()) for column in range(GRID_COLUMNS)] for row in range(rows)]
        widths = [len(widest) + CELL_PADDING for widest in self.widest_values()]
        heading = Text(drawing.SPACE * NAME_WIDTH, style=Style.BOLD, no_wrap=True)
        for column, name in enumerate(labels.MSG_MODULATOR_COLUMNS):
            heading.append(padded(name.ljust(widths[column] - CELL_PADDING)), style=Style.BOLD)
        lines = [Text(drawing.NOTHING), heading]
        for row, modulator in enumerate(file_format.MODULATOR_NAMES):
            line = Text(no_wrap=True)
            line.append(cursor_mark(self.cursor.get_place() // GRID_COLUMNS == row) + modulator.ljust(NAME_WIDTH - len(cursor_mark(False))), style=Style.BOLD)
            for column in range(GRID_COLUMNS):
                selected = self.cursor.get_place() == row * GRID_COLUMNS + column
                line.append(padded(cells[row][column].ljust(widths[column] - CELL_PADDING)), style=Style.REVERSE if selected else Style.PLAIN)
            lines.append(line)
        lines += [Text(drawing.NOTHING), Text(drawing.SPACE + fields[self.cursor.get_place()].label, style=Style.DIM)]
        return lines
