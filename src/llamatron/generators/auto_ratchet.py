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
from llamatron.held import Held, is_phrase, phrase
from llamatron.note import Rest
from llamatron.clip_grid import _Validated

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

        counts = _cycle(self.counts)
        return self._ratcheted(positions, counts), clip.length

    def _ratcheted(self, positions, counts):
        """Return positions with each note or chord chopped by the next count, and rests left as they are."""
        result = []
        for position in positions:
            if isinstance(position, Rest):
                result.append(position)
            elif isinstance(position, Held):
                result.append(self._ratcheted_held(position, counts))
            else:
                result += _chopped(position, next(counts))
        return result

    def _ratcheted_held(self, held, counts):
        """Return a held sound with its notes chopped, still held in the same place."""
        parts = held.sound if is_phrase(held.sound) else [held.sound]
        return Held(phrase(self._ratcheted(parts, counts)), held.length)


def _chopped(position, count):
    """Return a note or chord as count adjacent equal repeats, or as it is for a count of one."""
    if count == UNCHANGED:
        return [position]
    return [divide(position, count)] * count


def _cycle(counts):
    """Return the counts over and over, one for each note or chord in turn."""
    while True:
        yield from counts
