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

"""A scale the song names, like main: { root: F, type: minor }, for the song and scenes to use."""

from llamatron.composition.file_format import ScaleSetting
from llamatron.composition.llama_data import LlamaData
from llamatron.composition.checks import reading
from llamatron.composition.invalid_value import InvalidValue
from llamatron.note import NOTE_NAMES, Note
from llamatron.scale import Scale, ScaleType

MSG_EXPECTED_ROOT_AND_TYPE = 'expected a root and a type, like {{ root: F, type: minor }}, got {data!r}'
MSG_EXPECTED_ROOT_NOTE = 'expected a root note like F or Bb, got {root!r}'
MSG_UNKNOWN_SCALE_TYPE = 'unknown scale type {kind!r}, expected one of: {names}'
# Scale type names, as error messages list them.
NAME_LIST_SEPARATOR = ', '
# A file can write a scale type with spaces, like natural minor, where its member name has underscores.
WORD_GAP, MEMBER_WORD_GAP = ' ', '_'


class NamedScale(LlamaData):
    """A root note and a kind of scale, which the song keeps under a name of the user's choosing.

    The root and the kind are kept as the file writes them, like 'F' and 'minor', so that saving
    writes them back the same way.
    """

    __slots__ = ('_root', '_kind')

    def __init__(self, root, kind):
        self._root = root
        self._kind = kind

    @classmethod
    def from_data(cls, data, where, song=None):
        with reading(where):
            if not isinstance(data, dict) or set(data) != {ScaleSetting.ROOT, ScaleSetting.TYPE}:
                raise InvalidValue(MSG_EXPECTED_ROOT_AND_TYPE.format(data=data))
            root, kind = data[ScaleSetting.ROOT], data[ScaleSetting.TYPE]
            if not is_root_note(root):
                raise InvalidValue(MSG_EXPECTED_ROOT_NOTE.format(root=root))
            if not is_scale_type(kind):
                raise InvalidValue(MSG_UNKNOWN_SCALE_TYPE.format(kind=kind, names=NAME_LIST_SEPARATOR.join(scale_type_names())))
            return cls(root, kind)

    def to_data(self):
        return {ScaleSetting.ROOT: self._root, ScaleSetting.TYPE: self._kind}

    def scale_at(self, octave):
        """Return this scale with its root in an octave, in this project's numbering."""
        return Scale(Note(self._root, octave), ScaleType[_scale_type_member(self._kind)])


def is_root_note(text):
    """Return whether text names a root note, like F, C# or Bb."""
    return isinstance(text, str) and text in NOTE_NAMES


def is_scale_type(kind):
    """Return whether a file's scale type, like 'minor' or 'natural minor', is one llamatron knows."""
    return _scale_type_member(kind) in ScaleType.__members__


def scale_type_name(kind):
    """Return a scale type's name as a file writes it, like 'minor' for ScaleType.MINOR."""
    return kind.name.lower()


def scale_type_names():
    """Return every scale type's name as a file writes it, like 'minor', in alphabetical order."""
    return sorted(scale_type_name(ScaleType[member_name]) for member_name in ScaleType.__members__)


def _scale_type_member(kind):
    """Return the ScaleType member name a file's scale type means, so that 'natural minor' is NATURAL_MINOR."""
    return str(kind).strip().upper().replace(WORD_GAP, MEMBER_WORD_GAP)
