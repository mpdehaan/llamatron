# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The wizard's Form branch: which of the subgenre's forms the song takes, with a branch under it for each section in order."""

from rich.text import Text

from llamatron.interface.forms.nodes import Field, NumberField, Toggle
from llamatron.interface.tracker import drawing
from llamatron.interface.tracker.drawing import Style
from llamatron.interface.tracker.screens.shared.field import Button, ChoiceField, gauge_shown
from llamatron.interface.tracker.screens.wizard.branch import Branch
from llamatron.interface.tracker.screens.wizard.section_branch import SectionBranch
from llamatron.user_strings import errors, labels, legends, marks, messages
from llamatron.wizards.create_song import wizard_limits, wizard_names

# Sections are counted from 1, as they are shown.
FIRST_SECTION_NUMBER = 1


class FormBranch(Branch):
    """The song's form, and its sections as branches."""

    __slots__ = ()

    def name(self):
        return labels.MSG_WIZARD_FORM_BRANCH

    def refusal(self):
        return None if self.get_choices().is_ready() else errors.ERR_WIZARD_CHOOSE_GENRE_AND_SUBGENRE

    def sections(self):
        return self.get_choices().get_song_form().form_sections()

    def children(self):
        return [SectionBranch(page=self.get_page(), place=place) for place in range(len(self.sections()))]

    def fields(self):
        choices = self.get_choices()
        if not choices.is_ready():
            return []
        # The form is only shown here: a suggested form is taken through a button and a dialog, never by
        # stepping a field, which could replace the sections a person changed with one stray key.
        page = self.get_page()
        # A planned song gives every section an Energy, and from it who plays, how hard, how loud and how each section leaves.
        plan = [Toggle(label=labels.MSG_WIZARD_SONG_PLAN_LABEL, on=choices.has_song_plan(), set=page.choosing(choices.set_song_plan))] if choices.can_have_song_plan() else []
        if choices.has_song_plan():
            plan.append(NumberField(page=page, label=labels.MSG_WIZARD_CONTRAST_LABEL, number=choices.get_contrast(), shown=gauge_shown(place=choices.get_contrast(), lowest=wizard_names.LOWEST_ENERGY, highest=wizard_names.HIGHEST_ENERGY), lowest=wizard_names.LOWEST_ENERGY, highest=wizard_names.HIGHEST_ENERGY, set=page.choosing(choices.set_contrast)))
        # How the song starts and ends comes first, since a band settles how to get in and out before the middle is arranged.
        return [*self.stage_fields(), *plan, Field(label=labels.MSG_WIZARD_FORM_LABEL, value=lambda: marks.MSG_WIZARD_OWN_FORM if choices.get_song_form().has_own_form() else choices.get_song_form().get_form()),
                Button(label=labels.MSG_WIZARD_SUGGESTED_FORM_BUTTON, key_name=legends.KeyName.ENTER, enter=self.get_page().pick_suggested_form, enter_what=legends.MSG_WIZARD_SUGGESTED_FORM_WHAT),
                *([Button(label=labels.MSG_WIZARD_FORM_QUESTIONS_BUTTON, key_name=legends.KeyName.ENTER, enter=self.get_page().ask_form_questions, enter_what=legends.MSG_WIZARD_FORM_QUESTIONS_WHAT)] if choices.get_song_form().form_questions() else [])]

    def stage_fields(self):
        """Return the fields of how the song starts and ends: the way of each, who starts alone and is left alone, and how long a stage lasts. Each stage
        is a section of its own in the tree, to change like any other; opening or closing sections a person changed read as the person's own."""
        choices = self.get_choices()
        page = self.get_page()

        def staging(setter):
            def set_way(value):
                try:
                    page.choosing(setter)(value)
                except ValueError as problem:
                    page.refuse(str(problem))
            return set_way
        fields = []
        start, end = choices.get_song_form().get_start(), choices.get_song_form().get_end()
        if choices.get_song_form().starts():
            fields.append(ChoiceField(page=page, label=labels.MSG_WIZARD_STARTS_LABEL, choices=choices.get_song_form().starts(), current=start or choices.get_song_form().starts()[0], shown=None if start is not None else labels.MSG_WIZARD_OWN_START, set=staging(choices.get_song_form().set_start)))
        if choices.get_song_form().ends():
            fields.append(ChoiceField(page=page, label=labels.MSG_WIZARD_ENDS_LABEL, choices=choices.get_song_form().ends(), current=end or choices.get_song_form().ends()[0], shown=None if end is not None else labels.MSG_WIZARD_OWN_START, set=staging(choices.get_song_form().set_end)))
        if (start in wizard_limits.WAYS_WITH_FIRST_PLAYER or end in wizard_limits.WAYS_WITH_FIRST_PLAYER) and len(choices.get_song_form().first_players()) > 1:
            titles = {choices.player(role).title(): role for role in choices.get_song_form().first_players()}
            fields.append(ChoiceField(page=page, label=labels.MSG_WIZARD_FIRST_PLAYER_LABEL, choices=list(titles), current=choices.player(choices.get_song_form().get_first_player()).title(), set=staging(lambda title: choices.get_song_form().set_first_player(titles[title]))))
        if start in wizard_limits.WAYS_WITH_SETUP_BARS or end in wizard_limits.WAYS_WITH_SETUP_BARS:
            bars = {str(count): count for count in choices.get_song_form().setup_bars_offered()}
            fields.append(ChoiceField(page=page, label=labels.MSG_WIZARD_SETUP_BARS_LABEL, choices=list(bars), current=str(choices.get_song_form().get_setup_bars()), set=staging(lambda count: choices.get_song_form().set_setup_bars(bars[count]))))
        return fields

    def remarks(self, width):
        """Return the form's sections in order, each with its bars, so that the whole form reads at a glance; or what to choose first."""
        choices = self.get_choices()
        if not choices.is_ready():
            return [Text(drawing.INDENT + messages.MSG_WIZARD_CHOOSE_FIRST, style=Style.DIM)]
        hint = [Text(drawing.INDENT + messages.MSG_WIZARD_SECTIONS_HINT, style=Style.DIM), Text()]
        sections = choices.get_song_form().section_labels()
        longest = max((len(name) for name in sections), default=0)
        if choices.has_song_plan():
            # A planned song's sections each say their Energy and how they leave.
            try:
                said = choices.said_of_sections()
            except (ValueError, KeyError, IndexError):
                said = []
            if len(said) == len(sections):
                return hint + [Text(drawing.INDENT + labels.MSG_WIZARD_PLAN_LINE.format(number=place + FIRST_SECTION_NUMBER, name=name, width=longest, said=said[place])) for place, name in enumerate(sections)]
        return hint + [Text(drawing.INDENT + marks.MSG_WIZARD_SECTION_LINE.format(number=place + FIRST_SECTION_NUMBER, name=name, width=longest, bars=choices.section(place).bars()))
                for place, name in enumerate(sections)]

    # A new section is added at the end of the form from here, and after a section from the section.

    def adds(self):
        return self.get_choices().is_ready()

    def add(self, kind):
        self.get_choices().get_song_form().add_section(place=len(self.sections()), kind=kind)

    def kinds_to_add(self):
        return self.get_choices().get_song_form().section_kinds()
