# llamatron: a Python language and framework for producing MIDI clips.
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

from llamatron.composition.file_format import REGISTER_NAMES, RegisterSetting
from llamatron.composition.limits import MAX_REGISTER_VALUE, MIN_REGISTER_VALUE
from llamatron.tui.lists import Field, FieldPage
from llamatron.tui.pattern_editor import TOGGLE_OFF, TOGGLE_ON

CRUMB = 'REGISTERS'
# Each register's settings on the page, labelled like "AX minimum", in the order they're shown.
FIELD_LABEL = '{name} {what}'
NUMBER_FIELDS = [(RegisterSetting.DEFAULT, 'default'), (RegisterSetting.MINIMUM, 'minimum'), (RegisterSetting.MAXIMUM, 'maximum')]
WRAP_FIELD = 'wraps'
PROMPT = '{label} ({lowest} to {highest})'
ENTER_WHAT = 'type'
CLEAR_WHAT = 'default'
TOGGLE_WHAT = 'toggle'


class RegistersPage(FieldPage):
    """Each register's default, minimum and maximum, and whether it wraps."""

    crumbs = (CRUMB,)
    HELP = (
        'The four registers, AX to DX, are numbers the whole song shares. Pattern steps change them with AX+= and use them with AX+Note and AX+Vel, on the pattern editor\'s register rows.',
        '',
        'Each starts at its default when rendering starts, and again whenever a scene resets it. Adding never takes one past its minimum or maximum: it stops there, or, if it wraps, jumps to the other end.',
        '',
        'Up and down select. Left and right, or + and -, change a number, Enter types one, and Bksp goes back to its default. Enter switches wraps on and off.',
    )

    def fields(self):
        result = []
        for name in REGISTER_NAMES:
            result += self.register_fields(name)
        return result

    def register_fields(self, name):
        """Return one register's settings as fields."""
        register = self.document.register(name)
        values = {
            RegisterSetting.DEFAULT: register.get_default(), RegisterSetting.MINIMUM: register.get_minimum(),
            RegisterSetting.MAXIMUM: register.get_maximum(),
        }
        result = [self.number_field(name, setting, what, values[setting]) for setting, what in NUMBER_FIELDS]
        wraps = register.wraps()
        result.append(Field(
            FIELD_LABEL.format(name=name, what=WRAP_FIELD), lambda: TOGGLE_ON if wraps else TOGGLE_OFF, None,
            lambda: self.change(name, RegisterSetting.WRAP, not wraps), TOGGLE_WHAT,
        ))
        return result

    def number_field(self, name, setting, what, value):
        label = FIELD_LABEL.format(name=name, what=what)
        prompt = PROMPT.format(label=label, lowest=MIN_REGISTER_VALUE, highest=MAX_REGISTER_VALUE)
        return Field(
            label, lambda: value,
            lambda offset: self.change(name, setting, max(min(value + offset, MAX_REGISTER_VALUE), MIN_REGISTER_VALUE)),
            lambda: self.ask_number(prompt, value, lambda number: self.change(name, setting, number), MIN_REGISTER_VALUE, MAX_REGISTER_VALUE),
            ENTER_WHAT, lambda: self.change(name, setting, None), CLEAR_WHAT,
        )

    def change(self, name, setting, value):
        """Change a setting, showing why if the register refuses it, like a minimum above the default."""
        problem = self.document.set_register_setting(name, setting, value)
        if problem:
            self.status = problem
