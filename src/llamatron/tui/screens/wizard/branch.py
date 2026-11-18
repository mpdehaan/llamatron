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
"""A branch of the song wizard's tree: one part of the song a person may look at and change.

The wizard's page knows nothing of any one branch. It asks each branch for its name, the
branches under it and its fields, and draws the tree and the fields from the answers, so that a
branch is added, moved or split by changing the branches alone (who expects to
revise how the wizard is organized).
"""

from llamatron.strings import legends, marks
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.drawing import NOTHING
from llamatron.tui.screens.shared.field import ChoiceField, Field

# Where a picker opens, and what stepping picks, before anything is chosen.
FIRST_CHOICE = 0

# The key of the answer kept of whether a panel has a field that does something.
EDITABLE_ANSWER = 'editable'


class Branch:
    """One part of the wizard's tree. A subclass says what the part is called and what it holds."""

    __slots__ = ('_page',)

    def __init__(self, *, page):
        self._page = page

    def page(self):
        """Return the wizard's page, which shows this branch's dialogs and keeps the song's name."""
        return self._page

    def choices(self):
        """Return the choices of this run of the wizard, which every branch reads and changes."""
        return self._page.choices()

    def key(self):
        """Return what the page remembers the branch by, open or closed: its name, unless two branches share one."""
        return self.name()

    def name(self):
        """Return the branch's name in the tree."""
        raise NotImplementedError

    def title(self):
        """Return the heading over the branch's fields: its name in capitals, unless the branch says more."""
        return self.name().upper()

    def note(self):
        """Return a few words after the branch's name in the tree, such as what it waits for, or nothing."""
        return NOTHING

    def children(self):
        """Return the branches under this one, in order."""
        return []

    def fields(self):
        """Return the branch's fields, as a settings page's, made afresh each time."""
        return []

    def notes(self, width):
        """Return lines shown under the fields, such as an overview of what the branches under this one hold."""
        return []

    def choice_from_nothing(self, *, label, values, names, current, set_value):
        """Return a field that picks one of a list and starts with nothing chosen, as the genre and the subgenre do:
        it shows (choose) until then, and stepping it or opening its list starts from the first."""
        page = self.page()
        chosen = page.choosing(set_value)
        if current is not None:
            return ChoiceField(page=page, label=label, choices=values, names=names, current=current, shown=names[values.index(current)], set=chosen)

        def pick():
            page.ask(dialog=ChoiceDialog(title=label, options=names, current=FIRST_CHOICE), then=lambda place: chosen(values[place]))
        return Field(label=label, value=lambda: marks.MSG_WIZARD_CHOOSE, adjust=lambda offset: chosen(values[FIRST_CHOICE]), enter=pick, enter_what=legends.What.CHOOSE)

    def refusal(self):
        """Return why the cursor cannot move into the branch's fields yet, or None when it can."""
        return None

    def listens(self):
        """Return what Listen plays on this branch, as what it is called, the place of its section in the form and the player whose clip
        alone plays, None for everybody in the section; or None for a branch with nothing to hear."""
        return None

    # A branch that holds a list, or is one of a list, as the form and its sections: the page gives such a branch the tracker's keys for a list.

    def takes(self):
        """Return what draws another take of what the cursor is on in this branch's fields, a function of no arguments, or None where
        nothing there has takes."""
        return None

    def adds(self):
        """Return whether a new thing can be added from this branch."""
        return False

    def kinds_to_add(self):
        """Return the kinds of thing that can be added from here, which a picker offers."""
        return []

    def add(self, kind):
        """Add a new thing of a kind at the end of the list this branch holds or is one of."""
        raise NotImplementedError

    def insert(self, kind):
        """Put a new thing of a kind before this branch, which is one of a list."""
        raise NotImplementedError

    def is_listed(self):
        """Return whether the branch is one of a list, so that it can be copied, removed and moved."""
        return False

    def copy(self):
        raise NotImplementedError

    def remove(self):
        raise NotImplementedError

    def move(self, offset):
        """Move the branch earlier or later in its list, and return whether it moved."""
        raise NotImplementedError

    def can_be_edited(self):
        """Return whether any field of the branch does something, so that a branch only to be read takes no cursor."""
        # The legend asks at every key, and making a panel's fields may mean making the song, so the answer is kept with the choices.
        return self.choices().remembered(key=(EDITABLE_ANSWER, type(self).__name__, self.name()), compute=lambda: any(field.enter or field.adjust for field in self.fields()))
