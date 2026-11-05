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

from dataclasses import dataclass
from enum import Enum

from llamatron.note import Note


class ScaleType(Enum):
    """Each value is one octave of the scale, as half steps above the root."""

    # Major and its modes. IONIAN is another name for MAJOR, and AEOLIAN and
    # NATURAL_MINOR are other names for MINOR.
    MAJOR = (0, 2, 4, 5, 7, 9, 11)
    IONIAN = MAJOR
    DORIAN = (0, 2, 3, 5, 7, 9, 10)
    PHRYGIAN = (0, 1, 3, 5, 7, 8, 10)
    LYDIAN = (0, 2, 4, 6, 7, 9, 11)
    MIXOLYDIAN = (0, 2, 4, 5, 7, 9, 10)
    MINOR = (0, 2, 3, 5, 7, 8, 10)
    AEOLIAN = MINOR
    NATURAL_MINOR = MINOR
    LOCRIAN = (0, 1, 3, 5, 6, 8, 10)

    # Other major and minor scales. MELODIC_MINOR is the ascending form.
    HARMONIC_MINOR = (0, 2, 3, 5, 7, 8, 11)
    MELODIC_MINOR = (0, 2, 3, 5, 7, 9, 11)
    HARMONIC_MAJOR = (0, 2, 4, 5, 7, 8, 11)

    # Pentatonic and blues
    MAJOR_PENTATONIC = (0, 2, 4, 7, 9)
    MINOR_PENTATONIC = (0, 3, 5, 7, 10)
    BLUES = (0, 3, 5, 6, 7, 10)
    MAJOR_BLUES = (0, 2, 3, 4, 7, 9)

    # Symmetric scales
    CHROMATIC = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11)
    WHOLE_TONE = (0, 2, 4, 6, 8, 10)
    WHOLE_HALF_DIMINISHED = (0, 2, 3, 5, 6, 8, 9, 11)
    HALF_WHOLE_DIMINISHED = (0, 1, 3, 4, 6, 7, 9, 10)

    # Jazz and other popular scales
    LYDIAN_DOMINANT = (0, 2, 4, 6, 7, 9, 10)
    ALTERED = (0, 1, 3, 4, 6, 8, 10)
    BEBOP_DOMINANT = (0, 2, 4, 5, 7, 9, 10, 11)
    PHRYGIAN_DOMINANT = (0, 1, 4, 5, 7, 8, 10)
    HUNGARIAN_MINOR = (0, 2, 3, 6, 7, 8, 11)
    DOUBLE_HARMONIC = (0, 1, 4, 5, 7, 8, 11)


@dataclass(frozen=True)
class Scale:
    """A scale that runs upward from its root to the top of the MIDI range.

    Every note in the scale has the same length as the root.
    """

    root: Note
    typ: ScaleType

    def __post_init__(self):
        if not isinstance(self.root, Note):
            raise ValueError(f'expected a Note, got {self.root!r}')
        if not isinstance(self.typ, ScaleType):
            raise ValueError(f'expected a ScaleType, got {self.typ!r}')
