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

"""A section of the wizard's form: its kind, how long it lasts and who plays in it; it can be copied, removed and moved."""

from llamatron.composition.limits import MAX_NAME_LENGTH, MAX_TEMPO, MIN_TEMPO
from llamatron.macro_composer.arranger import CHORDS
from llamatron.macro_composer.joins import LEAVES
from llamatron.macro_composer.song_plan import ENERGY, HIGHEST_ENERGY, LOWEST_ENERGY, NOT_AT_ALL, RISES, ROOT_OF_PLACE, SETUP, TEMPO_END_OF_PLACE, TEMPO_OF_PLACE, TYPE_OF_PLACE
from llamatron.macro_composer.wizard_choices import LEAVES_AS_JOIN, SCALE_TYPES, SHAPE_OF_SECTION, chords_as_text
from llamatron.music.note import ROOT_NAMES
from llamatron.strings.labels import (
    MSG_WIZARD_BARS_LABEL, MSG_WIZARD_FROM_ORIGIN, MSG_WIZARD_FROM_PLAN, MSG_WIZARD_KIND_LABEL, MSG_WIZARD_SECTION_ORIGINS, MSG_WIZARD_SECTION_OWN_LABELS, MSG_WIZARD_SECTION_ROLE_LABEL,
    MSG_WIZARD_VALUE_FROM,
)
from llamatron.strings.legends import MSG_FROM_PLAN_WHAT
from llamatron.strings.marks import MSG_WIZARD_ROLE_FROM_PLAN
from llamatron.strings.messages import MSG_WIZARD_LISTEN_SECTION, MSG_WIZARD_SECTION_CHORDS_PROMPT
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.tui.screens.shared.field import ChoiceField, Field, NumberField, Toggle
from llamatron.tui.screens.wizard.branch import Branch

# What two sections of one name are told apart by: the section's number in the form and its name.
SECTION_KEY = '{number} {name}'
# Sections are counted from 1, as they are shown.
FIRST_SECTION_NUMBER = 1


# The numbers a section can be given of its own, each with its range, and the choices of each field chosen from a list.
NUMBERS_OF_SECTION = {ENERGY: (LOWEST_ENERGY, HIGHEST_ENERGY), TEMPO_OF_PLACE: (MIN_TEMPO, MAX_TEMPO), TEMPO_END_OF_PLACE: (MIN_TEMPO, MAX_TEMPO)}
CHOICES_OF_SECTION = {LEAVES: list(LEAVES_AS_JOIN), SETUP: [NOT_AT_ALL], ROOT_OF_PLACE: list(ROOT_NAMES), TYPE_OF_PLACE: list(SCALE_TYPES)}


class SectionBranch(Branch):
    """A section of the form, by its place in the form."""

    __slots__ = ('_place',)

    def __init__(self, *, page, place):
        super().__init__(page=page)
        self._place = place

    def key(self):
        return SECTION_KEY.format(number=self._place + FIRST_SECTION_NUMBER, name=self.name())

    def name(self):
        return self.choices().section_labels()[self._place]

    def fields(self):
        choices = self.choices()
        page = self.page()
        place = self._place
        kinds = choices.section_kinds()
        fields = [ChoiceField(page=page, label=MSG_WIZARD_KIND_LABEL, choices=kinds, current=choices.section_kind(place),
                              set=page.choosing(lambda kind: choices.set_section_kind(place=place, kind=kind)))]
        lengths = choices.bars_offered(place)
        if len(lengths) > 1:
            fields.append(ChoiceField(page=page, label=MSG_WIZARD_BARS_LABEL, choices=lengths, names=[str(bars) for bars in lengths], current=choices.section_bars(place),
                                      set=page.choosing(lambda bars: choices.set_section_bars(place=place, bars=bars))))
        else:
            # A held section, or one whose parts fill only its usual length, shows its bars and takes no key.
            fields.append(Field(label=MSG_WIZARD_BARS_LABEL, value=lambda: choices.section_bars(place)))
        if choices.section_has_role(place):
            fields.append(self.role_field())
        fields += [self.own_field(field) for field in choices.section_own_fields(place)]
        plays = choices.section_plays(place)
        return [*fields, *(Toggle(label=choices.role_title(role), on=role in plays, set=self.plays_setter(role)) for role in choices.roles_in() if role in choices.roles_shown())]

    # What a section of a planned song is given of its own: each field shows what the section takes and where from until it is given, and Bksp gives it back.

    def own_setter(self, field):
        """Return what gives the section a value of its own for a field, None giving the field back, and says why where the song cannot take it."""
        choices = self.choices()
        page = self.page()
        place = self._place

        def set_own(value):
            try:
                page.choosing(lambda wanted: choices.set_section_own(place=place, field=field, value=wanted))(value)
            except ValueError as problem:
                page.refuse(str(problem))
        return set_own

    def own_field(self, field):
        choices = self.choices()
        page = self.page()
        place = self._place
        own = choices.section_own(place=place, field=field)
        usual = choices.section_from_plan(place=place, field=field)
        origin = MSG_WIZARD_SECTION_ORIGINS[field]
        shown = MSG_WIZARD_VALUE_FROM.format(value=usual, origin=origin) if own is None else None
        label = MSG_WIZARD_SECTION_OWN_LABELS[field]
        set_own = self.own_setter(field)
        clear = dict(clear=lambda: set_own(None), clear_what=origin) if own is not None else {}
        if field in NUMBERS_OF_SECTION:
            lowest, highest = NUMBERS_OF_SECTION[field]
            return NumberField(page=page, label=label, number=own, start=usual, shown=shown, lowest=lowest, highest=highest, set=set_own, **clear)
        if field == CHORDS:
            def ask():
                page.ask(dialog=PromptDialog(title=MSG_WIZARD_SECTION_CHORDS_PROMPT, value=chords_as_text(own) if own is not None else usual, max_length=MAX_NAME_LENGTH), then=set_own)
            return Field(label=label, value=lambda: shown if own is None else chords_as_text(own), enter=ask, **clear)
        if field == RISES:
            return Toggle(label=label, on=usual if own is None else own, set=set_own, **clear)
        from_above = MSG_WIZARD_FROM_ORIGIN.format(origin=origin)
        offered = choices.section_shapes(place) if field == SHAPE_OF_SECTION else CHOICES_OF_SECTION[field]
        return ChoiceField(page=page, label=label, choices=[from_above, *offered], current=from_above if own is None else own, shown=shown,
                           set=lambda picked: set_own(None if picked == from_above else picked), **clear)

    def listens(self):
        return MSG_WIZARD_LISTEN_SECTION.format(number=self._place + FIRST_SECTION_NUMBER, name=self.name()), self._place, None

    def role_field(self):
        """Return the field of what the answering player does in the section: the plan's, marked as the plan's, until the section is given
        its own from a list, and Bksp gives the section back to the plan."""
        choices = self.choices()
        page = self.page()
        place = self._place
        ways = choices.ways_beside()
        way = choices.section_role(place)
        own = choices.section_role_is_own(place)
        chosen = page.choosing(lambda picked: choices.set_section_role(place=place, way=None if picked == MSG_WIZARD_FROM_PLAN else picked))

        def to_plan():
            chosen(MSG_WIZARD_FROM_PLAN)
        return ChoiceField(page=page, label=MSG_WIZARD_SECTION_ROLE_LABEL.format(player=choices.role_title(choices.answered_by())), choices=[MSG_WIZARD_FROM_PLAN, *ways],
                           current=way if own else MSG_WIZARD_FROM_PLAN, shown=way if own else MSG_WIZARD_ROLE_FROM_PLAN.format(way=way), set=chosen,
                           clear=to_plan if own else None, clear_what=MSG_FROM_PLAN_WHAT)

    def plays_setter(self, role):
        """Return what has a player play in the section or sit it out, refusing to leave the section with nobody."""
        choices = self.choices()
        page = self.page()
        place = self._place

        def set_plays(on):
            try:
                page.choosing(lambda wanted: choices.set_section_plays(place=place, role=role, on=wanted))(on)
            except ValueError as problem:
                page.refuse(str(problem))
        return set_plays

    # A section is one of a list, the form's.

    def adds(self):
        return True

    def add(self, kind):
        """Put a new section of a kind at the end of the form, as A does on any row of a list."""
        self.choices().add_section(place=len(self.choices().form_sections()), kind=kind)

    def insert(self, kind):
        """Put a new section of a kind before this one, as insert does on Arrange."""
        self.choices().add_section(place=self._place, kind=kind)

    def kinds_to_add(self):
        return self.choices().section_kinds()

    def is_listed(self):
        return True

    def copy(self):
        self.choices().copy_section(self._place)

    def remove(self):
        self.choices().remove_section(self._place)

    def move(self, offset):
        return self.choices().move_section(place=self._place, offset=offset)
