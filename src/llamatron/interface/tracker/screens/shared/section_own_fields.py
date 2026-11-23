# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The fields of what a section of the song wizard's form may be given of its own: each shows what the section takes and where
from until it is given, and Bksp gives it back."""

import functools

from llamatron.interface.forms.nodes import ChoiceField, Field, gauge_shown, NumberField, Toggle
from llamatron.interface.tracker.screens.shared.section_fade import fade_field, give_section_own
from llamatron.model.schema import limits
from llamatron.model.values import note
from llamatron.user_strings import labels, messages
from llamatron.wizards.create_song import wizard_limits, wizard_names

# The numbers a section can be given of its own, each with its range, and the choices of each field chosen from a list.
NUMBERS_OF_SECTION = {
    wizard_names.SONG_PLAN_ENERGY: (wizard_names.LOWEST_ENERGY, wizard_names.HIGHEST_ENERGY),
    wizard_names.TEMPO_OF_PLACE: (limits.MIN_TEMPO, limits.MAX_TEMPO),
    wizard_names.TEMPO_END_OF_PLACE: (limits.MIN_TEMPO, limits.MAX_TEMPO),
}
CHOICES_OF_SECTION = {
    wizard_names.JOINS_LEAVES: list(wizard_limits.LEAVES_AS_JOIN),
    wizard_names.SONG_PLAN_SETUP: [wizard_names.NOT_AT_ALL],
    wizard_names.ROOT_OF_PLACE: list(note.ROOT_NAMES),
    wizard_names.TYPE_OF_PLACE: list(wizard_limits.SCALE_TYPES),
}
# The fields of a section's fade.
FADE_FIELDS = (wizard_names.SONG_PLAN_FADES, wizard_names.FADE_LEVEL, wizard_names.FADE_OVER)



class SectionOwnFields:
    """The fields of what one section of the form may be given of its own, by the section's place, each of the kind its
    value is: a number, the chords, a switch or a choice from a list."""

    __slots__ = ('_branch', '_choices', '_page', '_place')

    def __init__(self, *, branch, place):
        self._branch = branch
        self._choices = branch.get_choices()
        self._page = branch.get_page()
        self._place = place

    def _section(self):
        return self._choices.section(self._place)

    def fields_in(self, *, own, of_group):
        """Return the fields of a group of a section's own settings that the section offers."""
        fields = []
        for field in own:
            if field in of_group:
                fields.append(self.field(field))
        return fields

    def checker(self, of_group):
        """Return what says whether the section was given anything of its own for a group's fields."""
        return functools.partial(self._has_own_in, of_group=of_group)

    def _has_own_in(self, *, of_group):
        section = self._section()
        for field in of_group:
            if section.own(field=field) is not None:
                return True
        return False

    def setter(self, field):
        """Return what gives the section a value of its own for a field, None giving the field back, and says why where the song
        cannot take it."""
        page = self._page
        return page.refusing(functools.partial(give_section_own, choices=self._choices, place=self._place, field=field))

    def field(self, field):
        """Return the field of something the section may be given of its own, of the kind that thing is."""
        if field in FADE_FIELDS:
            return fade_field(branch=self._branch, place=self._place, field=field)
        if field in NUMBERS_OF_SECTION:
            return self._own_number_field(field)
        if field == wizard_names.ARRANGER_CHORDS:
            return self._own_chords_field()
        if field == wizard_names.SONG_PLAN_RISES:
            return self._own_toggle_field(field)
        return self._own_choice_field(field)

    def _shown_from_above(self, *, field, own, usual):
        """Return what a field shows while the section was given nothing of its own: the value from above and where from."""
        if own is not None:
            return None
        origin = labels.MSG_WIZARD_SECTION_ORIGINS[field]
        return labels.MSG_WIZARD_VALUE_FROM.format(value=usual, origin=origin)

    def _cleared_by(self, *, field, own):
        """Return what lets a field the section was given a value of its own for be cleared back to the value from above."""
        if own is None:
            return {}
        set_own = self.setter(field)
        return dict(clear=functools.partial(set_own, None), clear_what=labels.MSG_WIZARD_SECTION_ORIGINS[field])

    def _own_number_field(self, field):
        """Return the field of a number the section may be given of its own: its Energy, shown as a gauge, or a tempo."""
        section = self._section()
        own = section.own(field=field)
        usual = section.from_plan(field=field)
        shown = self._shown_from_above(field=field, own=own, usual=usual)
        lowest, highest = NUMBERS_OF_SECTION[field]
        if field == wizard_names.SONG_PLAN_ENERGY:
            # Energy is a gauge, as Contrast and the players' gauges are, the plan's saying so after the number.
            place = own
            if own is None:
                place = usual
            shown = gauge_shown(place=place, lowest=lowest, highest=highest, said=shown)
        clear = self._cleared_by(field=field, own=own)
        return NumberField(page=self._page, label=labels.MSG_WIZARD_SECTION_OWN_LABELS[field], number=own, start=usual, shown=shown,
                           lowest=lowest, highest=highest, set=self.setter(field), **clear)

    def _own_chords_field(self):
        """Return the field of the chords the section may be given of its own, typed as degrees."""
        field = wizard_names.ARRANGER_CHORDS
        section = self._section()
        own = section.own(field=field)
        usual = section.from_plan(field=field)
        text = self._shown_from_above(field=field, own=own, usual=usual)
        typed = usual
        if own is not None:
            text = section.own_chords_typed()
            typed = text
        page = self._page
        ask = functools.partial(page.ask_text, title=messages.MSG_WIZARD_SECTION_CHORDS_PROMPT, value=typed, then=self.setter(field), is_name=True)
        clear = self._cleared_by(field=field, own=own)
        return Field(label=labels.MSG_WIZARD_SECTION_OWN_LABELS[field], value=lambda: text, enter=ask, **clear)

    def _own_toggle_field(self, field):
        """Return the field of something the section may switch on or off of its own, such as whether it rises."""
        section = self._section()
        own = section.own(field=field)
        on = own
        if own is None:
            on = section.from_plan(field=field)
        clear = self._cleared_by(field=field, own=own)
        return Toggle(label=labels.MSG_WIZARD_SECTION_OWN_LABELS[field], on=on, set=self.setter(field), **clear)

    def _own_choice_field(self, field):
        """Return the field of something the section may be given of its own from a list, the value from above first."""
        section = self._section()
        own = section.own(field=field)
        usual = section.from_plan(field=field)
        from_above = labels.MSG_WIZARD_FROM_ORIGIN.format(origin=labels.MSG_WIZARD_SECTION_ORIGINS[field])
        if field == wizard_limits.SHAPE_OF_SECTION:
            offered = section.shapes()
        else:
            offered = CHOICES_OF_SECTION[field]
        current = own
        if own is None:
            current = from_above
        pick = functools.partial(self._pick_own, field=field, from_above=from_above)
        clear = self._cleared_by(field=field, own=own)
        return ChoiceField(page=self._page, label=labels.MSG_WIZARD_SECTION_OWN_LABELS[field], choices=[from_above, *offered], current=current,
                           shown=self._shown_from_above(field=field, own=own, usual=usual), set=pick, **clear)

    def _pick_own(self, picked, *, field, from_above):
        """Give the section the value picked of its own, or give the field back to the value from above."""
        set_own = self.setter(field)
        if picked == from_above:
            set_own(None)
        else:
            set_own(picked)
