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

from fractions import Fraction

from llamatron.note import _check_length
from llamatron.song import Clip, _Validated, exact_length


class PhraseFinder:
    """Finds where phrases probably end: straight after any long note or rest.

    Returns times in fractions of a whole note, not counting the very end of the clip. A
    length of 0.5 or more counts as long by default, which suits music mostly in quarters.
    """

    minimum_length = _Validated(_check_length)

    def __init__(self, minimum_length=0.5):
        self.minimum_length = minimum_length

    def analyze(self, clip):
        if not isinstance(clip, Clip):
            raise ValueError(f'expected a Clip, got {clip!r}')
        minimum = exact_length(self.minimum_length)
        total = clip.total_length()
        times = []
        now = Fraction(0)
        for position in clip.played_notes():
            length = exact_length(position.length)
            now += length
            if length >= minimum and now < total:
                times.append(now)
        return times
