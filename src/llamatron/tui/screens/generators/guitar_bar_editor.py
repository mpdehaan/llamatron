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

"""The editor of a Guitarify's bar of strokes: one stroke a cell, with an accent row under it.

Left and Right move along the cells, stopping at the ends. [ and ] step the cursor's stroke
through the strokes, stopping at both ends, and Up and Down do the same. Space or ENTER accents
the cursor's cell, drawn as every toggle is. I inserts a cell that plays nothing before the
cursor's and D removes the cursor's. S steps the cell's length, and R picks a ready-made bar,
which replaces the strokes, the accents and the cell's length together.
"""

from rich.text import Text

from llamatron.composition.file_format import STROKES, GeneratorKind, GuitarifySetting, Section, Stroke
from llamatron.composition.generator_settings import MAX_GUITAR_BAR
from llamatron.composition.guitar_bars import READY_BARS, ready_bar_matching
from llamatron.strings.help import HELP_GUITAR_BAR_EDITOR
from llamatron.strings.labels import Crumb, MSG_ACCENT_ROW_LABEL, MSG_CELL_ROW_LABEL, MSG_GUITAR_STROKE_NAMES, MSG_READY_BAR_NAMES, MSG_READY_BARS_TITLE, MSG_STROKE_ROW_LABEL
from llamatron.strings.marks import MSG_CELLS_SHOWN, MSG_STROKE_MARKS, MSG_TOGGLE_OFF, MSG_TOGGLE_ON
from llamatron.strings.messages import MSG_GUITAR_BAR_NOTE, MSG_GUITAR_CELL_ACCENTED_NOTE, MSG_GUITAR_CELL_NOTE
from llamatron.tui import keybindings
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.drawing import Box, NOTHING, Style
from llamatron.tui.key_table import STEP_BACK, STEP_FORWARD, cursor_moved
from llamatron.tui.screens.shared.shared import stepped
from llamatron.tui.screens.shared.shows_named_item import ShowsNamedItem
from llamatron.tui.screens.shared.step_editor import StepEditor
from llamatron.tui.screens.shared.step_grid import StepGrid

# The lengths S steps a cell through, going round.
CELL_LENGTHS = ['1/4', '1/8', '1/16', '1/12', '1/32']
FEWEST_CELLS = 1
FIRST_CHOICE = 0


class GuitarBarEditor(ShowsNamedItem, StepGrid, StepEditor):
    """A Guitarify's bar of strokes, a stroke and an accent a cell."""

    KEYS = keybindings.GuitarBarEditor
    HELP = HELP_GUITAR_BAR_EDITOR
    SECTION = Section.GUITARIFIES
    CRUMBS_BEFORE = (Crumb.GENERATORS,)
    CRUMBS_AFTER = (Crumb.STROKES,)
    CELL_WIDTH = 3
    STEPS_SHOWN = MSG_CELLS_SHOWN

    def __init__(self, *, holder, name):
        super().__init__(holder)
        self.show_item(name)

    def guitar(self):
        return self.document().song().get_generator_settings(kind=GeneratorKind.GUITARIFY, name=self.item)

    def strokes(self):
        return self.guitar().get_bar()

    def accents(self):
        return self.guitar().get_accents()

    def steps(self):
        return len(self.strokes())

    def store(self, *, strokes, accents, cell=None):
        """Keep the bar, its accents and, where given, its cell's length, as one change."""
        document = self.document()
        length = self.guitar().get_cell() if cell is None else cell
        document.set_generator_setting(section=self.SECTION, name=self.item, setting=GuitarifySetting.BAR, value=list(strokes))
        document.set_generator_setting(section=self.SECTION, name=self.item, setting=GuitarifySetting.ACCENTS, value=list(accents))
        document.set_generator_setting(section=self.SECTION, name=self.item, setting=GuitarifySetting.CELL, value=length)

    def keys(self):
        self.keep_step()
        result = [
            self.bind(self.KEYS.BACK, action=self.go_back), self.bind(self.KEYS.MOVE, action=self.move, wants_key=True),
            self.bind(self.KEYS.LESS, action=lambda: self.nudge(STEP_BACK)), self.bind(self.KEYS.MORE, action=lambda: self.nudge(STEP_FORWARD)),
            self.bind(self.KEYS.ACCENT, action=self.accent),
        ]
        if self.steps() < MAX_GUITAR_BAR:
            result.append(self.bind(self.KEYS.INSERT_CELL, action=self.insert))
        if self.steps() > FEWEST_CELLS:
            result.append(self.bind(self.KEYS.REMOVE_CELL, action=self.remove_cell))
        return [*result, self.bind(self.KEYS.CELL_LENGTH, action=self.next_cell_length), self.bind(self.KEYS.READY_BARS, action=self.pick_ready_bar)]

    def move(self, name):
        self.step = cursor_moved(place=self.step, name=name, count=self.steps())

    def nudge(self, direction):
        """Step the cursor's stroke to the one before or after, stopping at both ends."""
        strokes = self.strokes()
        strokes[self.step] = stepped(values=list(STROKES), current=strokes[self.step], offset=direction)
        self.store(strokes=strokes, accents=self.accents())

    def accent(self):
        accents = self.accents()
        accents[self.step] = not accents[self.step]
        self.store(strokes=self.strokes(), accents=accents)

    def insert(self):
        strokes = self.strokes()
        accents = self.accents()
        self.store(strokes=strokes[:self.step] + [Stroke.NOTHING] + strokes[self.step:], accents=accents[:self.step] + [False] + accents[self.step:])

    def remove_cell(self):
        strokes = self.strokes()
        accents = self.accents()
        self.store(strokes=strokes[:self.step] + strokes[self.step + 1:], accents=accents[:self.step] + accents[self.step + 1:])
        self.keep_step()

    def next_cell_length(self):
        """Step the cell's length through the choices, going round at the end."""
        current = self.guitar().get_cell()
        following = CELL_LENGTHS[(CELL_LENGTHS.index(current) + 1) % len(CELL_LENGTHS)] if current in CELL_LENGTHS else CELL_LENGTHS[FIRST_CHOICE]
        self.store(strokes=self.strokes(), accents=self.accents(), cell=following)

    def pick_ready_bar(self):
        names = list(READY_BARS)
        guitar = self.guitar()
        ready = ready_bar_matching(cell=guitar.get_cell(), strokes=guitar.get_bar(), accents=guitar.get_accents())
        dialog = ChoiceDialog(title=MSG_READY_BARS_TITLE, options=[MSG_READY_BAR_NAMES[name] for name in names], current=names.index(ready) if ready in names else FIRST_CHOICE)
        self.ask(dialog=dialog, then=lambda chosen: self.take_ready_bar(names[chosen]))

    def take_ready_bar(self, name):
        bar = READY_BARS[name]
        self.store(strokes=bar.strokes, accents=bar.accents, cell=bar.cell)
        self.keep_step()

    def body(self, *, width, height):
        self.keep_step()
        first, last = self.scroll_to_cursor(width)
        places = range(first, last)
        strokes = self.strokes()
        accents = self.accents()
        note = MSG_GUITAR_CELL_ACCENTED_NOTE if accents[self.step] else MSG_GUITAR_CELL_NOTE
        return [
            self.with_steps_shown(text=MSG_GUITAR_BAR_NOTE.format(cell=self.guitar().get_cell()), style=Style.DIM, width=width, first=first, last=last),
            Text(note.format(number=self.step + 1, stroke=MSG_GUITAR_STROKE_NAMES[strokes[self.step]])),
            Text(NOTHING),
            self.grid_rule(left=Box.TOP_LEFT, middle=Box.TOP_TEE, right=Box.TOP_RIGHT, count=len(places)),
            self.grid_line(label=MSG_CELL_ROW_LABEL, cells=[(place, str(place + 1)) for place in places], bold=True),
            self.grid_rule(left=Box.LEFT_TEE, middle=Box.CROSS, right=Box.RIGHT_TEE, count=len(places)),
            self.grid_line(label=MSG_STROKE_ROW_LABEL, cells=[(place, MSG_STROKE_MARKS[strokes[place]]) for place in places], selected=self.step),
            self.grid_line(label=MSG_ACCENT_ROW_LABEL, cells=[(place, MSG_TOGGLE_ON if accents[place] else MSG_TOGGLE_OFF) for place in places]),
            self.grid_rule(left=Box.BOTTOM_LEFT, middle=Box.BOTTOM_TEE, right=Box.BOTTOM_RIGHT, count=len(places)),
        ]
