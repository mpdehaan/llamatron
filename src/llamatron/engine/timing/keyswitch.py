# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Keyswitches as a render carries them: the slots a step asks for, and the notes a clip sends for them.

A keyswitch is a note a plugin reads as an order to change how it plays. A
pattern's step names slots of its track's instrument; playing the pattern gives SwitchedSlots,
which nothing between the pattern and the clip touches, no generator, scale or transposing; and
the clip's track turns each slot into the instrument's note, a SwitchNote, leaving out a slot the
instrument gives no note. The exporters' timing moves a SwitchNote with the note it belongs to,
by the clip's groove and its rushes and drags, and nothing else.
"""

from typing import NamedTuple


class SwitchedSlots(NamedTuple):
    """The slots one step's note is played with: when the note starts and ends as the pattern wrote it, in whole notes from the clip's start, and the slots."""

    start: object
    end: object
    slots: tuple

    def moved_by(self, time):
        """Return the same slots a time later, for a pass that starts there."""
        return SwitchedSlots(self.start + time, self.end + time, self.slots)

    def ending(self, end):
        """Return the same slots held until another end."""
        return SwitchedSlots(self.start, end, self.slots)


class SwitchNote(NamedTuple):
    """One keyswitch note a clip sends: when it starts and ends, in whole notes from the clip's start, before any groove, and its MIDI number."""

    start: object
    end: object
    midi_number: int
