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


from llamatron.generators.base import ClipGenerator
from llamatron.grid.positions import fit_to_length
from llamatron.music.sound import CHORD, HELD, HELD_SOUND, KIND, LENGTH, NOTES, PARTS, PHRASE, REST, Sound
from llamatron.support.length import Length
from llamatron.strings.errors import ERR_AUTO_RATCHET_NOT_A_LIST, ERR_BAD_COUNT

# A count of one leaves a note as it is, and a count can't be less than that.
UNCHANGED = 1


def divide(*, position, times):
    """Return a position that lasts 1/times as long."""
    if position[KIND] == CHORD:
        return Sound.chord([divide(position=note, times=times) for note in position[NOTES]])
    return Sound.with_length(position, Length.shared(position[LENGTH], times))


def _check_counts(counts):
    if not isinstance(counts, (list, tuple)) or not counts:
        raise ValueError(ERR_AUTO_RATCHET_NOT_A_LIST.format(value=counts))
    for count in counts:
        # bool is a subclass of int, but True is not a real count.
        if type(count) is not int or count < UNCHANGED:
            raise ValueError(ERR_BAD_COUNT.format(value=count))


class AutoRatchet(ClipGenerator):
    """Chops each note or chord into equal repeats, using the next count in a repeating cycle.

    With [1, 1, 4], the first two notes are unchanged, and the third becomes four adjacent
    notes that are each a quarter of its length. A chord uses one count and repeats as a
    whole, and rests don't use up a count. Every note still starts when it did before.
    """

    __slots__ = ('_counts', '_first', '_next')

    def __init__(self, counts, continuation=None):
        self.set_counts(counts)
        # Which count comes next: the first, or where the same track's clip before left off when its Restart carries on.
        self._first = 0 if continuation is None or continuation.state is None else continuation.state
        self._next = self._first

    def end_state(self):
        return self._next

    def get_counts(self):
        return self._counts

    def set_counts(self, counts):
        _check_counts(counts)
        self._counts = counts

    def _generate(self, clip):
        positions = clip.resolved_sounds()
        if clip.get_length() is not None:
            positions = fit_to_length(positions=positions, length=Length.exact(clip.get_length()))

        # Each clip starts from where it was handed, so that one generator makes the same clip every time.
        self._next = self._first
        counts = self._cycle()
        return self._ratcheted(positions=positions, counts=counts), clip.get_length()

    def _cycle(self):
        """Return the counts over and over, one for each note or chord in turn, from where it left off, noting each count used."""
        while True:
            count = self._counts[self._next % len(self._counts)]
            self._next = (self._next + 1) % len(self._counts)
            yield count

    def _ratcheted(self, *, positions, counts):
        """Return positions with each note or chord chopped by the next count, and rests left as they are."""
        result = []
        for position in positions:
            kind = position[KIND]
            if kind == REST:
                result.append(position)
            elif kind == HELD or kind == PHRASE:
                result.append(self._ratcheted_held(held=position, counts=counts))
            else:
                result += _chopped(position=position, count=next(counts))
        return result

    def _ratcheted_held(self, *, held, counts):
        """Return a held sound with its notes chopped, still held in the same place."""
        parts = held[PARTS] if held[KIND] == PHRASE else [held[HELD_SOUND]]
        return Sound.phrase(self._ratcheted(positions=parts, counts=counts), held[LENGTH])


def _chopped(*, position, count):
    """Return a note or chord as count adjacent equal repeats, or as it is for a count of one."""
    if count == UNCHANGED:
        return [position]
    return [divide(position=position, times=count)] * count

