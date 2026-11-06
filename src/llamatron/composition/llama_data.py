# llamatron: a Python language and framework for producing MIDI clips.
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

"""The base class for everything a song file stores."""


MSG_NEEDS_TO_DATA = '{kind} needs a to_data() method'
MSG_NEEDS_FROM_DATA = '{kind} needs a from_data() class method'


class LlamaData:
    """Something stored in a song file, which can turn itself into file data and back.

    to_data() returns the object's settings as plain data, in the song file's format: dictionaries,
    lists, text, numbers, true or false, and None. from_data() is a class method that builds the
    object from that data, checks it, and raises SongFileError for anything wrong, naming where in
    the file the problem is. A setting the data leaves out gets its default, so that a file from an
    older version still loads.

    Every subclass defines both, and a test checks that they do. Objects that contain others call
    their parts' methods, so a song saves and loads itself, and nothing else needs to know how an
    object is stored.
    """

    __slots__ = ()

    def to_data(self):
        """Return this object's settings as plain data in the song file's format."""
        raise NotImplementedError(MSG_NEEDS_TO_DATA.format(kind=type(self).__name__))

    @classmethod
    def from_data(cls, data, where, song=None):
        """Return an object built from plain data, or raise SongFileError if the data is wrong.

        where names the place in the file, like "scene 2", for error messages. song is the song
        being read, for objects that need to check names that other parts of the file define.
        """
        raise NotImplementedError(MSG_NEEDS_FROM_DATA.format(kind=cls.__name__))
