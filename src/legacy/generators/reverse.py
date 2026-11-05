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

from src.generators.base import ClipGenerator, fit_to_length


class Reverse(ClipGenerator):
    """Plays a clip backwards, last position first.

    If the clip has a set length, that whole length is reversed, so any silence at
    the end moves to the start. Each chord stays together as one position, so all
    of its notes still start at the same time.
    """

    def _generate(self, clip):
        if clip.length is None:
            return clip.notes[::-1], None
        return fit_to_length(clip.resolved_notes(), clip.length)[::-1], clip.length
