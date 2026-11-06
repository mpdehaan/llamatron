# llamatron: a Python language and framework for producing MIDI clips.
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

from llamatron.song import POSITION_TYPES, Clip, cut_position as _cut, exact_length, fit_to_length

__all__ = ['ClipGenerator', '_cut', 'exact_length', 'fit_to_length']

MSG_NOT_A_CLIP = 'expected a Clip, got {value!r}'
MSG_NOT_A_POSITION = 'expected a Note, Chord, Rest or Degree, got {value!r}'


class ClipGenerator(ABC):
    """Makes a new Clip from an existing one, which is left unchanged.

    To write a generator, implement _generate. The new clip keeps the original's
    name, scale and note_length, and gets its own id. Degrees stay as degrees, so the
    new clip still follows whichever scale applies when it's rendered. Use
    clip.resolved_notes() if a generator needs to know how long each position is.
    """

    __slots__ = ()

    def generate(self, clip):
        """Return a new Clip made from this one."""
        if not isinstance(clip, Clip):
            raise ValueError(MSG_NOT_A_CLIP.format(value=clip))
        # A clip's list can be appended to directly, so its contents are checked again here.
        for position in clip.notes:
            if not isinstance(position, POSITION_TYPES):
                raise ValueError(MSG_NOT_A_POSITION.format(value=position))
        notes, length = self._generate(clip)
        return Clip(
            name=clip.name, notes=notes, scale=self._new_scale(clip), length=length,
            note_length=clip.note_length, controls=clip.controls,
        )

    def _new_scale(self, clip):
        """Return the new clip's scale, which is the original's unless a generator changes it."""
        return clip.scale

    @abstractmethod
    def _generate(self, clip):
        """Return the new clip's list of notes and its length."""
