# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""How keyswitches are written on screen: a note in the set's octave labels with its MIDI number, a slot's name, and a step's keyswitches in words."""

from llamatron.composition import file_format, instrument as instrument_values
from llamatron.music import midi, note as note_values
from llamatron.strings import marks

# The room a slot's note takes at the right of its row, in both keyswitch dialogs.
KEYSWITCH_NOTE_WIDTH = 12


def keyswitch_note_text(*, setlist, note):
    """Return a keyswitch's MIDI note as the tracker writes it, its name in the set's octave labels and its number, like C0 (24)."""
    name = note_values.SHARP_NAMES[note % midi.HALF_STEPS_PER_OCTAVE] + str(setlist.shown_octave(note // midi.HALF_STEPS_PER_OCTAVE))
    return marks.MSG_KEYSWITCH_NOTE.format(name=name, number=note)


def keyswitches_of(instrument):
    """Return an instrument's ten slots, or ten empty ones when there is no instrument to ask."""
    return [instrument_values.NO_KEYSWITCH] * file_format.KEYSWITCH_SLOT_COUNT if instrument is None else instrument.get_keyswitches()


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
