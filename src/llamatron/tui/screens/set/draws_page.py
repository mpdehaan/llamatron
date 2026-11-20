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
"""The Draws page: the song's four draws, AD to DD, each a section of settings over its strip of slots."""

from llamatron.composition import file_format
from llamatron.composition.file_format import DrawSetting
from llamatron.strings import help as help_text, labels, marks, messages
from llamatron.tui import drawing, keybindings, themes
from llamatron.tui.screens.shared.field import ChoiceField, NumberField, Strip, Toggle
from llamatron.tui.screens.shared.field_page import FieldPage


class DrawsPage(FieldPage):
    """Each draw's direction, how many slots it holds, the range its values keep to, whether conditions redraw it, and its strip."""

    THEME = themes.DRAWS

    KEYS = keybindings.DrawsPage

    crumbs = (labels.Crumb.DRAWS,)
    HELP = help_text.HELP_DRAWS_PAGE

    def fields(self):
        """Return every draw's section, its heading and then its settings and strip, draw by draw."""
        result = []
        lit = self.app.transport.draw_places()
        for name in file_format.DRAW_NAMES:
            heading = self.heading(label=name, is_set=lambda name=name: not self.document().draw(name).is_default(), said=self.lit_said(name=name, lit=lit))
            result += [heading, *self.draw_fields(name=name, lit=lit.get(name))]
        return result

    def lit_said(self, *, name, lit):
        """Return what a draw's heading says while a song plays, its mark of a value inside and the slot it last took a value from, or None to say only the mark."""
        if name not in lit:
            return None
        mark = marks.MSG_SECTION_SET if not self.document().draw(name).is_default() else drawing.NOTHING
        return lambda: marks.MSG_DRAW_HEADING_LIT.format(mark=mark, place=lit[name] + 1)

    def draw_fields(self, *, name, lit=None):
        """Return one draw's settings, in the order they are shown, then its strip."""
        draw = self.document().draw(name)
        lowest = draw.get_value_min()
        highest = draw.get_value_max()
        fewest, most = draw.slot_count_limits()
        return [
            ChoiceField(page=self, label=labels.MSG_DRAW_DIRECTION_LABEL, choices=file_format.DRAW_DIRECTIONS, current=draw.get_direction(),
                        set=lambda choice: self.change(name=name, setting=DrawSetting.DIRECTION, value=None if choice == file_format.FORWARD else choice)),
            NumberField(page=self, label=labels.MSG_DRAW_SLOTS_LABEL, number=draw.slot_count(), lowest=fewest, highest=most,
                        set=lambda count: self.refuse_if(self.document().set_draw_slot_count(name=name, count=count))),
            self.range_field(name=name, label=labels.MSG_DRAW_VALUE_MIN_LABEL, setting=DrawSetting.VALUE_MIN, number=lowest, limits=draw.value_limits()),
            self.range_field(name=name, label=labels.MSG_DRAW_VALUE_MAX_LABEL, setting=DrawSetting.VALUE_MAX, number=highest, limits=draw.value_limits()),
            Toggle(label=labels.MSG_DRAW_CONDITIONS_REDRAW_LABEL, on=draw.redraws_in_conditions(),
                   set=lambda on: self.change(name=name, setting=DrawSetting.CONDITIONS_REDRAW, value=True if on else None)),
            Strip(label=labels.MSG_DRAW_STRIP_LABEL, lit=lit, cells=[self.slot_field(name=name, place=place, value=value, lowest=lowest, highest=highest) for place, value in enumerate(draw.get_slots())]),
        ]

    def range_field(self, *, name, label, setting, number, limits):
        """Return one end of a draw's range, between the limits every draw keeps to, Bksp going back to its default: the lowest
        limit for Value Min and the highest for Value Max."""
        lowest, highest = limits
        default = lowest if setting == DrawSetting.VALUE_MIN else highest
        return NumberField(
            page=self, label=label, number=number, lowest=lowest, highest=highest,
            set=lambda value: self.change(name=name, setting=setting, value=None if value == default else value),
            clear=lambda: self.change(name=name, setting=setting, value=None),
        )

    def slot_field(self, *, name, place, value, lowest, highest):
        """Return one slot of a draw's strip: stepped and typed within the draw's range, starting from 0 when blank, and Bksp makes it blank."""
        return NumberField(
            page=self, label=labels.MSG_DRAW_STRIP_LABEL, number=value, start=max(lowest, min(0, highest)), lowest=lowest, highest=highest,
            shown=drawing.NOTHING if value is None else None, title=messages.MSG_DRAW_SLOT_PROMPT.format(name=name, place=place + 1, lowest=lowest, highest=highest),
            set=lambda number: self.refuse_if(self.document().set_draw_slot(name=name, place=place, value=number)),
            clear=lambda: self.refuse_if(self.document().set_draw_slot(name=name, place=place, value=None)),
        )

    def change(self, *, name, setting, value):
        """Change a setting of a draw, showing why if the draw refuses it, like a Value Min above the Value Max."""
        self.refuse_if(self.document().set_draw_setting(name=name, setting=setting, value=value))

    def refuse_if(self, problem):
        """Show a problem on the status line, where there is one."""
        if problem:
            self.refuse(problem)
