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
"""One section of a song's named objects, in the order the file lists them, with the same operations for every kind."""

from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.llama_data import data_as_kept, data_built_anew
from llamatron.strings.errors import ERR_NAME_TAKEN, ERR_NO_SUCH_ITEM, ERR_SONG_NAME_NOT_TEXT
from llamatron.support.revised import notes_change, Revised

FIRST_PLACE = 0


def _name_for_sorting(pair):
    return str(pair[0]).lower()


def moved_in_list(*, items, place, offset):
    """Return a list with one item moved up or down, or None if that would go past either end."""
    target = place + offset
    if not FIRST_PLACE <= place < len(items) or not FIRST_PLACE <= target < len(items):
        return None
    result = list(items)
    result.insert(target, result.pop(place))
    return result


class NamedItems(Revised):
    """The patterns, tracks, scales, chains, generators of one kind or registers of a song: items by name, in order.

    Names are unique within a section, and the label, like pattern, names the kind in messages.
    A section the file leaves out is unwritten: it has no items, and saving leaves it out too.
    Filling it in makes it an empty section that saving writes. Every change checks what it's
    given and raises InvalidValue, leaving the section as it was.
    """

    __slots__ = ('_label', '_items')

    def __init__(self, *, label, items=None):
        self.note_change()
        self._label = label
        self._items = None if items is None else dict(items)

    def is_written(self):
        """Return whether the file had this section, even an empty one."""
        return self._items is not None

    @notes_change
    def fill_in(self):
        """Make an unwritten section an empty one, so that saving writes it."""
        if self._items is None:
            self._items = {}

    def to_data(self):
        return self.data_from(data_built_anew)

    def kept_data(self):
        """Return the section's data put together from the data each item keeps, which is shared and never changed."""
        return self.data_from(data_as_kept)

    def data_from(self, part_data):
        """Return the section's data, each item's taken with part_data: built anew, or as the item keeps it."""
        return {name: part_data(item) for name, item in self._all().items()}

    def same_item(self, *, name, data):
        """Return the item with a name if the data it keeps is this data, or None: the item that reading this data again would only build again."""
        item = self._all().get(name)
        return item if item is not None and item.kept_data() == data else None

    def _all(self):
        return self._items or {}

    # Reading.

    def has(self, name):
        return name in self._all()

    def get(self, name):
        """Return the item with a name, or raise InvalidValue if there's none. One lookup, since the tracker asks for a pattern for every cell it draws."""
        try:
            return self._all()[name]
        except KeyError:
            raise InvalidValue(ERR_NO_SUCH_ITEM.format(label=self._label, name=name)) from None

    def find(self, name):
        """Return the item with a name, or None if there's none."""
        return self._all().get(name)

    def names(self):
        """Return the names, in the section's order."""
        return list(self._all())

    def items(self):
        """Return (name, item) pairs, in the section's order."""
        return list(self._all().items())

    def values(self):
        """Return the items, in the section's order."""
        return list(self._all().values())

    # Changing. Each change keeps the order of everything else.

    @notes_change
    def add(self, *, name, item, after=None):
        """Add an item at the end, or right after another item."""
        self._check_new_name(name)
        pairs = self.items()
        place = len(pairs) if after is None else self._place_of(after) + 1
        pairs.insert(place, (name, item))
        self._items = dict(pairs)

    @notes_change
    def insert(self, *, name, item, place):
        """Add an item at a place in the order, before the item that was there."""
        self._check_new_name(name)
        pairs = self.items()
        pairs.insert(place, (name, item))
        self._items = dict(pairs)

    @notes_change
    def replace(self, *, name, item):
        """Put a new item under an existing name, keeping its place."""
        self._check(name)
        self._items[name] = item

    @notes_change
    def remove(self, name):
        self._check(name)
        del self._items[name]

    @notes_change
    def rename(self, *, old, new):
        """Rename an item, keeping its place."""
        self._check(old)
        if new != old:
            self._check_new_name(new)
        self._items = {(new if name == old else name): item for name, item in self._items.items()}

    @notes_change
    def move(self, *, place, offset):
        """Move an item up or down, and return whether it moved, which it can't past either end."""
        moved = moved_in_list(items=self.items(), place=place, offset=offset)
        if moved is None:
            return False
        self._items = dict(moved)
        return True

    @notes_change
    def sort(self):
        """Put the items in alphabetical order of name, ignoring case."""
        self._items = dict(sorted(self._all().items(), key=_name_for_sorting))

    def _place_of(self, name):
        return self.names().index(name)

    def _check(self, name):
        if not self.has(name):
            raise InvalidValue(ERR_NO_SUCH_ITEM.format(label=self._label, name=name))

    def _check_new_name(self, name):
        if not isinstance(name, str):
            raise InvalidValue(ERR_SONG_NAME_NOT_TEXT.format(name=name))
        if self.has(name):
            raise InvalidValue(ERR_NAME_TAKEN.format(label=self._label, name=name))
