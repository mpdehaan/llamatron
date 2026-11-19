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

"""A MIDI note as its name and octave, shown and typed: C3 is note 36, as a drum pattern writes its notes."""

from llamatron.music import note as note_values
from llamatron.strings import marks
from llamatron.tui.keys import SHARP_CHARACTER

NOTES_IN_OCTAVE = 12
LOWEST_NOTE = 0
HIGHEST_NOTE = 127
SHARP = SHARP_CHARACTER
FLAT = 'b'
HALF_STEPS_OF_LETTER = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
HALF_STEPS_OF_MARK = {SHARP: 1, FLAT: -1}


def note_shown(note):
    """Return a MIDI note as its name and octave, a black key as a sharp."""
    return marks.MSG_NOTE_NAME_SHOWN.format(name=note_values.SHARP_NAMES[note % NOTES_IN_OCTAVE], octave=note // NOTES_IN_OCTAVE)


def note_typed(text):
    """Return the MIDI note typed as a letter, a sharp or a flat where there is one, and an octave, such as C3, f#4 or Bb2, or None for
    text that is no note there is."""
    text = text.strip()
    if not text or text[0].upper() not in HALF_STEPS_OF_LETTER:
        return None
    rest = text[1:]
    mark = 0
    if rest[:1] in HALF_STEPS_OF_MARK and not rest[:1].isdigit():
        mark = HALF_STEPS_OF_MARK[rest[0]]
        rest = rest[1:]
    if not rest.isdigit():
        return None
    note = int(rest) * NOTES_IN_OCTAVE + HALF_STEPS_OF_LETTER[text[0].upper()] + mark
    return note if LOWEST_NOTE <= note <= HIGHEST_NOTE else None
