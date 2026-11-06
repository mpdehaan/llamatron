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

"""What a track has played, for another track's grab steps to take notes from."""

from llamatron.renderers.timing import timed_events


class GrabSource:
    """The notes a finished clip starts, by when they start, like the Cirklon's note grab."""

    def __init__(self, clip):
        events, _ = timed_events(clip, clip.scale)
        self._onsets = {}
        for start, _, number, _ in events:
            self._onsets.setdefault(start, set()).add(number)
        self._times = sorted(self._onsets)

    def note_at(self, time):
        """Return the MIDI number of the note most recently started at or before a time, or None.

        A chord gives its lowest note. Chords are built upward from the root, so that's the root
        for now, but inversions would need to change this.
        """
        started = [moment for moment in self._times if moment <= time]
        return min(self._onsets[started[-1]]) if started else None
