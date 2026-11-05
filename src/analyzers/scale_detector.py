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

from fractions import Fraction

from src.note import Note
from src.renderers.timing import timed_notes
from src.scale import Scale, ScaleType
from src.song import Clip

DEFAULT_TYPES = (ScaleType.MAJOR, ScaleType.MINOR)


class ScaleDetector:
    """Guesses a clip's scale from how long its notes sound.

    The best scale has the most sounding time inside it. C major and A minor share the same
    notes, so ties go to the scale whose root is the clip's last note, since tunes tend to
    finish at home, and then to the one whose root sounds longest. The root is the nearest
    one at or below the clip's lowest note. This looks at the clip's notes, so degrees need
    the clip to have a scale already.
    """

    def __init__(self, types=DEFAULT_TYPES):
        if not types or not all(isinstance(typ, ScaleType) for typ in types):
            raise ValueError(f'expected a list of ScaleType, got {types!r}')
        self.types = tuple(types)

    def analyze(self, clip):
        """Return the best-fitting Scale, or raise ValueError if the clip has no notes."""
        if not isinstance(clip, Clip):
            raise ValueError(f'expected a Clip, got {clip!r}')
        notes, _ = timed_notes(clip, clip.scale)
        if not notes:
            raise ValueError('finding a scale needs a clip with notes in it')
        times = {}
        for start, end, pitch in notes:
            times[pitch % 12] = times.get(pitch % 12, Fraction(0)) + (end - start)
        last = max(notes)[2] % 12

        def fit(choice):
            root, typ = choice
            in_scale = sum(
                time for pitch, time in times.items()
                if (pitch - root) % 12 in typ.value
            )
            return (in_scale, root == last, times.get(root, 0))

        root, typ = max(
            ((root, typ) for root in range(12) for typ in self.types), key=fit,
        )
        lowest = min(pitch for _, _, pitch in notes)
        root_pitch = lowest - (lowest - root) % 12
        if root_pitch < 0:
            root_pitch += 12
        return Scale(Note.from_midi_number(root_pitch), typ)
