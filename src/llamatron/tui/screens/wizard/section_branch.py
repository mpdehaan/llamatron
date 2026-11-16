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

from llamatron.strings.labels import MSG_WIZARD_BARS_LABEL, MSG_WIZARD_KIND_LABEL
from llamatron.tui.screens.shared.field import ChoiceField, Field, Toggle
from llamatron.tui.screens.wizard.branch import Branch

# What two sections of one name are told apart by: the section's number in the form and its name.
SECTION_KEY = '{number} {name}'
# Sections are counted from 1, as they are shown.
FIRST_SECTION_NUMBER = 1


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
        plays = choices.section_plays(place)
        return [*fields, *(Toggle(label=choices.role_title(role), on=role in plays, set=self.plays_setter(role)) for role in choices.roles_in())]

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
