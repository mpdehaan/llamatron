# noose6: a Python language and framework for producing MIDI clips.
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

"""Works out when each note in a clip plays, for renderers to write out."""

from fractions import Fraction

from src.chord import Chord
from src.note import Degree, Note, Rest

# A beat is a quarter note, which matches how MIDI and Live measure both time and tempo.
BEATS_PER_WHOLE_NOTE = 4
VELOCITY = 100


def _degree_to_note(position, scale):
    """Return a Note for a Degree, leaving anything else as it is."""
    if not isinstance(position, Degree):
        return position
    if scale is None:
        raise ValueError(f'{position!r} needs a scale, but the clip, scene and song have none')
    return position.to_note(scale)


def _sounding_notes(position):
    """Return {MIDI number: length} for one position in a clip."""
    # A clip's list can be appended to directly, so its contents are checked again here.
    if isinstance(position, Rest):
        return {}
    if isinstance(position, Note):
        return {position.midi_number: position.length}
    if isinstance(position, Chord):
        lengths = {}
        for note in position.notes:
            lengths[note.midi_number] = max(note.length, lengths.get(note.midi_number, 0))
        return lengths
    raise ValueError(f'expected a Note, Chord or Rest, got {position!r}')


def timed_notes(clip, scale):
    """Return a clip's notes as (start, end, MIDI number), and the clip's total length.

    Times are exact fractions of a whole note. This is where lengths and degrees are
    finally settled, as late as possible. Notes are cut off at the end of the clip.
    """
    notes = [_degree_to_note(position, scale) for position in clip.resolved_notes()]
    positions = [(_sounding_notes(position), position.length) for position in notes]
    if clip.length is None:
        clip_length = sum((Fraction(length) for _, length in positions), Fraction(0))
    else:
        clip_length = Fraction(clip.length)

    timed = []
    position_start = Fraction(0)
    for sounding_notes, position_length in positions:
        start = min(position_start, clip_length)
        for midi_number, note_length in sounding_notes.items():
            end = min(position_start + Fraction(note_length), clip_length)
            if end > start:
                timed.append((start, end, midi_number))
        position_start += Fraction(position_length)
    return timed, clip_length
