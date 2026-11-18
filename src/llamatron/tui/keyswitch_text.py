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
"""How keyswitches are written on screen: a note in the set's octave labels with its MIDI number, a slot's name, and a step's keyswitches in words."""

from llamatron.composition.file_format import KEYSWITCH_SLOT_COUNT
from llamatron.composition.instrument import NO_KEYSWITCH
from llamatron.music import midi
from llamatron.music.note import SHARP_NAMES
from llamatron.strings import marks

# The room a slot's note takes at the right of its row, in both keyswitch dialogs.
KEYSWITCH_NOTE_WIDTH = 12


def keyswitch_note_text(*, setlist, note):
    """Return a keyswitch's MIDI note as the tracker writes it, its name in the set's octave labels and its number, like C0 (24)."""
    name = SHARP_NAMES[note % midi.HALF_STEPS_PER_OCTAVE] + str(setlist.shown_octave(note // midi.HALF_STEPS_PER_OCTAVE))
    return marks.MSG_KEYSWITCH_NOTE.format(name=name, number=note)


def keyswitches_of(instrument):
    """Return an instrument's ten slots, or ten empty ones when there is no instrument to ask."""
    return [NO_KEYSWITCH] * KEYSWITCH_SLOT_COUNT if instrument is None else instrument.get_keyswitches()


def slot_name(*, keyswitches, slot):
    """Return what a slot is called: its name where the instrument gives it one, and its number otherwise."""
    name = keyswitches[slot].name
    return marks.MSG_KEYSWITCH_SLOT_NAMED.format(slot=slot) if name is None else name


def slots_in_words(*, keyswitches, slots):
    """Return a step's keyswitches as a list in words, each by its name or its number."""
    return marks.MSG_KEYSWITCH_SEPARATOR.join(slot_name(keyswitches=keyswitches, slot=slot) for slot in slots)


def shown_name(keyswitch):
    """Return a slot's name as a list shows it, (none) where it has none."""
    return marks.MSG_NONE_SHOWN if keyswitch.name is None else keyswitch.name
