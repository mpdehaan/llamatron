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

"""A scale the song names, like main: { root: F, type: minor }, for the song and scenes to use."""

from llamatron.composition.file_format import ACCIDENTALS, Accidental, ScaleSetting
from llamatron.composition.limits import MIN_DEGREE
from llamatron.composition.llama_data import LlamaData
from llamatron.composition.checks import reading
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.setting import Checked, check_settings, described
from llamatron.music.midi import HALF_STEPS_PER_OCTAVE
from llamatron.music.note import NOTE_NAMES, Note
from llamatron.music.scale import Scale, ScaleType
from llamatron.strings.errors import ERR_EXPECTED_ROOT_AND_TYPE, ERR_EXPECTED_ROOT_NOTE, ERR_UNKNOWN_SCALE_TYPE
from llamatron.support.revised import notes_change

# Scale type names, as error messages list them.
NAME_LIST_SEPARATOR = ', '
# A file can write a scale type with spaces, like natural minor, where its member name has underscores.
WORD_GAP = ' '
MEMBER_WORD_GAP = '_'


# Any octave does for spelling a scale's notes, since names don't change with the octave.
SPELLING_OCTAVE = 4


def note_names(*, root, half_steps):
    """Return the names of the notes a root and one octave of half steps make, like D E F G A B C."""
    start = Note(name=root, octave_number=SPELLING_OCTAVE)
    return [start.half_step(step).get_name() for step in half_steps]


class NamedScale(LlamaData):
    """A root note and a kind of scale, which the song keeps under a name of the user's choosing.

    The root and the kind are kept as the file writes them, like 'F' and 'minor', so that saving
    writes them back the same way.
    """

    __slots__ = ('_root', '_kind')

    def __init__(self, *, root, kind):
        self.note_change()
        self._root = root
        self._kind = kind

    @classmethod
    def from_data(cls, *, data, where, song=None):
        with reading(where):
            if not isinstance(data, dict) or set(data) != set(SETTINGS):
                raise InvalidValue(ERR_EXPECTED_ROOT_AND_TYPE.format(data=data))
            check_settings(settings=SETTINGS, data=data)
            return cls(root=data[ScaleSetting.ROOT], kind=data[ScaleSetting.TYPE])

    def to_data(self):
        return {ScaleSetting.ROOT: self._root, ScaleSetting.TYPE: self._kind}

    def get_root(self):
        """Return its root as the file writes it, like 'F#'."""
        return self._root

    def get_kind(self):
        """Return its type as the file writes it, like 'minor'."""
        return self._kind

    def scale_at(self, octave):
        """Return this scale with its root in an octave, in this project's numbering."""
        return Scale(root=Note(name=self._root, octave_number=octave), typ=self.get_scale_type())

    def get_scale_type(self):
        return ScaleType[_scale_type_member(self._kind)]

    def get_half_steps(self):
        """Return one octave of the scale as half steps above the root, starting with 0."""
        return self.get_scale_type().value

    def get_size(self):
        """Return how many notes the scale has in an octave, which is the highest degree before it wraps."""
        return len(self.get_half_steps())

    def degree_above(self, *, degree, octave, accidental, half_steps):
        """Return the degree, octave and accidental of the note this many half steps above a degree, for the piano roll's chord ghosts.

        A note on a scale note is that degree; one a half step above a scale note is that degree
        sharpened, or the next degree flattened when it's a half step below that; and a note that
        is neither, in a scale with a wide gap, is None, since no row can show it.
        """
        steps = self.get_half_steps()
        octaves_up, place = divmod(degree - MIN_DEGREE, len(steps))
        total = (octave + octaves_up) * HALF_STEPS_PER_OCTAVE + steps[place] + ACCIDENTALS.get(accidental, 0) + half_steps
        tone_octave, within = divmod(total, HALF_STEPS_PER_OCTAVE)
        below = max(index for index, step in enumerate(steps) if step <= within)
        if steps[below] == within:
            return below + MIN_DEGREE, tone_octave, None
        if within - steps[below] == 1:
            return below + MIN_DEGREE, tone_octave, Accidental.SHARP
        above = steps[below + 1] if below + 1 < len(steps) else HALF_STEPS_PER_OCTAVE
        if above - within == 1:
            octaves_more, place_above = divmod(below + 1, len(steps))
            return place_above + MIN_DEGREE, tone_octave + octaves_more, Accidental.FLAT
        return None

    def get_note_names(self):
        """Return the name of each degree's note, from the root up, spelled as the rest of the program spells them."""
        return note_names(root=self._root, half_steps=self.get_half_steps())

    def octave_of_degree(self, *, octave, place):
        """Return the octave a degree sounds in when the root is in an octave: the same one, or the next where the degree crosses C, since octaves are numbered from C."""
        root = Note(name=self._root, octave_number=SPELLING_OCTAVE)
        return octave + (root.get_midi_number() + self.get_half_steps()[place]) // HALF_STEPS_PER_OCTAVE - SPELLING_OCTAVE

    def copy(self):
        return NamedScale(root=self._root, kind=self._kind)

    # Changing the scale, which changes everything that plays in it.

    @notes_change
    def set_root(self, root):
        SETTINGS[ScaleSetting.ROOT].check(root)
        self._root = root

    @notes_change
    def set_kind(self, kind):
        SETTINGS[ScaleSetting.TYPE].check(kind)
        self._kind = kind


def is_root_note(text):
    """Return whether text names a root note, like F, C# or Bb."""
    return isinstance(text, str) and text in NOTE_NAMES


def is_scale_type(kind):
    """Return whether a file's scale type, like 'minor' or 'natural minor', is one llamatron knows."""
    return _scale_type_member(kind) in ScaleType.__members__


# Every scale type the file accepts, aliases like aeolian included, in the order the enum lists them.
SCALE_TYPE_NAMES = [member_name.lower() for member_name in ScaleType.__members__]


def scale_type_name(kind):
    """Return a scale type's name as a file writes it, like 'minor' for ScaleType.MINOR."""
    return kind.name.lower()


def scale_type_names():
    """Return every scale type's name as a file writes it, like 'minor', in alphabetical order."""
    return sorted(scale_type_name(ScaleType[member_name]) for member_name in ScaleType.__members__)


def scale_type_called(kind):
    """Return the ScaleType a file's scale type names, which is one is_scale_type accepted."""
    return ScaleType[_scale_type_member(kind)]


def _scale_type_member(kind):
    """Return the ScaleType member name a file's scale type means, so that 'natural minor' is NATURAL_MINOR."""
    return str(kind).strip().upper().replace(WORD_GAP, MEMBER_WORD_GAP)


def _check_root(root):
    if not is_root_note(root):
        raise InvalidValue(ERR_EXPECTED_ROOT_NOTE.format(root=root))


def _check_kind(kind):
    if not is_scale_type(kind):
        raise InvalidValue(ERR_UNKNOWN_SCALE_TYPE.format(kind=kind, names=NAME_LIST_SEPARATOR.join(scale_type_names())))


# A named scale's two settings, each described once, in the order they're written to a file. A scale needs both.
SETTINGS = described(
    Checked(name=ScaleSetting.ROOT, check=_check_root),
    Checked(name=ScaleSetting.TYPE, check=_check_kind),
)
