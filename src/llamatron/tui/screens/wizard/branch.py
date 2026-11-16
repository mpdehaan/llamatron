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
branch is added, moved or split by changing the branches alone (the user's ask, who expects to
revise how the wizard is organized).
"""

from llamatron.tui.drawing import NOTHING


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

    def refusal(self):
        """Return why the cursor cannot move into the branch's fields yet, or None when it can."""
        return None

    # A branch that holds a list, or is one of a list, as the form and its sections: the page gives such a branch the tracker's keys for a list.

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
        return any(field.enter or field.adjust for field in self.fields())
