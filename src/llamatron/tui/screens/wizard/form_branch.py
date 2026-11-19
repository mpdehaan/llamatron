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

from llamatron.macro_composer import song_plan, wizard_choices
from llamatron.strings import errors, labels, legends, marks, messages
from llamatron.tui import drawing
from llamatron.tui.drawing import Style
from llamatron.tui.screens.shared.field import Button, ChoiceField, Field, gauge_shown, NumberField, Toggle
from llamatron.tui.screens.wizard.branch import Branch
from llamatron.tui.screens.wizard.section_branch import SectionBranch

# Sections are counted from 1, as they are shown.
FIRST_SECTION_NUMBER = 1


class FormBranch(Branch):
    """The song's form, and its sections as branches."""

    __slots__ = ()

    def name(self):
        return labels.MSG_WIZARD_FORM_BRANCH

    def refusal(self):
        return None if self.choices().is_ready() else errors.ERR_WIZARD_CHOOSE_GENRE_AND_SUBGENRE

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
        plan = [Toggle(label=labels.MSG_WIZARD_SONG_PLAN_LABEL, on=choices.has_song_plan(), set=page.choosing(choices.set_song_plan))] if choices.can_have_song_plan() else []
        if choices.has_song_plan():
            plan.append(NumberField(page=page, label=labels.MSG_WIZARD_CONTRAST_LABEL, number=choices.get_contrast(), shown=gauge_shown(place=choices.get_contrast(), lowest=song_plan.LOWEST_ENERGY, highest=song_plan.HIGHEST_ENERGY), lowest=song_plan.LOWEST_ENERGY, highest=song_plan.HIGHEST_ENERGY, set=page.choosing(choices.set_contrast)))
        # How the song starts and ends comes first, since a band settles how to get in and out before the middle is arranged.
        return [*self.stage_fields(), *plan, Field(label=labels.MSG_WIZARD_FORM_LABEL, value=lambda: marks.MSG_WIZARD_OWN_FORM if choices.has_own_form() else choices.get_form()),
                Button(label=labels.MSG_WIZARD_SUGGESTED_FORM_BUTTON, key_name=legends.KeyName.ENTER, enter=self.page().pick_suggested_form, enter_what=legends.MSG_WIZARD_SUGGESTED_FORM_WHAT),
                *([Button(label=labels.MSG_WIZARD_FORM_QUESTIONS_BUTTON, key_name=legends.KeyName.ENTER, enter=self.page().ask_form_questions, enter_what=legends.MSG_WIZARD_FORM_QUESTIONS_WHAT)] if choices.form_questions() else [])]

    def stage_fields(self):
        """Return the fields of how the song starts and ends: the way of each, who starts alone and is left alone, and how long a stage lasts. Each stage
        is a section of its own in the tree, to change like any other; opening or closing sections a person changed read as the person's own."""
        choices = self.choices()
        page = self.page()

        def staging(setter):
            def set_way(value):
                try:
                    page.choosing(setter)(value)
                except ValueError as problem:
                    page.refuse(str(problem))
            return set_way
        fields = []
        start, end = choices.get_start(), choices.get_end()
        if choices.starts():
            fields.append(ChoiceField(page=page, label=labels.MSG_WIZARD_STARTS_LABEL, choices=choices.starts(), current=start or choices.starts()[0], shown=None if start is not None else labels.MSG_WIZARD_OWN_START, set=staging(choices.set_start)))
        if choices.ends():
            fields.append(ChoiceField(page=page, label=labels.MSG_WIZARD_ENDS_LABEL, choices=choices.ends(), current=end or choices.ends()[0], shown=None if end is not None else labels.MSG_WIZARD_OWN_START, set=staging(choices.set_end)))
        if (start in wizard_choices.WAYS_WITH_FIRST_PLAYER or end in wizard_choices.WAYS_WITH_FIRST_PLAYER) and len(choices.first_players()) > 1:
            titles = {choices.role_title(role): role for role in choices.first_players()}
            fields.append(ChoiceField(page=page, label=labels.MSG_WIZARD_FIRST_PLAYER_LABEL, choices=list(titles), current=choices.role_title(choices.get_first_player()), set=staging(lambda title: choices.set_first_player(titles[title]))))
        if start in wizard_choices.WAYS_WITH_SETUP_BARS or end in wizard_choices.WAYS_WITH_SETUP_BARS:
            bars = {str(count): count for count in choices.setup_bars_offered()}
            fields.append(ChoiceField(page=page, label=labels.MSG_WIZARD_SETUP_BARS_LABEL, choices=list(bars), current=str(choices.get_setup_bars()), set=staging(lambda count: choices.set_setup_bars(bars[count]))))
        return fields

    def notes(self, width):
        """Return the form's sections in order, each with its bars, so that the whole form reads at a glance; or what to choose first."""
        choices = self.choices()
        if not choices.is_ready():
            return [Text(drawing.INDENT + messages.MSG_WIZARD_CHOOSE_FIRST, style=Style.DIM)]
        hint = [Text(drawing.INDENT + messages.MSG_WIZARD_SECTIONS_HINT, style=Style.DIM), Text()]
        sections = choices.section_labels()
        longest = max((len(name) for name in sections), default=0)
        if choices.has_song_plan():
            # A planned song's sections each say their Energy and how they leave.
            try:
                said = choices.said_of_sections()
            except (ValueError, KeyError, IndexError):
                said = []
            if len(said) == len(sections):
                return hint + [Text(drawing.INDENT + labels.MSG_WIZARD_PLAN_LINE.format(number=place + FIRST_SECTION_NUMBER, name=name, width=longest, said=said[place])) for place, name in enumerate(sections)]
        return hint + [Text(drawing.INDENT + marks.MSG_WIZARD_SECTION_LINE.format(number=place + FIRST_SECTION_NUMBER, name=name, width=longest, bars=choices.section_bars(place)))
                for place, name in enumerate(sections)]

    # A new section is added at the end of the form from here, and after a section from the section.

    def adds(self):
        return self.choices().is_ready()

    def add(self, kind):
        self.choices().add_section(place=len(self.sections()), kind=kind)

    def kinds_to_add(self):
        return self.choices().section_kinds()
