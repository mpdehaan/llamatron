# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A scale the song names, like main: { root: F, type: minor }, for the song and scenes to use."""

from llamatron.caching.revised import notes_change
from llamatron.model.file.checks import reading
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.objects.llama_data import LlamaData
from llamatron.model.schema import file_format, limits
from llamatron.model.schema.file_format import Accidental, ScaleSetting
from llamatron.model.schema.setting import check_settings, Checked, described
from llamatron.model.values import note, scale as scale_values
from llamatron.model.values.note import Note
from llamatron.model.values.scale import Scale, ScaleType
from llamatron.music_theory.fundamentals import intervals
from llamatron.user_strings import errors

# Scale type names, as error messages list them.
NAME_LIST_SEPARATOR = ', '
# A file can write a scale type with spaces, like natural minor, where its member name has underscores.
WORD_GAP = ' '
MEMBER_WORD_GAP = '_'




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
                raise InvalidValue(errors.ERR_EXPECTED_ROOT_AND_TYPE.format(data=data))
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
        octaves_up, place = divmod(degree - limits.MIN_DEGREE, len(steps))
        total = (octave + octaves_up) * intervals.HALF_STEPS_PER_OCTAVE + steps[place] + file_format.ACCIDENTALS.get(accidental, 0) + half_steps
        tone_octave, within = divmod(total, intervals.HALF_STEPS_PER_OCTAVE)
        below = 0
        for index, step in enumerate(steps):
            if step <= within:
                below = index
        if steps[below] == within:
            return below + limits.MIN_DEGREE, tone_octave, None
        if within - steps[below] == 1:
            return below + limits.MIN_DEGREE, tone_octave, Accidental.SHARP
        above = intervals.HALF_STEPS_PER_OCTAVE
        if below + 1 < len(steps):
            above = steps[below + 1]
        if above - within == 1:
            octaves_more, place_above = divmod(below + 1, len(steps))
            return place_above + limits.MIN_DEGREE, tone_octave + octaves_more, Accidental.FLAT
        return None

    def get_note_names(self):
        """Return the name of each degree's note, from the root up, spelled as the rest of the program spells them."""
        return scale_values.note_names(root=self._root, half_steps=self.get_half_steps())

    def octave_of_degree(self, *, octave, place):
        """Return the octave a degree sounds in when the root is in an octave: the same one, or the next where the degree crosses C, since octaves are numbered from C."""
        root = Note(name=self._root, octave_number=scale_values.SPELLING_OCTAVE)
        return octave + (root.get_midi_number() + self.get_half_steps()[place]) // intervals.HALF_STEPS_PER_OCTAVE - scale_values.SPELLING_OCTAVE

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
    return isinstance(text, str) and text in note.NOTE_NAMES


def is_scale_type(kind):
    """Return whether a file's scale type, like 'minor' or 'natural minor', is one llamatron knows."""
    return _scale_type_member(kind) in ScaleType.__members__


# Every scale type the file accepts, aliases like aeolian included, in the order the enum lists them.


def scale_type_name(kind):
    """Return a scale type's name as a file writes it, like 'minor' for ScaleType.MINOR."""
    return kind.name.lower()


def scale_type_names():
    """Return every scale type's name as a file writes it, like 'minor', in alphabetical order."""
    names = [scale_type_name(ScaleType[member_name]) for member_name in ScaleType.__members__]
    return sorted(names)


def scale_type_called(kind):
    """Return the ScaleType a file's scale type names, which is one is_scale_type accepted."""
    return ScaleType[_scale_type_member(kind)]


def _scale_type_member(kind):
    """Return the ScaleType member name a file's scale type means, so that 'natural minor' is NATURAL_MINOR."""
    return str(kind).strip().upper().replace(WORD_GAP, MEMBER_WORD_GAP)


def _check_root(root):
    if not is_root_note(root):
        raise InvalidValue(errors.ERR_EXPECTED_ROOT_NOTE.format(root=root))


def _check_kind(kind):
    if not is_scale_type(kind):
        raise InvalidValue(errors.ERR_UNKNOWN_SCALE_TYPE.format(kind=kind, names=NAME_LIST_SEPARATOR.join(scale_type_names())))


# A named scale's two settings, each described once, in the order they're written to a file. A scale needs both.
SETTINGS = described(
    Checked(name=ScaleSetting.ROOT, check=_check_root),
    Checked(name=ScaleSetting.TYPE, check=_check_kind),
)
