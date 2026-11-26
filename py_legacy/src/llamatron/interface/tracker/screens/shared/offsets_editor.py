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

from llamatron.engine.generators import arp as arp_plugin
from llamatron.engine.generators.arp import schema
from llamatron.interface.forms import step_grid as step_grid_nodes
from llamatron.interface.tracker import drawing, keybindings
from llamatron.interface.tracker.components.signed_gauge import SignedGauge
from llamatron.interface.tracker.screens.shared.generator_editor import GeneratorEditor
from llamatron.interface.tracker.screens.shared.one_row_editor import OneRowEditor
from llamatron.user_strings import help as help_text, labels, messages


# The lines around the gauge: the note, a blank line, the top rule, the Step row, the zero line, the Offset row and the bottom rule.
LINES_AROUND_GAUGE = 7
# How many levels the gauge has either side of the zero line: five on a usual console, up to seven on a taller one, and never none.
MAX_GAUGE_LEVELS = 7
MIN_GAUGE_LEVELS = 1
# What a silent step becomes when Space or Enter plays it again.
PLAYS_UNMOVED = 0


class OffsetsEditor(GeneratorEditor, OneRowEditor):
    """An arpeggiator's offsets: one row of up to 16 steps, drawn as a gauge around a zero line."""

    KEYS = keybindings.OffsetsEditor

    HELP = help_text.HELP_OFFSETS_EDITOR

    SECTION = arp_plugin.SECTION
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    CRUMBS_AFTER = (labels.Crumb.OFFSETS,)
    # A cell is wide enough for the cursor's marks around the largest value, like <+24▲> or <<16>>.
    CELL_WIDTH = 6
    MOST = schema.MAX_OFFSET
    MOST_STEPS = schema.MAX_OFFSETS
    INSERT = KEYS.INSERT_STEP
    REMOVE = KEYS.REMOVE_STEP

    def __init__(self, *, holder, name, built_in=None):
        super().__init__(holder=holder, name=name, built_in=built_in)

    def offsets(self):
        return self.settings().get_offsets()

    def values(self):
        return self.offsets()

    def still_exists(self):
        # Opening this editor gives an arp without offsets a row of them, so undoing that leaves nothing to edit here.
        return super().still_exists() and self.offsets() is not None

    def more_keys(self):
        return [self.bind(self.KEYS.SILENT if self.value_here() is not None else self.KEYS.PLAY, action=self.toggle)]

    def set_value(self, value):
        # Through the settings the page shows, so that a clip's or a track's built-in Arp is changed as one of the set's list is.
        self.document().change_set(self.settings().set_cell, step=self.step, value=value)

    def toggle(self):
        """Make a step that plays silent, or play a silent step again, unmoved."""
        self.set_value(PLAYS_UNMOVED if self.value_here() is None else None)

    def add_step(self):
        self.document().change_set(self.settings().insert_cell, self.step)

    def remove_step_here(self):
        self.document().change_set(self.settings().remove_cell, self.step)

    # Drawing.

    def gauge_levels(self, height):
        """Return how many levels the gauge draws either side of the zero line, as many as the screen has room for up to seven."""
        return max(min((height - LINES_AROUND_GAUGE) // 2, MAX_GAUGE_LEVELS), MIN_GAUGE_LEVELS)

    def body(self, *, width, height):
        self.keep_step()
        first, last = self.scroll_to_cursor(width)
        places = range(first, last)
        gauge = SignedGauge(values=self.offsets(), levels=self.gauge_levels(height), cursor=self.step)
        lines = [
            self.with_steps_shown(text=messages.MSG_OFFSETS_NOTE, dim=True, first=first, last=last),
            Text(drawing.NOTHING),
            self.grid_rule(edge=step_grid_nodes.TOP, count=len(places)),
        ]
        lines.append(self.grid_line(label=labels.MSG_STEP_ROW_LABEL, cells=[(place, gauge.step_text(place)) for place in places], selected=self.step, bold=True))
        for level in gauge.levels_above():
            lines.append(self.grid_line(label=drawing.NOTHING, cells=[(place, gauge.cell(place=place, level=level)) for place in places]))
        lines.append(self.grid_rule(edge=step_grid_nodes.ACROSS, count=len(places)))
        for level in gauge.levels_below():
            lines.append(self.grid_line(label=drawing.NOTHING, cells=[(place, gauge.cell(place=place, level=level)) for place in places]))
        lines.append(self.grid_line(label=labels.MSG_OFFSET_ROW_LABEL, cells=[(place, gauge.value_text(place)) for place in places], selected=self.step))
        lines.append(self.grid_rule(edge=step_grid_nodes.BOTTOM, count=len(places)))
        return self.drawn(lines=lines, width=width)
