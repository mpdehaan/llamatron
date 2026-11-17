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

from llamatron.composition.file_format import GeneratorKind, Section
from llamatron.composition.generator_settings import LINES_IN_BARS, PHRASING_DEFAULTS, PhrasingSetting
from llamatron.generators.phrasing import BREATHS, JOINS, RISES
from llamatron.strings import help as help_text
from llamatron.strings import labels, messages
from llamatron.tui import keybindings
from llamatron.tui.screens.shared.field import ChoiceField, NameField
from llamatron.tui.screens.shared.field_page import FieldPage
from llamatron.tui.screens.shared.shows_named_item import ShowsNamedItem


class PhrasingEditor(ShowsNamedItem, FieldPage):

    KEYS = keybindings.PhrasingEditor
    HELP = help_text.HELP_PHRASING_EDITOR
    SECTION = Section.PHRASINGS
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    RENAME_PROMPT = messages.MSG_RENAME_GENERATOR_PROMPT.format(label=labels.MSG_PHRASING_LABEL)

    def __init__(self, *, holder, name):
        super().__init__(holder)
        self.show_item(name)

    def phrasing(self):
        return self.document().song().get_generator_settings(kind=GeneratorKind.PHRASING, name=self.item)

    def store(self, *, setting, value):
        """Keep a setting, left out of the file where it is what a Phrasing starts with."""
        self.document().set_generator_setting(section=Section.PHRASINGS, name=self.item, setting=setting, value=None if value == PHRASING_DEFAULTS[setting] else value)

    def choice(self, *, label, setting, choices, names=None):
        """Return a field that chooses one of a setting's values from a list, shown by its name where its value is not a word."""
        current = self.phrasing().get_own(setting)
        return ChoiceField(
            page=self, label=label, choices=list(choices), names=names, current=current, shown=None if names is None else names[list(choices).index(current)],
            set=lambda chosen: self.store(setting=setting, value=chosen),
        )

    def fields(self):
        return [
            NameField(value=lambda: self.item, rename=self.rename),
            self.choice(label=labels.MSG_PHRASING_LINE_LABEL, setting=PhrasingSetting.LINE_BARS, choices=LINES_IN_BARS, names=[labels.MSG_PHRASING_LINE_NAMES[bars] for bars in LINES_IN_BARS]),
            self.choice(label=labels.MSG_PHRASING_BREATH_LABEL, setting=PhrasingSetting.BREATH, choices=BREATHS),
            self.choice(label=labels.MSG_PHRASING_RISE_LABEL, setting=PhrasingSetting.RISE_AND_FALL, choices=RISES),
            self.choice(label=labels.MSG_PHRASING_NOTES_LABEL, setting=PhrasingSetting.NOTES, choices=JOINS),
        ]
