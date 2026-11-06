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

from dataclasses import replace

from llamatron.chord import Chord
from llamatron.generators.base import ClipGenerator, exact_length, fit_to_length
from llamatron.note import Rest
from llamatron.song import _Validated

# A count of one leaves a note as it is, and a count can't be less than that.
UNCHANGED = 1
MSG_NOT_A_LIST = 'expected a list of counts, got {value!r}'
MSG_BAD_COUNT = 'invalid count: {value!r} (must be a positive integer)'


def divide(position, times):
    """Return a position that lasts 1/times as long."""
    if isinstance(position, Chord):
        return Chord([divide(note, times) for note in position.notes])
    return replace(position, length=exact_length(position.length) / times)


def _check_counts(counts):
    if not isinstance(counts, (list, tuple)) or not counts:
        raise ValueError(MSG_NOT_A_LIST.format(value=counts))
    for count in counts:
        # bool is a subclass of int, but True is not a real count.
        if type(count) is not int or count < UNCHANGED:
            raise ValueError(MSG_BAD_COUNT.format(value=count))


class AutoRatchet(ClipGenerator):
    """Chops each note or chord into equal repeats, using the next count in a repeating cycle.

    With [1, 1, 4], the first two notes are unchanged, and the third becomes four adjacent
    notes that are each a quarter of its length. A chord uses one count and repeats as a
    whole, and rests don't use up a count. Every note still starts when it did before.
    """

    __slots__ = ('_counts',)

    counts = _Validated(_check_counts)

    def __init__(self, counts):
        self.counts = counts

    def _generate(self, clip):
        positions = clip.resolved_notes()
        if clip.length is not None:
            positions = fit_to_length(positions, clip.length)

        result = []
        played = 0
        for position in positions:
            if isinstance(position, Rest):
                result.append(position)
                continue
            count = self.counts[played % len(self.counts)]
            played += 1
            if count == UNCHANGED:
                result.append(position)
            else:
                result += [divide(position, count)] * count
        return result, clip.length
