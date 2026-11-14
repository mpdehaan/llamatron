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

"""A column of the grid a song renders into: one track's clips."""

from llamatron.composition.checks import check_drum, check_fluidsynth, check_gm_sound, check_mute, check_name
from llamatron.strings.errors import ERR_COLUMN_IN_A_GRID
from llamatron.strings.reprs import REPR_CLIP_COLUMN


class ClipColumn:
    """A column of the grid a song renders into, which is one track's clips. Its id is None unless it's in a grid.

    A muted column still has its clips, so a renderer writes them, but Live starts with the
    track switched off. It's for tracks that other tracks grab notes from. Whether the track is a
    drum track and the General MIDI sound of its instrument are for the General MIDI export, which
    puts drums on channel 10 and gives every other track its sound, and whether its instrument plays
    through FluidSynth is for the WAV export, which plays only those tracks through FluidSynth.
    """

    __slots__ = ('_id', '_name', '_mute', '_drum', '_gm_sound', '_fluidsynth')

    def __init__(self, *, name=None, mute=False, drum=False, gm_sound=None, fluidsynth=False):
        check_name(name)
        check_mute(mute)
        check_drum(drum)
        check_gm_sound(gm_sound)
        check_fluidsynth(fluidsynth)
        self._id = None
        self._name = name
        self._mute = mute
        self._drum = drum
        self._gm_sound = gm_sound
        self._fluidsynth = fluidsynth

    def get_id(self):
        return self._id

    def set_id(self, new_id):
        """Give the column its id as it joins a grid. A column joins only one grid, so a second id is refused."""
        if self._id is not None:
            raise ValueError(ERR_COLUMN_IN_A_GRID.format(column=self))
        self._id = new_id

    def get_name(self):
        return self._name

    def set_name(self, name):
        check_name(name)
        self._name = name

    def get_mute(self):
        return self._mute

    def set_mute(self, mute):
        check_mute(mute)
        self._mute = mute

    def is_drum(self):
        return self._drum

    def get_gm_sound(self):
        """Return the General MIDI sound of the track's instrument, 1 to 128, or None for none."""
        return self._gm_sound

    def plays_through_fluidsynth(self):
        """Return whether the track's instrument plays through FluidSynth, which the WAV export plays."""
        return self._fluidsynth

    def __repr__(self):
        return REPR_CLIP_COLUMN.format(name=self._name, mute=self._mute, drum=self._drum, gm_sound=self._gm_sound, id=self._id)
