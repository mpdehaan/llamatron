# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Draws page as a presenter: the song's eight draws, AD to HD, each a section of its settings over its strip of slots, and
while a song plays, the slot each draw last took a value from, lit."""

from llamatron.interface.forms.nodes import ChoiceField, NumberField, Strip, Toggle
from llamatron.model.schema import file_format
from llamatron.model.schema.file_format import DrawSetting
from llamatron.user_strings import labels, marks, messages

# A blank slot, and a heading's mark of no value inside.
NOTHING = ''


class DrawsPresenter:
    """What the Draws page shows and does, for the set a document holds: page is what its fields ask through and what makes a
    section's heading, and lit the place of the slot each draw last took a value from while a song plays, by name."""

    __slots__ = ('_page', '_document', '_lit')

    def __init__(self, *, page, document, lit):
        self._page = page
        self._document = document
        self._lit = lit

    def form(self):
        """Return the page's form: every draw's section, its heading and then its settings and strip, draw by draw."""
        result = []
        lit = self._lit
        for name in file_format.DRAW_NAMES:
            heading = self._page.heading(label=name, is_set=lambda name=name: not self._document.draw(name).is_default(), said=self.lit_said(name=name, lit=lit))
            result += [heading, *self.draw_fields(name=name, lit=lit.get(name))]
        return result

    def lit_said(self, *, name, lit):
        """Return what a draw's heading says while a song plays, its mark of a value inside and the slot it last took a value from, or None to say only the mark."""
        if name not in lit:
            return None
        mark = marks.MSG_SECTION_SET if not self._document.draw(name).is_default() else NOTHING
        return lambda: marks.MSG_DRAW_HEADING_LIT.format(mark=mark, place=lit[name] + 1)

    def draw_fields(self, *, name, lit=None):
        """Return one draw's settings, in the order they are shown, then its strip."""
        draw = self._document.draw(name)
        lowest = draw.get_value_min()
        highest = draw.get_value_max()
        fewest, most = draw.slot_count_limits()
        return [
            ChoiceField(page=self._page, label=labels.MSG_DRAW_DIRECTION_LABEL, choices=file_format.DRAW_DIRECTIONS, current=draw.get_direction(),
                        set=lambda choice: self.change(name=name, setting=DrawSetting.DIRECTION, value=None if choice == file_format.FORWARD else choice)),
            NumberField(page=self._page, label=labels.MSG_DRAW_SLOTS_LABEL, number=draw.slot_count(), lowest=fewest, highest=most,
                        set=lambda count: self.refuse_if(self._document.set_draw_slot_count(name=name, count=count))),
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
            page=self._page, label=label, number=number, lowest=lowest, highest=highest,
            set=lambda value: self.change(name=name, setting=setting, value=None if value == default else value),
            clear=lambda: self.change(name=name, setting=setting, value=None), clear_what=str(default),
        )

    def slot_field(self, *, name, place, value, lowest, highest):
        """Return one slot of a draw's strip: stepped and typed within the draw's range, starting from 0 when blank, and Bksp makes it blank."""
        return NumberField(
            page=self._page, label=labels.MSG_DRAW_STRIP_LABEL, number=value, start=max(lowest, min(0, highest)), lowest=lowest, highest=highest,
            shown=NOTHING if value is None else None, title=messages.MSG_DRAW_SLOT_PROMPT.format(name=name, place=place + 1, lowest=lowest, highest=highest),
            set=lambda number: self.refuse_if(self._document.set_draw_slot(name=name, place=place, value=number)),
            clear=lambda: self.refuse_if(self._document.set_draw_slot(name=name, place=place, value=None)),
        )

    def change(self, *, name, setting, value):
        """Change a setting of a draw, showing why if the draw refuses it, like a Value Min above the Value Max."""
        self.refuse_if(self._document.set_draw_setting(name=name, setting=setting, value=value))

    def refuse_if(self, problem):
        """Show a problem on the status line, where there is one."""
        if problem:
            self._page.refuse(problem)
