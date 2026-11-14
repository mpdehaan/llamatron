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
"""The field of one end of a range of octaves, which the track editor and the voice leading editor share, shown and typed in the set's octave labels."""

from llamatron.strings.legends import MSG_WHOLE_RANGE_WHAT, What
from llamatron.tui.screens.field import Field
from llamatron.tui.screens.shared import octave_moved


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
        enter_what=What.EDIT, clear=lambda: set_octave(default), clear_what=MSG_WHOLE_RANGE_WHAT,
    )
