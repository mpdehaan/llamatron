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

"""What every page of one generator shares: its settings, found one way, and a value stored one way."""

from llamatron.tui.screens.shared.shows_named_item import ShowsNamedItem


class GeneratorEditor(ShowsNamedItem):
    """A page of one generator of the set: `settings()` is the generator's settings, and `store()` keeps one of them.

    SECTION, which every page of a named thing says, is the section of the generator's kind.
    """

    __slots__ = ()

    def settings(self):
        """Return the settings of the generator the page shows."""
        return self.document().generator(section=self.SECTION, name=self.item)

    def store(self, *, setting, value):
        """Keep one setting by its file name, checked as reading a file checks it, or None to leave it out of the file."""
        self.document().change(self.settings().set_setting, name=setting, value=value)
