# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The field of one end of a range of octaves, which the track editor and the voice leading editor share, shown and typed in the set's octave labels."""

from llamatron.tui.screens.shared.field import Field
from llamatron.tui.screens.shared.shared import octave_moved
from llamatron.user_strings import legends


def octave_field(*, page, label, current, lowest, highest, default, set_octave):
    """Return a field for one end of a range of octaves, a track's or a voice leading's, shown and typed in the set's octave labels and kept from crossing the other end."""
    song = page.document().song()

    def within(octave):
        return max(min(octave, highest()), lowest())
    return Field(
        label=label, value=lambda: song.shown_octave(current()),
        adjust=lambda offset: set_octave(within(octave_moved(octave=current(), offset=offset))),
        enter=lambda: page.ask_number(title=label, value=song.shown_octave(current()), then=lambda shown: set_octave(song.stored_octave(shown)),
                                      low=song.shown_octave(lowest()), high=song.shown_octave(highest())),
        enter_what=legends.What.EDIT, clear=lambda: set_octave(default), clear_what=legends.MSG_WHOLE_RANGE_WHAT,
    )
