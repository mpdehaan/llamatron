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
"""The wizard's Form branch: which of the subgenre's forms the song takes, with a branch under it for each section in order."""

from rich.text import Text

from llamatron.macro_composer.song_plan import HIGHEST_ENERGY, LOWEST_ENERGY
from llamatron.strings.errors import ERR_WIZARD_CHOOSE_GENRE_AND_SUBGENRE
from llamatron.strings.labels import MSG_WIZARD_CONTRAST_LABEL, MSG_WIZARD_FORM_BRANCH, MSG_WIZARD_FORM_LABEL, MSG_WIZARD_PLAN_LINE, MSG_WIZARD_SONG_PLAN_LABEL, MSG_WIZARD_SUGGESTED_FORM_BUTTON
from llamatron.strings.legends import KeyName, MSG_WIZARD_SUGGESTED_FORM_WHAT
from llamatron.strings.marks import MSG_WIZARD_OWN_FORM, MSG_WIZARD_SECTION_LINE
from llamatron.strings.messages import MSG_WIZARD_CHOOSE_FIRST, MSG_WIZARD_SECTIONS_HINT
from llamatron.tui.drawing import INDENT, Style
from llamatron.tui.screens.shared.field import Button, Field, NumberField, Toggle
from llamatron.tui.screens.wizard.branch import Branch
from llamatron.tui.screens.wizard.section_branch import SectionBranch

# Sections are counted from 1, as they are shown.
FIRST_SECTION_NUMBER = 1


class FormBranch(Branch):
    """The song's form, and its sections as branches."""

    __slots__ = ()

    def name(self):
        return MSG_WIZARD_FORM_BRANCH

    def refusal(self):
        return None if self.choices().is_ready() else ERR_WIZARD_CHOOSE_GENRE_AND_SUBGENRE

    def sections(self):
        return self.choices().form_sections()

    def children(self):
        return [SectionBranch(page=self.page(), place=place) for place in range(len(self.sections()))]

    def fields(self):
        choices = self.choices()
        if not choices.is_ready():
            return []
        # The form is only shown here: a suggested form is taken through a button and a dialog, never by
        # stepping a field, which could replace the sections a person changed with one stray key.
        page = self.page()
        # A planned song gives every section an Energy, and from it who plays, how hard, how loud and how each section leaves.
        plan = [Toggle(label=MSG_WIZARD_SONG_PLAN_LABEL, on=choices.has_song_plan(), set=page.choosing(choices.set_song_plan))] if choices.can_have_song_plan() else []
        if choices.has_song_plan():
            plan.append(NumberField(page=page, label=MSG_WIZARD_CONTRAST_LABEL, number=choices.get_contrast(), lowest=LOWEST_ENERGY, highest=HIGHEST_ENERGY, set=page.choosing(choices.set_contrast)))
        return [Field(label=MSG_WIZARD_FORM_LABEL, value=lambda: MSG_WIZARD_OWN_FORM if choices.has_own_form() else choices.get_form()), *plan,
                Button(label=MSG_WIZARD_SUGGESTED_FORM_BUTTON, key_name=KeyName.ENTER, enter=self.page().pick_suggested_form, enter_what=MSG_WIZARD_SUGGESTED_FORM_WHAT)]

    def notes(self, width):
        """Return the form's sections in order, each with its bars, so that the whole form reads at a glance; or what to choose first."""
        choices = self.choices()
        if not choices.is_ready():
            return [Text(INDENT + MSG_WIZARD_CHOOSE_FIRST, style=Style.DIM)]
        hint = [Text(INDENT + MSG_WIZARD_SECTIONS_HINT, style=Style.DIM), Text()]
        sections = choices.section_labels()
        longest = max((len(name) for name in sections), default=0)
        if choices.has_song_plan():
            # A planned song's sections each say their Energy and how they leave.
            try:
                said = choices.said_of_sections()
            except (ValueError, KeyError, IndexError):
                said = []
            if len(said) == len(sections):
                return hint + [Text(INDENT + MSG_WIZARD_PLAN_LINE.format(number=place + FIRST_SECTION_NUMBER, name=name, width=longest, said=said[place])) for place, name in enumerate(sections)]
        return hint + [Text(INDENT + MSG_WIZARD_SECTION_LINE.format(number=place + FIRST_SECTION_NUMBER, name=name, width=longest, bars=choices.section_bars(place)))
                for place, name in enumerate(sections)]

    # A new section is added at the end of the form from here, and after a section from the section.

    def adds(self):
        return self.choices().is_ready()

    def add(self, kind):
        self.choices().add_section(place=len(self.sections()), kind=kind)

    def kinds_to_add(self):
        return self.choices().section_kinds()
