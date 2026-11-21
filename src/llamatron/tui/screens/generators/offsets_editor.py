# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Offsets editor page: an arpeggiator's offsets, up to 16 steps drawn as a gauge of bars either side of a zero line.

Each offset is a bar from the zero line, five scale steps either
side on a usual console and seven on a taller one, a value past the edge fills to it and is marked
in the Offset row under the gauge, like +7▲, and the cursor's column is marked at both ends,
<<4>> around the step number and <+7▲> around the offset, in reverse video too. A row wider than
the screen scrolls sideways like the pattern editor rather than wrapping onto more blocks.
"""

from rich.text import Text

from llamatron.composition import file_format
from llamatron.composition.file_format import Section
from llamatron.generators import arp as arp_values
from llamatron.tui import drawing, keybindings
from llamatron.tui.components.signed_gauge import SignedGauge
from llamatron.tui.drawing import Box, Style
from llamatron.tui.screens.shared.generator_editor import GeneratorEditor
from llamatron.tui.screens.shared.one_row_editor import OneRowEditor
from llamatron.user_strings import help as help_text, labels, messages


# The lines around the gauge: the note, a blank line, the top rule, the Step row, the zero line, the Offset row and the bottom rule; and the rule over the add rows, when any shows.
LINES_AROUND_GAUGE = 7
RULE_OVER_ADDS = 1
# How many levels the gauge has either side of the zero line: five on a usual console, up to seven on a taller one, and never none.
MAX_GAUGE_LEVELS = 7
MIN_GAUGE_LEVELS = 1
# What a silent step becomes when Space or Enter plays it again.
PLAYS_UNMOVED = 0
# The row the cursor edits: the Offset row, then each register's add row under it, which Tab steps through.
OFFSET_ROW = 0
BLANK_CELL = ''


class OffsetsEditor(GeneratorEditor, OneRowEditor):
    """An arpeggiator's offsets: one row of up to 16 steps, drawn as a gauge around a zero line, and under it a row per register of what each step adds to it, which Tab moves the cursor between."""

    KEYS = keybindings.OffsetsEditor

    HELP = help_text.HELP_OFFSETS_EDITOR

    SECTION = Section.ARPS
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    CRUMBS_AFTER = (labels.Crumb.OFFSETS,)
    # A cell is wide enough for the cursor's marks around the largest value, like <+24▲> or <<16>>.
    CELL_WIDTH = 6
    MOST = arp_values.MAX_OFFSET
    MOST_STEPS = arp_values.MAX_OFFSETS
    INSERT = KEYS.INSERT_STEP
    REMOVE = KEYS.REMOVE_STEP

    def __init__(self, *, holder, name):
        super().__init__(holder=holder, name=name)
        self.edited_row = OFFSET_ROW

    def offsets(self):
        return self.settings().get_offsets()

    def register_edited(self):
        """Return the register whose add row the cursor is on, or None on the Offset row."""
        return None if self.edited_row == OFFSET_ROW else file_format.REGISTER_NAMES[self.edited_row - 1]

    def values(self):
        register = self.register_edited()
        return self.offsets() if register is None else self.settings().get_step_adds(register)

    def most(self):
        register = self.register_edited()
        return self.MOST if register is None else self.document().song().get_register(register).get_allowed_inc_max()

    def shown_add_rows(self):
        """Return the registers whose add rows show: those that add on some step, and the one the cursor is on, so that an arp with no adds draws as it always has."""
        arp = self.settings()
        return [register for register in file_format.REGISTER_NAMES if register == self.register_edited() or any(arp.get_step_adds(register) or [])]

    def next_row(self):
        """Move the cursor to the next row, from the Offset row through each register's add row and back."""
        self.edited_row = (self.edited_row + 1) % (len(file_format.REGISTER_NAMES) + 1)

    def still_exists(self):
        # Opening this editor gives an arp without offsets a row of them, so undoing that leaves nothing to edit here.
        return super().still_exists() and self.offsets() is not None

    def more_keys(self):
        result = [self.bind(self.KEYS.NEXT_ROW, action=self.next_row)]
        if self.register_edited() is None:
            result.append(self.bind(self.KEYS.SILENT if self.value_here() is not None else self.KEYS.PLAY, action=self.toggle))
        return result

    def set_value(self, value):
        register = self.register_edited()
        if register is None:
            self.document().set_arp_offset(name=self.item, step=self.step, offset=value)
        else:
            self.document().set_arp_step_add(name=self.item, register=register, step=self.step, add=value)

    def toggle(self):
        """Make a step that plays silent, or play a silent step again, unmoved."""
        self.set_value(PLAYS_UNMOVED if self.value_here() is None else None)

    def add_step(self):
        self.document().insert_arp_offset(name=self.item, step=self.step)

    def remove_step_here(self):
        self.document().remove_arp_offset(name=self.item, step=self.step)

    # Drawing.

    def gauge_levels(self, height):
        """Return how many levels the gauge draws either side of the zero line, as many as the screen has room for up to seven, after the add rows that show."""
        shown = self.shown_add_rows()
        around = LINES_AROUND_GAUGE + (len(shown) + RULE_OVER_ADDS if shown else 0)
        return max(min((height - around) // 2, MAX_GAUGE_LEVELS), MIN_GAUGE_LEVELS)

    def body(self, *, width, height):
        self.keep_step()
        first, last = self.scroll_to_cursor(width)
        places = range(first, last)
        gauge = SignedGauge(values=self.offsets(), levels=self.gauge_levels(height), cursor=self.step)
        lines = [
            self.with_steps_shown(text=messages.MSG_OFFSETS_NOTE, style=Style.DIM, width=width, first=first, last=last),
            Text(drawing.NOTHING),
            self.grid_rule(left=Box.TOP_LEFT, middle=Box.TOP_TEE, right=Box.TOP_RIGHT, count=len(places)),
        ]
        lines.append(self.grid_line(label=labels.MSG_STEP_ROW_LABEL, cells=[(place, gauge.step_text(place)) for place in places], selected=self.step, bold=True))
        for level in gauge.levels_above():
            lines.append(self.grid_line(label=drawing.NOTHING, cells=[(place, gauge.cell(place=place, level=level)) for place in places]))
        lines.append(self.grid_rule(left=Box.LEFT_TEE, middle=Box.CROSS, right=Box.RIGHT_TEE, count=len(places)))
        for level in gauge.levels_below():
            lines.append(self.grid_line(label=drawing.NOTHING, cells=[(place, gauge.cell(place=place, level=level)) for place in places]))
        on_offsets = self.register_edited() is None
        lines.append(self.grid_line(label=labels.MSG_OFFSET_ROW_LABEL, cells=[(place, gauge.value_text(place)) for place in places], selected=self.step if on_offsets else None))
        shown = self.shown_add_rows()
        if shown:
            lines.append(self.grid_rule(left=Box.LEFT_TEE, middle=Box.CROSS, right=Box.RIGHT_TEE, count=len(places)))
        for register in shown:
            adds = self.settings().get_step_adds(register)
            cells = [(place, BLANK_CELL if not adds[place] else str(adds[place])) for place in places]
            lines.append(self.grid_line(label=labels.MSG_STEP_ADD_ROW_LABEL.format(name=register), cells=cells, selected=self.step if register == self.register_edited() else None))
        lines.append(self.grid_rule(left=Box.BOTTOM_LEFT, middle=Box.BOTTOM_TEE, right=Box.BOTTOM_RIGHT, count=len(places)))
        return lines
