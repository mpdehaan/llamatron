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

from abc import ABC, abstractmethod
from typing import NamedTuple

from llamatron.grid.clip import Clip
from llamatron.strings.errors import ERR_NOT_A_CLIP


class Continuation(NamedTuple):
    """Where a generator carries on from when its Restart doesn't start it over with the clip: how far into its run the clip starts, in whole notes, how long the whole run lasts, and the state the same track's clip before left it in, or None."""

    offset: object
    span: object
    state: object


class ClipGenerator(ABC):
    """Makes a new Clip from an existing one, which is left unchanged.

    To write a generator, implement _generate. The new clip keeps the original's
    name, scale and note_length, and gets its own id. Degrees stay as degrees, so the
    new clip still follows whichever scale applies when it's rendered. A generator works on
    the clip's sounds, the tuples of music/sound.py, and clip.resolved_sounds() gives them
    with every length filled in, for one that needs to know how long each position is.
    """

    __slots__ = ()

    def generate(self, clip):
        """Return a new Clip made from this one."""
        if not isinstance(clip, Clip):
            raise ValueError(ERR_NOT_A_CLIP.format(value=clip))
        # A clip's list can be appended to directly, and reading it as sounds refuses anything that is no position.
        sounds, length = self._generate(clip)
        return Clip(
            name=clip.get_name(), sounds=sounds, scale=self._new_scale(clip), length=length,
            note_length=clip.get_note_length(), controls=clip.get_controls(),
        )

    def end_state(self):
        """Return the state the clip it last made left it in, for the same track's next clip to carry on from when its Restart says so. Most keep none."""
        return None

    def register_adds(self):
        """Return what the clip it last made adds to the registers, as (time from the clip's start, adds by register) in time order. Most generators add nothing."""
        return []

    def _new_scale(self, clip):
        """Return the new clip's scale, which is the original's unless a generator changes it."""
        return clip.get_scale()

    @abstractmethod
    def _generate(self, clip):
        """Return the new clip's list of sounds and its length."""
