# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The editor of a Guitarify's bar of strokes: one stroke a cell, with an accent row under it.

Left and Right move along the cells, stopping at the ends. [ and ] step the cursor's stroke
through the strokes, stopping at both ends, and Up and Down do the same. Space or ENTER accents
the cursor's cell, drawn as every toggle is. I inserts a cell that plays nothing before the
cursor's and D removes the cursor's. S steps the cell's length, and R picks a ready-made bar,
which replaces the strokes, the accents and the cell's length together.
"""
from rich.text import Text

from llamatron.engine.generators import guitarify as guitarify_plugin
from llamatron.engine.generators.guitarify import model as guitarify_settings, schema as guitar_bars
from llamatron.engine.generators.guitarify.schema import ready_bar_matching
from llamatron.interface.forms.nodes import stepped
from llamatron.interface.tracker import drawing, key_table, keybindings
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.drawing import Box, Style
from llamatron.interface.tracker.screens.shared.generator_editor import GeneratorEditor
from llamatron.interface.tracker.screens.shared.step_editor import StepEditor
from llamatron.interface.tracker.screens.shared.step_grid import StepGrid
from llamatron.model.schema import file_format
from llamatron.user_strings import help as help_text, labels, marks, messages

# The lengths S steps a cell through, going round.
CELL_LENGTHS = ['1/4', '1/8', '1/16', '1/12', '1/32']
FEWEST_CELLS = 1
FIRST_CHOICE = 0


class GuitarBarEditor(GeneratorEditor, StepGrid, StepEditor):
    """A Guitarify's bar of strokes, a stroke and an accent a cell."""

    KEYS = keybindings.GuitarBarEditor
    HELP = help_text.HELP_GUITAR_BAR_EDITOR
    SECTION = guitarify_plugin.SECTION
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    CRUMBS_AFTER = (labels.Crumb.STROKES,)
    CELL_WIDTH = 3
    STEPS_SHOWN = marks.MSG_CELLS_SHOWN

    def strokes(self):
        return self.settings().get_bar()

    def accents(self):
        return self.settings().get_accents()

    def step_count(self):
        return len(self.strokes())

    def store(self, *, strokes, accents, cell=None):
        """Keep the bar, its accents and, where given, its cell's length, as one change."""
        self.document().change_set(self.settings().set_bar, strokes=strokes, accents=accents, cell=cell)

    def keys(self):
        self.keep_step()
        result = [
            self.bind(self.KEYS.BACK, action=self.go_back), self.bind(self.KEYS.MOVE, action=self.move_cursor, wants_key=True),
            self.bind(self.KEYS.LESS, action=lambda: self.nudge(key_table.STEP_BACK)), self.bind(self.KEYS.MORE, action=lambda: self.nudge(key_table.STEP_FORWARD)),
            self.bind(self.KEYS.ACCENT, action=self.accent),
        ]
        if self.step_count() < guitarify_settings.MAX_GUITAR_BAR:
            result.append(self.bind(self.KEYS.INSERT_CELL, action=self.insert))
        if self.step_count() > FEWEST_CELLS:
            result.append(self.bind(self.KEYS.REMOVE_CELL, action=self.remove_cell))
        return [*result, self.bind(self.KEYS.CELL_LENGTH, action=self.next_cell_length), self.bind(self.KEYS.READY_BARS, action=self.pick_ready_bar)]

    def move_cursor(self, name):
        self.move_step(name)

    def nudge(self, direction):
        """Step the cursor's stroke to the one before or after, stopping at both ends."""
        self.document().change_set(self.settings().set_cell, step=self.step, value=stepped(values=list(file_format.STROKES), current=self.strokes()[self.step], offset=direction))

    def accent(self):
        accents = self.accents()
        accents[self.step] = not accents[self.step]
        self.store(strokes=self.strokes(), accents=accents)

    def insert(self):
        self.document().change_set(self.settings().insert_cell, self.step)

    def remove_cell(self):
        self.document().change_set(self.settings().remove_cell, self.step)
        self.keep_step()

    def next_cell_length(self):
        """Step the cell's length through the choices, going round at the end."""
        current = self.settings().get_cell()
        following = CELL_LENGTHS[(CELL_LENGTHS.index(current) + 1) % len(CELL_LENGTHS)] if current in CELL_LENGTHS else CELL_LENGTHS[FIRST_CHOICE]
        self.store(strokes=self.strokes(), accents=self.accents(), cell=following)

    def pick_ready_bar(self):
        names = list(guitar_bars.READY_BARS)
        guitar = self.settings()
        ready = ready_bar_matching(cell=guitar.get_cell(), strokes=guitar.get_bar(), accents=guitar.get_accents())
        dialog = ChoiceDialog(title=labels.MSG_READY_BARS_TITLE, options=[labels.MSG_READY_BAR_NAMES[name] for name in names], current=names.index(ready) if ready in names else FIRST_CHOICE)
        self.ask(dialog=dialog, then=lambda chosen: self.take_ready_bar(names[chosen]))

    def take_ready_bar(self, name):
        bar = guitar_bars.READY_BARS[name]
        self.store(strokes=bar.strokes, accents=bar.accents, cell=bar.cell)
        self.keep_step()

    def body(self, *, width, height):
        self.keep_step()
        first, last = self.scroll_to_cursor(width)
        places = range(first, last)
        strokes = self.strokes()
        accents = self.accents()
        note = messages.MSG_GUITAR_CELL_ACCENTED_NOTE if accents[self.step] else messages.MSG_GUITAR_CELL_NOTE
        return [
            self.with_steps_shown(text=messages.MSG_GUITAR_BAR_NOTE.format(cell=self.settings().get_cell()), style=Style.DIM, width=width, first=first, last=last),
            Text(note.format(number=self.step + 1, stroke=labels.MSG_GUITAR_STROKE_NAMES[strokes[self.step]])),
            Text(drawing.NOTHING),
            self.grid_rule(left=Box.TOP_LEFT, middle=Box.TOP_TEE, right=Box.TOP_RIGHT, count=len(places)),
            self.grid_line(label=labels.MSG_CELL_ROW_LABEL, cells=[(place, str(place + 1)) for place in places], bold=True),
            self.grid_rule(left=Box.LEFT_TEE, middle=Box.CROSS, right=Box.RIGHT_TEE, count=len(places)),
            self.grid_line(label=labels.MSG_STROKE_ROW_LABEL, cells=[(place, marks.MSG_STROKE_MARKS[strokes[place]]) for place in places], selected=self.step),
            self.grid_line(label=labels.MSG_ACCENT_ROW_LABEL, cells=[(place, marks.MSG_TOGGLE_ON if accents[place] else marks.MSG_TOGGLE_OFF) for place in places]),
            self.grid_rule(left=Box.BOTTOM_LEFT, middle=Box.BOTTOM_TEE, right=Box.BOTTOM_RIGHT, count=len(places)),
        ]
