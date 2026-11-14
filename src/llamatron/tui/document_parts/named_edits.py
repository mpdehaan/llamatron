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
"""The Document's edits to anything that has a name: renaming, copying, deleting, moving and sorting take the section the thing is in, and so does asking which names a section has.

A pattern, a scale, an arp, an AutoRatchet, a chain, a groove, a song and a track are each a
named item of a section, and the set and the song edit every section the same way. So these five
edits are written once and take the section, where each kind had a method of its own before.
The little that differs by kind is here too, in one place: the current song follows its rename
and moves on when it's deleted, a factory groove can be copied into the set's own, and a track's
copy stands beside the track with its clips. Adding differs for every kind, since each new thing
starts with something else, so each kind keeps its own add.
"""

from llamatron.composition.file_format import Section
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.sections import SONG_SECTIONS
from llamatron.strings.errors import ERR_LAST_SONG
from llamatron.composition.naming import copy_name

# The place of the song before a deleted one, which becomes current, and the first place, for when the first song was deleted.
ONE_BEFORE = 1
FIRST_PLACE = 0


class NamedEdits:
    """Renaming, copying, deleting, moving and sorting the named items of any section, each through the set's or the song's own methods.

    It holds no data of its own: it works on what Document keeps, through `self._setlist`,
    `self.song()` and `self._change(method, ...)`, which makes one change through an object's own
    method and notes it.
    """

    __slots__ = ()

    def _owner_of(self, section):
        """Return the object that holds a section: the song for its tracks and registers, otherwise the set."""
        return self.song() if section in SONG_SECTIONS else self._setlist

    def names_of(self, section):
        """Return the names in a section, in order: the song's for its tracks, the set's otherwise, with the factory grooves before the set's own."""
        if section == Section.GROOVES:
            return self._setlist.get_groove_names()
        return self._owner_of(section).get_item_names(section)

    def has_named(self, *, section, name):
        """Return whether a section has an item of a name, a factory groove among the grooves."""
        return name in self.names_of(section)

    def rename_named(self, *, section, old, new):
        """Rename an item of a section, which changes every reference to it by name. A renamed song stays current."""
        self._change(self._owner_of(section).rename_item, section=section, old=old, new=new)
        if section == Section.SONGS and old == self._current:
            self._current = new

    def copy_named(self, *, section, name):
        """Add a copy of an item of a section and return the copy's name.

        The copy goes at the end of the section, except a track's, which stands right after the
        track with a copy of each of its clips. A groove can be a factory groove, whose copy is
        one of the set's own.
        """
        if section == Section.GROOVES:
            return self._copy_groove(name)
        if section == Section.TRACKS:
            return self._copy_track(name)
        owner = self._owner_of(section)
        new = copy_name(name=name, taken=owner.get_item_names(section))
        self._change(owner.copy_item, section=section, name=name, new=new)
        return new

    def _copy_groove(self, name):
        new = copy_name(name=name, taken=self._setlist.get_groove_names())
        self._change(self._setlist.add_item, section=Section.GROOVES, name=new, item=self._setlist.get_groove(name).copy())
        return new

    def _copy_track(self, name):
        new = copy_name(name=name, taken=self.song().get_track_names())
        self._change(self.song().copy_track, name=name, new=new)
        return new

    def delete_named(self, *, section, name):
        """Delete an item of a section. Whoever asks has checked that nothing uses it.

        A deleted track takes its clips with it and stops any clip grabbing from it. The last
        song can't be deleted, because there's always a current song, and deleting the current
        song makes the one before it current.
        """
        if section == Section.SONGS:
            self._delete_song(name)
        else:
            self._change(self._owner_of(section).remove_item, section=section, name=name)
        # The last instrument leaves nothing to play through, so deleting it turns real-time playback off (the user's design of 2026-11-09).
        if section == Section.INSTRUMENTS and not self._setlist.get_instrument_names() and self._setlist.is_real_time():
            self._change(self._setlist.set_real_time, False)

    def _delete_song(self, name):
        names = self.song_names()
        if len(names) <= 1:
            raise InvalidValue(ERR_LAST_SONG)
        self._change(self._setlist.remove_item, section=Section.SONGS, name=name)
        if name == self._current:
            self.select_song(self.song_names()[max(names.index(name) - ONE_BEFORE, FIRST_PLACE)])

    def move_named(self, *, section, place, offset):
        """Move an item up or down its section, and return whether it moved."""
        if not self._owner_of(section).move_item(section=section, place=place, offset=offset):
            return False
        self.changed()
        return True

    def sort_named(self, section):
        """Put a section's items in order of their names, for good."""
        self._change(self._owner_of(section).sort_items, section)

    def move_generator(self, *, place, offset):
        """Move a generator up or down the Generators page's list, every kind on one list, and return whether it moved."""
        pairs = self._setlist.ordered_generators()
        moved = place + offset
        if not 0 <= moved < len(pairs):
            return False
        self._change(self._setlist.move_generator, place=place, offset=offset)
        return True
