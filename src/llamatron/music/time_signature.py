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
"""Time signatures, like 4/4 or 6/8: how many beats make a bar, and which note counts as a beat.

A time signature changes nothing about when notes play. The pattern editor uses it to show which
steps start a beat, and the exporters write it so that a DAW draws its bars in the right places.
"""

import re

from llamatron.support.rational import Rational
from llamatron.strings.errors import ERR_BAD_TIME_SIGNATURE
from llamatron.strings.reprs import REPR_TIME_SIGNATURE

# How a time signature is written, in a file and on screen: beats over the note that is one beat.
TIME_SIGNATURE_TEXT = '{beats}/{unit}'
_WRITTEN = re.compile(r'(\d+)/(\d+)')
# How many beats a bar can hold, and the notes that can be a beat, as the bottom number names them.
MIN_BEATS = 1
MAX_BEATS = 32
UNITS = (1, 2, 4, 8, 16, 32)
# The units as a message lists them.
UNITS_LISTED = ', '.join(str(unit) for unit in UNITS)
# In compound meters like 6/8, 9/8 and 12/8 the beat is a dotted note, three of the bottom
# number's notes, so a bar of 6/8 is counted in two, not six.
COMPOUND_GROUP = 3
# A bar of 3/8 or 3/4 is counted in three, so compound meters start at six.
SMALLEST_COMPOUND = 6
# A whole number has this denominator.
WHOLE = 1


def is_time_signature(text):
    """Return whether text is a time signature, written like 4/4, with beats and a note value in range."""
    match = _WRITTEN.fullmatch(text) if isinstance(text, str) else None
    if match is None:
        return False
    beats = int(match.group(1))
    unit = int(match.group(2))
    return MIN_BEATS <= beats <= MAX_BEATS and unit in UNITS


class TimeSignature:
    """An immutable time signature: a number of beats over the note that is one beat, like 4 over 4."""

    __slots__ = ('_beats', '_unit')

    def __init__(self, *, beats, unit):
        if not is_time_signature(TIME_SIGNATURE_TEXT.format(beats=beats, unit=unit)):
            raise ValueError(ERR_BAD_TIME_SIGNATURE.format(lowest=MIN_BEATS, highest=MAX_BEATS, units=UNITS_LISTED, value=TIME_SIGNATURE_TEXT.format(beats=beats, unit=unit)))
        self._beats = beats
        self._unit = unit

    @classmethod
    def from_text(cls, text):
        """Return the time signature written as text, like 6/8, or raise ValueError if it isn't one."""
        if not is_time_signature(text):
            raise ValueError(ERR_BAD_TIME_SIGNATURE.format(lowest=MIN_BEATS, highest=MAX_BEATS, units=UNITS_LISTED, value=text))
        beats, unit = text.split(TIME_SIGNATURE_TEXT.format(beats='', unit=''))
        return cls(beats=int(beats), unit=int(unit))

    def get_beats(self):
        """Return the top number: how many of the bottom number's notes make a bar."""
        return self._beats

    def get_unit(self):
        """Return the bottom number: the note that is counted, as a fraction of a whole note."""
        return self._unit

    def to_text(self):
        return TIME_SIGNATURE_TEXT.format(beats=self._beats, unit=self._unit)

    def is_compound(self):
        """Return whether the beat is a dotted note, as in 6/8, where the bar is counted in two."""
        return self._beats >= SMALLEST_COMPOUND and self._beats % COMPOUND_GROUP == 0

    def beat_length(self):
        """Return how long one beat lasts, in whole notes: the bottom number's note, or three of them in a compound meter."""
        notes = COMPOUND_GROUP if self.is_compound() else 1
        return Rational(notes, self._unit)

    def bar_length(self):
        """Return how long one bar lasts, in whole notes."""
        return Rational(self._beats, self._unit)

    def starts_a_beat(self, time):
        """Return whether a time, in whole notes from the start of a bar, falls exactly on a beat."""
        return (Rational(time) / self.beat_length()).denominator == WHOLE

    def __eq__(self, other):
        return isinstance(other, TimeSignature) and (self._beats, self._unit) == (other._beats, other._unit)

    def __hash__(self):
        return hash((self._beats, self._unit))

    def __repr__(self):
        return REPR_TIME_SIGNATURE.format(beats=self._beats, unit=self._unit)
