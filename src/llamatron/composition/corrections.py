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
"""The corrections offered when a set file holds a value that can't be used but has an allowed value near it.

A whole number outside its range has the nearest end of the range, a length that is too long has
the longest allowed, and a choice outside its fixed list has the default. Anything else wrong
with a file, like a name that doesn't exist or text where a number belongs, has no such value,
and the file is refused as it always was.

Reading a file stays strict: the first wrong value raises. When that value has an allowed value
near it, the error carries a Correction, which knows where in the file's data the value is and
what to put there. Setlist.from_data_corrected applies it and reads again, until the set reads
or a problem with no correction stops it, and returns the corrections made, for the tracker's
dialog or the command line to show before anything is opened. Nothing here changes a file.
"""

from llamatron.strings.errors import ERR_WHERE_WITHIN
from llamatron.strings.messages import MSG_CORRECTED, MSG_CORRECTED_SEVERAL, MSG_CORRECTED_TO_DEFAULT
from llamatron.strings.names import MSG_THE_FILE

# What nearest() answers for a value with no allowed value near it. None can't say so, since None is a value a file can hold.
NO_NEAREST_VALUE = object()
# What nearest() answers when the nearest allowed thing is to leave the setting out of the file, which gives it its default.
LEFT_OUT = object()
# A place with nothing before the setting's name.
NO_PLACE = ''


def place_without(*, where, name):
    """Return a place in a file without the setting's name at its end, for a line that names the setting itself.

    Some places end with the name, like "song (verse), tempo", some are the name alone, like
    "step_size" for one of the set's own settings, and some don't hold it, like "song (verse),
    track (bass)". A setting of the set itself is in the file, not in any part of it.
    """
    if where is None or where == name:
        return MSG_THE_FILE
    ending = ERR_WHERE_WITHIN.format(where=NO_PLACE, part=name)
    return where[:-len(ending)] if where.endswith(ending) else where


def changed_count(*, found, used):
    """Return how many values of a list a correction changes, or None for a correction of one value."""
    if not isinstance(found, list) or not isinstance(used, list):
        return None
    return sum(1 for before, after in zip(found, used) if before != after)


class Correction:
    """One value of a file's data that can't be used, and the allowed value to put in its place.

    holder is the part of the data that holds the value, under key. name is what a message calls
    the value: a setting, or a pattern's row. used is the value to put there, or LEFT_OUT to
    take the key out, so that the setting has its default. A correction of a list, like a
    pattern's row, changes every value of the list that needs it at once, and counts them.
    """

    __slots__ = ('_holder', '_key', '_name', '_found', '_used', '_where')

    def __init__(self, *, holder, key, name, found, used):
        self._holder = holder
        self._key = key
        self._name = name
        self._found = found
        self._used = used
        self._where = None

    def apply(self):
        """Put the allowed value in the data, or take the setting out of it."""
        if self._used is LEFT_OUT:
            del self._holder[self._key]
        else:
            self._holder[self._key] = self._used

    def set_place(self, where):
        """Note where in the file the value is, as the error that carries this correction says it."""
        self._where = where

    def get_name(self):
        return self._name

    def get_found(self):
        return self._found

    def get_used(self):
        return self._used

    def get_count(self):
        """Return how many values of a list this changes, or None when it changes one value."""
        return changed_count(found=self._found, used=self._used)

    def get_place(self):
        """Return where in the file the value is, without the value's own name."""
        return place_without(where=self._where, name=self._name)

    def described(self):
        """Return one line saying where the value is, what was found and what is used in its place."""
        count = self.get_count()
        if count is not None:
            return MSG_CORRECTED_SEVERAL.format(where=self.get_place(), name=self._name, count=count)
        if self._used is LEFT_OUT:
            return MSG_CORRECTED_TO_DEFAULT.format(where=self.get_place(), name=self._name, found=self._found)
        return MSG_CORRECTED.format(where=self.get_place(), name=self._name, found=self._found, used=self._used)
