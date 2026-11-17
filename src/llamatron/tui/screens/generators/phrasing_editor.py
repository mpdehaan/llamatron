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
"""The Phrasing editor: how long a line is, how the lines breathe, and a table of what each kind of section does of its own."""

from llamatron.composition.file_format import SECTION_KINDS, GeneratorKind, Section
from llamatron.composition.generator_settings import DEFAULT_LINE_BARS, LINES_IN_BARS, PHRASING_DEFAULTS, PhrasingSetting
from llamatron.generators.phrasing import BREATHS, FEWEST_EARLY, LINE_LENGTHS, MOST_EARLY
from llamatron.strings.help import HELP_PHRASING_EDITOR
from llamatron.strings.labels import (
    Crumb, MSG_BY_SECTION_CELL_TITLE, MSG_BY_SECTION_COLUMN, MSG_BY_SECTION_HEADING, MSG_PHRASING_BREATH_LABEL, MSG_PHRASING_EARLY_LABEL, MSG_PHRASING_LABEL, MSG_PHRASING_LINE_LABEL, MSG_PHRASING_LINE_LENGTHS_LABEL,
    MSG_PHRASING_LINE_NAMES,
)
from llamatron.strings.marks import MSG_PICKER_MARK, MSG_SAME_AS_ABOVE
from llamatron.strings.messages import MSG_RENAME_GENERATOR_PROMPT
from llamatron.tui import keybindings
from llamatron.tui.screens.shared.field import Cells, ChoiceField, Field, NameField, NumberField
from llamatron.tui.screens.shared.field_page import FieldPage
from llamatron.tui.screens.shared.shows_named_item import ShowsNamedItem

# What a kind of section can say of its own, in the order of the table's cells, each with its label and its choices.
EARLY_COUNTS = tuple(range(FEWEST_EARLY, MOST_EARLY + 1))
BY_SECTION_CELLS = (
    (PhrasingSetting.BREATH, MSG_PHRASING_BREATH_LABEL, BREATHS),
    (PhrasingSetting.LINE_LENGTHS, MSG_PHRASING_LINE_LENGTHS_LABEL, LINE_LENGTHS),
    (PhrasingSetting.EARLY_NOTES, MSG_PHRASING_EARLY_LABEL, EARLY_COUNTS),
)


def column_width(*, label, choices):
    """Return how wide a column of the table is: as wide as its heading and its longest value."""
    return max(len(label), len(MSG_SAME_AS_ABOVE), *[len(str(choice)) for choice in choices])


class PhrasingEditor(ShowsNamedItem, FieldPage):

    KEYS = keybindings.PhrasingEditor
    HELP = HELP_PHRASING_EDITOR
    SECTION = Section.PHRASINGS
    CRUMBS_BEFORE = (Crumb.GENERATORS,)
    RENAME_PROMPT = MSG_RENAME_GENERATOR_PROMPT.format(label=MSG_PHRASING_LABEL)

    def __init__(self, *, holder, name):
        super().__init__(holder)
        self.show_item(name)

    def phrasing(self):
        return self.document().song().get_generator_settings(kind=GeneratorKind.PHRASING, name=self.item)

    def store(self, *, setting, value, default):
        """Keep a setting, left out of the file where it is what a Phrasing starts with."""
        self.document().set_generator_setting(section=Section.PHRASINGS, name=self.item, setting=setting, value=None if value == default else value)

    def store_own(self, *, section, setting, value):
        self.document().set_phrasing_section_own(name=self.item, section=section, setting=setting, value=value)

    def choice(self, *, label, setting, choices):
        return ChoiceField(
            page=self, label=label, choices=list(choices), current=self.phrasing().get_own(setting),
            set=lambda chosen: self.store(setting=setting, value=chosen, default=PHRASING_DEFAULTS[setting]),
        )

    def own_cell(self, *, section, setting, label, choices):
        """Return one cell of a section's row: the section's own value, or that it takes the value above."""
        own = self.phrasing().get_section_own(section=section, name=setting)
        names = [MSG_SAME_AS_ABOVE, *[str(choice) for choice in choices]]
        values = [None, *choices]
        return ChoiceField(
            page=self, label=MSG_BY_SECTION_CELL_TITLE.format(section=section, label=label), choices=names, current=names[values.index(own)],
            shown=names[values.index(own)].ljust(column_width(label=label, choices=choices)),
            set=lambda chosen: self.store_own(section=section, setting=setting, value=values[names.index(chosen)]),
            clear=lambda: self.store_own(section=section, setting=setting, value=None),
        )

    def section_row(self, section):
        cells = [self.own_cell(section=section, setting=setting, label=label, choices=choices) for setting, label, choices in BY_SECTION_CELLS]
        return Cells(label=section, cells=cells)

    def column_headings(self):
        """Return the row that names the table's columns, over the cells of every section's row. It holds nothing to change."""
        headings = [Field(label=label, value=lambda label=label, choices=choices: label.upper().ljust(column_width(label=label, choices=choices) + len(MSG_PICKER_MARK))) for _, label, choices in BY_SECTION_CELLS]
        return Cells(label=MSG_BY_SECTION_COLUMN, cells=headings)

    def any_section_set(self):
        return bool(self.phrasing().to_data().get(PhrasingSetting.BY_SECTION))

    def fields(self):
        phrasing = self.phrasing()
        early = phrasing.get_own(PhrasingSetting.EARLY_NOTES)
        return [
            NameField(value=lambda: self.item, rename=self.rename),
            ChoiceField(
                page=self, label=MSG_PHRASING_LINE_LABEL, choices=list(LINES_IN_BARS), names=[MSG_PHRASING_LINE_NAMES[bars] for bars in LINES_IN_BARS],
                current=phrasing.get_line_bars(), shown=MSG_PHRASING_LINE_NAMES[phrasing.get_line_bars()],
                set=lambda bars: self.store(setting=PhrasingSetting.LINE_BARS, value=bars, default=DEFAULT_LINE_BARS),
            ),
            self.choice(label=MSG_PHRASING_BREATH_LABEL, setting=PhrasingSetting.BREATH, choices=BREATHS),
            self.choice(label=MSG_PHRASING_LINE_LENGTHS_LABEL, setting=PhrasingSetting.LINE_LENGTHS, choices=LINE_LENGTHS),
            NumberField(
                page=self, label=MSG_PHRASING_EARLY_LABEL, number=early, lowest=FEWEST_EARLY, highest=MOST_EARLY,
                set=lambda count: self.store(setting=PhrasingSetting.EARLY_NOTES, value=count, default=PHRASING_DEFAULTS[PhrasingSetting.EARLY_NOTES]),
            ),
            self.heading(label=MSG_BY_SECTION_HEADING, is_set=self.any_section_set),
            self.column_headings(),
            *[self.section_row(section) for section in SECTION_KINDS],
        ]

