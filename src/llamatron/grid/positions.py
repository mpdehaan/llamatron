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

"""Arithmetic on the positions a clip lists: notes, chords, rests, degrees and held sounds.

Every position has a length, in fractions of a whole note, and these functions cut positions
to a length and take pieces out of them, which is what sections, repeats and generators need.
The positions are sounds, the tuples of music/sound.py, and every length here is a pair of
whole numbers (support/length.py), since this is done for every note of a render.
"""

from llamatron.support.length import FINEST_LENGTH, ZERO, Length
from llamatron.support.rational import Rational
from llamatron.music.sound import CHORD, HELD, HELD_SOUND, KIND, LENGTH, NOTES, PARTS, PHRASE, REST, Sound



def exact_length(length):
    """Return a length as an exact fraction, a Rational, for what a clip is asked in numbers: its own length, a section's ends, a CC value's time.

    Lengths like 1/12 are slightly inexact as floats, so without this, three of them
    would fall just short of a quarter note and leave a tiny extra note or rest. A length
    that's already an exact fraction is returned as it is.
    """
    if type(length) is Rational and length.denominator <= FINEST_LENGTH:
        return length
    return Rational(length).limit_denominator(FINEST_LENGTH)


def cut_position(*, position, length):
    """Return a position that lasts no longer than length."""
    if Length.at_most(position[LENGTH], length):
        return position
    if position[KIND] == CHORD:
        return Sound.chord([cut_position(position=note, length=length) for note in position[NOTES]])
    # A held sound only has its place cut. Its sound is cut where the clip ends, when it's played.
    return Sound.with_length(position, length)


def fit_to_length(*, positions, length):
    """Return positions that last exactly length, cutting notes off or adding a final rest."""
    result = []
    remaining = length
    for position in positions:
        if not Length.is_positive(remaining):
            break
        result.append(cut_position(position=position, length=remaining))
        remaining = Length.subtract(remaining, Length.shorter(position[LENGTH], remaining))
    if Length.is_positive(remaining):
        result.append((REST, remaining))
    return result


def piece_of(*, position, offset, length):
    """Return the part of a position that starts offset into it and lasts length.

    A piece that is the whole position is the position itself.
    """
    own = position[LENGTH]
    if offset == ZERO and Length.at_most(own, length):
        return position
    kind = position[KIND]
    if kind == REST:
        return (REST, length)
    if kind == HELD or kind == PHRASE:
        rest_of_sound = sound_from(held=position, offset=offset)
        if rest_of_sound is None:
            return (REST, length)
        kind_left, sound_left = rest_of_sound
        return (kind_left, Length.shorter(Length.subtract(own, offset), length), sound_left)
    if kind == CHORD:
        pieces = [piece_of(position=note, offset=offset, length=length) for note in position[NOTES] if Length.less(offset, note[LENGTH])]
        return Sound.chord(pieces) if pieces else (REST, length)
    return Sound.with_length(position, Length.shorter(Length.subtract(own, offset), length))


def sound_from(*, held, offset):
    """Return what's left of a held sound or phrase from offset into it, as its kind and what it holds, or None if it's over by then."""
    if held[KIND] == HELD:
        sound = held[HELD_SOUND]
        remaining = [note[LENGTH] for note in _notes_of(sound) if Length.less(offset, note[LENGTH])]
        if not remaining:
            return None
        piece = piece_of(position=sound, offset=offset, length=Length.subtract(Length.longest(remaining), offset))
        return None if piece[KIND] == REST else (HELD, piece)
    parts = []
    start = ZERO
    for part in held[PARTS]:
        end = Length.add(start, part[LENGTH])
        if Length.less(offset, end):
            parts.append(part if Length.at_most(offset, start) else piece_of(position=part, offset=Length.subtract(offset, start), length=Length.subtract(end, offset)))
        start = end
    return (PHRASE, tuple(parts)) if parts else None


def _notes_of(sound):
    """Return the notes of a note or chord."""
    return sound[NOTES] if sound[KIND] == CHORD else [sound]
