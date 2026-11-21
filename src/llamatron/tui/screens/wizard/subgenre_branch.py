# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The song wizard's Subgenre branch, under Genre: the subgenre and the settings that are the subgenre's own."""

from llamatron.composition import limits
from llamatron.tui.screens.shared.field import ChoiceField, NumberField
from llamatron.tui.screens.wizard.branch import Branch
from llamatron.user_strings import errors, labels, legends, marks


class SubgenreBranch(Branch):
    """The subgenre, and what a subgenre is played with: only the settings that mean something for the one chosen are shown."""

    __slots__ = ()

    def name(self):
        return labels.MSG_WIZARD_SUBGENRE_BRANCH

    def refusal(self):
        return None if self.get_choices().get_genre() is not None else errors.ERR_WIZARD_CHOOSE_GENRE

    def fields(self):
        choices = self.get_choices()
        page = self.get_page()
        if choices.get_genre() is None:
            return []
        subgenres = choices.subgenres()
        fields = [self.choice_from_nothing(label=labels.MSG_WIZARD_SUBGENRE_LABEL, values=subgenres, names=subgenres, current=choices.get_subgenre(), set_value=choices.set_subgenre)]
        if not choices.is_ready():
            return fields
        if choices.variants():
            fields.append(self.variant_field())
        lowest, highest = choices.tempo_range()
        fields.append(NumberField(page=page, label=labels.MSG_TEMPO_LABEL, number=choices.get_tempo(), shown=marks.MSG_WIZARD_TEMPO_SHOWN.format(tempo=choices.get_tempo(), low=lowest, high=highest),
                                  lowest=limits.MIN_TEMPO, highest=limits.MAX_TEMPO, set=page.choosing(choices.set_tempo)))
        if choices.has_swing():
            # The subgenre's own swing is said to be the genre's.
            swing = choices.get_swing()
            shown = labels.MSG_WIZARD_VALUE_FROM.format(value=swing, origin=legends.MSG_FROM_GENRE_WHAT) if swing == choices.swing_of_genre() else None
            fields.append(ChoiceField(page=page, label=labels.MSG_WIZARD_SWING_LABEL, choices=choices.swings(), current=swing, shown=shown, set=page.choosing(choices.set_swing)))
        return fields

    def variant_field(self):
        """Return the field of the kind of song the subgenre makes, whose picker says what each kind is; choosing one says so too."""
        choices = self.get_choices()
        page = self.get_page()
        kinds = choices.variants()

        def chosen(kind):
            choices.set_variant(kind)
            page.say(choices.variant_says())
        return ChoiceField(page=page, label=labels.MSG_WIZARD_VARIANT_LABEL, choices=kinds, names=[labels.MSG_WIZARD_VARIANT_NAMED.format(name=kind, says=choices.variant_says(variant=kind)) for kind in kinds],
                           current=choices.get_variant(), set=page.choosing(chosen))
